"""Neo4j database connection and query execution handler."""
import os
from typing import Optional, Dict, Any, List
from neo4j import GraphDatabase, Driver, Session
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load environment variables from .env or config.env
load_dotenv()  # Try .env first
config_file = os.getenv("CONFIG_FILE", "config/config.env")
if os.path.exists(config_file):
    load_dotenv(config_file)  # Load config.env if it exists

console = Console()


class Neo4jHandler:
    """Handles Neo4j database connections and query execution."""
    
    def __init__(self):
        """Initialize Neo4j connection using environment variables."""
        self.uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE", "healthproject")
        
        if not self.password:
            raise ValueError("NEO4J_PASSWORD environment variable is required")
        
        self.driver: Optional[Driver] = None
        self._connect()
    
    def connect(self, uri, user, password, database=None):
        """
        Connect to a Neo4j database with specific credentials.
        
        Args:
            uri: Connection URI
            user: Username
            password: Password
            database: Database name (optional)
        """
        # Close existing connection if open
        self.close()
        
        self.uri = uri
        self.user = user
        self.password = password
        if database:
            self.database = database
            
        self._connect()

    def set_database(self, database):
        """
        Switch to a different database using current credentials.
        
        Args:
            database: Name of the database to switch to
        """
        self.database = database
        console.print(f"[bold bright_blue]🔄 Switched to database: {self.database}[/bold bright_blue]")

    def test_connection(self) -> bool:
        """
        Test the current connection parameters.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False


    def _connect(self):
        """Establish connection to Neo4j database."""
        # Prefer bolt:// for direct connections (avoids routing issues)
        # Try different URI schemes if the default fails
        uris_to_try = [
            self.uri,
            self.uri.replace("neo4j://", "bolt://"),  # Try bolt first if originally neo4j
            self.uri.replace("127.0.0.1", "localhost"),
            self.uri.replace("neo4j://127.0.0.1", "bolt://localhost"),
            "bolt://host.docker.internal:7687", # Add Docker host fallback
        ]
        
        last_error = None
        for test_uri in uris_to_try:
            try:
                # IMPORTANT: Create a new driver for each attempt
                # Closing the old one if it exists to clean up
                if self.driver:
                    self.driver.close()
                
                self.driver = GraphDatabase.driver(test_uri, auth=(self.user, self.password))
                # Verify connection
                self.driver.verify_connectivity()
                
                # If we get here, connection works!
                console.print(f"[bold bright_green]✅ Connected to Neo4j at {test_uri}[/bold bright_green]")
                console.print(f"[bold bright_blue]📊 Using database: {self.database}[/bold bright_blue]")
                self.uri = test_uri  # Update to working URI
                return
            except Exception as e:
                last_error = e
                # Don't print every failure, just continue
                continue
        
        # If all attempts failed, show detailed error
        console.print(f"[bold bright_red]❌ Failed to connect to Neo4j[/bold bright_red]")
        console.print(f"[bright_red]   Tried URIs: {', '.join(uris_to_try)}[/bright_red]")
        console.print(f"[bright_red]   Error: {str(last_error)}[/bright_red]")
        console.print(f"[yellow]   Tip: Run 'python3 test_connection.py' to diagnose connection issues[/yellow]")
        raise ConnectionError(f"Failed to connect to Neo4j: {str(last_error)}")
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j database")
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                records = []
                for record in result:
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
        except Exception as e:
            console.print(f"[bold bright_red]❌ Query execution error: {str(e)}[/bold bright_red]")
            raise
    
    def format_results(self, results: List[Dict[str, Any]]) -> str:
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
        
        console.print(table)
        return f"\n{len(results)} record(s) returned."
    
    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            console.print("[bold bright_blue]🔌 Disconnected from Neo4j[/bold bright_blue]")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

