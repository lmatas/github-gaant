"""Tests for Excel parser."""

from datetime import date
from pathlib import Path
import tempfile

import pytest

from src.models import IssueState, Project, Task
from src.parsers.excel_parser import (
    load_project_from_excel,
    save_project_to_excel,
    flatten_tasks_for_excel,
    task_to_row,
)


class TestExcelParser:
    """Tests for Excel parser."""
    
    def test_project_roundtrip(self):
        """Project can be saved and loaded from Excel."""
        project = Project(
            id="P_1",
            number=1,
            title="Test Project",
            url="https://github.com/orgs/test/projects/1",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Test Task",
                    start_date=date(2026, 1, 20),
                    end_date=date(2026, 1, 25),
                    assignees=["user1", "user2"],
                    labels=["feature", "priority:high"],
                    milestone="v1.0",
                ),
            ],
        )
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        
        try:
            save_project_to_excel(project, path)
            loaded = load_project_from_excel(path)
            
            assert loaded.title == project.title
            assert loaded.number == project.number
            assert len(loaded.tasks) == 1
            assert loaded.tasks[0].title == "Test Task"
            assert loaded.tasks[0].start_date == date(2026, 1, 20)
            assert loaded.tasks[0].end_date == date(2026, 1, 25)
            assert set(loaded.tasks[0].assignees) == {"user1", "user2"}
            assert set(loaded.tasks[0].labels) == {"feature", "priority:high"}
        finally:
            path.unlink()
    
    def test_subtasks_hierarchy(self):
        """Subtasks are flattened and restored correctly."""
        project = Project(
            id="P_1",
            number=1,
            title="Test Project",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Parent Task",
                    start_date=date(2026, 1, 20),
                    subtasks=[
                        Task(
                            issue_number=2,
                            issue_id="I_2",
                            title="Child Task 1",
                            start_date=date(2026, 1, 21),
                        ),
                        Task(
                            issue_number=3,
                            issue_id="I_3",
                            title="Child Task 2",
                            start_date=date(2026, 1, 22),
                        ),
                    ],
                ),
            ],
        )
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        
        try:
            save_project_to_excel(project, path)
            loaded = load_project_from_excel(path)
            
            # Should have 1 root task with 2 subtasks
            assert len(loaded.tasks) == 1
            assert loaded.tasks[0].title == "Parent Task"
            assert len(loaded.tasks[0].subtasks) == 2
            assert loaded.tasks[0].subtasks[0].title == "Child Task 1"
            assert loaded.tasks[0].subtasks[1].title == "Child Task 2"
        finally:
            path.unlink()
    
    def test_flatten_tasks_for_excel(self):
        """Tasks are flattened correctly with parent references."""
        tasks = [
            Task(
                issue_number=1,
                issue_id="I_1",
                title="Parent",
                subtasks=[
                    Task(issue_number=2, issue_id="I_2", title="Child"),
                ],
            ),
        ]
        
        rows = flatten_tasks_for_excel(tasks)
        
        assert len(rows) == 2
        assert rows[0]["issue"] == 1
        assert rows[0]["parent"] is None
        assert rows[1]["issue"] == 2
        assert rows[1]["parent"] == 1
    
    def test_task_to_row(self):
        """Task is converted to row correctly."""
        task = Task(
            issue_number=42,
            issue_id="I_42",
            title="My Task",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 25),
            assignees=["user1"],
            labels=["bug"],
            state=IssueState.CLOSED,
            milestone="v1.0",
        )
        
        row = task_to_row(task, parent_issue=10)
        
        assert row["issue"] == 42
        assert row["title"] == "My Task"
        assert row["start"] == date(2026, 1, 20)
        assert row["end"] == date(2026, 1, 25)
        assert row["assignees"] == "user1"
        assert row["labels"] == "bug"
        assert row["status"] == "closed"
        assert row["parent"] == 10
        assert row["milestone"] == "v1.0"
    
    def test_closed_status(self):
        """Closed status is preserved."""
        project = Project(
            id="P_1",
            number=1,
            title="Test",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Closed Task",
                    state=IssueState.CLOSED,
                ),
            ],
        )
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        
        try:
            save_project_to_excel(project, path)
            loaded = load_project_from_excel(path)
            
            assert loaded.tasks[0].state == IssueState.CLOSED
        finally:
            path.unlink()
