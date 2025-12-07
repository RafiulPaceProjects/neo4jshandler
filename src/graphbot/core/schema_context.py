"""Generate schema context for the Neo4j database to help with query generation."""
import asyncio
import logging
from typing import Any
from graphbot.handlers import Neo4jHandler
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


class SchemaContext:
    """Manages database schema information for context-aware query generation."""
    
    def __init__(self, neo4j_handler: Neo4jHandler):
        """Initialize with Neo4j handler."""
        self.neo4j = neo4j_handler
        self._schema_cache = None
        self._semantic_summary = None  # New: Store AI-generated summary
        self._sampled_values = {} # Store manually inspected values to enrich context
    
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
            self._raw_schema = insights['raw_schema']
            self._update_schema_cache()

    def add_sampled_values(self, label: str, property_name: str, values: list[Any]):
        """
        Enrich schema context with sampled values for a specific property.
        """
        key = f"{label}.{property_name}"
        self._sampled_values[key] = values
        self._update_schema_cache()

    def _update_schema_cache(self):
        """Rebuild the cached schema string with all available info."""
        parts = []
        if self._semantic_summary:
            parts.append(f"Database Semantic Summary: {self._semantic_summary}")
        
        if hasattr(self, '_raw_schema'):
            parts.append("Technical Schema:")
            parts.append(self._raw_schema)
            
        if self._sampled_values:
            parts.append("\n### Sampled Property Values (Ground Truth):")
            for key, vals in self._sampled_values.items():
                val_str = ", ".join(map(str, vals[:5]))
                parts.append(f"- {key}: [{val_str}, ...]")
                
        self._schema_cache = "\n\n".join(parts)
    
    def get_schema_context(self) -> str:
        """Synchronous wrapper for get_schema_context_async."""
        return asyncio.run(self.get_schema_context_async())

    async def get_schema_context_async(self) -> str:
        """
        Get a formatted schema context string for use in prompts asynchronously.
        
        Returns:
            String describing the database schema
        """
        if self._schema_cache:
            return self._schema_cache
        
        # Fallback to legacy extraction if no cache/insights provided
        return await self._generate_legacy_schema_async()

    async def _generate_legacy_schema_async(self) -> str:
        """Original schema extraction logic (fallback) updated for async."""
        if not self.neo4j.driver:
             return "Database schema information unavailable (Not connected)."

        try:
            async with self.neo4j.driver.session(database=self.neo4j.database) as session:
                # Optimization: Run these in parallel or batch if possible, but for now keep sequential
                # Get node labels
                result = await session.run("MATCH (n) RETURN DISTINCT labels(n) as labels LIMIT 100")
                labels_set = set()
                async for record in result:
                    labels_set.update(record["labels"])
                labels = sorted(list(labels_set))
                
                # Get relationship types
                result = await session.run("MATCH ()-[r]->() RETURN DISTINCT type(r) as type LIMIT 100")
                rel_types_list = [record["type"] async for record in result]
                rel_types = sorted(list(set(rel_types_list)))
                
                # Get sample properties for each label
                label_props = {}
                for label in labels:
                    # Optimized query: get sample of properties from 3 nodes
                    result = await session.run(f"MATCH (n:`{label}`) RETURN n LIMIT 3")
                    props_summary = {}
                    async for record in result:
                        node = record["n"]
                        # In async driver, node might be accessed differently or same as sync
                        # The node object structure should be similar (Node graph object)
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
                        result = await session.run(f"MATCH (n:`{label}`) RETURN count(n) as count")
                        count_rec = await result.single()
                        count = count_rec["count"]
                    except Exception as e:
                        logger.debug(f"Count query failed: {e}")
                        count = "unknown"
                        
                    context_parts.append(f"  - {label} ({count} nodes): properties include {props_str}")
                
                context_parts.append("\nRelationship Types:")
                for rel_type in rel_types:
                    result = await session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count")
                    count_rec = await result.single()
                    count = count_rec["count"]
                    # Try to find the pattern
                    result = await session.run(f"MATCH (a)-[r:`{rel_type}`]->(b) RETURN DISTINCT labels(a)[0] as from_label, labels(b)[0] as to_label LIMIT 5")
                    patterns = set()
                    async for record in result:
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
        self._sampled_values = {}
