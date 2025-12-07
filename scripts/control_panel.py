#!/usr/bin/env python3
"""
Control Panel for Neo4j GraphBot.
Manages LLM profiles, context settings, and monitors usage.
"""
import os
import sys
import yaml
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# Add src to path to import internal modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from graphbot.services.llm import LLMFactory

console = Console()
CONFIG_PATH = "config/providers.yaml"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        console.print(f"[red]Config file not found at {CONFIG_PATH}[/red]")
        sys.exit(1)
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    console.print(f"[green]Configuration saved to {CONFIG_PATH}[/green]")

def show_status(config):
    active_profile = config.get('active_profile')
    profiles = config.get('profiles', {})
    
    console.print(Panel.fit(
        f"[bold blue]Neo4j GraphBot Control Panel[/bold blue]\n"
        f"Active Profile: [bold green]{active_profile}[/bold green]",
        subtitle="v1.0"
    ))

    table = Table(title="Available LLM Profiles")
    table.add_column("Profile Name", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Main Model", style="green")
    table.add_column("Max Tokens", style="yellow")
    table.add_column("Status", justify="center")

    for name, details in profiles.items():
        is_active = (name == active_profile)
        status_mark = "✅" if is_active else " "
        table.add_row(
            name,
            details.get('provider', 'unknown'),
            details.get('models', {}).get('main', 'unknown'),
            str(details.get('max_context_tokens', 'N/A')),
            status_mark
        )
    
    console.print(table)

def switch_profile(config):
    profiles = list(config.get('profiles', {}).keys())
    
    if not profiles:
        console.print("[red]No profiles defined![/red]")
        return

    choice = Prompt.ask("Enter profile name to activate", choices=profiles)
    
    if choice:
        config['active_profile'] = choice
        save_config(config)
        console.print(f"[green]Switched to profile: {choice}[/green]")

async def test_connection(config):
    console.print("\n[bold]Testing connection with active profile...[/bold]")
    try:
        # Re-initialize factory/provider with current config
        provider = LLMFactory.get_provider(CONFIG_PATH)
        
        console.print(f"Provider: [cyan]{type(provider).__name__}[/cyan]")
        
        with console.status("[bold green]Sending test request..."):
            response = await provider.generate_text("Hello! distinct short reply.", system_instruction="You are a test bot.")
            
        console.print(f"[green]Success![/green]")
        console.print(f"[dim]Response: {response.content}[/dim]")
        if response.token_usage:
            console.print(f"[dim]Token Usage: {response.token_usage}[/dim]")
            
    except Exception as e:
        console.print(f"[bold red]Connection failed:[/bold red] {e}")

def main():
    while True:
        config = load_config()
        console.clear()
        show_status(config)
        
        console.print("\n[bold]Actions:[/bold]")
        console.print("1. [bold cyan]S[/bold cyan]witch Profile")
        console.print("2. [bold cyan]T[/bold cyan]est Connection")
        console.print("3. [bold cyan]E[/bold cyan]xit")
        
        action = Prompt.ask("\nSelect action", choices=["1", "2", "3", "s", "t", "e", "S", "T", "E"], default="3")
        
        if action.lower() in ['1', 's']:
            switch_profile(config)
            Prompt.ask("Press Enter to continue...")
        elif action.lower() in ['2', 't']:
            asyncio.run(test_connection(config))
            Prompt.ask("Press Enter to continue...")
        elif action.lower() in ['3', 'e']:
            console.print("Goodbye!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\nExiting...")

