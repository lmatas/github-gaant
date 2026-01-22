"""Synchronization logic between GitHub and local files (YAML/Excel)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from .config import get_github_token, load_config
from .github_graphql import GitHubGraphQLClient, fetch_project_data
from .github_rest import GitHubRESTClient, create_issue_from_task, update_issue_from_task
from .models import Config, IssueState, Project, Task
from .parsers.yaml_parser import (
    load_project_from_yaml,
    save_project_to_yaml,
    yaml_exists,
)
from .parsers.excel_parser import (
    load_project_from_excel,
    save_project_to_excel,
    excel_exists,
)
from .parsers.mermaid_gen import (
    generate_mermaid_gantt,
    save_mermaid_to_file,
)

console = Console()


def is_excel_file(path: Path) -> bool:
    """Check if path is an Excel file."""
    return path.suffix.lower() in (".xlsx", ".xls")


def file_exists(path: Path) -> bool:
    """Check if the file exists (YAML or Excel)."""
    if is_excel_file(path):
        return excel_exists(path)
    return yaml_exists(path)


def save_project(project: Project, path: Path) -> None:
    """Save project to file (auto-detect format from extension)."""
    if is_excel_file(path):
        save_project_to_excel(project, path)
    else:
        save_project_to_yaml(project, path)


def load_project(path: Path) -> Project:
    """Load project from file (auto-detect format from extension)."""
    if is_excel_file(path):
        return load_project_from_excel(path)
    return load_project_from_yaml(path)


class ChangeType(str, Enum):
    """Type of change detected."""
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


@dataclass
class TaskChange:
    """Represents a change to a task."""
    change_type: ChangeType
    local_task: Optional[Task]
    remote_task: Optional[Task]
    issue_number: Optional[int]
    changes: List[str]  # Description of what changed


def pull_from_github(config: Config, output_path: Optional[Path] = None) -> Project:
    """
    Pull project data from GitHub and save to local files.
    Always exports to YAML, Excel and Mermaid Gantt (.md).
    GitHub is source of truth on pull.
    """
    token = get_github_token()
    
    console.print(f"[blue]Fetching project #{config.project_number} from {config.repo}...[/blue]")
    
    project = fetch_project_data(config, token)
    
    console.print(f"[green]✓ Found {project.total_tasks} tasks[/green]")
    
    # Determine base name from config or output_path
    if output_path is None:
        output_path = Path(config.output_file)
    
    base_name = output_path.stem
    output_dir = output_path.parent
    
    # Always save to YAML
    yaml_path = output_dir / f"{base_name}.yaml"
    save_project_to_yaml(project, yaml_path)
    console.print(f"[green]✓ Saved YAML to {yaml_path}[/green]")
    
    # Always save to Excel
    excel_path = output_dir / f"{base_name}.xlsx"
    save_project_to_excel(project, excel_path)
    console.print(f"[green]✓ Saved Excel to {excel_path}[/green]")
    
    # Always save Mermaid Gantt to .md
    mermaid_path = output_dir / f"{base_name}_gantt.md"
    mermaid_content = generate_mermaid_gantt(project)
    save_mermaid_to_file(mermaid_content, mermaid_path)
    console.print(f"[green]✓ Saved Mermaid Gantt to {mermaid_path}[/green]")
    
    # Save issue bodies to issues/<number>.md
    issues_dir = output_dir / "issues"
    body_count = save_issue_bodies(project.tasks, issues_dir)
    if body_count > 0:
        console.print(f"[green]✓ Saved {body_count} issue bodies to {issues_dir}/[/green]")
    
    return project


def save_issue_bodies(tasks: List[Task], issues_dir: Path) -> int:
    """Save issue bodies to separate markdown files recursively."""
    count = 0
    for task in tasks:
        if task.issue_number > 0 and task.body:
            issues_dir.mkdir(parents=True, exist_ok=True)
            body_path = issues_dir / f"{task.issue_number}.md"
            # Write body with header comment
            content = f"<!-- Issue #{task.issue_number}: {task.title} -->\n\n{task.body}"
            body_path.write_text(content, encoding="utf-8")
            count += 1
        # Process subtasks
        count += save_issue_bodies(task.subtasks, issues_dir)
    return count


def load_issue_body(issue_number: int, issues_dir: Path) -> Optional[str]:
    """Load issue body from markdown file if it exists."""
    body_path = issues_dir / f"{issue_number}.md"
    if body_path.exists():
        content = body_path.read_text(encoding="utf-8")
        # Strip the header comment if present
        lines = content.split("\n")
        if lines and lines[0].startswith("<!-- Issue #"):
            # Skip header comment and empty line after it
            content = "\n".join(lines[2:]) if len(lines) > 2 else ""
        return content.strip() if content.strip() else None
    return None


def load_bodies_into_tasks(tasks: List[Task], issues_dir: Path) -> int:
    """Load issue bodies from files into tasks recursively."""
    count = 0
    for task in tasks:
        if task.issue_number > 0:
            body = load_issue_body(task.issue_number, issues_dir)
            if body is not None:
                task.body = body
                count += 1
        count += load_bodies_into_tasks(task.subtasks, issues_dir)
    return count



def compare_tasks(local: Task, remote: Task) -> List[str]:
    """Compare two tasks and return list of differences."""
    changes: List[str] = []
    
    if local.title != remote.title:
        changes.append(f"title: '{remote.title}' → '{local.title}'")
    
    if local.start_date != remote.start_date:
        changes.append(f"start_date: {remote.start_date} → {local.start_date}")
    
    if local.end_date != remote.end_date:
        changes.append(f"end_date: {remote.end_date} → {local.end_date}")
    
    if set(local.assignees) != set(remote.assignees):
        changes.append(f"assignees: {remote.assignees} → {local.assignees}")
    
    if set(local.labels) != set(remote.labels):
        changes.append(f"labels: {remote.labels} → {local.labels}")
    
    if local.state != remote.state:
        changes.append(f"state: {remote.state.value} → {local.state.value}")
    
    # Compare body content
    local_body = (local.body or "").strip()
    remote_body = (remote.body or "").strip()
    if local_body != remote_body:
        changes.append("body: content changed")
    
    return changes



def detect_changes(
    local_project: Project, 
    remote_project: Project
) -> List[TaskChange]:
    """Detect changes between local and remote projects."""
    changes: List[TaskChange] = []
    
    # Build lookup maps
    def flatten_with_parents(tasks: List[Task]) -> Dict[int, Task]:
        result: Dict[int, Task] = {}
        for task in tasks:
            if task.issue_number > 0:
                result[task.issue_number] = task
            for subtask in task.subtasks:
                if subtask.issue_number > 0:
                    result[subtask.issue_number] = subtask
        return result
    
    local_tasks = flatten_with_parents(local_project.tasks)
    remote_tasks = flatten_with_parents(remote_project.tasks)
    
    # Find new and modified tasks
    for issue_num, local_task in local_tasks.items():
        if issue_num == 0:
            # New task (no issue number yet)
            changes.append(TaskChange(
                change_type=ChangeType.NEW,
                local_task=local_task,
                remote_task=None,
                issue_number=None,
                changes=["new task"],
            ))
        elif issue_num in remote_tasks:
            # Existing task - check for modifications
            remote_task = remote_tasks[issue_num]
            task_changes = compare_tasks(local_task, remote_task)
            if task_changes:
                changes.append(TaskChange(
                    change_type=ChangeType.MODIFIED,
                    local_task=local_task,
                    remote_task=remote_task,
                    issue_number=issue_num,
                    changes=task_changes,
                ))
        else:
            # Task exists locally but not in remote (orphaned)
            changes.append(TaskChange(
                change_type=ChangeType.NEW,
                local_task=local_task,
                remote_task=None,
                issue_number=issue_num,
                changes=["task not in project"],
            ))
    
    # Find tasks in new local entries (issue_number = 0)
    # Find tasks in new local entries (issue_number = 0), recursively
    def find_new_tasks_recursive(tasks: List[Task]):
        for task in tasks:
            if task.issue_number == 0:
                changes.append(TaskChange(
                    change_type=ChangeType.NEW,
                    local_task=task,
                    remote_task=None,
                    issue_number=None,
                    changes=["new task to create"],
                ))
            find_new_tasks_recursive(task.subtasks)
    
    find_new_tasks_recursive(local_project.tasks)
    
    return changes


def push_to_github(
    config: Config, 
    local_path: Optional[Path] = None,
    dry_run: bool = False,
    enforce_subissues: bool = False
) -> List[TaskChange]:
    """
    Push local changes to GitHub.
    Creates new issues, updates existing ones, and syncs date fields.
    If enforce_subissues is True, ensures all subtasks are linked as sub-issues.
    """
    token = get_github_token()
    
    if local_path is None:
        local_path = Path(config.output_file)
    
    if not file_exists(local_path):
        console.print(f"[red]Error: {local_path} not found. Run 'gaant pull' first.[/red]")
        return []
    
    console.print(f"[blue]Loading local file {local_path}...[/blue]")
    local_project = load_project(local_path)
    
    # Load issue bodies from issues/<number>.md files
    issues_dir = local_path.parent / "issues"
    if issues_dir.exists():
        body_count = load_bodies_into_tasks(local_project.tasks, issues_dir)
        if body_count > 0:
            console.print(f"[blue]Loaded {body_count} issue bodies from {issues_dir}/[/blue]")
    
    console.print(f"[blue]Fetching current state from GitHub...[/blue]")
    remote_project = fetch_project_data(config, token)
    
    # Detect changes
    changes = detect_changes(local_project, remote_project)

    
    if not changes and not enforce_subissues:
        console.print("[green]✓ No changes to push[/green]")
        return []
    
    if changes:
        console.print(f"[yellow]Found {len(changes)} changes:[/yellow]")
        for change in changes:
            if change.change_type == ChangeType.NEW:
                console.print(f"  [green]+ NEW:[/green] {change.local_task.title}")
            elif change.change_type == ChangeType.MODIFIED:
                console.print(f"  [yellow]~ MODIFIED:[/yellow] #{change.issue_number}")
                for c in change.changes:
                    console.print(f"      {c}")
        
        if dry_run:
            console.print("[yellow]Dry run - no changes applied[/yellow]")
            return changes
    else:
        console.print("[green]✓ No changes to push[/green]")
    
    # Apply changes
    rest_client = GitHubRESTClient(token)
    graphql_client = GitHubGraphQLClient(token)
    repo = rest_client.get_repo(config.owner, config.repo_name)
    
    # Build a map of task to parent task for sub-issue linking
    def build_parent_map(tasks: List[Task], parent: Optional[Task] = None) -> Dict[int, Task]:
        """Build a map from task id() to its parent task."""
        result: Dict[int, Task] = {}
        for task in tasks:
            if parent is not None:
                result[id(task)] = parent
            result.update(build_parent_map(task.subtasks, task))
        return result
    
    task_to_parent = build_parent_map(local_project.tasks)
    
    # Track newly created issues for sub-issue linking
    created_issues: Dict[int, str] = {}  # id(task) -> issue_node_id
    
    # Build a lookup map from issue_number to issue_id from remote project
    def build_issue_id_map(tasks: List[Task]) -> Dict[int, str]:
        """Build a map from issue_number to issue_id (GraphQL node ID)."""
        result: Dict[int, str] = {}
        for task in tasks:
            if task.issue_number > 0 and task.issue_id:
                result[task.issue_number] = task.issue_id
            result.update(build_issue_id_map(task.subtasks))
        return result
    
    issue_id_lookup = build_issue_id_map(remote_project.tasks)
    
    for change in changes:
        if change.change_type == ChangeType.NEW and change.local_task:
            if change.local_task.issue_number == 0:
                # Create new issue
                console.print(f"[blue]Creating issue: {change.local_task.title}[/blue]")
                issue = create_issue_from_task(rest_client, repo, change.local_task)
                console.print(f"[green]✓ Created #{issue.number}[/green]")
                
                # Add to project
                issue_node_id = rest_client.get_issue_node_id(issue)
                # Update local task with new issue number and store node ID
                change.local_task.issue_number = issue.number
                change.local_task.issue_id = issue_node_id
                created_issues[id(change.local_task)] = issue_node_id
                # Also add to lookup for potential nested sub-issues
                issue_id_lookup[issue.number] = issue_node_id
                
                if remote_project.id and issue_node_id:
                    item_id = graphql_client.add_issue_to_project(
                        remote_project.id, 
                        issue_node_id
                    )
                    if item_id:
                        change.local_task.project_item_id = item_id
                        console.print(f"[green]✓ Added to project[/green]")
                        
                        # Set date fields
                        if change.local_task.start_date and remote_project.start_date_field_id:
                            graphql_client.update_date_field(
                                remote_project.id,
                                item_id,
                                remote_project.start_date_field_id,
                                change.local_task.start_date
                            )
                        if change.local_task.end_date and remote_project.end_date_field_id:
                            graphql_client.update_date_field(
                                remote_project.id,
                                item_id,
                                remote_project.end_date_field_id,
                                change.local_task.end_date
                            )
                
                # Link as sub-issue if this task has a parent
                parent_task = task_to_parent.get(id(change.local_task))
                if parent_task and parent_task.issue_number > 0:
                    # Look up parent's issue_id from remote data or newly created issues
                    parent_issue_id = issue_id_lookup.get(parent_task.issue_number)
                    if parent_issue_id:
                        success = graphql_client.add_sub_issue(
                            parent_issue_id,
                            issue_node_id
                        )
                        if success:
                            console.print(f"[green]✓ Linked as sub-issue of #{parent_task.issue_number}[/green]")
                        else:
                            console.print(f"[yellow]! Could not link as sub-issue[/yellow]")
        
        elif change.change_type == ChangeType.MODIFIED and change.local_task:
            console.print(f"[blue]Updating #{change.issue_number}...[/blue]")
            issue = rest_client.get_issue(repo, change.issue_number)
            update_issue_from_task(rest_client, issue, change.local_task)
            
            # Update date fields if changed and project item exists
            if change.local_task.project_item_id:
                date_updated = False
                for c in change.changes:
                    if "start_date" in c and remote_project.start_date_field_id:
                        graphql_client.update_date_field(
                            remote_project.id,
                            change.local_task.project_item_id,
                            remote_project.start_date_field_id,
                            change.local_task.start_date
                        )
                        date_updated = True
                    if "end_date" in c and remote_project.end_date_field_id:
                        graphql_client.update_date_field(
                            remote_project.id,
                            change.local_task.project_item_id,
                            remote_project.end_date_field_id,
                            change.local_task.end_date
                        )
                        date_updated = True
                
                if date_updated:
                    console.print(f"[green]✓ Updated dates[/green]")
            
            console.print(f"[green]✓ Updated #{change.issue_number}[/green]")
    
    # Enforce sub-issue relationships if requested
    if enforce_subissues and not dry_run:
        console.print("[blue]Enforcing sub-issue relationships...[/blue]")
        
        def enforce_subissues_recursive(tasks: List[Task], parent_issue_id: Optional[str] = None):
            for task in tasks:
                task_issue_id = issue_id_lookup.get(task.issue_number)
                
                # If this task has subtasks, link them as sub-issues
                for subtask in task.subtasks:
                    if subtask.issue_number > 0 and task_issue_id:
                        child_issue_id = issue_id_lookup.get(subtask.issue_number)
                        if child_issue_id:
                            success = graphql_client.add_sub_issue(task_issue_id, child_issue_id)
                            if success:
                                console.print(f"[green]✓ Linked #{subtask.issue_number} as sub-issue of #{task.issue_number}[/green]")
                            else:
                                console.print(f"[yellow]! Could not link #{subtask.issue_number} (may already be linked)[/yellow]")
                
                # Recurse into subtasks
                enforce_subissues_recursive(task.subtasks, task_issue_id)
        
        enforce_subissues_recursive(local_project.tasks)
    
    # Save updated project (with new IDs) back to file
    save_project(local_project, local_path)
    console.print(f"[green]✓ Updated {local_path} with new IDs[/green]")
    
    console.print(f"[green]✓ Push complete[/green]")
    return changes


def get_status(config: Config, local_path: Optional[Path] = None) -> List[TaskChange]:
    """Show status comparing local file with GitHub."""
    token = get_github_token()
    
    if local_path is None:
        local_path = Path(config.output_file)
    
    if not file_exists(local_path):
        console.print(f"[yellow]No local file found at {local_path}[/yellow]")
        console.print("Run 'gaant pull' to fetch from GitHub")
        return []
    
    local_project = load_project(local_path)
    
    # Load issue bodies from issues/<number>.md files
    issues_dir = local_path.parent / "issues"
    if issues_dir.exists():
        load_bodies_into_tasks(local_project.tasks, issues_dir)
    
    remote_project = fetch_project_data(config, token)
    
    changes = detect_changes(local_project, remote_project)
    
    return changes

