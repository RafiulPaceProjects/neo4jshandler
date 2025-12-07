"""Insight Agent for automatic database mapping and analysis."""
from typing import Any, Dict, List, TYPE_CHECKING
import asyncio
from rich.console import Console
from graphbot.handlers import Neo4jHandler
from graphbot.services.cache_manager import get_cache_manager, create_cache_key

if TYPE_CHECKING:
    from graphbot.services.unified_llm_service import UnifiedLLMService

console = Console()

# Constants for retry logic
MAX_LLM_RETRIES = 2
LLM_RETRY_DELAY = 1.0


class InsightAgent:
    """
    Background agent that maps the database structure and generates
    semantic insights using a worker model.
    """
    
    def __init__(self, llm_service: "UnifiedLLMService"):
        """Initialize with LLM service to access worker model."""
        self.llm_service = llm_service
        self.worker_model = self.llm_service.get_worker_model()
    
    def analyze_database(self, neo4j_handler: Neo4jHandler) -> dict[str, Any]:
        """Synchronous wrapper for backward compatibility."""
        return asyncio.run(self.analyze_database_async(neo4j_handler))

    async def analyze_database_async(self, neo4j_handler: Neo4jHandler) -> dict[str, Any]:
        """
        Analyze database structure and content asynchronously.

        Args:
            neo4j_handler: Active Neo4j connection handler

        Returns:
            Dictionary containing schema info, summary, and suggested questions
        """
        # Check for cache first
        if not neo4j_handler.driver:
             return {
                "raw_schema": "Schema unavailable",
                "summary": "Could not analyze database (Not connected).",
                "suggested_questions": []
            }

        # Use centralized cache manager
        cache_manager = get_cache_manager()
        cache_key = create_cache_key(neo4j_handler.uri, neo4j_handler.database, "insights")

        # Try to get from cache
        cached_data = cache_manager.get(cache_key)
        if cached_data:
            console.print("[dim]Loaded schema insights from cache.[/dim]")
            return cached_data

        try:
            # We use a simple print here instead of Progress because this runs in background
            # and might interfere with the main input loop if not careful.
            # But since we are refactoring to async, we can use a spinner if we await it.
            # For background tasks, usually we just let it finish.
            # If the user is waiting (startup), we can show progress.
            
            console.print("[dim cyan]🔍 Insight Agent started mapping database...[/dim cyan]")

            # Step 1: Raw Schema Extraction
            raw_schema = await self._extract_raw_schema_async(neo4j_handler)
            
            # Step 2: Semantic Summary Generation
            summary = await self._generate_summary_async(raw_schema)
            
            # Step 3: Question Suggestion
            questions = await self._suggest_questions_async(raw_schema, summary)
            
            result = {
                "raw_schema": raw_schema,
                "summary": summary,
                "suggested_questions": questions
            }

            # Save to centralized cache
            try:
                cache_manager.put(cache_key, result)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not save to cache: {e}[/yellow]")

            console.print("[dim green]✅ Insight Agent finished analysis.[/dim green]")
            return result
            
        except Exception as e:
            console.print(f"[bold red]❌ Insight generation failed: {str(e)}[/bold red]")
            return {
                "raw_schema": "Schema unavailable",
                "summary": "Could not analyze database.",
                "suggested_questions": []
            }

    async def _extract_raw_schema_async(self, neo4j: Neo4jHandler) -> str:
        """Extract detailed schema stats from Neo4j using optimized single-session queries."""
        schema_parts = []
        
        try:
            async with neo4j.driver.session(database=neo4j.database) as session:
                # 1. Get Node Labels and Counts (Optimized)
                label_query = """
                CALL db.labels() YIELD label
                CALL {
                    WITH label
                    MATCH (n) WHERE label IN labels(n)
                    RETURN count(n) as count
                }
                RETURN label, count
                ORDER BY label
                """
                
                result = await session.run(label_query)
                schema_parts.append("## Node Labels")
                
                # Collect all labels first to ensure result consumption
                labels_data = [record async for record in result]
                
                for record in labels_data:
                    label = record["label"]
                    count = record["count"]
                    
                    if count > 0:
                        # Get properties sample in the same session
                        props_res = await session.run(f"MATCH (n:`{label}`) RETURN keys(n) as k LIMIT 1")
                        props_rec = await props_res.single()
                        prop_list = props_rec["k"] if props_rec else []
                        schema_parts.append(f"- **{label}**: {count:,} nodes. Properties: {', '.join(prop_list[:5])}")
                    else:
                        schema_parts.append(f"- **{label}**: 0 nodes.")

                # 2. Get Relationships and Counts
                rel_query = """
                CALL db.relationshipTypes() YIELD relationshipType
                CALL {
                    WITH relationshipType
                    MATCH ()-[r]->() WHERE type(r) = relationshipType
                    RETURN count(r) as count
                }
                RETURN relationshipType, count
                ORDER BY relationshipType
                """
                
                result = await session.run(rel_query)
                schema_parts.append("\n## Relationships")
                
                async for record in result:
                    r_type = record["relationshipType"]
                    count = record["count"]
                    schema_parts.append(f"- **{r_type}**: {count:,} connections.")
                    
        except Exception as e:
            console.print(f"[yellow]Warning: Schema extraction error: {str(e)}[/yellow]")
            return f"Error extracting schema: {str(e)}"
            
        return "\n".join(schema_parts)

    async def _generate_summary_async(self, schema_text: str) -> str:
        """Use worker model to summarize the domain asynchronously with retry logic."""
        prompt = f"""You are a Database Analyst. Analyze the following Neo4j schema and provide a concise, high-level summary of what this database represents.
        
        Identify:
        1. The main domain (e.g., "Healthcare", "Movies", "Finance").
        2. The core entities and how they relate.
        3. Any interesting data volume stats.
        
        Schema:
        {schema_text}
        
        Output a short paragraph (max 3 sentences)."""
        
        last_error = None
        for attempt in range(MAX_LLM_RETRIES):
            try:
                response = await self.worker_model.generate_content_async(prompt)
                if hasattr(response, 'text'):
                    return response.text.strip()
                elif hasattr(response, 'content'):
                    return response.content.strip()
                return "Summary generation failed (No text response)."
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                # Check if error is retryable
                if any(pattern in error_str for pattern in ['timeout', 'cancelled', '504', '503', '502', '500']):
                    if attempt < MAX_LLM_RETRIES - 1:
                        console.print(f"[dim yellow]⚠️  Summary generation retry {attempt + 1}/{MAX_LLM_RETRIES}...[/dim yellow]")
                        await asyncio.sleep(LLM_RETRY_DELAY * (attempt + 1))
                        continue
                break
        
        console.print(f"[yellow]Warning: Summary generation error: {str(last_error)[:100]}[/yellow]")
        return "Database summary unavailable."

    async def _suggest_questions_async(self, schema_text: str, summary: str) -> list[str]:
        """Generate starting questions based on schema asynchronously with retry logic."""
        prompt = f"""Based on this database schema and summary, suggest 3 interesting natural language questions a user might want to ask.

        Summary: {summary}

        Schema:
        {schema_text}

        Output ONLY a list of 3 questions, one per line. No numbering or bullets."""

        last_error = None
        for attempt in range(MAX_LLM_RETRIES):
            try:
                response = await self.worker_model.generate_content_async(prompt)
                text = ""
                if hasattr(response, 'text'):
                    text = response.text
                elif hasattr(response, 'content'):
                    text = response.content
                
                if text:
                    lines = [line.strip().lstrip('- ').lstrip('123. ') for line in text.strip().split('\n') if line.strip()]
                    return lines[:3]
                return []
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                # Check if error is retryable
                if any(pattern in error_str for pattern in ['timeout', 'cancelled', '504', '503', '502', '500']):
                    if attempt < MAX_LLM_RETRIES - 1:
                        await asyncio.sleep(LLM_RETRY_DELAY * (attempt + 1))
                        continue
                break
        
        console.print(f"[yellow]Warning: Question suggestion error: {str(last_error)[:100] if last_error else 'Unknown'}[/yellow]")
        return []

    def _extract_raw_schema(self, neo4j: Neo4jHandler) -> str:
        """Synchronous wrapper for raw schema extraction."""
        try:
            return asyncio.get_event_loop().run_until_complete(self._extract_raw_schema_async(neo4j))
        except RuntimeError:
             # If loop is already running, we can't use run_until_complete
             # But since this is a wrapper, we should assume it's called from sync code.
             # If called from async code, user should use _async version.
             # We can try to use asyncio.run if no loop is running, or create a new loop.
             return asyncio.run(self._extract_raw_schema_async(neo4j))

    def _generate_summary(self, schema_text: str) -> str:
        """Synchronous wrapper for summary generation."""
        try:
            return asyncio.get_event_loop().run_until_complete(self._generate_summary_async(schema_text))
        except RuntimeError:
            return asyncio.run(self._generate_summary_async(schema_text))

    def _suggest_questions(self, schema_text: str, summary: str) -> list[str]:
        """Synchronous wrapper for question suggestion."""
        try:
            return asyncio.get_event_loop().run_until_complete(self._suggest_questions_async(schema_text, summary))
        except RuntimeError:
            return asyncio.run(self._suggest_questions_async(schema_text, summary))
