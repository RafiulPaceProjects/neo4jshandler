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
        # Check for cache first
        import json
        import os
        import hashlib
        
        # Create a unique cache key based on DB connection string (simple version)
        # In a real scenario, might want to check DB hash or last updated time
        cache_key = hashlib.md5(f"{neo4j_handler.uri}-{neo4j_handler.database}".encode()).hexdigest()
        cache_file = f".graphbot_cache_{cache_key}.json"
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    # Optional: Add timestamp check to expire cache after X hours
                    console.print("[dim]Loaded schema insights from cache.[/dim]")
                    return cached_data
            except Exception:
                pass # Fallback to fresh analysis

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
                
            result = {
                "raw_schema": raw_schema,
                "summary": summary,
                "suggested_questions": questions
            }
            
            # Save to cache
            try:
                with open(cache_file, 'w') as f:
                    json.dump(result, f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not save cache: {e}[/yellow]")
                
            return result
            
        except Exception as e:
            console.print(f"[bold red]❌ Insight generation failed: {str(e)}[/bold red]")
            return {
                "raw_schema": "Schema unavailable",
                "summary": "Could not analyze database.",
                "suggested_questions": []
            }

    def _extract_raw_schema(self, neo4j: Neo4jHandler) -> str:
        """Extract detailed schema stats from Neo4j using parallel execution."""
        schema_parts = []
        import concurrent.futures
        
        try:
            with neo4j.driver.session(database=neo4j.database) as session:
                # 1. Get Node Labels (Fast)
                result = session.run("CALL db.labels() YIELD label RETURN label")
                labels = [r["label"] for r in result]
                
                # 2. Get Relationships (Fast)
                result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
                rels = [r["relationshipType"] for r in result]

            # Helper function for parallel execution
            def process_label(label):
                try:
                    # Create a new session for each thread to be thread-safe
                    with neo4j.driver.session(database=neo4j.database) as thread_session:
                        count_res = thread_session.run(f"MATCH (n:`{label}`) RETURN count(n) as c")
                        count = count_res.single()["c"]
                        
                        if count > 0:
                            props_res = thread_session.run(f"MATCH (n:`{label}`) RETURN keys(n) as k LIMIT 1")
                            props_rec = props_res.single()
                            prop_list = props_rec["k"] if props_rec else []
                            return f"- **{label}**: {count:,} nodes. Properties: {', '.join(prop_list[:5])}"
                        else:
                            return f"- **{label}**: 0 nodes."
                except Exception:
                    return f"- **{label}**: (Error fetching stats)"

            # Helper function for parallel execution (Relationships)
            def process_rel(r_type):
                try:
                    with neo4j.driver.session(database=neo4j.database) as thread_session:
                        count_res = thread_session.run(f"MATCH ()-[r:`{r_type}`]->() RETURN count(r) as c")
                        count = count_res.single()["c"]
                        return f"- **{r_type}**: {count:,} connections."
                except Exception:
                    return f"- **{r_type}**: (Error fetching stats)"

            # 3. Parallel Execution for Labels
            schema_parts.append("## Node Labels")
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all label tasks
                future_to_label = {executor.submit(process_label, label): label for label in labels}
                for future in concurrent.futures.as_completed(future_to_label):
                    schema_parts.append(future.result())

            # 4. Parallel Execution for Relationships
            schema_parts.append("\n## Relationships")
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all rel tasks
                future_to_rel = {executor.submit(process_rel, r_type): r_type for r_type in rels}
                for future in concurrent.futures.as_completed(future_to_rel):
                    schema_parts.append(future.result())
                    
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

