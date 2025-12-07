"""Generate schema context for the Neo4j database to help with query generation."""
from graphbot.handlers import Neo4jHandler
from rich.console import Console

console = Console()


class SchemaContext:
    """Manages database schema information for context-aware query generation."""
    
    def __init__(self, neo4j_handler: Neo4jHandler):
        """Initialize with Neo4j handler."""
        self.neo4j = neo4j_handler
        self._schema_cache = None
        self._semantic_summary = None  # New: Store AI-generated summary
    
    def set_insights(self, insights: dict):
        """
        Inject semantic insights from InsightAgent.
        
        Args:
            insights: Dictionary containing summary and raw schema
        """
        if insights.get("summary"):
            self._semantic_summary = insights["summary"]
            
        # Use the raw schema string from insight agent if available to avoid re-fetching
        if insights.get("raw_schema"):
            # We wrap it with our context format
            self._schema_cache = f"Database Semantic Summary: {self._semantic_summary}\n\nTechnical Schema:\n{insights['raw_schema']}"
    
    def get_schema_context(self) -> str:
        """
        Get a formatted schema context string for use in prompts.
        
        Returns:
            String describing the database schema
        """
        if self._schema_cache:
            return self._schema_cache
        
        # Fallback to legacy extraction if no cache/insights provided
        return self._generate_legacy_schema()

    def _generate_legacy_schema(self) -> str:
        """Original schema extraction logic (fallback)."""
        try:
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                # Optimization: Run these in parallel or batch if possible, but for now keep sequential
                # Get node labels
                result = session.run("MATCH (n) RETURN DISTINCT labels(n) as labels LIMIT 100")
                labels_set = set()
                for record in result:
                    labels_set.update(record["labels"])
                labels = sorted(list(labels_set))
                
                # Get relationship types
                result = session.run("MATCH ()-[r]->() RETURN DISTINCT type(r) as type LIMIT 100")
                rel_types = sorted([record["type"] for record in result])
                
                # Get sample properties for each label
                label_props = {}
                for label in labels:
                    # Optimized query: get sample of properties from 3 nodes
                    # Using CALL {} IN TRANSACTIONS or APOC could speed this up for huge DBs
                    # But LIMIT 3 is generally fast enough
                    result = session.run(f"MATCH (n:`{label}`) RETURN n LIMIT 3")
                    props_summary = {}
                    for record in result:
                        node = record["n"]
                        for key, value in dict(node).items():
                            if key not in props_summary:
                                props_summary[key] = []
                            if len(props_summary[key]) < 3:
                                props_summary[key].append(repr(value))
                    
                    # Format properties with examples
                    formatted_props = []
                    for key, examples in props_summary.items():
                        example_str = ", ".join(examples[:3])
                        formatted_props.append(f"{key} (e.g. {example_str})")
                    
                    label_props[label] = formatted_props[:10]  # Limit to first 10 properties
                
                # Build context string
                context_parts = ["Database Schema:"]
                if self._semantic_summary:
                    context_parts.insert(0, f"Domain Summary: {self._semantic_summary}\n")

                context_parts.append("\nNode Labels (entities):")
                for label in labels:
                    props = label_props.get(label, [])
                    props_str = "; ".join(props) if props else "no properties"
                    # Fast count optimization
                    try:
                        # Try optimized count store first (Neo4j 4.3+)
                        result = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count")
                        count = result.single()["count"]
                    except:
                        count = "unknown"
                        
                    context_parts.append(f"  - {label} ({count} nodes): properties include {props_str}")
                
                context_parts.append("\nRelationship Types:")
                for rel_type in rel_types:
                    result = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count")
                    count = result.single()["count"]
                    # Try to find the pattern
                    result = session.run(f"MATCH (a)-[r:`{rel_type}`]->(b) RETURN DISTINCT labels(a)[0] as from_label, labels(b)[0] as to_label LIMIT 5")
                    patterns = set()
                    for record in result:
                        from_label = record["from_label"] or "Node"
                        to_label = record["to_label"] or "Node"
                        patterns.add(f"({from_label})-[{rel_type}]->({to_label})")
                    
                    if patterns:
                        for pattern in patterns:
                            context_parts.append(f"  - {rel_type} ({count} total): {pattern}")
                    else:
                        context_parts.append(f"  - {rel_type} ({count} relationships)")
                
                self._schema_cache = "\n".join(context_parts)
                return self._schema_cache
                
        except Exception as e:
            console.print(f"[yellow]Warning: Could not generate schema context: {str(e)}[/yellow]")
            return "Database schema information unavailable."
    
    def clear_cache(self):
        """Clear the schema cache to force refresh."""
        self._schema_cache = None
        self._semantic_summary = None

