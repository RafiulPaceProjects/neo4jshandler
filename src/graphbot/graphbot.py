#!/usr/bin/env python3
"""Neo4j GraphBot - A CLI interface for interacting with Neo4j using natural language via Gemini API."""
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich import box

from graphbot.handlers import Neo4jHandler
from graphbot.services import GeminiService, InsightAgent
from graphbot.utils import QueryBuilder
from graphbot.core import SchemaContext

console = Console()


class GraphBot:
    """Main CLI application for Neo4j GraphBot."""
    
    def __init__(self):
        """Initialize GraphBot with Neo4j and Gemini services."""
        self.neo4j: Optional[Neo4jHandler] = None
        self.gemini: Optional[GeminiService] = None
        self.insight_agent: Optional[InsightAgent] = None
        self.schema_context: Optional[SchemaContext] = None
        self.query_builder = QueryBuilder()
        self.running = False
    
    def initialize(self):
        """Initialize connections to Neo4j and Gemini."""
        try:
            console.print("[bold bright_blue]🚀 Initializing GraphBot...[/bold bright_blue]")
            self.neo4j = Neo4jHandler()
            self.gemini = GeminiService()
            self.insight_agent = InsightAgent(self.gemini)
            self.schema_context = SchemaContext(self.neo4j)
            
            # Initial auto-mapping if connected
            self._run_auto_mapping()
            
            console.print("[bold bright_green]✅ GraphBot ready![/bold bright_green]\n")
            return True
        except Exception as e:
            console.print(f"[bold bright_red]❌ Initialization failed: {str(e)}[/bold bright_red]")
            console.print("[yellow]Please check your environment variables and try again.[/yellow]")
            return False

    def _run_auto_mapping(self):
        """Run the insight agent to map the database."""
        if not self.neo4j or not self.neo4j.driver:
            return

        console.print("\n[bold cyan]🔍 Auto-Mapping Database...[/bold cyan]")
        insights = self.insight_agent.analyze_database(self.neo4j)
        
        # Inject insights into schema context
        if self.schema_context:
            self.schema_context.set_insights(insights)
            
        # Display Summary
        if insights.get("summary"):
            console.print(Panel(insights["summary"], 
                              title="[bold green]Database Summary[/bold green]",
                              border_style="green",
                              box=box.ROUNDED))
                              
        # Display Suggested Questions
        if insights.get("suggested_questions"):
            console.print("[bold yellow]💡 Suggested Questions:[/bold yellow]")
            for q in insights["suggested_questions"]:
                console.print(f"  • {q}")
        console.print()
    
    def display_welcome(self):
        """Display welcome message."""
        welcome_text = Text()
        welcome_text.append("╔═══════════════════════════════════════╗\n", style="bold bright_blue")
        welcome_text.append("║   ", style="bold bright_blue")
        welcome_text.append("Neo4j GraphBot", style="bold bright_red on bright_blue")
        welcome_text.append("   ║\n", style="bold bright_blue")
        welcome_text.append("╚═══════════════════════════════════════╝\n", style="bold bright_blue")
        welcome_text.append("\n", style="bold bright_blue")
        welcome_text.append("Author: Rafiul Haider\n", style="bold white")
        welcome_text.append("\n", style="bold bright_blue")
        welcome_text.append("🎯 ", style="bold bright_blue")
        welcome_text.append("Your intelligent companion for Neo4j graph exploration.\n", style="bold white")
        welcome_text.append("Connect to any Neo4j database and interact using natural language.\n", style="dim white")
        welcome_text.append("\n", style="bold bright_blue")
        welcome_text.append("💡 ", style="bold bright_red")
        welcome_text.append("Quick Commands:\n", style="bold bright_blue")
        welcome_text.append("  • Type your question or request in natural language\n", style="bright_blue")
        welcome_text.append("  • Type ", style="bright_blue")
        welcome_text.append("'connect'", style="bold bright_red")
        welcome_text.append(" to change database connection\n", style="bright_blue")
        welcome_text.append("  • Type ", style="bright_blue")
        welcome_text.append("'use <db>'", style="bold bright_red")
        welcome_text.append(" to switch active database\n", style="bright_blue")
        welcome_text.append("  • Type ", style="bright_blue")
        welcome_text.append("'help'", style="bold bright_red")
        welcome_text.append(" for more commands\n", style="bright_blue")
        
        console.print(Panel(welcome_text, 
                          title="[bold bright_red]Welcome[/bold bright_red]", 
                          border_style="bright_blue",
                          box=box.DOUBLE))
        console.print()
    
    def display_help(self):
        """Display help information."""
        help_text = Text()
        help_text.append("🤖 ", style="bold bright_red")
        help_text.append("Example Queries:\n", style="bold bright_blue")
        help_text.append("  • ", style="bright_blue")
        help_text.append('"Show me all nodes"\n', style="bright_red")
        help_text.append("  • ", style="bright_blue")
        help_text.append('"Find relationships between User and Product nodes"\n', style="bright_red")
        help_text.append("  • ", style="bright_blue")
        help_text.append('"Count the number of nodes in the graph"\n', style="bright_red")
        help_text.append("  • ", style="bright_blue")
        help_text.append('"Find the shortest path between Node A and Node B"\n', style="bright_red")
        help_text.append("\n", style="bright_blue")
        help_text.append("⚙️  ", style="bold bright_red")
        help_text.append("System Commands:\n", style="bold bright_blue")
        help_text.append("  • ", style="bright_blue")
        help_text.append("connect", style="bold bright_red")
        help_text.append(" - Interactive login to a new database instance\n", style="bright_blue")
        help_text.append("  • ", style="bright_blue")
        help_text.append("use <db_name>", style="bold bright_red")
        help_text.append(" - Switch to a different database on current server\n", style="bright_blue")
        help_text.append("  • ", style="bright_blue")
        help_text.append("schema", style="bold bright_red")
        help_text.append(" - refresh and show current database schema\n", style="bright_blue")
        help_text.append("  • ", style="bright_blue")
        help_text.append("clear", style="bold bright_red")
        help_text.append(" - Clear the screen\n", style="bright_blue")
        help_text.append("  • ", style="bright_blue")
        help_text.append("model", style="bold bright_red")
        help_text.append(" - Switch the Main Brain AI model\n", style="bright_blue")
        help_text.append("  • ", style="bright_blue")
        help_text.append("quit/exit", style="bold bright_red")
        help_text.append(" - Exit the application\n", style="bright_blue")
        
        console.print(Panel(help_text, 
                          title="[bold bright_red]Help[/bold bright_red]", 
                          border_style="bright_blue",
                          box=box.DOUBLE))
        console.print()
    
    def process_query(self, user_input: str):
        """Process user input and execute query."""
        if not user_input.strip():
            return
        
        try:
            # Get schema context for better query generation
            schema_context = self.schema_context.get_schema_context() if self.schema_context else None
            
            # Generate Cypher query from natural language
            cypher_query = self.gemini.generate_cypher_query(user_input, context=schema_context)
            
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
                confirm = Prompt.ask("[bold bright_blue]Continue?[/bold bright_blue]", choices=["y", "n"], default="n")
                if confirm.lower() != "y":
                    console.print("[bold bright_red]Query cancelled.[/bold bright_red]")
                    return
            
            # Execute query
            console.print("[bold bright_blue]⚡ Executing query...[/bold bright_blue]")
            results = self.neo4j.execute_query(cypher_query)
            
            # Display results
            if results:
                self.neo4j.format_results(results)
                
                # Generate explanation
                explanation = self.gemini.explain_result(cypher_query, results, user_input)
                console.print(f"\n[bold bright_blue]💬 Explanation:[/bold bright_blue] [dim]{explanation}[/dim]")
            else:
                console.print("[bold bright_green]✅ Query executed successfully (no results returned).[/bold bright_green]")
            
        except Exception as e:
            console.print(f"[bold bright_red]❌ Error: {str(e)}[/bold bright_red]")
    
    def run(self):
        """Main application loop."""
        if not self.initialize():
            sys.exit(1)
        
        self.display_welcome()
        self.running = True
        
        while self.running:
            try:
                user_input = Prompt.ask("\n[bold bright_red]GraphBot[/bold bright_red] [bold bright_blue]→[/bold bright_blue]").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[bold bright_blue]👋 Goodbye![/bold bright_blue]")
                    break
                elif user_input.lower() == 'connect':
                    console.print("[bold bright_blue]🔌 Connect to Neo4j Database[/bold bright_blue]")
                    uri = Prompt.ask("URI (default: bolt://localhost:7687)", default="bolt://localhost:7687")
                    user = Prompt.ask("Username (default: neo4j)", default="neo4j")
                    password = Prompt.ask("Password", password=True)
                    database = Prompt.ask("Database (optional)")
                    
                    try:
                        self.neo4j.connect(uri, user, password, database if database else None)
                        # Refresh schema and insights
                        if self.schema_context:
                            self.schema_context.clear_cache()
                            self._run_auto_mapping()
                    except Exception as e:
                        console.print(f"[bold bright_red]❌ Connection failed: {str(e)}[/bold bright_red]")
                    continue
                
                elif user_input.lower().startswith('use '):
                    parts = user_input.split()
                    if len(parts) > 1:
                        new_db = parts[1]
                        try:
                            self.neo4j.set_database(new_db)
                            if self.schema_context:
                                self.schema_context.clear_cache()
                                console.print("[dim]Schema cache cleared. Re-mapping database...[/dim]")
                                self._run_auto_mapping()
                        except Exception as e:
                            console.print(f"[bold bright_red]❌ Failed to switch database: {str(e)}[/bold bright_red]")
                    else:
                        console.print("[bold bright_red]❌ Usage: use <database_name>[/bold bright_red]")
                    continue

                elif user_input.lower() == 'help':
                    self.display_help()
                    continue
                elif user_input.lower() == 'clear':
                    console.clear()
                    self.display_welcome()
                    continue
                elif user_input.lower() == 'schema':
                    if self.schema_context:
                        schema = self.schema_context.get_schema_context()
                        console.print(Panel(schema, 
                                          title="[bold bright_red]Database Schema[/bold bright_red]", 
                                          border_style="bright_blue",
                                          box=box.DOUBLE))
                    else:
                        console.print("[bold bright_red]Schema context not available[/bold bright_red]")
                    continue

                elif user_input.lower() == 'model':
                    console.print("\n[bold cyan]🧠 Select Main Brain Model:[/bold cyan]")
                    
                    # Get available models from service
                    models = self.gemini.model_names
                    current = self.gemini.main_model_name
                    
                    for i, m in enumerate(models):
                        prefix = "👉" if m == current else "  "
                        style = "bold green" if m == current else "white"
                        console.print(f"{prefix} {i+1}. [{style}]{m}[/{style}]")
                    
                    choice = Prompt.ask("\nSelect model number", default="1")
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(models):
                            new_model = models[idx]
                            if self.gemini.set_main_model(new_model):
                                console.print(f"[bold green]✅ Switched to {new_model}[/bold green]")
                            else:
                                console.print(f"[bold red]❌ Failed to switch to {new_model}[/bold red]")
                        else:
                            console.print("[red]Invalid selection[/red]")
                    except ValueError:
                        console.print("[red]Invalid input[/red]")
                    continue
                
                # Process natural language query
                self.process_query(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[bold bright_red]⚠️  Interrupted. Type 'quit' to exit.[/bold bright_red]")
            except EOFError:
                console.print("\n[bold bright_blue]👋 Goodbye![/bold bright_blue]")
                break
            except Exception as e:
                console.print(f"[bold bright_red]❌ Unexpected error: {str(e)}[/bold bright_red]")
        
        # Cleanup
        if self.neo4j:
            self.neo4j.close()


def main():
    """Entry point for the application."""
    bot = GraphBot()
    bot.run()


if __name__ == "__main__":
    main()

