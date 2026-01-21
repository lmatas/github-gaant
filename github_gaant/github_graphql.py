"""GraphQL client for GitHub Projects V2 API."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from .models import Config, IssueState, Project, Task


class GitHubGraphQLClient:
    """Client for GitHub GraphQL API (Projects V2)."""
    
    def __init__(self, token: str):
        """Initialize the GraphQL client."""
        transport = RequestsHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=False)
    
    def get_project(self, owner: str, project_number: int, is_org: bool = True) -> Dict[str, Any]:
        """Get project details and fields."""
        if is_org:
            query = gql("""
                query($owner: String!, $number: Int!) {
                    organization(login: $owner) {
                        projectV2(number: $number) {
                            id
                            number
                            title
                            url
                            fields(first: 50) {
                                nodes {
                                    ... on ProjectV2Field {
                                        id
                                        name
                                        dataType
                                    }
                                    ... on ProjectV2IterationField {
                                        id
                                        name
                                    }
                                    ... on ProjectV2SingleSelectField {
                                        id
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            """)
            result = self.client.execute(query, variable_values={
                "owner": owner,
                "number": project_number
            })
            return result["organization"]["projectV2"]
        else:
            query = gql("""
                query($owner: String!, $number: Int!) {
                    user(login: $owner) {
                        projectV2(number: $number) {
                            id
                            number
                            title
                            url
                            fields(first: 50) {
                                nodes {
                                    ... on ProjectV2Field {
                                        id
                                        name
                                        dataType
                                    }
                                    ... on ProjectV2IterationField {
                                        id
                                        name
                                    }
                                    ... on ProjectV2SingleSelectField {
                                        id
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            """)
            result = self.client.execute(query, variable_values={
                "owner": owner,
                "number": project_number
            })
            return result["user"]["projectV2"]
    
    def get_project_items_with_issues(
        self, 
        project_id: str, 
        config: Config
    ) -> List[Dict[str, Any]]:
        """Get all project items with their issue data and field values."""
        query = gql("""
            query($projectId: ID!, $cursor: String) {
                node(id: $projectId) {
                    ... on ProjectV2 {
                        items(first: 100, after: $cursor) {
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                            nodes {
                                id
                                fieldValues(first: 20) {
                                    nodes {
                                        ... on ProjectV2ItemFieldTextValue {
                                            text
                                            field { ... on ProjectV2Field { name } }
                                        }
                                        ... on ProjectV2ItemFieldDateValue {
                                            date
                                            field { ... on ProjectV2Field { name } }
                                        }
                                        ... on ProjectV2ItemFieldSingleSelectValue {
                                            name
                                            field { ... on ProjectV2SingleSelectField { name } }
                                        }
                                        ... on ProjectV2ItemFieldNumberValue {
                                            number
                                            field { ... on ProjectV2Field { name } }
                                        }
                                    }
                                }
                                content {
                                    ... on Issue {
                                        id
                                        number
                                        title
                                        body
                                        state
                                        url
                                        assignees(first: 10) {
                                            nodes { login }
                                        }
                                        labels(first: 20) {
                                            nodes { name }
                                        }
                                        milestone { title }
                                        parent {
                                            number
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """)
        
        all_items = []
        cursor = None
        
        while True:
            result = self.client.execute(query, variable_values={
                "projectId": project_id,
                "cursor": cursor
            })
            
            items_data = result["node"]["items"]
            all_items.extend(items_data["nodes"])
            
            if not items_data["pageInfo"]["hasNextPage"]:
                break
            cursor = items_data["pageInfo"]["endCursor"]
        
        return all_items
    
    def get_sub_issues(self, issue_id: str) -> List[Dict[str, Any]]:
        """Get sub-issues for a given issue."""
        query = gql("""
            query($issueId: ID!, $cursor: String) {
                node(id: $issueId) {
                    ... on Issue {
                        subIssues(first: 100, after: $cursor) {
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                            nodes {
                                id
                                number
                                title
                                body
                                state
                                url
                                assignees(first: 10) {
                                    nodes { login }
                                }
                                labels(first: 20) {
                                    nodes { name }
                                }
                                milestone { title }
                            }
                        }
                    }
                }
            }
        """)
        
        all_sub_issues = []
        cursor = None
        
        while True:
            result = self.client.execute(query, variable_values={
                "issueId": issue_id,
                "cursor": cursor
            })
            
            sub_issues_data = result["node"]["subIssues"]
            all_sub_issues.extend(sub_issues_data["nodes"])
            
            if not sub_issues_data["pageInfo"]["hasNextPage"]:
                break
            cursor = sub_issues_data["pageInfo"]["endCursor"]
        
        return all_sub_issues
    
    def update_date_field(
        self, 
        project_id: str, 
        item_id: str, 
        field_id: str, 
        date_value: date
    ) -> bool:
        """Update a date field on a project item."""
        mutation = gql("""
            mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $date: Date!) {
                updateProjectV2ItemFieldValue(
                    input: {
                        projectId: $projectId
                        itemId: $itemId
                        fieldId: $fieldId
                        value: { date: $date }
                    }
                ) {
                    projectV2Item {
                        id
                    }
                }
            }
        """)
        
        try:
            self.client.execute(mutation, variable_values={
                "projectId": project_id,
                "itemId": item_id,
                "fieldId": field_id,
                "date": date_value.isoformat()
            })
            return True
        except Exception:
            return False
    
    def add_issue_to_project(self, project_id: str, issue_id: str) -> Optional[str]:
        """Add an issue to a project and return the project item ID."""
        mutation = gql("""
            mutation($projectId: ID!, $contentId: ID!) {
                addProjectV2ItemById(
                    input: {
                        projectId: $projectId
                        contentId: $contentId
                    }
                ) {
                    item {
                        id
                    }
                }
            }
        """)
        
        try:
            result = self.client.execute(mutation, variable_values={
                "projectId": project_id,
                "contentId": issue_id
            })
            return result["addProjectV2ItemById"]["item"]["id"]
        except Exception:
            return None


def parse_project_items_to_tasks(
    items: List[Dict[str, Any]], 
    config: Config,
    graphql_client: GitHubGraphQLClient
) -> List[Task]:
    """Convert GraphQL project items to Task models."""
    tasks: List[Task] = []
    task_by_number: Dict[int, Task] = {}
    
    for item in items:
        content = item.get("content")
        if not content or "number" not in content:
            continue  # Skip draft issues
        
        # Extract date fields
        start_date = None
        end_date = None
        
        for field_value in item.get("fieldValues", {}).get("nodes", []):
            if not field_value:
                continue
            field = field_value.get("field", {})
            field_name = field.get("name", "")
            
            if "date" in field_value and field_name == config.date_fields.start:
                start_date = date.fromisoformat(field_value["date"])
            elif "date" in field_value and field_name == config.date_fields.end:
                end_date = date.fromisoformat(field_value["date"])
        
        # Create task
        task = Task(
            issue_number=content["number"],
            issue_id=content["id"],
            project_item_id=item["id"],
            title=content["title"],
            body=content.get("body"),
            state=IssueState.CLOSED if content["state"] == "CLOSED" else IssueState.OPEN,
            url=content.get("url"),
            start_date=start_date,
            end_date=end_date,
            assignees=[a["login"] for a in content.get("assignees", {}).get("nodes", [])],
            labels=[l["name"] for l in content.get("labels", {}).get("nodes", [])],
            milestone=content.get("milestone", {}).get("title") if content.get("milestone") else None,
            parent_issue_number=content.get("parent", {}).get("number") if content.get("parent") else None,
        )
        
        tasks.append(task)
        task_by_number[task.issue_number] = task
    
    # Build hierarchy based on parent relationships
    root_tasks: list[Task] = []
    for task in tasks:
        if task.parent_issue_number and task.parent_issue_number in task_by_number:
            parent = task_by_number[task.parent_issue_number]
            parent.subtasks.append(task)
        else:
            root_tasks.append(task)
    
    return root_tasks


def fetch_project_data(config: Config, token: str) -> Project:
    """Fetch complete project data from GitHub."""
    client = GitHubGraphQLClient(token)
    
    # Try as organization first, then as user
    try:
        project_data = client.get_project(config.owner, config.project_number, is_org=True)
    except Exception:
        project_data = client.get_project(config.owner, config.project_number, is_org=False)
    
    # Find date field IDs
    start_field_id = None
    end_field_id = None
    
    for field in project_data.get("fields", {}).get("nodes", []):
        if not field:
            continue
        if field.get("name") == config.date_fields.start:
            start_field_id = field.get("id")
        elif field.get("name") == config.date_fields.end:
            end_field_id = field.get("id")
    
    # Get all items
    items = client.get_project_items_with_issues(project_data["id"], config)
    
    # Parse to tasks
    tasks = parse_project_items_to_tasks(items, config, client)
    
    return Project(
        id=project_data["id"],
        number=project_data["number"],
        title=project_data["title"],
        url=project_data.get("url"),
        start_date_field_id=start_field_id,
        end_date_field_id=end_field_id,
        tasks=tasks,
    )
