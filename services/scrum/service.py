import io
import json
from typing import List, Dict, Any
from fastapi import UploadFile
import docx
import pypdf
from openai import AsyncAzureOpenAI
from config import settings

import tiktoken

class JiraScrumMasterService:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.API_VERSION
        )

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

    async def decompose_tasks(self, text: str) -> List[Dict[str, Any]]:
        token_count = self.count_tokens(text)
        print(f"Token count: {token_count}")
        
        if token_count > 100000:
            print("Token count > 100k, summarizing...")
            text = await self.summarize_text(text)
            
        prompt = f"""
        You are an expert Scrum Master and Technical Project Manager.
        Analyze the following project document and decompose it into a list of Jira tasks.
        The document might be in Russian or English. Output the tasks in the SAME LANGUAGE as the document.
        
        For each task, provide:
        - summary: A concise title for the task.
        - description: A detailed description of what needs to be done.
        - type: Task, Story, or Bug.
        - required_skills: A list of technical skills required to complete this task (e.g., Python, React, SQL, AWS, iOS, Android).

        Return the result as a JSON array of objects. Do not include markdown formatting.

        Document Content:
        {text[:10000]}  # Truncate to avoid token limits if necessary
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
            # Handle potential wrapping in a key like "tasks" or just a raw list
            parsed = json.loads(result)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                # Look for a list value
                for key, value in parsed.items():
                    if isinstance(value, list):
                        return value
                return [parsed] # Fallback
            return []
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {result}")
            return []

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
                    print(f"Derived skills for {user.get('name')} {user.get('surname')} ({job}): {user['skills']}")
            
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
        
        Use BROAD skill categories that match common job roles, not specific technologies.
        
        Example structure:
        [
            {{
                "summary": "Epic Title",
                "type": "Epic",
                "stories": [
                    {{
                        "summary": "Story Title",
                        "type": "Story",
                        "subtasks": [
                            {{ "summary": "Subtask Title", "type": "Subtask", "required_skills": ["Python"] }}
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
        
        print(f"\n=== Assignment Debug ===")
        print(f"Organization: {organization.get('name', 'Unknown')}")
        print(f"Number of users: {len(users)}")
        for user in users:
            print(f"  - {user.get('name', '')} {user.get('surname', '')}: {user.get('skills', [])}")
        
        def find_best_match(required_skills):
            best_match = None
            max_overlap = -1
            
            print(f"\nFinding match for skills: {required_skills}")
            
            for user in users:
                user_skills = set(user.get("skills", []))
                overlap = len(set(required_skills).intersection(user_skills))
                
                if overlap > 0:
                    print(f"  - {user.get('name')} {user.get('surname')}: {overlap} matches")
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_match = user
            
            if best_match:
                print(f"  → Best match: {best_match.get('name')} {best_match.get('surname')} ({max_overlap} skills)")
            else:
                print(f"  → No match found")
            
            return best_match

        def process_item(item):
            if "required_skills" in item:
                assignee = find_best_match(item["required_skills"])
                item["assignee"] = f"{assignee['name']} {assignee['surname']}" if assignee else "Unassigned"
            
            if "stories" in item:
                item["stories"] = [process_item(story) for story in item["stories"]]
            
            if "subtasks" in item:
                item["subtasks"] = [process_item(subtask) for subtask in item["subtasks"]]
                
            return item

        return [process_item(task) for task in tasks]

    async def create_jira_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Mock Jira creation
        created_tasks = []
        
        def mock_create(item, parent_id=None):
            # Simulate creating a task in Jira and getting an ID
            fake_id = f"JIRA-{len(created_tasks) + 100}"
            item["jira_id"] = fake_id
            item["parent_id"] = parent_id
            created_tasks.append(item)
            print(f"Created Jira {item['type']}: {item['summary']} ({fake_id}) assigned to {item.get('assignee', 'Unassigned')}")
            
            if "stories" in item:
                for story in item["stories"]:
                    mock_create(story, fake_id)
            
            if "subtasks" in item:
                for subtask in item["subtasks"]:
                    mock_create(subtask, fake_id)
            
            return item

        return [mock_create(task) for task in tasks]
