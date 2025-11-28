# Jira API Integration - Creating Epics, Tasks, and Subtasks

This document describes the implementation of creating epics, tasks, and subtasks in Jira using the service.

## Overview

Three new endpoints have been added to interact with the Jira API at `https://jira.azed.kz/api/jira`:

1. **POST /epics** - Create an epic
2. **POST /issues** - Create a task (issue)
3. **POST /subtasks** - Create a subtask

## API Endpoints

### 1. Create Epic

**Endpoint:** `POST /epics`

**Headers:**
```json
{
  "Authorization": "Bearer <your_token>",
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "summary": "string"
}
```

**Response:**
```json
{
  "id": "10023",
  "key": "SCRUM-16",
  "self": "https://birka88.atlassian.net/rest/api/3/issue/10023"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/epics \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"summary": "Implement User Authentication System"}'
```

---

### 2. Create Task (Issue)

**Endpoint:** `POST /issues`

**Headers:**
```json
{
  "Authorization": "Bearer <your_token>",
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "summary": "string",
  "assigneeAccountId": "string (optional)",
  "assigneeEmail": "string (optional)"
}
```

**Response:**
```json
{
  "id": "10022",
  "key": "SCRUM-15",
  "self": "https://birka88.atlassian.net/rest/api/3/issue/10022"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/issues \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Design login page",
    "assigneeEmail": "john.doe@example.com"
  }'
```

---

### 3. Create Subtask

**Endpoint:** `POST /subtasks`

**Headers:**
```json
{
  "Authorization": "Bearer <your_token>",
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "summary": "string",
  "parentKey": "string"
}
```

**Response:**
```json
{
  "id": "10028",
  "key": "SCRUM-17",
  "self": "https://birka88.atlassian.net/rest/api/3/issue/10028"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/subtasks \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Create login form component",
    "parentKey": "SCRUM-15"
  }'
```

---

## Getting Assignee Information

The `assigneeAccountId` and `assigneeEmail` for tasks can be obtained from the existing **GET /organization** endpoint:

**Endpoint:** `GET https://api.azed.kz/api/v1/organization`

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corp",
  "positions": [
    {
      "id": 1,
      "name": "Developer",
      "is_reviewer": false
    }
  ],
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "John",
      "surname": "Doe",
      "email": "john.doe@example.com",
      "position_id": 1,
      "job": "Software Engineer"
    }
  ]
}
```

You can use the `id` field as `assigneeAccountId` and the `email` field as `assigneeEmail` when creating tasks.

---

## Implementation Details

### Service Layer (`service.py`)

Three new async methods have been added to `JiraScrumMasterService`:

1. **`create_epic(summary: str, token: str)`**
   - Creates an epic in Jira
   - Returns: Dict with id, key, and self

2. **`create_task(summary: str, assignee_account_id: str = None, assignee_email: str = None, token: str = None)`**
   - Creates a task/issue in Jira
   - Optionally assigns to a user
   - Returns: Dict with id, key, and self

3. **`create_subtask(summary: str, parent_key: str, token: str)`**
   - Creates a subtask under a parent task
   - Requires parent task key (e.g., "SCRUM-15")
   - Returns: Dict with id, key, and self

### API Layer (`main.py`)

Three new FastAPI endpoints expose these service methods:

- `@app.post("/epics")` → `create_epic()`
- `@app.post("/issues")` → `create_task()`
- `@app.post("/subtasks")` → `create_subtask()`

All endpoints:
- Require `Authorization` header with Bearer token
- Return appropriate HTTP status codes (200, 400, 401, 500)
- Include error handling for Jira API failures

---

## Complete Workflow Example

Here's a typical workflow for creating a hierarchical task structure:

```python
import requests

BASE_URL = "http://localhost:8000"
headers = {
    "Authorization": "Bearer your_token",
    "Content-Type": "application/json"
}

# Step 1: Create an epic
epic_response = requests.post(
    f"{BASE_URL}/epics",
    headers=headers,
    json={"summary": "User Authentication Feature"}
).json()

# Step 2: Create a task under the epic
task_response = requests.post(
    f"{BASE_URL}/issues",
    headers=headers,
    json={
        "summary": "Implement login functionality",
        "assigneeEmail": "john.doe@example.com"
    }
).json()

task_key = task_response["key"]  # e.g., "SCRUM-15"

# Step 3: Create subtasks under the task
subtask1 = requests.post(
    f"{BASE_URL}/subtasks",
    headers=headers,
    json={
        "summary": "Create login form UI",
        "parentKey": task_key
    }
).json()

subtask2 = requests.post(
    f"{BASE_URL}/subtasks",
    headers=headers,
    json={
        "summary": "Implement authentication logic",
        "parentKey": task_key
    }
).json()

print(f"Created epic: {epic_response['key']}")
print(f"Created task: {task_response['key']}")
print(f"Created subtasks: {subtask1['key']}, {subtask2['key']}")
```

---

## Error Handling

All endpoints handle the following errors:

- **401 Unauthorized**: Missing or invalid Authorization header
- **400 Bad Request**: Invalid request data (e.g., missing required fields)
- **500 Internal Server Error**: Jira API errors or server issues

Example error response:
```json
{
  "detail": "Failed to create task: Connection timeout"
}
```

---

## Testing

To test the endpoints:

1. **Start the server:**
   ```bash
   cd c:\Users\joyfu\.vscode\Projects\backend\services\scrum
   python main.py
   ```

2. **Run the example script:**
   ```bash
   python example_usage.py
   ```

3. **Or use the interactive API docs:**
   - Open browser to `http://localhost:8000/docs`
   - Use the Swagger UI to test endpoints

---

## Configuration

The Jira API URL is configured in `config.py`:

```python
JIRA_API_URL = os.getenv("JIRA_API_URL", "https://jira.azed.kz/api/jira")
```

You can override it by setting the `JIRA_API_URL` environment variable in your `.env` file.

---

## Notes

- All three methods make real HTTP POST requests to the Jira API
- The `create_jira_tasks()` method remains as a mock implementation for the existing `/decompose` workflow
- Authorization tokens are passed via the `Authorization` header in Bearer format
- The service automatically extracts the token from "Bearer <token>" format
