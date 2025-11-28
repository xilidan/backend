#!/usr/bin/env python3
"""
Clean patch script for service.py - uses precise line-based editing
"""

def patch_service_file():
    file_path = r"c:\Users\joyfu\.vscode\Projects\backend\services\scrum\service.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find specific line numbers
    create_task_sig_line = None
    payload_end_line = None
    create_jira_tasks_start = None
    jira_res_none_line = None
    story_create_line = None
    create_jira_end = None
    analyze_transcription_line = None
    
    for i, line in enumerate(lines):
        if 'async def create_task(self, summary: str, assignee_account_id: str = None,' in line:
            create_task_sig_line = i
        elif 'payload["assigneeEmail"] = assignee_email' in line and  payload_end_line is None:
            payload_end_line = i
        elif 'async def create_jira_tasks(self, tasks: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:' in line:
            create_jira_tasks_start = i
        elif 'jira_res = None' in line and jira_res_none_line is None and i > 320:
            jira_res_none_line = i
        elif '# Create Story/Task' in line and story_create_line is None:
            story_create_line = i
        elif 'print("[JIRA INTEGRATION] Batch Creation Completed")' in line:
            create_jira_end = i - 1  # Line before this
        elif 'async def analyze_transcription(self, request) -> Dict[str, str]:' in line:
            analyze_transcription_line = i
    
    # Apply patches
    
    # 1. Update create_task signature (line ~427)
    if create_task_sig_line:
        lines[create_task_sig_line + 1] = lines[create_task_sig_line + 1].replace(
            'assignee_email: str = None, token: str = None)',
            'assignee_email: str = None, due_date: str = None, token: str = None)'
        )
    
    # 2. Add dueDate to payload (after line ~453)
    if payload_end_line:
        indent = '        '
        lines.insert(payload_end_line + 1, f'{indent}if due_date:\\r\\n')
        lines.insert(payload_end_line + 2, f'{indent}    payload["dueDate"] = due_date\\r\\n')
    
    # 3. Update create_jira_tasks start
    if create_jira_tasks_start:
        # Add created_issue_keys right after created_items
        for i in range(create_jira_tasks_start, create_jira_tasks_start + 10):
            if 'created_items = []' in lines[i]:
                lines.insert(i + 1, '        created_issue_keys = []  # Track all created issue keys\\r\\n')
                # Now add sprint fetching before the for loop
                for j in range(i, i + 20):
                    if 'for item in tasks:' in lines[j]:
                        sprint_code = """        
        # Get active sprint ID
        active_sprint_id = await self.get_active_sprint(token)
        if active_sprint_id:
            print(f"[INFO] Active Sprint found: {active_sprint_id}")
        else:
            print("[INFO] No active sprint found. Issues will remain in backlog.")
        
"""
                        lines.insert(j, sprint_code)
                        break
                break
    
    # 4. Add due_date and issue key collection at jira_res = None
    if jira_res_none_line:
        lines.insert(jira_res_none_line, '                due_date = item.get(\\'due_date\\')  # Get due_date if present\\r\\n')
        lines.insert(jira_res_none_line + 1, '                \\r\\n')
        
        # Find the create_task call after this
        for i in range(jira_res_none_line, jira_res_none_line + 10):
            if 'jira_res = await self.create_task(summary, assignee_email=assignee_email, token=token)' in lines[i]:
                lines[i] = lines[i].replace(
                    'jira_res = await self.create_task(summary, assignee_email=assignee_email, token=token)',
                    'jira_res = await self.create_task(summary, assignee_email=assignee_email, due_date=due_date, token=token)\\r\\n' +
                    '                    # Collect issue keys for sprint assignment (non-Epics only)\\r\\n' +
                    '                    if jira_res and jira_res.get(\\'key\\'):\\r\\n' +
                    '                        created_issue_keys.append(jira_res.get(\\'key\\'))'
                )
                break
    
    # 5. Update story creation
    if story_create_line:
        lines.insert(story_create_line + 1, '                        story_due_date = story.get(\\'due_date\\')\\r\\n')
        # Update the next line
        for i in range(story_create_line, story_create_line + 5):
            if 'story_res = await self.create_task(story_summary, assignee_email=story_assignee, token=token)' in lines[i]:
                lines[i] = lines[i].replace(
                    'story_res = await self.create_task(story_summary, assignee_email=story_assignee, token=token)',
                    'story_res = await self.create_task(story_summary, assignee_email=story_assignee, due_date=story_due_date, token=token)'
                )
                lines.insert(i + 1, '                        \\r\\n')
                lines.insert(i + 2, '                        # Collect story keys for sprint assignment\\r\\n')
                lines.insert(i + 3, '                        if story_res and story_res.get(\\'key\\'):\\r\\n')
                lines.insert(i + 4, '                            created_issue_keys.append(story_res.get(\\'key\\'))\\r\\n')
                break
    
    # 6. Add sprint movement at end of create_jira_tasks
    if create_jira_end:
        sprint_move_code = """                
        # Move all created issues to active sprint
        if active_sprint_id and created_issue_keys:
            print(f"\\n[INFO] Moving {len(created_issue_keys)} issues to sprint {active_sprint_id}...")
            await self.move_issues_to_sprint(active_sprint_id, created_issue_keys, token)
        
"""
        lines.insert(create_jira_end, sprint_move_code)
    
    # 7. Add helper methods before analyze_transcription
    if analyze_transcription_line:
        helper_methods = '''
    async def get_active_sprint(self, token: str):
        """
        Fetch sprints and return the ID of the first active sprint.
        
        Returns:
            Sprint ID if an active sprint is found, None otherwise
        """
        url = f"{settings.JIRA_API_URL}/sprints"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        print(f"\\n[JIRA API] Fetching sprints from {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            sprints = data.get("sprints", [])
            for sprint in sprints:
                if sprint.get("state") == "active":
                    sprint_name = sprint.get("name", "Unknown")
                    sprint_id = sprint.get("id")
                    print(f"✅ Found active sprint: {sprint_name} (ID: {sprint_id})")
                    return sprint_id
            
            print("⚠️  No active sprint found")
            return None
            
        except requests.RequestException as e:
            print(f"❌ ERROR fetching sprints: {str(e)}")
            return None

    async def move_issues_to_sprint(self, sprint_id: int, issue_keys: List[str], token: str):
        """
        Move a list of issues to a specific sprint.
        
        Args:
            sprint_id: The ID of the target sprint
            issue_keys: List of issue keys to move (e.g., ["SCRUM-1", "SCRUM-2"])
            token: Authorization token
        """
        if not issue_keys:
            return
        
        url = f"{settings.JIRA_API_URL}/sprints/{sprint_id}/issues"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "issueKeys": issue_keys
        }
        
        print(f"\\n[JIRA API] Moving {len(issue_keys)} issues to sprint {sprint_id}")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"Response Status: {response.status_code}")
            
            if response.status_code in [200, 204]:
                print(f"✅ SUCCESS: Moved {len(issue_keys)} issues to sprint")
            else:
                print(f"Response Body: {response.text}")
                response.raise_for_status()
                
        except requests.RequestException as e:
            print(f"❌ ERROR moving issues to sprint: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response Body: {e.response.text}")
            # Don't raise - this is a non-critical operation

'''
        lines.insert(analyze_transcription_line, helper_methods)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✅ Successfully patched service.py")

if __name__ == "__main__":
    patch_service_file()
