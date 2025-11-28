"""
Example usage of the new Jira API endpoints.

This demonstrates how to create epics, tasks, and subtasks using the service.
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "your_auth_token_here"  # Replace with actual token

# Headers
headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


def create_epic_example():
    """Create an epic in Jira"""
    url = f"{BASE_URL}/epics"
    payload = {
        "summary": "Implement User Authentication System"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"Create Epic Response: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def create_task_example(assignee_email=None):
    """Create a task (issue) in Jira"""
    url = f"{BASE_URL}/issues"
    payload = {
        "summary": "Design login page UI"
    }
    
    # Optionally add assignee information
    if assignee_email:
        payload["assigneeEmail"] = assignee_email
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"Create Task Response: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def create_task_with_assignee_example():
    """Create a task with assignee information from organization"""
    # First, you would get organization info to find user details
    # For this example, we'll use placeholder values
    url = f"{BASE_URL}/issues"
    payload = {
        "summary": "Implement OAuth2 authentication",
        "assigneeEmail": "john.doe@example.com",
        # "assigneeAccountId": "550e8400-e29b-41d4-a716-446655440000"  # Optional
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"Create Task with Assignee Response: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def create_subtask_example(parent_key):
    """Create a subtask under a parent task"""
    url = f"{BASE_URL}/subtasks"
    payload = {
        "summary": "Create login form component",
        "parentKey": parent_key  # e.g., "SCRUM-15"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"Create Subtask Response: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def complete_workflow_example():
    """
    Complete workflow: Create epic -> task -> subtask
    """
    print("=" * 60)
    print("Creating Epic...")
    print("=" * 60)
    epic_result = create_epic_example()
    print("\n")
    
    print("=" * 60)
    print("Creating Task...")
    print("=" * 60)
    task_result = create_task_with_assignee_example()
    parent_key = task_result.get("key", "SCRUM-15")  # Get the key from response
    print("\n")
    
    print("=" * 60)
    print("Creating Subtask...")
    print("=" * 60)
    subtask_result = create_subtask_example(parent_key)
    print("\n")
    
    print("=" * 60)
    print("Workflow Complete!")
    print(f"Epic: {epic_result.get('key')}")
    print(f"Task: {task_result.get('key')}")
    print(f"Subtask: {subtask_result.get('key')}")
    print("=" * 60)


if __name__ == "__main__":
    # Run the complete workflow
    try:
        complete_workflow_example()
    except requests.RequestException as e:
        print(f"Error: {e}")
        print("\nNote: Make sure the server is running on http://localhost:8000")
        print("Start the server with: python main.py")
