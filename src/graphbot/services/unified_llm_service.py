import os
from typing import Optional
from rich.console import Console

from graphbot.services.llm import (
    LLMFactory, 
    LLMProvider,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMModelNotFoundError,
    LLMTimeoutError,
    LLMServerError,
)
from graphbot.services.context_manager import ContextManager

console = Console()

class UnifiedLLMService:
    """
    Unified LLM Service that uses LLMFactory and ContextManager 
    to support multiple providers and robust context handling.
    Acts as a drop-in replacement for GeminiService where possible.
    """
    
    def __init__(self, config_path: str = "config/providers.yaml"):
        self.config_path = config_path
        self._provider: Optional[LLMProvider] = None
        self._context_manager: Optional[ContextManager] = None
        self._initialize_provider()
        
        # Compatibility properties
        self.model_names = [] # Populate based on provider?
        self.main_model_name = self._provider.main_model if self._provider else "Unknown"

    def _initialize_provider(self):
        try:
            self._provider = LLMFactory.get_provider(self.config_path)
            # Default to some reasonable max tokens if not in config
            max_tokens = self._provider.config.get('max_context_tokens', 10000)
            self._context_manager = ContextManager(self._provider, max_tokens=max_tokens)
            
            # Populate model names for display/switching if possible
            # For now just list the configured ones
            self.model_names = [
                self._provider.config['models']['main'],
                self._provider.config['models']['worker']
            ]
            self.main_model_name = self._provider.main_model
            
            console.print(f"[bold green]🧠 LLM Provider initialized: {self._provider.config.get('provider')}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]⚠️  LLM Provider initialization failed: {e}[/bold red]")
            # Fallback or raise?
            raise

    async def generate_cypher_query_async(self, user_input: str, context: Optional[str] = None) -> str:
        """Generate Cypher query using the active provider."""
        
        system_instruction = self._get_prompt("cypher_gen")
        if not system_instruction:
            # Fallback hardcoded prompt
            system_instruction = """You are an expert Neo4j Cypher Query Developer.
Translate user requests to Cypher.
Output ONLY the Cypher code. No markdown.
"""

        # Prepare prompt with context management
        final_prompt = await self._context_manager.prepare_prompt(
            user_input=user_input,
            system_instruction=system_instruction,
            context_data=context
        )
        
        try:
            response = await self._provider.generate_text(final_prompt, system_instruction=system_instruction)
            
            query = response.content.strip()
            # Cleanup code blocks
            if query.startswith("```"):
                lines = query.split("\n")
                if len(lines) > 2:
                    query = "\n".join(lines[1:-1])
                query = query.replace("```cypher", "").replace("```", "").strip()
                
            console.print(f"[bold bright_blue]🔍 Generated query ({response.model_name}):[/bold bright_blue] [dim]{query}[/dim]")
            if response.token_usage:
                console.print(f"[dim]Token usage: {response.token_usage}[/dim]")
                
            return query
            
        except LLMAuthenticationError as e:
            console.print(f"[bold red]❌ Authentication Error[/bold red]")
            console.print(f"[red]   {e}[/red]")
            console.print(f"[yellow]💡 Tips:[/yellow]")
            console.print(f"[yellow]   1. Check your config/config.env has GEMINI_API_KEY set correctly[/yellow]")
            console.print(f"[yellow]   2. Verify your API key at https://makersuite.google.com/app/apikey[/yellow]")
            raise
            
        except LLMModelNotFoundError as e:
            console.print(f"[bold red]❌ Model Not Found[/bold red]")
            console.print(f"[red]   {e}[/red]")
            console.print(f"[yellow]💡 Try running 'model' command to switch to an available model.[/yellow]")
            raise
            
        except LLMRateLimitError as e:
            console.print(f"[bold red]❌ Rate Limit Exceeded[/bold red]")
            console.print(f"[red]   {e}[/red]")
            if e.retry_after:
                console.print(f"[yellow]💡 Try again in {e.retry_after:.0f} seconds.[/yellow]")
            else:
                console.print(f"[yellow]💡 Check your API quota at https://ai.dev/usage[/yellow]")
            raise
            
        except LLMTimeoutError as e:
            console.print(f"[bold red]❌ Request Timed Out[/bold red]")
            console.print(f"[red]   {e}[/red]")
            console.print(f"[yellow]💡 This is usually a transient error. Please try again.[/yellow]")
            raise
            
        except LLMServerError as e:
            console.print(f"[bold red]❌ Server Error[/bold red]")
            console.print(f"[red]   {e}[/red]")
            console.print(f"[yellow]💡 The API server is experiencing issues. Please try again later.[/yellow]")
            raise
            
        except LLMError as e:
            console.print(f"[bold red]❌ LLM Error: {e}[/bold red]")
            raise
            
        except Exception as e:
            console.print(f"[bold red]❌ Unexpected error: {e}[/bold red]")
            raise

    async def explain_result_async(self, query: str, results: list, user_input: str) -> str:
        """Generate explanation of query results with graceful error handling."""
        system_instruction = self._get_prompt("summary_gen") or "Explain the results concisely."
        
        prompt_content = f"""
Original request: {user_input}
Cypher query: {query}
Results count: {len(results)}
Results sample: {str(results)[:500]}
"""
        try:
            final_prompt = await self._context_manager.prepare_prompt(
                user_input=prompt_content,
                system_instruction=system_instruction
            )
            
            response = await self._provider.generate_text(final_prompt, system_instruction=system_instruction)
            return response.content.strip()
            
        except LLMRateLimitError:
            console.print("[dim yellow]⚠️  Could not generate explanation (rate limit). Showing raw results.[/dim yellow]")
            return f"Query executed successfully. {len(results)} result(s) returned."
            
        except LLMTimeoutError:
            console.print("[dim yellow]⚠️  Could not generate explanation (timeout). Showing raw results.[/dim yellow]")
            return f"Query executed successfully. {len(results)} result(s) returned."
            
        except (LLMError, Exception) as e:
            console.print(f"[dim yellow]⚠️  Could not generate explanation: {str(e)[:100]}[/dim yellow]")
            return f"Query executed successfully. {len(results)} result(s) returned."

    def get_worker_model(self):
        # Return a wrapper or the provider itself configured for worker mode
        # The InsightAgent expects an object with generate_content_async
        # We can return a small adapter
        return WorkerModelAdapter(self._provider)

    def set_main_model(self, model_name: str) -> bool:
        # For now, just try to update the current provider's main model in memory
        # In a real app we might want to reload the factory with a different profile
        if model_name:
            self._provider.main_model = model_name
            self.main_model_name = model_name
            return True
        return False
        
    def _get_prompt(self, key: str) -> Optional[str]:
        # Try to get from config
        default_prompts = self._provider.config.get('default_prompts', {})
        prompt_name = default_prompts.get(key)
        
        # Load full config to get prompts section (not just profile)
        # This is a bit inefficient reading file again, but okay for MVP
        try:
            with open(self.config_path, 'r') as f:
                full_config = import_yaml().safe_load(f)
                prompts = full_config.get('prompts', {})
                return prompts.get(prompt_name)
        except Exception:
            return None

def import_yaml():
    import yaml
    return yaml

class WorkerModelAdapter:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def generate_content_async(self, prompt: str):
        # Adapt to what InsightAgent expects (response.text)
        response = await self.provider.generate_text(prompt, is_worker=True)

        class ResponseWrapper:
            def __init__(self, text):
                self.text = text
                self.content = text  # Add content attribute for compatibility

        return ResponseWrapper(response.content)

