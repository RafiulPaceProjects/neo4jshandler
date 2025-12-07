#!/usr/bin/env python3
"""Neo4j GraphBot - A CLI interface for interacting with Neo4j using natural language via LLM."""
import sys
import os
import asyncio
import time
import subprocess
from typing import Optional
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich import box
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.tree import Tree
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner

from graphbot.handlers import Neo4jHandler, Neo4jConnectionError, Neo4jQueryError
from graphbot.services import (
    UnifiedLLMService,
    InsightAgent,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMModelNotFoundError,
    LLMTimeoutError,
    LLMServerError,
)
from graphbot.services.schema_inspector import SchemaInspector
from graphbot.services.cache_manager import get_cache_manager
from graphbot.utils import QueryBuilder
from graphbot.core import SchemaContext

console = Console()


class GraphBot:
    """Main CLI application for Neo4j GraphBot."""
    
    def __init__(self):
        """Initialize GraphBot with Neo4j and Unified LLM services."""
        self.neo4j: Optional[Neo4jHandler] = None
        self.llm: Optional[UnifiedLLMService] = None
        self.insight_agent: Optional[InsightAgent] = None
        self.schema_inspector: Optional[SchemaInspector] = None
        self.schema_context: Optional[SchemaContext] = None
        self.query_builder = QueryBuilder()
        self.running = False
        self.mapping_task: Optional[asyncio.Task] = None
        self.cache_saver_task: Optional[asyncio.Task] = None
        
        # New: Main Agent Router context
        self._router_context = {
            "last_action": None,
            "session_history": []
        }
    
    async def initialize_async(self):
        """Initialize connections to Neo4j and LLM."""
        try:
            console.print(Rule("[bold bright_blue]🚀 Initializing GraphBot[/bold bright_blue]"))
            self.neo4j = Neo4jHandler()
            
            # Initialize Unified LLM Service
            self.llm = UnifiedLLMService()
            
            # Insight Agent still expects a service with get_worker_model logic
            self.insight_agent = InsightAgent(self.llm)
            
            self.schema_inspector = SchemaInspector(self.neo4j)
            self.schema_context = SchemaContext(self.neo4j)
            
            # Initial auto-mapping if connected
            self.mapping_task = asyncio.create_task(self._run_auto_mapping_async())
            
            console.print("[bold bright_green]✅ GraphBot ready![/bold bright_green]\n")
            return True
        except Exception as e:
            console.print(f"[bold bright_red]❌ Initialization failed: {str(e)}[/bold bright_red]")
            console.print("[yellow]Please check your environment variables and try again.[/yellow]")
            return False

    async def _auto_save_cache_loop(self):
        """Background task to periodically save cache if dirty."""
        cache_manager = get_cache_manager()
        while self.running:
            try:
                await asyncio.sleep(60) # Save every minute
                await asyncio.to_thread(cache_manager.save_if_dirty)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
        
        # Final save on exit
        await asyncio.to_thread(cache_manager.save_if_dirty)

    async def _run_auto_mapping_async(self):
        """Run the insight agent to map the database in background."""
        if not self.neo4j or not self.neo4j.driver:
            return

        if not await self.neo4j.verify_connectivity_async():
            return

        insights = await self.insight_agent.analyze_database_async(self.neo4j)
        
        if self.schema_context:
            self.schema_context.set_insights(insights)
            
        console.print("\n[dim green]✨ Database mapping complete. Type 'schema' to view details.[/dim green]")

    
    def display_welcome(self):
        """Display welcome message."""
        welcome_text = Text()
        welcome_text.append("Neo4j GraphBot", style="bold bright_red on bright_blue")
        welcome_text.append("\n\nAuthors: Rafiul Haider, Ali Khan, Yogesh\n", style="bold white")
        welcome_text.append("CS 673 — Scalable Databases (Fall 2025) @ Pace University\n", style="dim white")
        welcome_text.append("\n🎯 Your intelligent companion for Neo4j graph exploration.\n", style="bold bright_blue")
        
        content = Group(
            welcome_text,
            Rule(style="bright_blue"),
            Markdown("""
**Quick Commands:**
* Type your question in natural language
* `inspect` to check property values
* `panel` to open Control Panel
* `connect` to change database
* `help` for more commands
""")
        )
        
        console.print(Panel(content, 
                          title="[bold bright_red]Welcome[/bold bright_red]", 
                          border_style="bright_blue",
                          box=box.DOUBLE))
        console.print()
    
    def display_help(self):
        """Display help information."""
        
        tree = Tree("🤖 [bold bright_red]GraphBot Help[/bold bright_red]")
        
        queries = tree.add("📝 [bold bright_blue]Example Queries[/bold bright_blue]")
        queries.add('"Show me all nodes"')
        queries.add('"Find relationships between User and Product nodes"')
        queries.add('"Count the number of nodes in the graph"')
        
        commands = tree.add("⚙️  [bold bright_blue]System Commands[/bold bright_blue]")
        commands.add("[bold bright_red]panel[/bold bright_red] - Open AI Control Panel")
        commands.add("[bold bright_red]inspect[/bold bright_red] - Interactive schema inspection")
        commands.add("[bold bright_red]connect[/bold bright_red] - Connect to database")
        commands.add("[bold bright_red]use <db>[/bold bright_red] - Switch database")
        commands.add("[bold bright_red]schema[/bold bright_red] - View schema")
        commands.add("[bold bright_red]model[/bold bright_red] - Switch AI model")
        commands.add("[bold bright_red]cache[/bold bright_red] - Cache management")
        commands.add("[bold bright_red]clear[/bold bright_red] - Clear screen")
        commands.add("[bold bright_red]quit[/bold bright_red] - Exit")
        
        console.print(Panel(tree, border_style="bright_blue", box=box.ROUNDED))
        console.print()
    
    async def _route_request(self, user_input: str) -> str:
        """
        Determine if this is a query generation request, chit-chat, or needs other agents.
        Handles basic chit-chat locally to save tokens.
        """
        low_input = user_input.lower().strip()
        
        # 1. Local Chit-Chat Detection (Zero Token Cost)
        # Extend this list as needed
        greetings = {'hi', 'hello', 'hey', 'greetings', 'sup', 'yo', 'howdy', 'hola'}
        if low_input in greetings or low_input.startswith(('hi ', 'hello ', 'hey ')):
             # Basic greeting pattern
             if len(low_input.split()) < 4: # Short greetings only
                return "chitchat"
        
        if "who are you" in low_input or "what are you" in low_input:
             return "identity"
        
        # Conversational / General QA check
        # If input is clearly not a database query (e.g., "how are you doing", "what is the meaning of life")
        # We want to avoid generating Cypher.
        # This is hard to do perfectly without LLM, but we can catch common patterns.
        common_conversational = ['how are you', 'how is it going', 'doing well', 'thanks', 'thank you', 'goodbye', 'bye']
        if any(phrase in low_input for phrase in common_conversational):
            return "chitchat_general"

        # 2. Default to Cypher Query for everything else
        # Future: Use LLM classifier for complex cases
        return "cypher_query"

    async def process_query_async(self, user_input: str):
        """Process user input and execute query asynchronously."""
        if not user_input.strip():
            return
        
        try:
            # 1. Main Agent Routing (Decision Phase)
            action = await self._route_request(user_input)
            
            # Store decision in context
            self._router_context["last_action"] = action
            self._router_context["session_history"].append({"role": "user", "content": user_input})
            
            if action == "chitchat":
                response = "Hi! I'm your Neo4j GraphBot assistant. I can help you query and analyze your graph database. What would you like to know?"
                console.print(Panel(response, title="[bold green]GraphBot[/bold green]", border_style="green", box=box.ROUNDED))
                self._router_context["session_history"].append({"role": "assistant", "content": response})
                return

            if action == "identity":
                response = "I am GraphBot, an intelligent CLI assistant powered by LLMs to help you interact with Neo4j databases using natural language."
                console.print(Panel(response, title="[bold green]GraphBot[/bold green]", border_style="green", box=box.ROUNDED))
                self._router_context["session_history"].append({"role": "assistant", "content": response})
                return
            
            if action == "chitchat_general":
                # For general conversation, we might want to use the LLM but NOT try to generate Cypher.
                # Or just give a canned response if we want 'least tokens'.
                # Let's use a lightweight conversational path if possible, or just a polite canned response for now to be safe on tokens.
                response = "I'm doing well, thank you! I'm ready to help you explore your graph database. Please ask me a question about your data."
                console.print(Panel(response, title="[bold green]GraphBot[/bold green]", border_style="green", box=box.ROUNDED))
                self._router_context["session_history"].append({"role": "assistant", "content": response})
                return

            if action == "cypher_query":
                # Delegate to Cypher Agent
                await self._handle_cypher_flow(user_input)
            else:
                console.print(f"[yellow]Action '{action}' not implemented yet.[/yellow]")
            
        except LLMAuthenticationError:
            # Already logged in unified_llm_service
            pass
        except LLMModelNotFoundError:
            # Already logged in unified_llm_service
            pass
        except LLMRateLimitError:
            # Already logged in unified_llm_service
            pass
        except LLMTimeoutError:
            # Already logged in unified_llm_service
            pass
        except LLMServerError:
            # Already logged in unified_llm_service
            pass
        except LLMError as e:
            console.print(f"[bold bright_red]❌ LLM Error: {str(e)[:200]}[/bold bright_red]")
        except Neo4jConnectionError as e:
            console.print(f"[bold bright_red]❌ Database Connection Error: {str(e)[:200]}[/bold bright_red]")
            console.print(f"[yellow]💡 Try running 'connect' to reconnect to the database.[/yellow]")
        except Neo4jQueryError as e:
            console.print(f"[bold bright_red]❌ Query Error: {str(e)[:200]}[/bold bright_red]")
        except Exception as e:
            console.print(f"[bold bright_red]❌ Unexpected Error: {str(e)[:200]}[/bold bright_red]")

    async def _handle_cypher_flow(self, user_input: str):
        """Handle standard Cypher generation and execution flow."""
        cypher_query = None
        
        with Live(Spinner("dots", text="[bold cyan]Thinking...[/bold cyan]"), refresh_per_second=10, transient=True):
            # Get schema context
            schema_context = await self.schema_context.get_schema_context_async() if self.schema_context else None
            
            # Generate Query
            cypher_query = await self.llm.generate_cypher_query_async(user_input, context=schema_context)
        
        if not cypher_query:
            return

        # Display Generated Query with Syntax Highlighting
        console.print(Panel(
            Syntax(cypher_query, "cypher", theme="monokai", line_numbers=False),
            title="[bold bright_blue]Generated Cypher[/bold bright_blue]",
            border_style="bright_blue",
            box=box.ROUNDED
        ))
        
        # Validate query
        is_valid, error_msg = self.query_builder.validate_query(cypher_query)
        if not is_valid:
            console.print(f"[bold bright_red]❌ Query validation failed: {error_msg}[/bold bright_red]")
            return
        
        # Sanitize query
        cypher_query = self.query_builder.sanitize_query(cypher_query)
        
        # Confirm write operations
        if not self.query_builder.is_read_only(cypher_query):
            console.print("[bold bright_red]⚠️  WARNING: This query will modify the database![/bold bright_red]")
            confirm = await asyncio.to_thread(Prompt.ask, "[bold bright_blue]Continue?[/bold bright_blue]", choices=["y", "n"], default="n")
            if confirm.lower() != "y":
                console.print("[bold bright_red]Query cancelled.[/bold bright_red]")
                return
        
        # Execute query
        results = None
        with Live(Spinner("dots", text="[bold green]Executing query...[/bold green]"), refresh_per_second=10, transient=True):
            results = await self.neo4j.execute_query_async(cypher_query)
        
        # Display results
        if results:
            self.neo4j.format_results(results)
            
            # Generate explanation
            with Live(Spinner("dots", text="[bold magenta]Analyzing results...[/bold magenta]"), refresh_per_second=10, transient=True):
                explanation = await self.llm.explain_result_async(cypher_query, results, user_input)
            
            # Store result in session history
            self._router_context["session_history"].append({"role": "assistant", "content": explanation})
            
            console.print(Panel(
                Markdown(explanation),
                title="[bold bright_blue]Insight[/bold bright_blue]",
                border_style="green",
                box=box.ROUNDED
            ))
        else:
            console.print("[bold bright_green]✅ Query executed successfully (no results returned).[/bold bright_green]")
            self._router_context["session_history"].append({"role": "assistant", "content": "Query executed successfully."})
    
    async def run_async(self):
        """Main application loop."""
        if not await self.initialize_async():
            sys.exit(1)
        
        self.display_welcome()
        self.running = True
        
        # Start cache saver
        self.cache_saver_task = asyncio.create_task(self._auto_save_cache_loop())
        
        while self.running:
            try:
                # User Input
                console.print(Rule(style="dim"))
                user_input = await asyncio.to_thread(
                    Prompt.ask, "\n[bold bright_red]GraphBot[/bold bright_red] [bold bright_blue]→[/bold bright_blue]"
                )
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[bold bright_blue]👋 Goodbye![/bold bright_blue]")
                    break
                
                if await self._handle_command(user_input):
                    continue
                
                # Process natural language query
                await self.process_query_async(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[bold bright_red]⚠️  Interrupted. Type 'quit' to exit.[/bold bright_red]")
            except EOFError:
                console.print("\n[bold bright_blue]👋 Goodbye![/bold bright_blue]")
                break
            except Exception as e:
                console.print(f"[bold bright_red]❌ Unexpected error: {str(e)}[/bold bright_red]")
        
        # Cleanup
        if self.cache_saver_task:
            self.cache_saver_task.cancel()
            try:
                await self.cache_saver_task
            except asyncio.CancelledError:
                pass

        if self.neo4j:
            await self.neo4j.close_async()

    async def _handle_command(self, user_input: str) -> bool:
        """Handle built-in commands. Returns True if command was handled."""
        cmd = user_input.lower().strip()
        
        if cmd == 'panel':
            # Run the control panel script in a subprocess or import it?
            # Importing is better but it's a script. Let's run it via shell for isolation or refactor.
            # Refactoring control_panel to be importable is best.
            # For now, let's just use os.system since it's a CLI tool switch
            console.print("[dim]Opening Control Panel...[/dim]")
            await asyncio.to_thread(
                subprocess.run, 
                ["python3", "neo4jsinteract/scripts/control_panel.py"],
                check=False
            )
            # Reload config after panel close
            if self.llm:
                # Re-init LLM to pick up changes
                self.llm = UnifiedLLMService() 
            return True

        if cmd == 'connect':
            console.print("[bold bright_blue]🔌 Connect to Neo4j Database[/bold bright_blue]")
            uri = await asyncio.to_thread(Prompt.ask, "URI (default: bolt://localhost:7687)", default="bolt://localhost:7687")
            user = await asyncio.to_thread(Prompt.ask, "Username (default: neo4j)", default="neo4j")
            password = await asyncio.to_thread(Prompt.ask, "Password", password=True)
            database = await asyncio.to_thread(Prompt.ask, "Database (optional)")
            
            try:
                await self.neo4j.connect_async(uri, user, password, database if database else None)
                if self.schema_context:
                    self.schema_context.clear_cache()
                    self.mapping_task = asyncio.create_task(self._run_auto_mapping_async())
            except Exception as e:
                console.print(f"[bold bright_red]❌ Connection failed: {str(e)}[/bold bright_red]")
            return True
        
        if cmd.startswith('use '):
            parts = user_input.split()
            if len(parts) > 1:
                new_db = parts[1]
                try:
                    self.neo4j.set_database(new_db)
                    if self.schema_context:
                        self.schema_context.clear_cache()
                        console.print("[dim]Schema cache cleared. Re-mapping database...[/dim]")
                        self.mapping_task = asyncio.create_task(self._run_auto_mapping_async())
                except Exception as e:
                    console.print(f"[bold bright_red]❌ Failed to switch database: {str(e)}[/bold bright_red]")
            else:
                console.print("[bold bright_red]❌ Usage: use <database_name>[/bold bright_red]")
            return True

        if cmd == 'help':
            self.display_help()
            return True
        
        if cmd == 'clear':
            console.clear()
            self.display_welcome()
            return True
        
        if cmd == 'schema':
            if self.schema_context:
                schema = await self.schema_context.get_schema_context_async()
                console.print(Panel(Syntax(schema, "markdown"), 
                                  title="[bold bright_red]Database Schema[/bold bright_red]", 
                                  border_style="bright_blue",
                                  box=box.ROUNDED))
            else:
                console.print("[bold bright_red]Schema context not available[/bold bright_red]")
            return True
        
        if cmd == 'inspect':
            if not self.schema_inspector:
                console.print("[bold red]Schema inspector not initialized[/bold red]")
                return True
                
            console.print("[bold cyan]🔎 Interactive Schema Inspection[/bold cyan]")
            labels_input = await asyncio.to_thread(Prompt.ask, "Labels (comma sep)")
            props_input = await asyncio.to_thread(Prompt.ask, "Properties (comma sep)")
            
            labels = [l.strip() for l in labels_input.split(',') if l.strip()]
            props = [p.strip() for p in props_input.split(',') if p.strip()]
            
            if labels and props:
                await self.schema_inspector.interactive_check(labels, props)
                if self.schema_context:
                    for label in labels:
                        for prop in props:
                            values = await self.schema_inspector.inspect_value_distribution(label, prop)
                            if values:
                                self.schema_context.add_sampled_values(label, prop, values)
                                console.print(f"[dim]Added {label}.{prop} values to AI context.[/dim]")
            else:
                console.print("[yellow]Please provide both labels and properties.[/yellow]")
            return True

        if cmd == 'model':
            # Now handled via panel mostly, but keep simple switch
            if not self.llm: return True
            console.print("\n[bold cyan]🧠 Select Main Brain Model:[/bold cyan]")
            models = self.llm.model_names
            current = self.llm.main_model_name

            for i, m in enumerate(models):
                prefix = "👉" if m == current else "  "
                style = "bold green" if m == current else "white"
                console.print(f"{prefix} {i+1}. [{style}]{m}[/{style}]")

            choice = await asyncio.to_thread(Prompt.ask, "\nSelect model number", default="1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(models):
                    new_model = models[idx]
                    if self.llm.set_main_model(new_model):
                        console.print(f"[bold green]✅ Switched to {new_model}[/bold green]")
                    else:
                        console.print(f"[bold red]❌ Failed to switch to {new_model}[/bold red]")
            except ValueError:
                console.print("[red]Invalid input[/red]")
            return True

        if cmd == 'cache':
            await self._handle_cache_command()
            return True
            
        return False

    async def _handle_cache_command(self):
        """Handle cache management commands."""
        cache_manager = get_cache_manager()

        console.print("\n[bold cyan]📦 Cache Management[/bold cyan]")
        console.print("[dim]Available commands: stats, list, clear, cleanup[/dim]")

        sub_cmd = await asyncio.to_thread(Prompt.ask, "Enter cache command", default="stats")

        if sub_cmd == 'stats':
            stats = cache_manager.get_stats()
            console.print(f"\n[bold blue]Cache Statistics:[/bold blue]")
            console.print(f"Total entries: {stats['total_entries']}")
            if stats['total_entries'] > 0:
                console.print(f"Average age: {stats['average_age']:.1f} seconds")
                console.print(f"Oldest entry: {time.ctime(stats['oldest_entry'])}")
                console.print(f"Newest entry: {time.ctime(stats['newest_entry'])}")
                console.print(f"Total accesses: {stats['total_accesses']}")

        elif sub_cmd == 'list':
            entries = cache_manager.list_entries()
            if not entries:
                console.print("[dim]Cache is empty[/dim]")
            else:
                console.print(f"\n[bold blue]Cache Entries ({len(entries)}):[/bold blue]")
                from rich.table import Table
                table = Table(show_header=True)
                table.add_column("Key", style="cyan")
                table.add_column("Age (min)", style="yellow", justify="right")
                table.add_column("Access Count", style="green", justify="right")
                table.add_column("Size (KB)", style="magenta", justify="right")

                for entry in entries[:20]:  # Show first 20 entries
                    age_min = entry['age_seconds'] / 60
                    size_kb = entry['data_size'] / 1024
                    table.add_row(
                        entry['key'][:20] + "..." if len(entry['key']) > 20 else entry['key'],
                        f"{age_min:.1f}",
                        str(entry['access_count']),
                        f"{size_kb:.1f}"
                    )
                console.print(table)
                if len(entries) > 20:
                    console.print(f"[dim]... and {len(entries) - 20} more entries[/dim]")

        elif sub_cmd == 'clear':
            confirm = await asyncio.to_thread(Prompt.ask, "Clear all cache entries? (y/N)", default="n")
            if confirm.lower() in ['y', 'yes']:
                cache_manager.clear()
                console.print("[bold green]✅ Cache cleared[/bold green]")
            else:
                console.print("[dim]Cache clear cancelled[/dim]")

        elif sub_cmd == 'cleanup':
            cache_manager.cleanup()
            console.print("[bold green]✅ Cache maintenance completed[/bold green]")

        else:
            console.print(f"[red]Unknown cache command: {sub_cmd}[/red]")

    def run(self):
        """Entry point wrapper."""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            pass


def main():
    """Entry point for the application."""
    bot = GraphBot()
    bot.run()


if __name__ == "__main__":
    main()
