import io
import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import UploadFile
import docx
import pypdf
import requests

from openai import AsyncAzureOpenAI
from config import settings

import tiktoken
from rating_service import RatingService
from mongo_client import MongoClient

class JiraScrumMasterService:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.API_VERSION
        )
        self.rating_service = RatingService()
        self.mongo_client = MongoClient()

    async def parse_file(self, file: UploadFile) -> str:
        content = await file.read()
        file_ext = file.filename.split('.')[-1].lower()

        if file_ext == 'docx':
            return self._parse_docx(content)
        elif file_ext == 'pdf':
            return self._parse_pdf(content)
        elif file_ext == 'md':
            return self._parse_md(content)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

    def _parse_docx(self, content: bytes) -> str:
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([para.text for para in doc.paragraphs])

    def _parse_pdf(self, content: bytes) -> str:
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text

    def _parse_md(self, content: bytes) -> str:
        return content.decode('utf-8')

    def count_tokens(self, text: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4") # Use gpt-4 encoding as approximation
        return len(encoding.encode(text))

    async def summarize_text(self, text: str) -> str:
        prompt = f"""
        Summarize the following technical document, retaining all key requirements, constraints, and architectural details.
        The summary should be detailed enough to be used for task decomposition.
        
        Document Content:
        {text[:50000]} # Truncate to safe limit for summarization request
        """
        
        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful technical assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    async def get_organization_info(self, token: str) -> Dict[str, Any]:
        # Call the real backend API to get organization info
        import requests
        
        url = f"{settings.BACKEND_API_URL}/organization"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        print(f"Fetching organization info from {url} with token: {token[:10]}...")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            org_data = response.json()
            
            # Log organization info in the requested format
            # Log organization info in the requested format
            # If org_data already has "organization" key, use it directly, otherwise wrap it
            if "organization" in org_data and isinstance(org_data["organization"], dict):
                log_data = org_data
            else:
                log_data = {"organization": org_data}
            
            print(json.dumps(log_data, indent=2))
            
            # Derive skills from job titles since backend doesn't provide them
            for user in org_data.get("users", []):
                if "skills" not in user:
                    job = user.get("job", "").lower()
                    skills = []
                    
                    # Backend/Server skills
                    if any(word in job for word in ["backend", "server", "api"]):
                        skills.extend(["Backend", "API", "Python", "FastAPI", "SQL", "Database"])
                    
                    # Frontend skills
                    if any(word in job for word in ["frontend", "ui", "ux"]):
                        skills.extend(["Frontend", "UI", "UX", "React", "TypeScript", "CSS"])
                    
                    # Mobile skills
                    if any(word in job for word in ["mobile", "ios", "android", "app"]):
                        skills.extend(["Mobile", "iOS", "Android", "Swift", "Kotlin"])
                    
                    # DevOps/Infrastructure
                    if any(word in job for word in ["devops", "infrastructure", "cloud"]):
                        skills.extend(["DevOps", "AWS", "Docker", "Kubernetes", "CI/CD"])
                    
                    # QA/Testing
                    if any(word in job for word in ["qa", "test", "quality"]):
                        skills.extend(["Testing", "QA", "Automation", "Selenium"])
                    
                    # Data/Analytics
                    if any(word in job for word in ["data", "analytics", "ml", "ai"]):
                        skills.extend(["Data", "Analytics", "ML", "Python", "SQL"])
                    
                    # Security
                    if any(word in job for word in ["security", "auth"]):
                        skills.extend(["Security", "Authentication", "Encryption"])
                    
                    # Senior/Lead positions get architecture skills
                    if any(word in job for word in ["senior", "lead", "principal", "architect"]):
                        skills.extend(["Architecture", "Design", "Leadership"])
                    
                    # General engineering skills
                    if any(word in job for word in ["engineer", "developer", "programmer"]):
                        skills.extend(["Programming", "Development"])
                    
                    user["skills"] = list(set(skills))  # Remove duplicates
                    # print(f"Derived skills for {user.get('name')} {user.get('surname')} ({job}): {user['skills']}")
            
            return org_data
        except requests.RequestException as e:
            print(f"Error fetching organization info: {e}")
            raise ValueError(f"Failed to fetch organization info: {str(e)}")

    async def decompose_tasks(self, text: str) -> List[Dict[str, Any]]:
        token_count = self.count_tokens(text)
        print(f"Token count: {token_count}")
        
        if token_count > 100000:
            print("Token count > 100k, summarizing...")
            text = await self.summarize_text(text)
            
        prompt = f"""
        You are an expert Scrum Master and Technical Project Manager.
        Analyze the following project document and decompose it into a hierarchy of Epics, Stories, and Subtasks.
        The document might be in Russian or English. Output the tasks in the SAME LANGUAGE as the document.
        
        Structure the output as a JSON list of Epics. Each Epic should have a list of 'stories', and each Story should have a list of 'subtasks'.
        
        For each item (Epic, Story, Subtask), provide:
        - summary: A concise title.
        - description: Detailed description.
        - type: "Epic", "Story", or "Subtask".
        - required_skills: A list of broad skill categories required (e.g., "Backend", "Frontend", "Mobile", "iOS", "Android", "DevOps", "QA", "Security", "UI", "UX", "Architecture").
        - complexity: An integer from 1 to 10 indicating task difficulty (1=trivial, 5=moderate, 10=very complex). Consider factors like:
          * Technical difficulty and expertise required
          * Integration complexity
          * Amount of research needed
          * Risk and unknowns
          * Size and scope of work
        
        Use BROAD skill categories that match common job roles, not specific technologies.
        
        Example structure:
        [
            {{
                "summary": "Epic Title",
                "type": "Epic",
                "complexity": 8,
                "required_skills": ["Backend", "Architecture"],
                "stories": [
                    {{
                        "summary": "Story Title",
                        "type": "Story",
                        "complexity": 6,
                        "required_skills": ["Backend"],
                        "subtasks": [
                            {{ 
                                "summary": "Subtask Title", 
                                "type": "Subtask", 
                                "complexity": 3,
                                "required_skills": ["Python"] 
                            }}
                        ]
                    }}
                ]
            }}
        ]

        Return ONLY the JSON array.

        Document Content:
        {text[:10000]}
        """

        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        result = response.choices[0].message.content
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "epics" in parsed:
                return parsed["epics"]
            if isinstance(parsed, list):
                return parsed
            # Handle wrapper keys
            for key, value in parsed.items():
                if isinstance(value, list):
                    return value
            return [parsed]
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {result}")
            return []

    def assign_tasks(self, tasks: List[Dict[str, Any]], organization: Dict[str, Any]) -> List[Dict[str, Any]]:
        users = organization.get("users", [])
        
        # print(f"\n=== Assignment Debug ===")
        # print(f"Organization: {organization.get('name', 'Unknown')}")
        # print(f"Number of users: {len(users)}")
        
        user_ratings = self.rating_service.get_ratings_for_users(users)
        
        for user in users:
            email = user.get('email')
            rating = user_ratings.get(email, 0)
            user['rating'] = rating
            # print(f"  - {user.get('name', '')} {user.get('surname', '')}: skills={user.get('skills', [])}, rating={rating}")
        
        def find_best_match(required_skills, complexity):
            candidates = []
            
            # print(f"\nFinding match for skills: {required_skills}, complexity: {complexity}")
            
            for user in users:
                user_skills = set(user.get("skills", []))
                overlap = len(set(required_skills).intersection(user_skills))
                
                if overlap > 0:
                    rating = user.get('rating', 0)
                    score = overlap * 10 + rating / 100
                    
                    candidates.append({
                        'user': user,
                        'overlap': overlap,
                        'rating': rating,
                        'score': score
                    })
                    
                    # print(f"  - {user.get('name')} {user.get('surname')}: {overlap} skill matches, rating={rating}, score={score:.2f}")
            
            if not candidates:
                # print(f"  -> No match found")
                return None
            
            candidates.sort(key=lambda x: (-x['overlap'], -x['rating']))
            
            complexity_threshold = 7
            if complexity >= complexity_threshold:
                high_rated = [c for c in candidates if c['rating'] >= 300]
                if high_rated:
                    best = high_rated[0]['user']
                    # print(f"  -> Complex task (>={complexity_threshold}): assigned to high-rated user {best.get('name')} {best.get('surname')} (rating={best.get('rating')})")
                    return best
            
            best = candidates[0]['user']
            # print(f"  -> Best match: {best.get('name')} {best.get('surname')} (overlap={candidates[0]['overlap']}, rating={best.get('rating')})")
            return best

        def process_item(item):
            complexity = item.get("complexity", 5)
            
            if "required_skills" in item:
                assignee = find_best_match(item["required_skills"], complexity)
                item["assignee"] = f"{assignee['name']} {assignee['surname']}" if assignee else "Unassigned"
                if assignee:
                    item["assignee_rating"] = assignee.get('rating', 0)
                    item["assignee_email"] = assignee.get('email')
            
            if "stories" in item:
                item["stories"] = [process_item(story) for story in item["stories"]]
            
            if "subtasks" in item:
                item["subtasks"] = [process_item(subtask) for subtask in item["subtasks"]]
                
            return item

        return [process_item(task) for task in tasks]


    async def create_jira_tasks(self, tasks: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
        created_items = []
        created_issue_keys = []  # Track all created issue keys
        
        print("\n" + "="*80)
        print("[JIRA INTEGRATION] Starting Batch Creation")
        print("="*80)
        
        # Get active sprint ID
        active_sprint_id = await self.get_active_sprint(token)
        if active_sprint_id:
            print(f"[INFO] Active Sprint found: {active_sprint_id}")
        else:
            print("[INFO] No active sprint found. Issues will remain in backlog.")
        
        for item in tasks:
            try:
                # 1. Create the main item (Epic or Task)
                summary = item.get('summary', 'Untitled')
                item_type = item.get('type', 'Task')
                assignee_email = item.get('assignee_email')
                
                jira_res = None
                due_date = item.get('due_date')  # Get due_date if present
                
                if item_type == 'Epic':
                    jira_res = await self.create_epic(summary, token)
                else:
                    # Story or Task
                    jira_res = await self.create_task(summary, assignee_email=assignee_email, due_date=due_date, token=token)
                    # Collect issue keys for sprint assignment (non-Epics only)
                    if jira_res and jira_res.get('key'):
                        created_issue_keys.append(jira_res.get('key'))
                
                if jira_res:
                    item['jira_key'] = jira_res.get('key')
                    item['jira_id'] = jira_res.get('id')
                    item['jira_link'] = jira_res.get('self')
                
                # 2. Process Stories (if this is an Epic)
                if 'stories' in item:
                    for story in item['stories']:
                        story_summary = story.get('summary', 'Untitled Story')
                        story_assignee = story.get('assignee_email')
                        
                        # Create Story/Task
                        story_due_date = story.get('due_date')
                        story_res = await self.create_task(story_summary, assignee_email=story_assignee, due_date=story_due_date, token=token)
                        
                        # Collect story keys for sprint assignment
                        if story_res and story_res.get('key'):
                            created_issue_keys.append(story_res.get('key'))
                        
                        story['jira_key'] = story_res.get('key')
                        story['jira_id'] = story_res.get('id')
                        story['jira_link'] = story_res.get('self')
                        
                        # 3. Process Subtasks for this Story
                        if 'subtasks' in story:
                            for subtask in story['subtasks']:
                                sub_summary = subtask.get('summary', 'Untitled Subtask')
                                await self.create_subtask(sub_summary, parent_key=story_res.get('key'), token=token)
                
                # 3. Process Subtasks (if this item has direct subtasks)
                if 'subtasks' in item and item_type != 'Epic':
                     for subtask in item['subtasks']:
                        sub_summary = subtask.get('summary', 'Untitled Subtask')
                        # Only create subtask if we have a parent key
                        if item.get('jira_key'):
                            await self.create_subtask(sub_summary, parent_key=item['jira_key'], token=token)
                            
                created_items.append(item)
                
            except Exception as e:
                print(f"âŒ ERROR processing item {item.get('summary')}: {str(e)}")
                # Continue with next item instead of failing everything
                continue
                
        # Move all created issues to active sprint
        if active_sprint_id and created_issue_keys:
            print(f"\n[INFO] Moving {len(created_issue_keys)} issues to sprint {active_sprint_id}...")
            await self.move_issues_to_sprint(active_sprint_id, created_issue_keys, token)
        
        print("\n" + "="*80)
        print("[JIRA INTEGRATION] Batch Creation Completed")
        print("="*80 + "\n")
        
        return created_items

    async def create_epic(self, summary: str, token: str) -> Dict[str, Any]:
        """
        Create an epic in Jira.
        
        Args:
            summary: The epic title/summary
            token: Authorization token for the request
            
        Returns:
            Dictionary with id, key, and self fields from Jira response
        """
        url = f"{settings.JIRA_API_URL}/epics"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "summary": summary
        }
        
        print("\n" + "="*80)
        print("[JIRA API] Creating Epic")
        print("="*80)
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"Token: {token[:10]}..." if len(token) > 10 else f"Token: {token}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\nâœ… SUCCESS: Epic created!")
            print(f"   - ID: {result.get('id', 'N/A')}")
            print(f"   - Key: {result.get('key', 'N/A')}")
            print(f"   - URL: {result.get('self', 'N/A')}")
            print("="*80 + "\n")
            return result
        except requests.RequestException as e:
            print(f"\nâŒ ERROR: Failed to create epic")
            print(f"   Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response Status: {e.response.status_code}")
                print(f"   Response Body: {e.response.text}")
            print("="*80 + "\n")
            raise ValueError(f"Failed to create epic: {str(e)}")

    async def create_task(self, summary: str, assignee_account_id: str = None, 
                         assignee_email: str = None, due_date: str = None, token: str = None) -> Dict[str, Any]:
        """
        Create a task (issue) in Jira.
        
        Args:
            summary: The task title/summary
            assignee_account_id: Account ID of the assignee (optional)
            assignee_email: Email of the assignee (optional)
            token: Authorization token for the request
            
        Returns:
            Dictionary with id, key, and self fields from Jira response
        """
        url = f"{settings.JIRA_API_URL}/issues"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "summary": summary
        }
        
        if assignee_account_id:
            payload["assigneeAccountId"] = assignee_account_id
        if assignee_email:
            payload["assigneeEmail"] = assignee_email
        if due_date:
            payload["dueDate"] = due_date
        
        print("\n" + "="*80)
        print("[JIRA API] Creating Task (Issue)")
        print("="*80)
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"Token: {token[:10]}..." if len(token) > 10 else f"Token: {token}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\nâœ… SUCCESS: Task created!")
            print(f"   - ID: {result.get('id', 'N/A')}")
            print(f"   - Key: {result.get('key', 'N/A')}")
            print(f"   - URL: {result.get('self', 'N/A')}")
            if assignee_email or assignee_account_id:
                print(f"   - Assignee: {assignee_email or assignee_account_id}")
            print("="*80 + "\n")
            return result
        except requests.RequestException as e:
            print(f"\nâŒ ERROR: Failed to create task")
            print(f"   Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response Status: {e.response.status_code}")
                print(f"   Response Body: {e.response.text}")
            print("="*80 + "\n")
            raise ValueError(f"Failed to create task: {str(e)}")

    async def create_subtask(self, summary: str, parent_key: str, token: str) -> Dict[str, Any]:
        """
        Create a subtask in Jira.
        
        Args:
            summary: The subtask title/summary
            parent_key: Key of the parent task (e.g., "SCRUM-15")
            token: Authorization token for the request
            
        Returns:
            Dictionary with id, key, and self fields from Jira response
        """
        url = f"{settings.JIRA_API_URL}/subtasks"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "summary": summary,
            "parentKey": parent_key
        }
        
        print("\n" + "="*80)
        print("[JIRA API] Creating Subtask")
        print("="*80)
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"Token: {token[:10]}..." if len(token) > 10 else f"Token: {token}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\nâœ… SUCCESS: Subtask created!")
            print(f"   - ID: {result.get('id', 'N/A')}")
            print(f"   - Key: {result.get('key', 'N/A')}")
            print(f"   - URL: {result.get('self', 'N/A')}")
            print(f"   - Parent: {parent_key}")
            print("="*80 + "\n")
            return result
        except requests.RequestException as e:
            print(f"\nâŒ ERROR: Failed to create subtask")
            print(f"   Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response Status: {e.response.status_code}")
                print(f"   Response Body: {e.response.text}")
            print("="*80 + "\n")
            raise ValueError(f"Failed to create subtask: {str(e)}")

            
            if response.status_code in [200, 204]:
                print(f"âœ… SUCCESS: Moved {len(issue_keys)} issues to sprint")
            else:
                print(f"Response Body: {response.text}")
                response.raise_for_status()
                
        except requests.RequestException as e:
            print(f"âŒ ERROR moving issues to sprint: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response Body: {e.response.text}")
            # Don't raise - this is a non-critical operation

            print(f"   - Parent: {parent_key}")
            print("="*80 + "\n")
            return result
        except requests.RequestException as e:
            print(f"\nâŒ ERROR: Failed to create subtask")
            print(f"   Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response Status: {e.response.status_code}")
                print(f"   Response Body: {e.response.text}")
            print("="*80 + "\n")
            raise ValueError(f"Failed to create subtask: {str(e)}")


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
        
        print(f"\n[JIRA API] Fetching sprints from {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            sprints = data.get("sprints", [])
            for sprint in sprints:
                if sprint.get("state") == "active":
                    sprint_name = sprint.get("name", "Unknown")
                    sprint_id = sprint.get("id")
                    print(f"âœ… Found active sprint: {sprint_name} (ID: {sprint_id})")
                    return sprint_id
            
            print("âš ï¸  No active sprint found")
            return None
            
        except requests.RequestException as e:
            print(f"âŒ ERROR fetching sprints: {str(e)}")
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
        
        print(f"\n[JIRA API] Moving {len(issue_keys)} issues to sprint {sprint_id}")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"Response Status: {response.status_code}")
            
            if response.status_code in [200, 204]:
                print(f"âœ… SUCCESS: Moved {len(issue_keys)} issues to sprint")
            else:
                print(f"Response Body: {response.text}")
                response.raise_for_status()
                
        except requests.RequestException as e:
            print(f"âŒ ERROR moving issues to sprint: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response Body: {e.response.text}")
            # Don't raise - this is a non-critical operation

    async def analyze_transcription(self, request) -> Dict[str, str]:
        
        jira_url = f"{settings.JIRA_API_URL}/issues?sort=deadline&limit=10"
        print(f"Fetching Jira issues from {jira_url}...")
        
        try:
            response = requests.get(jira_url, headers={"accept": "application/json"}, timeout=10)
            response.raise_for_status()
            jira_data = response.json()
            issues = jira_data.get("issues", [])
            print(f"Fetched {len(issues)} issues from Jira.")
        except requests.RequestException as e:
            print(f"Error fetching Jira issues: {e}")
            issues = []

        issues_context = ""
        for issue in issues:
            key = issue.get("key", "UNKNOWN")
            fields = issue.get("fields") or {}
            summary = fields.get("summary", "No summary")
            description = fields.get("description", "No description")
            status = fields.get("status", {}).get("name", "Unknown")
            
            issues_context += f"- [{key}] {summary} (Status: {status})\n"
            if description:
                issues_context += f"  Description: {str(description)[:200]}...\n"

        transcription_text = ""
        for block in request.transcript.speaker_blocks:
            transcription_text += f"{block.speaker.name}: {block.words}\n"

        meeting_context = f"""
        Meeting: {request.title}
        Time: {request.start_time} - {request.end_time}
        Participants: {', '.join([p.name for p in request.participants])}
        
        Summary: {request.summary}
        
        Action Items:
        {chr(10).join([f"- {item.text}" for item in request.action_items])}
        
        Key Questions:
        {chr(10).join([f"- {q.text}" for q in request.key_questions])}
        
        Topics:
        {chr(10).join([f"- {t.text}" for t in request.topics])}
        
        Chapter Summaries:
        {chr(10).join([f"- {ch.title}: {ch.description}" for ch in request.chapter_summaries])}
        """

        prompt = f"""
        You are an expert Project Manager and Scrum Master.
        
        I have a transcription of a meeting and a list of existing Jira issues.
        Your goal is to identify important questions or topics that were NOT discussed in the meeting but are relevant to the existing issues or the project context implied by the transcription.
        
        CRITICAL: Detect the language used in the meeting transcript and respond in that EXACT SAME LANGUAGE. If the transcript is in Russian, respond in Russian. If in English, respond in English.
        
        Existing Jira Issues:
        {issues_context[:20000]}
        
        Meeting Context:
        {meeting_context[:10000]}
        
        Full Transcript:
        {transcription_text[:20000]}
        
        Instructions:
        1. Analyze the transcription to understand what was discussed.
        2. Cross-reference with the existing Jira issues.
        3. Identify gaps: What critical details, risks, or requirements related to the issues (or new topics mentioned) were missed?
        4. Generate a list of important questions to ask the team.
        
        Output Format:
        Return ONLY valid HTML content formatted for Telegram's HTML parser. Use these tags ONLY:
        - <b>text</b> for bold
        - <i>text</i> for italic
        - <u>text</u> for underline
        - <s>text</s> for strikethrough
        - <code>text</code> for inline code
        - <pre>text</pre> for code blocks
        - <a href="url">text</a> for links
        
        Structure your response with proper headings using <b> tags and organize questions in a clear list format.
        Do NOT use markdown, do NOT wrap in code blocks, return ONLY the HTML content.
        """

        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful technical assistant that outputs valid HTML."},
                {"role": "user", "content": prompt}
            ]
        )
        
        result_text = response.choices[0].message.content
        clean = result_text.replace("```html", "").replace("```", "").strip()
        return {"text": clean}

    async def create_epic(self, summary: str, token: str) -> Dict[str, Any]:
        """
        Create an epic in Jira.
        
        Args:
            summary: The epic title/summary
            token: Authorization token for the request
            
        Returns:
            Dictionary with id, key, and self fields from Jira response
        """
        url = f"{settings.JIRA_API_URL}/epics"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "summary": summary
        }
        
        print("\n" + "="*80)
        print("[JIRA API] Creating Epic")
        print("="*80)
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"Token: {token[:10]}..." if len(token) > 10 else f"Token: {token}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\nâœ… SUCCESS: Epic created!")
            print(f"   - ID: {result.get('id', 'N/A')}")
            print(f"   - Key: {result.get('key', 'N/A')}")
            print(f"   - URL: {result.get('self', 'N/A')}")
            print("="*80 + "\n")
            return result
        except requests.RequestException as e:
            print(f"\nâŒ ERROR: Failed to create epic")
            print(f"   Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response Status: {e.response.status_code}")
                print(f"   Response Body: {e.response.text}")
            print("="*80 + "\n")
            raise ValueError(f"Failed to create epic: {str(e)}")

    async def create_task(self, summary: str, assignee_account_id: str = None, 
                     assignee_email: str = None, due_date: str = None, token: str =  None) -> Dict[str, Any]:
        """
        Create a task (issue) in Jira.
        
        Args:
            summary: The task title/summary
            assignee_account_id: Account ID of the assignee (optional)
            assignee_email: Email of the assignee (optional)
            token: Authorization token for the request
            
        Returns:
            Dictionary with id, key, and self fields from Jira response
        """
        url = f"{settings.JIRA_API_URL}/issues"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "summary": summary
        }
        
        if assignee_account_id:
            payload["assigneeAccountId"] = assignee_account_id
        if assignee_email:
            payload["assigneeEmail"] = assignee_email
        if due_date:
            payload["dueDate"] = due_date

        
        print("\n" + "="*80)
        print("[JIRA API] Creating Task (Issue)")
        print("="*80)
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"Token: {token[:10]}..." if len(token) > 10 else f"Token: {token}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\nâœ… SUCCESS: Task created!")
            print(f"   - ID: {result.get('id', 'N/A')}")
            print(f"   - Key: {result.get('key', 'N/A')}")
            print(f"   - URL: {result.get('self', 'N/A')}")
            if assignee_email or assignee_account_id:
                print(f"   - Assignee: {assignee_email or assignee_account_id}")
            print("="*80 + "\n")
            return result
        except requests.RequestException as e:
            print(f"\nâŒ ERROR: Failed to create task")
            print(f"   Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response Status: {e.response.status_code}")
                print(f"   Response Body: {e.response.text}")
            print("="*80 + "\n")
            raise ValueError(f"Failed to create task: {str(e)}")

    async def create_subtask(self, summary: str, parent_key: str, token: str) -> Dict[str, Any]:
        """
        Create a subtask in Jira.
        
        Args:
            summary: The subtask title/summary
            parent_key: Key of the parent task (e.g., "SCRUM-15")
            token: Authorization token for the request
            
        Returns:
            Dictionary with id, key, and self fields from Jira response
        """
        url = f"{settings.JIRA_API_URL}/subtasks"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "summary": summary,
            "parentKey": parent_key
        }
        
        print("\n" + "="*80)
        print("[JIRA API] Creating Subtask")
        print("="*80)
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"Token: {token[:10]}..." if len(token) > 10 else f"Token: {token}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\nâœ… SUCCESS: Subtask created!")
            print(f"   - ID: {result.get('id', 'N/A')}")
            print(f"   - Key: {result.get('key', 'N/A')}")
            print(f"   - URL: {result.get('self', 'N/A')}")
            print(f"   - Parent: {parent_key}")
            print("="*80 + "\n")
            return result
        except requests.RequestException as e:
            print(f"\nâŒ ERROR: Failed to create subtask")
            print(f"   Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response Status: {e.response.status_code}")
                print(f"   Response Body: {e.response.text}")
            print("="*80 + "\n")
            raise ValueError(f"Failed to create subtask: {str(e)}")


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
        
        print(f"\n[JIRA API] Fetching sprints from {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            sprints = data.get("sprints", [])
            for sprint in sprints:
                if sprint.get("state") == "active":
                    sprint_name = sprint.get("name", "Unknown")
                    sprint_id = sprint.get("id")
                    print(f"âœ… Found active sprint: {sprint_name} (ID: {sprint_id})")
                    return sprint_id
            
            print("âš ï¸  No active sprint found")
            return None
            
        except requests.RequestException as e:
            print(f"âŒ ERROR fetching sprints: {str(e)}")
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
        
        print(f"\n[JIRA API] Moving {len(issue_keys)} issues to sprint {sprint_id}")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"Response Status: {response.status_code}")
            
            if response.status_code in [200, 204]:
                print(f"âœ… SUCCESS: Moved {len(issue_keys)} issues to sprint")
            else:
                print(f"Response Body: {response.text}")
                response.raise_for_status()
                
        except requests.RequestException as e:
            print(f"âŒ ERROR moving issues to sprint: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response Body: {e.response.text}")
            # Don't raise - this is a non-critical operation

    async def analyze_transcription(self, request) -> Dict[str, str]:
        
        jira_url = "https://jira.azed.kz/api/jira/issues?sort=deadline&limit=10"
        print(f"Fetching Jira issues from {jira_url}...")
        
        try:
            response = requests.get(jira_url, headers={"accept": "application/json"}, timeout=10)
            response.raise_for_status()
            jira_data = response.json()
            issues = jira_data.get("issues", [])
            print(f"Fetched {len(issues)} issues from Jira.")
        except requests.RequestException as e:
            print(f"Error fetching Jira issues: {e}")
            issues = []

        issues_context = ""
        for issue in issues:
            key = issue.get("key", "UNKNOWN")
            fields = issue.get("fields", {})
            summary = fields.get("summary", "No summary")
            description = fields.get("description", "No description")
            status = fields.get("status", {}).get("name", "Unknown")
            
            issues_context += f"- [{key}] {summary} (Status: {status})\n"
            if description:
                issues_context += f"  Description: {str(description)[:200]}...\n"

        transcription_text = ""
        for block in request.transcript.speaker_blocks:
            transcription_text += f"{block.speaker.name}: {block.words}\n"

        meeting_context = f"""
        Meeting: {request.title}
        Time: {request.start_time} - {request.end_time}
        Participants: {', '.join([p.name for p in request.participants])}
        
        Summary: {request.summary}
        
        Action Items:
        {chr(10).join([f"- {item.text}" for item in request.action_items])}
        
        Key Questions:
        {chr(10).join([f"- {q.text}" for q in request.key_questions])}
        
        Topics:
        {chr(10).join([f"- {t.text}" for t in request.topics])}
        
        Chapter Summaries:
        {chr(10).join([f"- {ch.title}: {ch.description}" for ch in request.chapter_summaries])}
        """

        prompt = f"""
        You are an expert Project Manager and Scrum Master.
        
        I have a transcription of a meeting and a list of existing Jira issues.
        Your goal is to identify important questions or topics that were NOT discussed in the meeting but are relevant to the existing issues or the project context implied by the transcription.
        
        CRITICAL: Detect the language used in the meeting transcript and respond in that EXACT SAME LANGUAGE. If the transcript is in Russian, respond in Russian. If in English, respond in English.
        
        Existing Jira Issues:
        {issues_context[:20000]}
        
        Meeting Context:
        {meeting_context[:10000]}
        
        Full Transcript:
        {transcription_text[:20000]}
        
        Instructions:
        1. Analyze the transcription to understand what was discussed.
        2. Cross-reference with the existing Jira issues.
        3. Identify gaps: What critical details, risks, or requirements related to the issues (or new topics mentioned) were missed?
        4. Generate a list of important questions to ask the team.
        
        Output Format:
        Return ONLY valid HTML content formatted for Telegram's HTML parser. Use these tags ONLY:
        - <b>text</b> for bold
        - <i>text</i> for italic
        - <u>text</u> for underline
        - <s>text</s> for strikethrough
        - <code>text</code> for inline code
        - <pre>text</pre> for code blocks
        - <a href="url">text</a> for links
        
        Structure your response with proper headings using <b> tags and organize questions in a clear list format.
        Do NOT use markdown, do NOT wrap in code blocks, return ONLY the HTML content.
        """

        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful technical assistant that outputs valid HTML."},
                {"role": "user", "content": prompt}
            ]
        )
        
        result_text = response.choices[0].message.content
        clean = result_text.replace("```html", "").replace("```", "").strip()
        return {"text": clean}

    async def sync_jira_data(self):
        """Fetch issues from Jira and cache them in MongoDB."""
        print("Syncing Jira data...")
        # Fetch more issues for caching
        jira_url = f"{settings.JIRA_API_URL}/issues?limit=100" 
        try:
            response = requests.get(jira_url, headers={"accept": "application/json"}, timeout=10)
            response.raise_for_status()
            data = response.json()
            issues = data.get("issues", [])
            
            # Transform for cache if needed, or store raw
            # We want to store key, summary, description, status, assignee
            cached_issues = []
            for issue in issues:
                fields = issue.get("fields") or {}
                status = fields.get("status") or {}
                assignee = fields.get("assignee") or {}
                
                cached_issues.append({
                    "key": issue.get("key"),
                    "summary": fields.get("summary"),
                    "description": fields.get("description"),
                    "status": status.get("name"),
                    "assignee": assignee.get("displayName"),
                    "updated": fields.get("updated")
                })
            
            await self.mongo_client.cache_jira_issues(cached_issues)
            print(f"Synced {len(cached_issues)} issues to MongoDB.")
            return len(cached_issues)
        except Exception as e:
            print(f"Error syncing Jira data: {e}")
            return 0

    async def chat(self, message: str, session_id: str, file: UploadFile = None, authorization: str = None):
        file_context = ""
        if file:
            try:
                if authorization:
                    yield "data: Analyzing file...\n\n"
                    await asyncio.sleep(0)
                    text = await self.parse_file(file)
                    token = authorization.split(" ")[1] if " " in authorization else authorization
                    organization = await self.get_organization_info(token)
                    
                    yield "data: Decomposing tasks (this may take a moment)...\n\n"
                    await asyncio.sleep(0)
                    tasks = await self.decompose_tasks(text)
                    assigned_tasks = self.assign_tasks(tasks, organization)
                    
                    yield "data: Creating tasks in Jira...\n\n"
                    await asyncio.sleep(0)
                    final_tasks = await self.create_jira_tasks(assigned_tasks, token)
                    
                    yield "data: Tasks created. Generating response...\n\n"
                    await asyncio.sleep(0)
                    task_summary = "\n".join([f"- {t.get('jira_key')} {t.get('summary')}" for t in final_tasks])
                    file_context = f"Uploaded File Processed. Created Jira Tasks:\n{task_summary}\n"
                else:
                    file_content = await self.parse_file(file)
                    if self.count_tokens(file_content) > 5000:
                        file_summary = await self.summarize_text(file_content)
                        file_context = f"Uploaded File Summary:\n{file_summary}\n"
                    else:
                        file_context = f"Uploaded File Content:\n{file_content}\n"
            except Exception as e:
                print(f"Error processing file: {e}")
                file_context = f"Error processing uploaded file: {e}\n"

        yield "data: Loading context...\n\n"
        await asyncio.sleep(0)
        
        history = await self.mongo_client.get_chat_history(session_id)
        cached_issues = await self.mongo_client.get_cached_issues(limit=20)
        jira_context = "Relevant Jira Issues:\n"
        for issue in cached_issues:
            jira_context += f"- [{issue['key']}] {issue['summary']} ({issue['status']})\n"

        system_prompt = """You are an expert Scrum Master assistant. 
        Use the provided Jira context and file content to answer the user's questions.
        If the user asks to create tasks, guide them on how to structure the request or use the decompose feature.
        Always be helpful, concise, and professional.
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        user_content = f"{jira_context}\n\n{file_context}\n\nUser Question: {message}"
        messages.append({"role": "user", "content": user_content})

        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=messages,
            stream=True
        )

        full_response = ""
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield f"data: {content}\n\n"
                await asyncio.sleep(0)

        await self.mongo_client.save_message(session_id, "user", message)
        await self.mongo_client.save_message(session_id, "assistant", full_response)