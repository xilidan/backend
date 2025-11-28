#!/usr/bin/env python3
"""
Script to update service.py with dueDate support and sprint auto-assignment
"""

def update_service_file():
    file_path = r"c:\Users\joyfu\.vscode\Projects\backend\services\scrum\service.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Update create_task method signature
    old_sig = "async def create_task(self, summary: str, assignee_account_id: str = None, \n                         assignee_email: str = None, token: str = None) -> Dict[str, Any]:"
    new_sig = "async def create_task(self, summary: str, assignee_account_id: str = None, \n                         assignee_email: str = None, due_date: str = None, token: str = None) -> Dict[str, Any]:"
    content = content.replace(old_sig, new_sig)
    
    # 2. Update create_task body to include dueDate in payload
    old_payload = """        if assignee_account_id:
            payload["assigneeAccountId"] = assignee_account_id
        if assignee_email:
            payload["assigneeEmail"] = assignee_email
        
        print("\\n" + "="*80)"""
    
    new_payload = """        if assignee_account_id:
            payload["assigneeAccountId"] = assignee_account_id
        if assignee_email:
            payload["assigneeEmail"] = assignee_email
        if due_date:
            payload["dueDate"] = due_date
        
        print("\\n" + "="*80)"""
    
    content = content.replace(old_payload, new_payload)
    
    # 3. Add helper methods at the end, before analyze_transcription
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
    
    # Insert before analyze_transcription
    marker = "    async def analyze_transcription(self, request) -> Dict[str, str]:"
    if marker in content:
        content = content.replace(marker, helper_methods + marker)
    
    # 4. Update create_jira_tasks method - split into parts for better control
    # Find and replace the start of create_jira_tasks
    old_start = """    async def create_jira_tasks(self, tasks: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
        created_items = []
        
        print("\\n" + "="*80)
        print("[JIRA INTEGRATION] Starting Batch Creation")
        print("="*80)
        
        for item in tasks:"""
    
    new_start = """    async def create_jira_tasks(self, tasks: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
        created_items = []
        created_issue_keys = []  # Track all created issue keys
        
        print("\\n" + "="*80)
        print("[JIRA INTEGRATION] Starting Batch Creation")
        print("="*80)
        
        # Get active sprint ID
        active_sprint_id = await self.get_active_sprint(token)
        if active_sprint_id:
            print(f"[INFO] Active Sprint found: {active_sprint_id}")
        else:
            print("[INFO]No active sprint found. Issues will remain in backlog.")
        
        for item in tasks:"""
    
    content = content.replace(old_start, new_start)
    
    # Update the Epic/Task creation block
    old_block1 = """                jira_res = None
                if item_type == 'Epic':
                    jira_res = await self.create_epic(summary, token)
                else:
                    # Story or Task
                    jira_res = await self.create_task(summary, assignee_email=assignee_email, token=token)"""
    
    new_block1 = """                jira_res = None
                due_date = item.get('due_date')  # Get due_date if present
                
                if item_type == 'Epic':
                    jira_res = await self.create_epic(summary, token)
                else:
                    # Story or Task
                    jira_res = await self.create_task(summary, assignee_email=assignee_email, due_date=due_date, token=token)
                    # Collect issue keys for sprint assignment (non-Epics only)
                    if jira_res and jira_res.get('key'):
                        created_issue_keys.append(jira_res.get('key'))"""
    
    content = content.replace(old_block1, new_block1)
    
    # Update story creation block
    old_block2 = """                        # Create Story/Task
                        story_res = await self.create_task(story_summary, assignee_email=story_assignee, token=token)
                        
                        story['jira_key'] = story_res.get('key')"""
    
    new_block2 = """                        # Create Story/Task
                        story_due_date = story.get('due_date')
                        story_res = await self.create_task(story_summary, assignee_email=story_assignee, due_date=story_due_date, token=token)
                        
                        # Collect story keys for sprint assignment
                        if story_res and story_res.get('key'):
                            created_issue_keys.append(story_res.get('key'))
                        
                        story['jira_key'] = story_res.get('key')"""
    
    content = content.replace(old_block2, new_block2)
    
    # Update the end of create_jira_tasks
    old_end = """                
        print("\\n" + "="*80)
        print("[JIRA INTEGRATION] Batch Creation Completed")
        print("="*80 + "\\n")
        
        return created_items"""
    
    new_end = """                
        # Move all created issues to active sprint
        if active_sprint_id and created_issue_keys:
            print(f"\\n[INFO] Moving {len(created_issue_keys)} issues to sprint {active_sprint_id}...")
            await self.move_issues_to_sprint(active_sprint_id, created_issue_keys, token)
        
        print("\\n" + "="*80)
        print("[JIRA INTEGRATION] Batch Creation Completed")
        print("="*80 + "\\n")
        
        return created_items"""
    
    content = content.replace(old_end, new_end)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Successfully updated service.py")
    print("  - Added due_date parameter to create_task")
    print("  - Added get_active_sprint method")
    print("  - Added move_issues_to_sprint method")
    print("  - Updated create_jira_tasks to auto-assign to active sprint")

if __name__ == "__main__":
    update_service_file()
