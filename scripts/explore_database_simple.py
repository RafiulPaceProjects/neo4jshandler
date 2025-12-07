#!/usr/bin/env python3
"""Explore Neo4j database structure - simple version."""
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from neo4j import GraphDatabase
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Load environment variables from .env or config.env
load_dotenv()
config_file = os.getenv("CONFIG_FILE", "config/config.env")
if os.path.exists(config_file):
    load_dotenv(config_file)

console = Console()

uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "healthproject")

if not password:
    console.print("[red]NEO4J_PASSWORD not set![/red]")
    exit(1)

# Try bolt:// if neo4j:// fails (bypasses routing)
if uri.startswith("neo4j://"):
    bolt_uri = uri.replace("neo4j://", "bolt://")
else:
    bolt_uri = uri

console.print(f"[cyan]Connecting to Neo4j at {bolt_uri}...[/cyan]")

try:
    driver = GraphDatabase.driver(bolt_uri, auth=(user, password))
    driver.verify_connectivity()
    console.print("[green]✓ Connected[/green]\n")
    
    # Use session with database parameter
    console.print(f"[cyan]Using database: {database}[/cyan]\n")
    with driver.session(database=database) as session:
        # Get all node labels
        console.print("[bold]Node Labels:[/bold]")
        try:
            result = session.run("CALL db.labels()")
            labels = [record["label"] for record in result]
            if labels:
                console.print(f"  Found {len(labels)} label(s): {', '.join(labels)}")
            else:
                console.print("  No labels found")
        except Exception as e:
            console.print(f"  Error: {str(e)}")
            # Fallback: query nodes directly
            result = session.run("MATCH (n) RETURN DISTINCT labels(n) as labels LIMIT 100")
            labels_set = set()
            for record in result:
                labels_set.update(record["labels"])
            labels = list(labels_set)
            if labels:
                console.print(f"  Found {len(labels)} label(s): {', '.join(labels)}")
        
        # Get all relationship types
        console.print("\n[bold]Relationship Types:[/bold]")
        try:
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in result]
            if rel_types:
                console.print(f"  Found {len(rel_types)} relationship type(s): {', '.join(rel_types)}")
            else:
                console.print("  No relationship types found")
        except Exception as e:
            console.print(f"  Error: {str(e)}")
            # Fallback: query relationships directly
            result = session.run("MATCH ()-[r]->() RETURN DISTINCT type(r) as type LIMIT 100")
            rel_types = [record["type"] for record in result]
            if rel_types:
                console.print(f"  Found {len(rel_types)} relationship type(s): {', '.join(rel_types)}")
        
        # Get node counts per label
        if labels:
            console.print("\n[bold]Node Counts by Label:[/bold]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Label", style="cyan")
            table.add_column("Count", style="green")
            
            for label in labels:
                try:
                    result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    count = result.single()["count"]
                    table.add_row(label, str(count))
                except Exception as e:
                    table.add_row(label, f"Error: {str(e)[:30]}")
            
            console.print(table)
        
        # Get relationship counts
        if rel_types:
            console.print("\n[bold]Relationship Counts by Type:[/bold]")
            rel_table = Table(show_header=True, header_style="bold magenta")
            rel_table.add_column("Type", style="cyan")
            rel_table.add_column("Count", style="green")
            
            for rel_type in rel_types:
                try:
                    result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                    count = result.single()["count"]
                    rel_table.add_row(rel_type, str(count))
                except Exception as e:
                    rel_table.add_row(rel_type, f"Error: {str(e)[:30]}")
            
            console.print(rel_table)
        
        # Get sample nodes with their properties
        if labels:
            console.print("\n[bold]Sample Nodes (first 3 of each label):[/bold]")
            for label in labels[:10]:  # Limit to first 10 labels
                try:
                    result = session.run(f"MATCH (n:{label}) RETURN n LIMIT 3")
                    nodes = [record["n"] for record in result]
                    if nodes:
                        console.print(f"\n  [cyan]{label}:[/cyan]")
                        for i, node in enumerate(nodes, 1):
                            props = dict(node)
                            # Show first few properties
                            prop_str = ", ".join([f"{k}: {str(v)[:30]}" for k, v in list(props.items())[:5]])
                            if len(props) > 5:
                                prop_str += f" ... ({len(props)} total properties)"
                            console.print(f"    {i}. {prop_str}")
                except Exception as e:
                    console.print(f"    Error getting {label}: {str(e)[:50]}")
        
        # Get sample relationships
        if rel_types:
            console.print("\n[bold]Sample Relationships:[/bold]")
            for rel_type in rel_types[:10]:  # Limit to first 10 types
                try:
                    result = session.run(f"MATCH (a)-[r:{rel_type}]->(b) RETURN a, r, b LIMIT 2")
                    rels = [(record["a"], record["r"], record["b"]) for record in result]
                    if rels:
                        console.print(f"\n  [cyan]{rel_type}:[/cyan]")
                        for i, (a, r, b) in enumerate(rels, 1):
                            a_labels = list(a.labels)
                            b_labels = list(b.labels)
                            console.print(f"    {i}. ({':'.join(a_labels)})-[{rel_type}]->({':'.join(b_labels)})")
                except Exception as e:
                    console.print(f"    Error getting {rel_type}: {str(e)[:50]}")
        
        # Get database statistics
        console.print("\n[bold]Database Statistics:[/bold]")
        try:
            result = session.run("MATCH (n) RETURN count(n) as total_nodes")
            total_nodes = result.single()["total_nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as total_rels")
            total_rels = result.single()["total_rels"]
            
            stats_text = f"Total Nodes: {total_nodes}\nTotal Relationships: {total_rels}"
            console.print(Panel(stats_text, title="Summary", border_style="green"))
        except Exception as e:
            console.print(f"  Error: {str(e)}")
        
    driver.close()
    console.print("\n[green]✓ Database exploration complete![/green]")
    
except Exception as e:
    console.print(f"[red]Error: {str(e)}[/red]")
    import traceback
    traceback.print_exc()
    exit(1)

