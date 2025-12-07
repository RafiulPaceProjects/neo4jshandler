"""Insight Agent for automatic database mapping and analysis."""
from typing import Dict, Any, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from graphbot.handlers import Neo4jHandler
from graphbot.services import GeminiService

console = Console()


class InsightAgent:
    """
    Background agent that maps the database structure and generates
    semantic insights using a worker model.
    """
    
    def __init__(self, gemini_service: GeminiService):
        """Initialize with Gemini service to access worker model."""
        self.gemini = gemini_service
        self.worker_model = self.gemini.get_worker_model()
    
    def analyze_database(self, neo4j_handler: Neo4jHandler) -> Dict[str, Any]:
        """
        Analyze database structure and content.
        
        Args:
            neo4j_handler: Active Neo4j connection handler
            
        Returns:
            Dictionary containing schema info, summary, and suggested questions
        """
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("[cyan]Mapping database structure...", total=3)
                
                # Step 1: Raw Schema Extraction
                raw_schema = self._extract_raw_schema(neo4j_handler)
                progress.advance(task)
                
                # Step 2: Semantic Summary Generation
                progress.update(task, description="[cyan]Generating semantic summary...")
                summary = self._generate_summary(raw_schema)
                progress.advance(task)
                
                # Step 3: Question Suggestion
                progress.update(task, description="[cyan]Brainstorming questions...")
                questions = self._suggest_questions(raw_schema, summary)
                progress.advance(task)
                
            return {
                "raw_schema": raw_schema,
                "summary": summary,
                "suggested_questions": questions
            }
            
        except Exception as e:
            console.print(f"[bold red]❌ Insight generation failed: {str(e)}[/bold red]")
            return {
                "raw_schema": "Schema unavailable",
                "summary": "Could not analyze database.",
                "suggested_questions": []
            }

    def _extract_raw_schema(self, neo4j: Neo4jHandler) -> str:
        """Extract detailed schema stats from Neo4j."""
        # Reuse the logic similar to SchemaContext but optimized for analysis
        schema_parts = []
        
        try:
            with neo4j.driver.session(database=neo4j.database) as session:
                # Node Labels & Counts
                result = session.run("CALL db.labels() YIELD label RETURN label")
                labels = [r["label"] for r in result]
                
                schema_parts.append("## Node Labels")
                for label in labels:
                    # Use escaped label names to handle special chars
                    try:
                        count_res = session.run(f"MATCH (n:`{label}`) RETURN count(n) as c")
                        count = count_res.single()["c"]
                    except Exception:
                        count = 0
                        
                    if count > 0:
                        props_res = session.run(f"MATCH (n:`{label}`) RETURN keys(n) as k LIMIT 1")
                        props_rec = props_res.single()
                        prop_list = props_rec["k"] if props_rec else []
                        schema_parts.append(f"- **{label}**: {count:,} nodes. Properties: {', '.join(prop_list[:5])}")
                    else:
                        schema_parts.append(f"- **{label}**: 0 nodes.")

                # Relationships
                schema_parts.append("\n## Relationships")
                result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
                rels = [r["relationshipType"] for r in result]
                
                for r_type in rels:
                    try:
                        count_res = session.run(f"MATCH ()-[r:`{r_type}`]->() RETURN count(r) as c")
                        count = count_res.single()["c"]
                    except Exception:
                        count = 0
                    schema_parts.append(f"- **{r_type}**: {count:,} connections.")
                    
        except Exception as e:
            console.print(f"[yellow]Warning: Schema extraction error: {str(e)}[/yellow]")
            return f"Error extracting schema: {str(e)}"
            
        return "\n".join(schema_parts)

    def _generate_summary(self, schema_text: str) -> str:
        """Use worker model to summarize the domain."""
        prompt = f"""You are a Database Analyst. Analyze the following Neo4j schema and provide a concise, high-level summary of what this database represents.
        
        Identify:
        1. The main domain (e.g., "Healthcare", "Movies", "Finance").
        2. The core entities and how they relate.
        3. Any interesting data volume stats.
        
        Schema:
        {schema_text}
        
        Output a short paragraph (max 3 sentences)."""
        
        try:
            response = self.worker_model.generate_content(prompt)
            if hasattr(response, 'text'):
                return response.text.strip()
            return "Summary generation failed (No text response)."
        except Exception as e:
            console.print(f"[yellow]Warning: Summary generation error: {str(e)}[/yellow]")
            return f"Summary generation failed: {str(e)}"

    def _suggest_questions(self, schema_text: str, summary: str) -> List[str]:
        """Generate starting questions based on schema."""
        prompt = f"""Based on this database schema and summary, suggest 3 interesting natural language questions a user might want to ask.
        
        Summary: {summary}
        
        Schema:
        {schema_text}
        
        Output ONLY a list of 3 questions, one per line. No numbering or bullets."""
        
        try:
            response = self.worker_model.generate_content(prompt)
            if hasattr(response, 'text'):
                lines = [line.strip().lstrip('- ').lstrip('123. ') for line in response.text.strip().split('\n') if line.strip()]
                return lines[:3]
            return []
        except Exception as e:
            console.print(f"[yellow]Warning: Question suggestion error: {str(e)}[/yellow]")
            return []

