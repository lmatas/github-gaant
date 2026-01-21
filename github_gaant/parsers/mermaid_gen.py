"""Mermaid Gantt chart generator."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from ..models import Project, Task, TaskStatus


def sanitize_title(title: str) -> str:
    """Sanitize title for Mermaid (remove special characters)."""
    # Remove characters that break Mermaid syntax
    return title.replace(":", "-").replace(";", "-").replace(",", " ")


def get_task_id(task: Task) -> str:
    """Generate a unique task ID for Mermaid."""
    return f"task{task.issue_number}"


def format_task_status(task: Task) -> str:
    """Format task status for Mermaid."""
    status = task.status
    if status == TaskStatus.DONE:
        return "done, "
    elif status == TaskStatus.IN_PROGRESS:
        return "active, "
    elif status == TaskStatus.CRITICAL:
        return "crit, "
    return ""


def format_task_line(task: Task, indent: int = 0) -> List[str]:
    """Format a task as Mermaid Gantt line(s)."""
    lines: List[str] = []
    
    # Skip tasks without dates
    if not task.start_date:
        return lines
    
    task_id = get_task_id(task)
    title = sanitize_title(task.title)
    status = format_task_status(task)
    
    # Calculate duration or use end date
    if task.end_date:
        duration = (task.end_date - task.start_date).days + 1
        duration_str = f"{duration}d"
    else:
        duration_str = "1d"  # Default to 1 day if no end date
    
    # Format: Task Title :status, id, start_date, duration
    line = f"    {title} :{status}{task_id}, {task.start_date.isoformat()}, {duration_str}"
    lines.append(line)
    
    return lines


def group_tasks_by_milestone(tasks: List[Task]) -> Dict[str, List[Task]]:
    """Group tasks by milestone for Mermaid sections."""
    groups: Dict[str, List[Task]] = {"No Milestone": []}
    
    for task in tasks:
        if task.milestone:
            if task.milestone not in groups:
                groups[task.milestone] = []
            groups[task.milestone].append(task)
        else:
            groups["No Milestone"].append(task)
    
    # Remove empty "No Milestone" group
    if not groups["No Milestone"]:
        del groups["No Milestone"]
    
    return groups


def flatten_tasks(tasks: List[Task]) -> List[Task]:
    """Flatten task hierarchy into a single list."""
    result: List[Task] = []
    for task in tasks:
        result.append(task)
        if task.subtasks:
            result.extend(flatten_tasks(task.subtasks))
    return result


def generate_mermaid_gantt(
    project: Project,
    title: Optional[str] = None,
    exclude_weekends: bool = True,
    group_by_milestone: bool = True,
) -> str:
    """Generate a Mermaid Gantt chart from a Project."""
    lines = ["```mermaid"]
    lines.append("gantt")
    
    # Title
    chart_title = title or project.title
    lines.append(f"    title {chart_title}")
    
    # Date format and axis configuration
    lines.append("    dateFormat YYYY-MM-DD")
    lines.append("    tickInterval 1week")
    lines.append("    axisFormat %d-%b")
    
    # Exclude weekends
    if exclude_weekends:
        lines.append("    excludes weekends")
    
    lines.append("")
    
    # Flatten all tasks for processing
    all_tasks = flatten_tasks(project.tasks)
    
    # Filter tasks with dates
    tasks_with_dates = [t for t in all_tasks if t.start_date]
    
    if not tasks_with_dates:
        lines.append("    %% No tasks with dates found")
        lines.append("```")
        return "\n".join(lines)
    
    if group_by_milestone:
        # Group by milestone
        groups = group_tasks_by_milestone(tasks_with_dates)
        
        for section_name, section_tasks in groups.items():
            lines.append(f"    section {section_name}")
            for task in sorted(section_tasks, key=lambda t: t.start_date or date.today()):
                lines.extend(format_task_line(task))
            lines.append("")
    else:
        # All tasks in one section
        lines.append(f"    section Tasks")
        for task in sorted(tasks_with_dates, key=lambda t: t.start_date or date.today()):
            lines.extend(format_task_line(task))
    
    lines.append("```")
    return "\n".join(lines)


def generate_mermaid_with_hierarchy(
    project: Project,
    title: Optional[str] = None,
    exclude_weekends: bool = True,
) -> str:
    """Generate a Mermaid Gantt chart preserving task hierarchy."""
    lines = ["```mermaid", "gantt"]
    
    # Title
    chart_title = title or project.title
    lines.append(f"    title {chart_title}")
    
    # Date format
    lines.append("    dateFormat YYYY-MM-DD")
    
    # Exclude weekends
    if exclude_weekends:
        lines.append("    excludes weekends")
    
    lines.append("")
    
    def add_task_section(task: Task, section_name: str) -> None:
        """Add a task and its subtasks as a section."""
        lines.append(f"    section {section_name}")
        
        # Add parent task
        if task.start_date:
            lines.extend(format_task_line(task))
        
        # Add subtasks
        for subtask in sorted(task.subtasks, key=lambda t: t.start_date or date.today()):
            if subtask.start_date:
                lines.extend(format_task_line(subtask))
        
        lines.append("")
    
    # Process each root task as a section
    for task in project.tasks:
        section_name = sanitize_title(task.title)
        if task.subtasks:
            add_task_section(task, section_name)
        elif task.start_date:
            # Single task without subtasks
            lines.append(f"    section {section_name}")
            lines.extend(format_task_line(task))
            lines.append("")
    
    lines.append("```")
    return "\n".join(lines)


def save_mermaid_to_file(content: str, path: Path) -> None:
    """Save Mermaid content to a markdown file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Gantt Chart\n\n")
        f.write(f"_Generated on {date.today().isoformat()}_\n\n")
        # Add style hint for better rendering
        f.write('<div style="width: 100%; overflow-x: auto;">\n\n')
        f.write(content)
        f.write("\n\n</div>")


def generate_table_view(project: Project) -> str:
    """Generate a markdown table view of tasks."""
    lines = ["# Project Tasks", ""]
    lines.append(f"**Project:** {project.title}")
    lines.append(f"**Progress:** {project.overall_progress}%")
    lines.append("")
    
    lines.append("| # | Title | Start | End | Status | Progress | Assignees |")
    lines.append("|---|-------|-------|-----|--------|----------|-----------|")
    
    def add_task_row(task: Task, indent: int = 0) -> None:
        prefix = "└─ " * indent if indent > 0 else ""
        title = f"{prefix}{task.title}"
        start = task.start_date.isoformat() if task.start_date else "-"
        end = task.end_date.isoformat() if task.end_date else "-"
        status = task.status.value
        progress = f"{task.progress}%"
        assignees = ", ".join(task.assignees) or "-"
        
        lines.append(f"| #{task.issue_number} | {title} | {start} | {end} | {status} | {progress} | {assignees} |")
        
        for subtask in task.subtasks:
            add_task_row(subtask, indent + 1)
    
    for task in project.tasks:
        add_task_row(task)
    
    return "\n".join(lines)
