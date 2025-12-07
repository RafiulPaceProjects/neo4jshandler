#!/usr/bin/env python3
"""Explore Neo4j database structure to understand schema."""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

load_dotenv()

console = Console()

uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "healthproject")

if not password:
    console.print("[red]NEO4J_PASSWORD not set![/red]")
    exit(1)

console.print(f"[cyan]Connecting to database: {database}[/cyan]")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    
    # Try with database parameter, fallback to default if it fails
    try:
        session = driver.session(database=database)
        # Test the session
        session.run("RETURN 1").single()
    except Exception as e:
        console.print(f"[yellow]Database '{database}' not accessible, using default database[/yellow]")
        session = driver.session()
    
    with session:
        # Get all node labels
        console.print("\n[bold]Node Labels:[/bold]")
        result = session.run("CALL db.labels()")
        labels = [record["label"] for record in result]
        if labels:
            console.print(f"  Found {len(labels)} label(s): {', '.join(labels)}")
        else:
            console.print("  No labels found")
        
        # Get all relationship types
        console.print("\n[bold]Relationship Types:[/bold]")
        result = session.run("CALL db.relationshipTypes()")
        rel_types = [record["relationshipType"] for record in result]
        if rel_types:
            console.print(f"  Found {len(rel_types)} relationship type(s): {', '.join(rel_types)}")
        else:
            console.print("  No relationship types found")
        
        # Get node counts per label
        console.print("\n[bold]Node Counts by Label:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Label", style="cyan")
        table.add_column("Count", style="green")
        
        for label in labels:
            result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            count = result.single()["count"]
            table.add_row(label, str(count))
        
        console.print(table)
        
        # Get relationship counts
        console.print("\n[bold]Relationship Counts by Type:[/bold]")
        rel_table = Table(show_header=True, header_style="bold magenta")
        rel_table.add_column("Type", style="cyan")
        rel_table.add_column("Count", style="green")
        
        for rel_type in rel_types:
            result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
            count = result.single()["count"]
            rel_table.add_row(rel_type, str(count))
        
        console.print(rel_table)
        
        # Get sample nodes with their properties
        console.print("\n[bold]Sample Nodes (first 5 of each label):[/bold]")
        for label in labels[:5]:  # Limit to first 5 labels
            result = session.run(f"MATCH (n:{label}) RETURN n LIMIT 5")
            nodes = [record["n"] for record in result]
            if nodes:
                console.print(f"\n  [cyan]{label}:[/cyan]")
                for i, node in enumerate(nodes, 1):
                    props = dict(node)
                    # Show first few properties
                    prop_str = ", ".join([f"{k}: {v}" for k, v in list(props.items())[:3]])
                    if len(props) > 3:
                        prop_str += f" ... ({len(props)} total properties)"
                    console.print(f"    {i}. {prop_str}")
        
        # Get sample relationships
        console.print("\n[bold]Sample Relationships:[/bold]")
        for rel_type in rel_types[:5]:  # Limit to first 5 types
            result = session.run(f"MATCH (a)-[r:{rel_type}]->(b) RETURN a, r, b LIMIT 3")
            rels = [(record["a"], record["r"], record["b"]) for record in result]
            if rels:
                console.print(f"\n  [cyan]{rel_type}:[/cyan]")
                for i, (a, r, b) in enumerate(rels, 1):
                    a_labels = list(a.labels)
                    b_labels = list(b.labels)
                    a_id = list(dict(a).keys())[0] if dict(a) else "node"
                    b_id = list(dict(b).keys())[0] if dict(b) else "node"
                    console.print(f"    {i}. ({':'.join(a_labels)})-[{rel_type}]->({':'.join(b_labels)})")
        
        # Get property keys used in the database
        console.print("\n[bold]Property Keys (top 20):[/bold]")
        result = session.run("CALL db.propertyKeys()")
        prop_keys = [record["propertyKey"] for record in result][:20]
        if prop_keys:
            console.print(f"  {', '.join(prop_keys)}")
            if len(prop_keys) == 20:
                console.print("  ... (showing first 20)")
        
        # Get database statistics
        console.print("\n[bold]Database Statistics:[/bold]")
        result = session.run("MATCH (n) RETURN count(n) as total_nodes")
        total_nodes = result.single()["total_nodes"]
        result = session.run("MATCH ()-[r]->() RETURN count(r) as total_rels")
        total_rels = result.single()["total_rels"]
        
        stats_text = f"Total Nodes: {total_nodes}\nTotal Relationships: {total_rels}"
        console.print(Panel(stats_text, title="Summary", border_style="green"))
        
    driver.close()
    console.print("\n[green]✓ Database exploration complete![/green]")
    
except Exception as e:
    console.print(f"[red]Error: {str(e)}[/red]")
    exit(1)

