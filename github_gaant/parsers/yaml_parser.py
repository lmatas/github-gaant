"""YAML parser for Gaant files."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..models import IssueState, Project, Task


def task_to_dict(task: Task) -> Dict[str, Any]:
    """Convert a Task to a dictionary for YAML serialization."""
    data: Dict[str, Any] = {
        "issue": task.issue_number,
        "title": task.title,
    }
    
    if task.start_date:
        data["start"] = task.start_date.isoformat()
    if task.end_date:
        data["end"] = task.end_date.isoformat()
    if task.assignees:
        data["assignees"] = task.assignees
    if task.labels:
        data["labels"] = task.labels
    if task.milestone:
        data["milestone"] = task.milestone
    if task.state == IssueState.CLOSED:
        data["closed"] = True
    
    # Store project and issue IDs for syncing
    if task.project_item_id:
        data["project_item_id"] = task.project_item_id
    if task.issue_id:
        data["issue_id"] = task.issue_id
    
    # Include computed fields for reference
    data["progress"] = task.progress
    
    if task.subtasks:
        data["subtasks"] = [task_to_dict(st) for st in task.subtasks]
    
    return data


def project_to_yaml(project: Project) -> str:
    """Convert a Project to YAML string."""
    data = {
        "project": {
            "id": project.id,
            "number": project.number,
            "title": project.title,
            "url": project.url,
            "progress": project.overall_progress,
        },
        "tasks": [task_to_dict(task) for task in project.tasks],
    }
    
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def save_project_to_yaml(project: Project, path: Path) -> None:
    """Save a Project to a YAML file."""
    yaml_content = project_to_yaml(project)
    with open(path, "w", encoding="utf-8") as f:
        f.write(yaml_content)


def dict_to_task(data: Dict[str, Any], project_id: Optional[str] = None) -> Task:
    """Convert a dictionary from YAML to a Task."""
    # Parse dates
    start_date = None
    end_date = None
    
    if "start" in data and data["start"]:
        if isinstance(data["start"], date):
            start_date = data["start"]
        else:
            start_date = date.fromisoformat(data["start"])
    
    if "end" in data and data["end"]:
        if isinstance(data["end"], date):
            end_date = data["end"]
        else:
            end_date = date.fromisoformat(data["end"])
    
    # Parse subtasks recursively
    subtasks = []
    if "subtasks" in data:
        subtasks = [dict_to_task(st, project_id) for st in data["subtasks"]]
    
    return Task(
        issue_number=data.get("issue", 0),
        issue_id=data.get("issue_id", ""),
        project_item_id=data.get("project_item_id"),
        title=data["title"],
        body=data.get("body"),
        state=IssueState.CLOSED if data.get("closed") else IssueState.OPEN,
        url=data.get("url"),
        start_date=start_date,
        end_date=end_date,
        assignees=data.get("assignees", []),
        labels=data.get("labels", []),
        milestone=data.get("milestone"),
        parent_issue_number=data.get("parent"),
        subtasks=subtasks,
    )


def load_project_from_yaml(path: Path) -> Project:
    """Load a Project from a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    project_data = data.get("project", {})
    tasks_data = data.get("tasks", [])
    
    project_id = project_data.get("id", "")
    tasks = [dict_to_task(t, project_id) for t in tasks_data]
    
    return Project(
        id=project_id,
        number=project_data.get("number", 0),
        title=project_data.get("title", ""),
        url=project_data.get("url"),
        tasks=tasks,
    )


def yaml_exists(path: Path) -> bool:
    """Check if the YAML file exists."""
    return path.exists() and path.is_file()
