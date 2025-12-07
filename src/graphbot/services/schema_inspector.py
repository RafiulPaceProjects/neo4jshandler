"""Inspector service to sample property values for better query accuracy."""
import asyncio
from typing import Any, Optional
from rich.console import Console
from graphbot.handlers import Neo4jHandler

console = Console()

# Constants
MAX_INSPECTION_RETRIES = 2
INSPECTION_RETRY_DELAY = 0.5


class SchemaInspector:
    """Service to inspect database content and sample values."""
    
    def __init__(self, neo4j_handler: Neo4jHandler):
        """Initialize with Neo4j handler."""
        self.neo4j = neo4j_handler
        
    async def inspect_value_distribution(self, label: str, property_name: str, limit: int = 10) -> list[Any]:
        """
        Fetch a sample of distinct values for a specific property with retry logic.
        
        Args:
            label: Node label
            property_name: Property name
            limit: Max number of samples
            
        Returns:
            List of distinct values
        """
        # Validate inputs to prevent issues
        if not label or not property_name:
            console.print(f"[yellow]⚠️  Invalid label or property name[/yellow]")
            return []
        
        # Basic sanitization (escape backticks)
        safe_label = label.replace('`', '``')
        safe_prop = property_name.replace('`', '``')
        
        query = f"""
        MATCH (n:`{safe_label}`)
        WHERE n.`{safe_prop}` IS NOT NULL
        RETURN DISTINCT n.`{safe_prop}` as val
        LIMIT $limit
        """
        
        last_error = None
        for attempt in range(MAX_INSPECTION_RETRIES):
            try:
                results = await self.neo4j.execute_query_async(query, {"limit": limit})
                return [r["val"] for r in results]
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check if error is retryable (transient/connection errors)
                if any(pattern in error_str for pattern in ['transient', 'unavailable', 'timeout', 'connection']):
                    if attempt < MAX_INSPECTION_RETRIES - 1:
                        await asyncio.sleep(INSPECTION_RETRY_DELAY * (attempt + 1))
                        continue
                # Non-retryable error or last attempt
                break
        
        console.print(f"[yellow]⚠️  Could not inspect values: {str(last_error)[:100] if last_error else 'Unknown error'}[/yellow]")
        return []

    async def interactive_check(self, potential_labels: list[str], suspected_properties: list[str]):
        """
        Interactively check values for suspected properties.
        
        Args:
            potential_labels: List of node labels to check
            suspected_properties: List of property names to check
        """
        if not potential_labels or not suspected_properties:
            console.print("[yellow]⚠️  Please provide both labels and properties to inspect.[/yellow]")
            return
            
        console.print("\n[bold cyan]🔎 Interactive Schema Inspector[/bold cyan]")
        
        for label in potential_labels:
            for prop in suspected_properties:
                try:
                    console.print(f"Checking [bold]{label}.{prop}[/bold]...")
                    values = await self.inspect_value_distribution(label, prop)
                    
                    if values:
                        # Safely convert values to strings for display
                        display_values = []
                        for v in values:
                            try:
                                display_values.append(str(v)[:50])  # Truncate long values
                            except Exception:
                                display_values.append("<unprintable>")
                        
                        console.print(f"  Found sample values: [dim]{', '.join(display_values)}[/dim]")
                        
                        # Heuristic: if boolean-like
                        if any(str(v).lower() in ['true', 'false', 'yes', 'no', '1', '0'] for v in values):
                            console.print(f"  [green]💡 Hint: This looks like a flag/boolean field.[/green]")
                    else:
                        console.print(f"  [dim]No values found or property doesn't exist.[/dim]")
                        
                except Exception as e:
                    console.print(f"  [red]Error checking {label}.{prop}: {str(e)[:50]}[/red]")
