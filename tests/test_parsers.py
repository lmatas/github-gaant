"""Tests for parsers."""

from datetime import date
from pathlib import Path
import tempfile

import pytest

from src.models import IssueState, Project, Task
from src.parsers.yaml_parser import (
    load_project_from_yaml,
    project_to_yaml,
    save_project_to_yaml,
)
from src.parsers.mermaid_gen import (
    generate_mermaid_gantt,
    generate_table_view,
    sanitize_title,
)


class TestYamlParser:
    """Tests for YAML parser."""
    
    def test_project_roundtrip(self):
        """Project can be saved and loaded."""
        project = Project(
            id="P_1",
            number=1,
            title="Test Project",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Test Task",
                    start_date=date(2026, 1, 20),
                    end_date=date(2026, 1, 25),
                    assignees=["user1"],
                    labels=["feature"],
                ),
            ],
        )
        
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = Path(f.name)
        
        try:
            save_project_to_yaml(project, path)
            loaded = load_project_from_yaml(path)
            
            assert loaded.title == project.title
            assert len(loaded.tasks) == 1
            assert loaded.tasks[0].title == "Test Task"
            assert loaded.tasks[0].start_date == date(2026, 1, 20)
        finally:
            path.unlink()
    
    def test_project_to_yaml_format(self):
        """YAML output has correct format."""
        project = Project(
            id="P_1",
            number=1,
            title="Test",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Task 1",
                    start_date=date(2026, 1, 20),
                ),
            ],
        )
        
        yaml_str = project_to_yaml(project)
        
        assert "project:" in yaml_str
        assert "tasks:" in yaml_str
        assert "issue: 1" in yaml_str
        assert "2026-01-20" in yaml_str


class TestMermaidGenerator:
    """Tests for Mermaid generator."""
    
    def test_sanitize_title(self):
        """Special characters are removed from titles."""
        assert sanitize_title("Task: Do something") == "Task- Do something"
        assert sanitize_title("A; B; C") == "A- B- C"
    
    def test_generate_gantt(self):
        """Mermaid Gantt is generated correctly."""
        project = Project(
            id="P_1",
            number=1,
            title="Test Project",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Task 1",
                    start_date=date(2026, 1, 20),
                    end_date=date(2026, 1, 25),
                    milestone="v1.0",
                ),
            ],
        )
        
        mermaid = generate_mermaid_gantt(project)
        
        assert "```mermaid" in mermaid
        assert "gantt" in mermaid
        assert "Test Project" in mermaid
        assert "2026-01-20" in mermaid
        assert "section v1.0" in mermaid
    
    def test_generate_table(self):
        """Table view is generated correctly."""
        project = Project(
            id="P_1",
            number=1,
            title="Test Project",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Task 1",
                    start_date=date(2026, 1, 20),
                    assignees=["user1"],
                ),
            ],
        )
        
        table = generate_table_view(project)
        
        assert "| # | Title |" in table
        assert "#1" in table
        assert "Task 1" in table
        assert "user1" in table
