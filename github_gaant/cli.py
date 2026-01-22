"""CLI for GitHub Gaant."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import get_github_token, load_config, save_config
from .models import Config, DateFieldConfig
from .parsers.mermaid_gen import (
    generate_mermaid_gantt,
    generate_mermaid_with_hierarchy,
    generate_table_view,
    save_mermaid_to_file,
)
from .sync import ChangeType, get_status, pull_from_github, push_to_github, file_exists, load_project

app = typer.Typer(
    name="gaant",
    help="Manage GitHub Issues as Gantt chart tasks",
    add_completion=False,
)
console = Console()


@app.command()
def init(
    repo: str = typer.Option(
        ..., 
        "--repo", "-r",
        help="Repository in format 'owner/repo'",
        prompt="Repository (owner/repo)"
    ),
    project_number: int = typer.Option(
        ..., 
        "--project", "-p",
        help="GitHub Project number",
        prompt="Project number"
    ),
    start_field: str = typer.Option(
        "Start Date",
        "--start-field",
        help="Name of the start date field in your Project"
    ),
    end_field: str = typer.Option(
        "Due Date",
        "--end-field", 
        help="Name of the end/due date field in your Project"
    ),
    output: str = typer.Option(
        "gaant.yaml",
        "--output", "-o",
        help="Output file name (.yaml or .xlsx)"
    ),
):
    """Initialize a new GitHub Gaant configuration."""
    # Validate extension
    if not output.endswith(('.yaml', '.yml', '.xlsx')):
        console.print("[yellow]Warning: Using .yaml extension. Supported: .yaml, .xlsx[/yellow]")
        output = output + ".yaml"
    
    config = Config(
        repo=repo,
        project_number=project_number,
        date_fields=DateFieldConfig(start=start_field, end=end_field),
        output_file=output,
    )
    
    config_path = Path("config.yaml")
    save_config(config, config_path)
    
    console.print(f"[green]✓ Created {config_path}[/green]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Add your GITHUB_TOKEN to .env file")
    console.print("2. Run 'gaant pull' to fetch issues from GitHub")
    
    # Create .env if it doesn't exist
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text("GITHUB_TOKEN=ghp_your_token_here\n")
        console.print(f"[green]✓ Created {env_path} (add your token)[/green]")


@app.command()
def pull(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config.yaml"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (.yaml or .xlsx, overrides config)"
    ),
):
    """Pull issues from GitHub and save to local file (YAML or Excel)."""
    try:
        config = load_config(config_path)
        project = pull_from_github(config, output)
        
        console.print(Panel(
            f"[bold]{project.title}[/bold]\n"
            f"Tasks: {project.total_tasks}\n"
            f"Progress: {project.overall_progress}%",
            title="Project Summary"
        ))
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def push(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config.yaml"
    ),
    source: Optional[Path] = typer.Option(
        None,
        "--source", "-s",
        help="Source file path (.yaml or .xlsx, overrides config)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run", "-n",
        help="Show what would be done without making changes"
    ),
    enforce_subissues: bool = typer.Option(
        False,
        "--enforce-subissues",
        help="Ensure all subtasks are linked as sub-issues to their parents in GitHub"
    ),
):
    """Push local changes to GitHub."""
    try:
        config = load_config(config_path)
        changes = push_to_github(config, source, dry_run, enforce_subissues)
        
        if changes:
            new_count = sum(1 for c in changes if c.change_type == ChangeType.NEW)
            mod_count = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED)
            console.print(f"\n[green]Summary: {new_count} new, {mod_count} modified[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config.yaml"
    ),
):
    """Show differences between local file and GitHub."""
    try:
        config = load_config(config_path)
        changes = get_status(config)
        
        if not changes:
            console.print("[green]✓ No changes detected[/green]")
            return
        
        table = Table(title="Changes")
        table.add_column("Type", style="bold")
        table.add_column("Issue")
        table.add_column("Details")
        
        for change in changes:
            if change.change_type == ChangeType.NEW:
                table.add_row(
                    "[green]NEW[/green]",
                    change.local_task.title if change.local_task else "-",
                    ", ".join(change.changes)
                )
            elif change.change_type == ChangeType.MODIFIED:
                table.add_row(
                    "[yellow]MODIFIED[/yellow]",
                    f"#{change.issue_number}",
                    ", ".join(change.changes)
                )
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def view(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config.yaml"
    ),
    source: Optional[Path] = typer.Option(
        None,
        "--source", "-s",
        help="Source file path (.yaml or .xlsx)"
    ),
    format: str = typer.Option(
        "mermaid",
        "--format", "-f",
        help="Output format: mermaid, hierarchy, table"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Save to file instead of printing"
    ),
    no_weekends: bool = typer.Option(
        True,
        "--no-weekends/--weekends",
        help="Exclude weekends from Gantt chart"
    ),
):
    """Generate a visual representation of the Gantt chart."""
    try:
        config = load_config(config_path)
        
        if source is None:
            source = Path(config.output_file)
        
        if not file_exists(source):
            console.print(f"[red]Error: {source} not found. Run 'gaant pull' first.[/red]")
            raise typer.Exit(1)
        
        project = load_project(source)
        
        if format == "mermaid":
            content = generate_mermaid_gantt(
                project, 
                exclude_weekends=no_weekends,
                group_by_milestone=True
            )
        elif format == "hierarchy":
            content = generate_mermaid_with_hierarchy(
                project,
                exclude_weekends=no_weekends
            )
        elif format == "table":
            content = generate_table_view(project)
        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            raise typer.Exit(1)
        
        if output:
            save_mermaid_to_file(content, output)
            console.print(f"[green]✓ Saved to {output}[/green]")
        else:
            console.print(content)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    config_path: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to config.yaml"
    ),
):
    """Validate configuration and connectivity."""
    try:
        console.print("[blue]Checking configuration...[/blue]")
        config = load_config(config_path)
        console.print(f"  [green]✓[/green] Config loaded: {config.repo}")
        
        console.print("[blue]Checking GitHub token...[/blue]")
        token = get_github_token()
        console.print(f"  [green]✓[/green] Token found")
        
        console.print("[blue]Testing GitHub connection...[/blue]")
        from .github_graphql import GitHubGraphQLClient
        client = GitHubGraphQLClient(token)
        
        # Try to get project
        try:
            project_data = client.get_project(config.owner, config.project_number, is_org=True)
        except Exception:
            project_data = client.get_project(config.owner, config.project_number, is_org=False)
        
        console.print(f"  [green]✓[/green] Project found: {project_data['title']}")
        
        # Check date fields
        fields = project_data.get("fields", {}).get("nodes", [])
        field_names = [f.get("name") for f in fields if f]
        
        if config.date_fields.start in field_names:
            console.print(f"  [green]✓[/green] Start date field found: {config.date_fields.start}")
        else:
            console.print(f"  [yellow]![/yellow] Start date field not found: {config.date_fields.start}")
            console.print(f"      Available fields: {', '.join(field_names)}")
        
        if config.date_fields.end in field_names:
            console.print(f"  [green]✓[/green] End date field found: {config.date_fields.end}")
        else:
            console.print(f"  [yellow]![/yellow] End date field not found: {config.date_fields.end}")
        
        console.print("\n[green]✓ Validation complete[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
