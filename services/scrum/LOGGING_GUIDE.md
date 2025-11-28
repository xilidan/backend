# Jira API Logging Guide

## Overview

Enhanced logging has been added to all Jira API methods to help you verify that tasks are actually being posted to Jira. The logs show:

- **Request details** (URL, payload, token)
- **Response status** (HTTP status code)
- **Response body** (full JSON response from Jira)
- **Success/failure indicators** (✅ or ❌)
- **Extracted key information** (ID, Key, URL)

## What You'll See in the Logs

### Successful Request Example

When a task is successfully created, you'll see:

```
================================================================================
[JIRA API] Creating Task (Issue)
================================================================================
URL: https://jira.azed.kz/api/jira/issues
Payload: {
  "summary": "Design login page",
  "assigneeEmail": "john.doe@example.com"
}
Token: eyJhbGciOi...

Response Status: 200
Response Body: {"id":"10022","key":"SCRUM-15","self":"https://birka88.atlassian.net/rest/api/3/issue/10022"}

✅ SUCCESS: Task created!
   - ID: 10022
   - Key: SCRUM-15
   - URL: https://birka88.atlassian.net/rest/api/3/issue/10022
   - Assignee: john.doe@example.com
================================================================================
```

### Failed Request Example

When a request fails, you'll see detailed error information:

```
================================================================================
[JIRA API] Creating Task (Issue)
================================================================================
URL: https://jira.azed.kz/api/jira/issues
Payload: {
  "summary": "Design login page"
}
Token: invalid_to...

Response Status: 401
Response Body: {"error":"Unauthorized","message":"Invalid authentication token"}

❌ ERROR: Failed to create task
   Error: 401 Client Error: Unauthorized for url: https://jira.azed.kz/api/jira/issues
   Response Status: 401
   Response Body: {"error":"Unauthorized","message":"Invalid authentication token"}
================================================================================
```

## Logged Information

### For All Requests

1. **URL** - The exact endpoint being called
2. **Payload** - The JSON data being sent (formatted for readability)
3. **Token** - First 10 characters of your auth token (for security)
4. **Response Status** - HTTP status code (200, 201, 400, 401, 500, etc.)
5. **Response Body** - Full response from Jira API

### For Successful Requests

- ✅ Success indicator
- **ID** - The Jira issue ID
- **Key** - The Jira issue key (e.g., SCRUM-15)
- **URL** - Direct link to the issue in Jira
- **Additional info** - Assignee for tasks, parent for subtasks

### For Failed Requests

- ❌ Error indicator
- **Error message** - What went wrong
- **Response Status** - HTTP error code
- **Response Body** - Error details from Jira API

## How to Verify Tasks Were Posted

### Method 1: Check the Logs

Look for the ✅ SUCCESS message and verify:
- Response Status is 200 or 201
- You receive a valid `key` (e.g., SCRUM-15)
- You receive a `self` URL

### Method 2: Visit the Jira Issue

Copy the URL from the `self` field in the success message:
```
URL: https://birka88.atlassian.net/rest/api/3/issue/10022
```

Or construct the Jira web URL using the key:
```
https://your-jira-instance.atlassian.net/browse/SCRUM-15
```

### Method 3: Use the Test Script

Run the test script to see all logging in action:

```bash
cd c:\Users\joyfu\.vscode\Projects\backend\services\scrum
python test_jira_logging.py
```

Make sure to update the token in the script first!

### Method 4: Check via FastAPI Logs

When using the API endpoints, the logs will appear in your server console:

```bash
# Start the server
python main.py

# In another terminal, make a request
curl -X POST http://localhost:8000/issues \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"summary": "Test task"}'

# Check the server console for detailed logs
```

## Common HTTP Status Codes

- **200 OK** - Request successful
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid data sent
- **401 Unauthorized** - Invalid or missing token
- **403 Forbidden** - Valid token but insufficient permissions
- **404 Not Found** - Endpoint or parent issue not found
- **500 Internal Server Error** - Server-side error

## Troubleshooting

### If you see 401 Unauthorized:
- Check your authentication token
- Verify the token hasn't expired
- Ensure you're using "Bearer {token}" format in headers

### If you see 404 Not Found:
- Verify the Jira API URL is correct
- For subtasks, check the parent key exists

### If you see 400 Bad Request:
- Check the payload format matches the API requirements
- Verify all required fields are present
- Check the error message in Response Body for specifics

### If you see timeout errors:
- Check your network connection
- Verify the Jira API is accessible
- Consider increasing the timeout value

## Logging Locations

The logs will appear in:

1. **Server Console** - When running `python main.py`
2. **Test Script Output** - When running `test_jira_logging.py`
3. **Application Logs** - If you've configured logging to file

## Example Complete Workflow Log

```
================================================================================
[JIRA API] Creating Epic
================================================================================
URL: https://jira.azed.kz/api/jira/epics
Payload: {
  "summary": "User Authentication System"
}
Token: eyJhbGciOi...

Response Status: 200
Response Body: {"id":"10023","key":"SCRUM-16","self":"https://birka88.atlassian.net/rest/api/3/issue/10023"}

✅ SUCCESS: Epic created!
   - ID: 10023
   - Key: SCRUM-16
   - URL: https://birka88.atlassian.net/rest/api/3/issue/10023
================================================================================

================================================================================
[JIRA API] Creating Task (Issue)
================================================================================
URL: https://jira.azed.kz/api/jira/issues
Payload: {
  "summary": "Implement login page",
  "assigneeEmail": "john.doe@example.com"
}
Token: eyJhbGciOi...

Response Status: 200
Response Body: {"id":"10024","key":"SCRUM-17","self":"https://birka88.atlassian.net/rest/api/3/issue/10024"}

✅ SUCCESS: Task created!
   - ID: 10024
   - Key: SCRUM-17
   - URL: https://birka88.atlassian.net/rest/api/3/issue/10024
   - Assignee: john.doe@example.com
================================================================================

================================================================================
[JIRA API] Creating Subtask
================================================================================
URL: https://jira.azed.kz/api/jira/subtasks
Payload: {
  "summary": "Create login form component",
  "parentKey": "SCRUM-17"
}
Token: eyJhbGciOi...

Response Status: 200
Response Body: {"id":"10025","key":"SCRUM-18","self":"https://birka88.atlassian.net/rest/api/3/issue/10025"}

✅ SUCCESS: Subtask created!
   - ID: 10025
   - Key: SCRUM-18
   - URL: https://birka88.atlassian.net/rest/api/3/issue/10025
   - Parent: SCRUM-17
================================================================================
```

## Next Steps

1. **Run the test script** to see the logging in action
2. **Check the extracted Key and URL** from successful responses
3. **Visit the Jira URL** to verify the issue was actually created
4. **Use the Key** to create related subtasks or link issues

The detailed logs provide complete transparency into what's being sent to Jira and what responses you're receiving, making it easy to verify that your tasks are actually being posted!
