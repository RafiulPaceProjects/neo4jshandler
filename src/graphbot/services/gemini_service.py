"""Gemini API service for natural language to Cypher query conversion."""
import os
import time
import asyncio
import hashlib
from typing import Optional, Dict
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables from .env or config.env
load_dotenv()  # Try .env first
config_file = os.getenv("CONFIG_FILE", "config/config.env")
if os.path.exists(config_file):
    load_dotenv(config_file)  # Load config.env if it exists

console = Console()


class GeminiService:
    """Handles Gemini API interactions for natural language processing."""
    
    def __init__(self):
        """Initialize Gemini API client."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        # Validate API key format (basic check)
        if len(api_key) < 20 or not api_key.startswith("AIza"):
            console.print("[bold bright_red]⚠️  Warning: API key format looks invalid[/bold bright_red]")
            console.print("[bright_red]   API keys typically start with 'AIza' and are longer than 20 characters[/bright_red]")
        
        genai.configure(api_key=api_key)
        
        # Try different model names (free-tier friendly first)
        # Prioritize models that are typically available on free tier
        # Note: Newer experimental models may have stricter quota limits
        self.model_names = [
            'gemini-3-pro-preview',      # Latest high-intelligence model
            'gemini-1.5-pro',            # Stable pro model (good for free tier)
            'gemini-1.5-flash',          # Stable flash model (best for free tier)
            'gemini-pro',                 # Legacy (usually available)
            'gemini-1.5-flash-latest',   # Latest stable flash (may have limits)
            'gemini-1.5-pro-latest',     # Latest stable pro (may have limits)
            'gemini-2.0-flash-exp',      # Experimental (often has quota limits)
        ]
        
        self.main_model = None
        self.main_model_name = None
        
        self.worker_model = None
        self.worker_model_name = None
        
        self.available_models = {}  # Dictionary mapping short names to full model paths
        
        self._query_cache: Dict[str, str] = {}
        self._cache_size = 100
        
        self._initialize_models()

    def _initialize_models(self):
        """Initialize both main and worker models."""
        # Try to list available models first (optimization: do this once)
        try:
            # Add timeout to avoid hanging on startup if API is slow
            # Note: genai.list_models() returns an iterator, we convert to list
            # Depending on library version, list_models might not support timeout directly
            all_models = list(genai.list_models())
            
            # Store both full names and short names
            self.available_models = {}
            for m in all_models:
                if 'generateContent' in m.supported_generation_methods:
                    short_name = m.name.split('/')[-1]
                    self.available_models[short_name] = m.name  # Store full path
            
            available_short_names = list(self.available_models.keys())
            console.print(f"[dim]Available models: {', '.join(available_short_names[:5])}...[/dim]")
            
            # Initialize Main Model (High Intelligence)
            self._init_main_model()
            
            # Initialize Worker Model (High Speed/Efficiency)
            self._init_worker_model()
            
        except Exception as e:
            # Fallback initialization if list_models fails or times out
            console.print(f"[bold bright_red]⚠️  Could not list models, trying defaults: {str(e)[:50]}...[/bold bright_red]")
            self._init_main_model(fallback=True)
            self._init_worker_model(fallback=True)
            
        if not self.main_model:
            raise ValueError("Failed to initialize Gemini API. No suitable models found.")

    def _init_main_model(self, fallback=False):
        """Initialize the main 'brain' model."""
        target_model = os.getenv("MAIN_MODEL", "gemini-3-pro-preview")
        
        # Try target model first
        if self._set_model(target_model, is_main=True, fallback=fallback):
            return

        # Fallback to preferred list
        for model_name in self.model_names:
            if self._set_model(model_name, is_main=True, fallback=fallback):
                return

    def _init_worker_model(self, fallback=False):
        """Initialize the worker 'insight' model."""
        target_model = os.getenv("WORKER_MODEL", "gemini-1.5-flash")
        
        # Try target model first
        if self._set_model(target_model, is_main=False, fallback=fallback):
            return

        # Fallback to flash/fast models
        fast_models = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
        for model_name in fast_models:
            if self._set_model(model_name, is_main=False, fallback=fallback):
                return
                
        # If no fast model, use same as main
        self.worker_model = self.main_model
        self.worker_model_name = self.main_model_name

    def _set_model(self, model_name: str, is_main: bool, fallback: bool) -> bool:
        """Helper to instantiate and set a model."""
        try:
            if not fallback and model_name in self.available_models:
                full_name = self.available_models[model_name]
                model = genai.GenerativeModel(full_name)
            else:
                # Direct instantiation attempt
                model = genai.GenerativeModel(model_name)
            
            if is_main:
                self.main_model = model
                self.main_model_name = model_name
                console.print(f"[bold bright_green]🧠 Main Brain initialized: [bold bright_blue]{model_name}[/bold bright_blue][/bold bright_green]")
            else:
                self.worker_model = model
                self.worker_model_name = model_name
                console.print(f"[bold bright_green]⚡ Worker Agent initialized: [bold bright_blue]{model_name}[/bold bright_blue][/bold bright_green]")
            return True
        except:
            return False

    def set_main_model(self, model_name: str) -> bool:
        """Dynamically switch the main model."""
        return self._set_model(model_name, is_main=True, fallback=True)

    def get_worker_model(self):
        """Return the worker model instance."""
        return self.worker_model

    
    def _extract_text(self, response) -> str:
        """
        Safely extract text from Gemini API response.
        
        Args:
            response: Gemini API response object
            
        Returns:
            Extracted text string
        """
        # Method 0: Check if response has a result attribute
        if hasattr(response, 'result'):
            try:
                result = response.result
                if hasattr(result, 'parts'):
                    parts = result.parts
                    if parts:
                        text_parts = []
                        for part in parts:
                            if hasattr(part, 'text'):
                                text_parts.append(str(part.text))
                            elif isinstance(part, str):
                                text_parts.append(part)
                        if text_parts:
                            return ''.join(text_parts)
            except Exception:
                pass
        
        # Method 1: Use response.parts (as suggested by error message)
        if hasattr(response, 'parts'):
            try:
                parts = response.parts
                if parts:
                    text_parts = []
                    for part in parts:
                        # Check if part has text attribute
                        if hasattr(part, 'text'):
                            text_parts.append(str(part.text))
                        # Check if part is directly a string
                        elif isinstance(part, str):
                            text_parts.append(part)
                        # Check if part has a get method
                        elif hasattr(part, 'get'):
                            text = part.get('text', '')
                            if text:
                                text_parts.append(str(text))
                    if text_parts:
                        return ''.join(text_parts)
            except Exception as e:
                pass
        
        # Method 2: Use response.candidates[0].content.parts (full lookup)
        if hasattr(response, 'candidates') and response.candidates:
            try:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    content = candidate.content
                    if hasattr(content, 'parts'):
                        parts = content.parts
                        if parts:
                            text_parts = []
                            for part in parts:
                                if hasattr(part, 'text'):
                                    text_parts.append(str(part.text))
                                elif isinstance(part, str):
                                    text_parts.append(part)
                                elif hasattr(part, 'get'):
                                    text = part.get('text', '')
                                    if text:
                                        text_parts.append(str(text))
                            if text_parts:
                                return ''.join(text_parts)
            except Exception as e:
                pass
        
        # Method 3: Try response.text (might work for simple responses)
        try:
            return str(response.text)
        except (ValueError, AttributeError):
            pass
        
        # If all methods fail, raise an error with debug info
        error_info = []
        if hasattr(response, 'candidates'):
            error_info.append(f"candidates={len(response.candidates) if response.candidates else 0}")
        if hasattr(response, 'parts'):
            error_info.append(f"parts={len(response.parts) if response.parts else 0}")
        
        raise ValueError(f"Could not extract text from Gemini response. Response has: {', '.join(error_info) if error_info else 'unknown structure'}")
    
    def generate_cypher_query(self, user_input: str, context: Optional[str] = None) -> str:
        """Synchronous wrapper for backward compatibility."""
        return asyncio.run(self.generate_cypher_query_async(user_input, context))

    async def generate_cypher_query_async(self, user_input: str, context: Optional[str] = None) -> str:
        """
        Convert natural language input to Cypher query asynchronously.
        
        Args:
            user_input: Natural language query from user
            context: Optional context about the database schema
            
        Returns:
            Cypher query string
        """
        # 1. Check Cache
        cache_key = hashlib.md5(f"{user_input}:{context}".encode()).hexdigest()
        if cache_key in self._query_cache:
            console.print("[dim]⚡ Using cached query...[/dim]")
            return self._query_cache[cache_key]

        # Build context-aware prompt
        base_prompt = """You are an expert Neo4j Cypher Query Developer.
