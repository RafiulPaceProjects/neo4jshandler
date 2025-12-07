"""Neo4j database connection and query execution handler."""
import os
import asyncio
from typing import Any, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import (
    ServiceUnavailable,
    AuthError,
    ClientError,
    TransientError,
    DatabaseError,
)
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load environment variables from .env or config.env
load_dotenv()  # Try .env first
config_file = os.getenv("CONFIG_FILE", "config/config.env")
if os.path.exists(config_file):
    load_dotenv(config_file)  # Load config.env if it exists

console = Console()

# Custom exceptions
class Neo4jConnectionError(Exception):
    """Raised when connection to Neo4j fails."""
    pass

class Neo4jQueryError(Exception):
    """Raised when query execution fails."""
    pass

# Retry configuration
MAX_QUERY_RETRIES = 2
RETRY_DELAY = 0.5


class Neo4jHandler:
    """Handles Neo4j database connections and query execution using Async Driver."""
    
    def __init__(self):
        """Initialize Neo4j connection parameters."""
        self.uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE", "healthproject")
        
        if not self.password:
            raise ValueError("NEO4J_PASSWORD environment variable is required")
        
        self.driver: Optional[AsyncDriver] = None
        
        # Initialize driver immediately but verification happens in connect/execute
        self._init_driver()
    
    def _init_driver(self):
        """Initialize the driver instance."""
        try:
            # Create async driver
            # Note: This doesn't establish a connection yet, just configures the driver
            self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
        except Exception as e:
            console.print(f"[bold bright_red]❌ Failed to create Neo4j driver: {str(e)}[/bold bright_red]")
            self.driver = None

    def connect(self, uri, user, password, database=None):
        """Synchronous wrapper for connect."""
        asyncio.run(self.connect_async(uri, user, password, database))

    async def connect_async(self, uri, user, password, database=None):
        """
        Connect to a Neo4j database with specific credentials.
        
        Args:
            uri: Connection URI
            user: Username
            password: Password
            database: Database name (optional)
        """
        # Close existing connection if open
        await self.close_async()
        
        self.uri = uri
        self.user = user
        self.password = password
        if database:
            self.database = database
            
        # Re-initialize driver
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
        
        # Verify connectivity
        if await self.verify_connectivity_async():
            console.print(f"[bold bright_green]✅ Connected to Neo4j at {self.uri}[/bold bright_green]")
            console.print(f"[bold bright_blue]📊 Using database: {self.database}[/bold bright_blue]")
        else:
            console.print(f"[bold bright_red]❌ Failed to connect to Neo4j at {self.uri}[/bold bright_red]")

    def set_database(self, database):
        """
        Switch to a different database using current credentials.
        
        Args:
            database: Name of the database to switch to
        """
        self.database = database
        console.print(f"[bold bright_blue]🔄 Switched to database: {self.database}[/bold bright_blue]")

    def test_connection(self) -> bool:
        """Synchronous wrapper for test_connection."""
        return asyncio.run(self.verify_connectivity_async())

    async def verify_connectivity_async(self) -> bool:
        """
        Test the current connection parameters.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        if not self.driver:
            return False
            
        try:
            await self.driver.verify_connectivity()
            return True
        except AuthError as e:
            console.print(f"[bold red]❌ Authentication failed: Invalid credentials[/bold red]")
            console.print(f"[red]   {str(e)[:100]}[/red]")
            return False
        except ServiceUnavailable as e:
            console.print(f"[bold red]❌ Neo4j service unavailable[/bold red]")
            console.print(f"[red]   {str(e)[:100]}[/red]")
            console.print(f"[yellow]💡 Check that Neo4j is running and accessible at {self.uri}[/yellow]")
            return False
        except Exception as e:
            console.print(f"[dim red]Connection check failed: {str(e)[:100]}[/dim red]")
            return False

    def execute_query(self, query: str, parameters: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """Synchronous wrapper for execute_query_async."""
        return asyncio.run(self.execute_query_async(query, parameters))

    async def execute_query_async(self, query: str, parameters: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """
        Execute a Cypher query and return results asynchronously with retry for transient errors.
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            List of result records as dictionaries
            
        Raises:
            Neo4jConnectionError: If not connected to database
            Neo4jQueryError: If query execution fails
        """
        if not self.driver:
            raise Neo4jConnectionError("Not connected to Neo4j database")
        
        last_error = None
        
        for attempt in range(MAX_QUERY_RETRIES):
            try:
                async with self.driver.session(database=self.database) as session:
                    result = await session.run(query, parameters or {})
                    # Fetch all records
                    records_list = [record async for record in result]
                    
                    records = []
                    for record in records_list:
                        # Convert Neo4j record to dictionary
                        record_dict = {}
                        for key in record.keys():
                            value = record[key]
                            # Convert Neo4j types to Python types
                            if hasattr(value, '__class__'):
                                if value.__class__.__name__ == 'Node':
                                    record_dict[key] = {
                                        'type': 'Node',
                                        'id': value.id,
                                        'labels': list(value.labels),
                                        'properties': dict(value)
                                    }
                                elif value.__class__.__name__ == 'Relationship':
                                    record_dict[key] = {
                                        'type': 'Relationship',
                                        'id': value.id,
                                        'type_name': value.type,
                                        'start_node': value.start_node.id,
                                        'end_node': value.end_node.id,
                                        'properties': dict(value)
                                    }
                                else:
                                    record_dict[key] = value
                            else:
                                record_dict[key] = value
                        records.append(record_dict)
                    return records
                    
            except AuthError as e:
                console.print(f"[bold red]❌ Authentication error: {str(e)[:100]}[/bold red]")
                raise Neo4jQueryError(f"Authentication failed: {str(e)[:100]}") from e
                
            except ClientError as e:
                # Syntax errors, constraint violations, etc. - don't retry
                error_msg = str(e)
                console.print(f"[bold red]❌ Query error: {error_msg[:200]}[/bold red]")
                
                # Provide helpful hints based on error type
                if "SyntaxError" in error_msg:
                    console.print(f"[yellow]💡 Check your Cypher query syntax.[/yellow]")
                elif "ConstraintViolation" in error_msg:
                    console.print(f"[yellow]💡 A constraint was violated. Check unique constraints.[/yellow]")
                elif "not found" in error_msg.lower():
                    console.print(f"[yellow]💡 A referenced label, property, or relationship type may not exist.[/yellow]")
                    
                raise Neo4jQueryError(f"Query failed: {error_msg[:200]}") from e
                
            except TransientError as e:
                # Transient errors can be retried
                last_error = e
                if attempt < MAX_QUERY_RETRIES - 1:
                    console.print(f"[dim yellow]⚠️  Transient error, retrying ({attempt + 1}/{MAX_QUERY_RETRIES})...[/dim yellow]")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                console.print(f"[bold red]❌ Query failed after {MAX_QUERY_RETRIES} retries: {str(e)[:100]}[/bold red]")
                raise Neo4jQueryError(f"Query failed after retries: {str(e)[:100]}") from e
                
            except ServiceUnavailable as e:
                # Connection lost - could retry
                last_error = e
                if attempt < MAX_QUERY_RETRIES - 1:
                    console.print(f"[dim yellow]⚠️  Connection lost, retrying ({attempt + 1}/{MAX_QUERY_RETRIES})...[/dim yellow]")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                console.print(f"[bold red]❌ Neo4j service unavailable: {str(e)[:100]}[/bold red]")
                raise Neo4jConnectionError(f"Service unavailable: {str(e)[:100]}") from e
                
            except DatabaseError as e:
                console.print(f"[bold red]❌ Database error: {str(e)[:100]}[/bold red]")
                raise Neo4jQueryError(f"Database error: {str(e)[:100]}") from e
                
            except Exception as e:
                console.print(f"[bold red]❌ Unexpected query error: {str(e)[:100]}[/bold red]")
                raise Neo4jQueryError(f"Unexpected error: {str(e)[:100]}") from e
        
        # Should not reach here
        raise Neo4jQueryError(f"Query failed: {last_error}")
    
    def format_results(self, results: list[dict[str, Any]]) -> str:
        """
        Format query results for display.
        
        Args:
            results: List of result records
            
        Returns:
            Formatted string representation
        """
        if not results:
            return "No results returned."
        
        # Create a table for better display
        table = Table(show_header=True, 
                     header_style="bold bright_red on bright_blue",
                     border_style="bright_blue",
                     row_styles=["bright_blue", "bright_red"])
        
        # Get all keys from all records
        all_keys = set()
        for record in results:
            all_keys.update(record.keys())
        
        if not all_keys:
            return "Empty results."
        
        # Add columns
        for key in sorted(all_keys):
            table.add_column(key, overflow="fold")
        
        # Add rows
        for record in results:
            row_values = []
            for key in sorted(all_keys):
                value = record.get(key, "")
                # Format complex types
                if isinstance(value, dict):
                    if value.get('type') == 'Node':
                        labels = ':'.join(value.get('labels', []))
                        props = ', '.join([f"{k}: {v}" for k, v in value.get('properties', {}).items()])
                        row_values.append(f"({labels} {{{props}}})")
                    elif value.get('type') == 'Relationship':
                        rel_type = value.get('type_name', '')
                        props = ', '.join([f"{k}: {v}" for k, v in value.get('properties', {}).items()])
                        row_values.append(f"-[{rel_type} {{{props}}}]->")
                    else:
                        row_values.append(str(value))
                elif isinstance(value, list):
                    row_values.append(str(value))
                else:
                    row_values.append(str(value))
            table.add_row(*row_values)
        
        # Display the table
        console.print(table)
        
        # We return a simple summary string, or we could return the table object if desired.
        # But per existing signature, we return string.
        # We can capture it properly if needed, but the original code was capturing it for testing AND printing.
        # Let's just print it and return a summary.
        return f"{len(results)} record(s) returned."
    
    def close(self):
        """Synchronous wrapper for close_async."""
        asyncio.run(self.close_async())

    async def close_async(self):
        """Close the database connection asynchronously."""
        if self.driver:
            await self.driver.close()
            console.print("[bold bright_blue]🔌 Disconnected from Neo4j[/bold bright_blue]")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    async def __aenter__(self):
        """Async Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async Context manager exit."""
        await self.close_async()