Your task is to accurately translate the user's natural language request into an executable Cypher query.

### STRICT OUTPUT RULES:
1. **Raw Text Only**: Output ONLY the Cypher code. Do NOT use markdown blocks (```cypher). Do NOT provide explanations or apologies.
2. **Syntax**: Use valid Neo4j Cypher syntax.

### QUERY GUIDELINES:
1. **Fuzzy Matching**: When searching for names or text, use case-insensitive contains (e.g., `WHERE toLower(n.name) CONTAINS toLower('search_term')`) unless searching by exact ID.
2. **Safety**: For DELETE operations, ensure you use `DETACH DELETE` if nodes might have relationships.
3. **Readability**: Always Return relevant, readable properties (e.g., names, IDs, counts) rather than just nodes (`RETURN n`).
4. **Limits**: For broad queries (e.g., "Show me all nodes"), ALWAYS append `LIMIT 25` to prevent database overloads.
5. **Logic**:
   - "How many" -> Use `RETURN count(...)`
   - "Find connections" -> Use `MATCH p=(a)-[*]->(b) ... RETURN p`

"""
        if context:
            base_prompt += f"\n### DATABASE SCHEMA:\n{context}\n"
        
        prompt = base_prompt + f"\nUser request: {user_input}\n\nCypher query:"
        
        # Try with retry logic and model fallback
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Use async generation
                response = await self.main_model.generate_content_async(prompt)
                
                # Debug: Print response structure if extraction fails
                try:
                    query = self._extract_text(response).strip()
                except Exception as extract_error:
                    # Try to debug the response structure
                    console.print(f"[yellow]Debug: Response type: {type(response)}[/yellow]")
                    console.print(f"[yellow]Debug: Response attributes: {dir(response)}[/yellow]")
                    if hasattr(response, 'candidates'):
                        console.print(f"[yellow]Debug: Has candidates: {len(response.candidates) if response.candidates else 0}[/yellow]")
                    if hasattr(response, 'parts'):
                        console.print(f"[yellow]Debug: Has parts: {len(response.parts) if response.parts else 0}[/yellow]")
                    raise extract_error
                
                # Remove markdown code blocks if present
                if query.startswith("```"):
                    lines = query.split("\n")
                    query = "\n".join(lines[1:-1]) if len(lines) > 2 else query
                    query = query.replace("```cypher", "").replace("```", "").strip()
                
                console.print(f"[bold bright_blue]🔍 Generated query:[/bold bright_blue] [dim]{query}[/dim]")
                
                # Update Cache
                if len(self._query_cache) >= self._cache_size:
                    # Remove oldest item (Python dicts are ordered by insertion)
                    self._query_cache.pop(next(iter(self._query_cache)))
                self._query_cache[cache_key] = query
                
                return query
                
            except Exception as e:
                error_str = str(e)
                
                # Check for API key errors (400)
                if "400" in error_str and ("API Key" in error_str or "API_KEY_INVALID" in error_str or "api key" in error_str.lower()):
                    console.print(f"[bold bright_red]❌ Invalid API Key[/bold bright_red]")
                    console.print(f"[bright_red]   Error: API Key not found or invalid[/bright_red]")
                    console.print(f"[bold bright_yellow]💡 Tips:[/bold bright_yellow]")
                    console.print(f"[bright_yellow]   1. Check your .env file has GEMINI_API_KEY set correctly[/bright_yellow]")
                    console.print(f"[bright_yellow]   2. Verify your API key at https://makersuite.google.com/app/apikey[/bright_yellow]")
                    console.print(f"[bright_yellow]   3. Make sure the API key is active and has proper permissions[/bright_yellow]")
                    raise Exception("Invalid API Key. Please check your GEMINI_API_KEY in the .env file.")
                
                # Check for model not found errors (404)
                if "404" in error_str or "not found" in error_str.lower():
                    # Try to switch to a different model
                    if attempt < max_retries - 1:
                        if self._try_fallback_model():
                            console.print(f"[bold bright_blue]🔄 Model not found, switched to: {self.main_model_name}[/bold bright_blue]")
                            continue
                        else:
                            console.print(f"[bold bright_red]❌ Model {self.main_model_name} not found and no fallback available[/bold bright_red]")
                            console.print(f"[bright_red]   Error: {error_str[:200]}[/bright_red]")
                            raise Exception(f"Model not found: {error_str[:200]}")
                    else:
                        console.print(f"[bold bright_red]❌ Model {self.main_model_name} not found after retries[/bold bright_red]")
                        raise Exception(f"Model not found: {error_str[:200]}")
                
                # Check for quota/rate limit errors (429)
                if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                    # Try to extract retry time
                    retry_time = None
                    if "retry in" in error_str.lower():
                        try:
                            import re
                            match = re.search(r'retry in ([\d.]+)s', error_str.lower())
                            if match:
                                retry_time = float(match.group(1))
                        except:
                            pass
                    
                    # If this is not the last attempt, try a different model
                    if attempt < max_retries - 1:
                        # Try to switch to a different model
                        if self._try_fallback_model():
                            console.print(f"[bold bright_blue]🔄 Switched to model: {self.main_model_name}[/bold bright_blue]")
                            continue
                        
                        # If no fallback model, wait and retry
                        wait_time = retry_time if retry_time else retry_delay * (attempt + 1)
                        console.print(f"[bold bright_yellow]⏳ Quota exceeded. Waiting {wait_time:.1f}s before retry...[/bold bright_yellow]")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Last attempt failed
                        console.print(f"[bold bright_red]❌ Quota exceeded for model {self.main_model_name}[/bold bright_red]")
                        console.print(f"[bright_red]   Error: {error_str[:200]}[/bright_red]")
                        console.print(f"[bold bright_yellow]💡 Tip: Check your API quota at https://ai.dev/usage?tab=rate-limit[/bold bright_yellow]")
                        raise Exception(f"Quota exceeded. Please check your API plan and billing details.")
                
                # For other errors, raise immediately
                if attempt == max_retries - 1:
                    console.print(f"[bold bright_red]❌ Error generating query: {error_str[:200]}[/bold bright_red]")
                    raise
                else:
                    # Retry for other errors with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    console.print(f"[bold bright_yellow]⚠️  Error occurred. Retrying in {wait_time}s...[/bold bright_yellow]")
                    await asyncio.sleep(wait_time)
        
        raise Exception("Failed to generate query after multiple attempts")
    
    def _try_fallback_model(self) -> bool:
        """Try to switch to a different model if current one has quota issues."""
        if not self.available_models:
            return False
        
        current_index = self.model_names.index(self.main_model_name) if self.main_model_name in self.model_names else -1
        
        # Try next available model in the list
        for i, model_name in enumerate(self.model_names):
            if i > current_index and model_name in self.available_models:
                try:
                    # Use the full model name if stored, otherwise use short name
                    self.set_main_model(model_name)
                    return True
                except:
                    continue
        
        return False
    
    def explain_result(self, query: str, results: list, user_input: str) -> str:
        """Synchronous wrapper for backward compatibility."""
        return asyncio.run(self.explain_result_async(query, results, user_input))

    async def explain_result_async(self, query: str, results: list, user_input: str) -> str:
        """
        Generate a natural language explanation of query results asynchronously.
        
        Args:
            query: The Cypher query that was executed
            results: The query results
            user_input: Original user input
            
        Returns:
            Natural language explanation
        """
        prompt = f"""Explain the results of this Neo4j Cypher query in natural language.

Original user request: {user_input}
Cypher query executed: {query}
Number of results: {len(results)}

Provide a brief, user-friendly explanation of what was found or what operation was performed."""
        
        try:
            response = await self.main_model.generate_content_async(prompt)
            return self._extract_text(response).strip()
        except Exception as e:
            console.print(f"[bold bright_red]⚠️  Could not generate explanation: {str(e)}[/bold bright_red]")
            return "Query executed successfully."
