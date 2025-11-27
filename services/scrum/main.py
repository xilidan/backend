<<<<<<< HEAD
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/api/v1/generate-feedback', methods=['POST'])
def generate_feedback():
    """
    Generate meeting feedback and questions based on transcription
    This is a mock implementation - integrate with actual AI model (OpenAI, etc.)
    """
    data = request.get_json()
    
    if not data or 'transcription' not in data:
        return jsonify({'error': 'transcription is required'}), 400
    
    transcription = data['transcription']
    
    # TODO: Integrate with actual AI model (GPT-4, Claude, etc.)
    # For now, return mock feedback
    feedback = f"""📊 Meeting Summary:
Based on the transcription, here are the key points:

1. Team discussed project progress and upcoming milestones
2. Identified potential blockers that need attention
3. Assigned action items to team members

💡 Recommendations:
- Follow up on action items before next meeting
- Schedule a technical review session
- Update project documentation
"""
    
    questions = [
        "What are the main blockers preventing progress?",
        "Do we need additional resources for upcoming sprint?",
        "Are all team members clear on their action items?",
        "When is the next checkpoint meeting scheduled?"
    ]
    
    return jsonify({
        'feedback': feedback,
        'questions': questions
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)

=======
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from service import JiraScrumMasterService
from typing import List, Dict, Any, Optional

app = FastAPI(title="Jira AI Scrum Master")
service = JiraScrumMasterService()

@app.post("/decompose", response_model=List[Dict[str, Any]])
async def decompose_document(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        # 1. Parse File
        text = await service.parse_file(file)
        
        # 2. Get Organization Info (using token)
        # Assuming token format "Bearer <token>"
        token = authorization.split(" ")[1] if " " in authorization else authorization
        organization = await service.get_organization_info(token)
        
        # 3. Decompose into Tasks (Epics -> Stories -> Subtasks)
        tasks = await service.decompose_tasks(text)
        
        # 4. Assign Tasks
        assigned_tasks = service.assign_tasks(tasks, organization)
        
        # 5. Create Tasks in Jira (Mocked)
        final_tasks = await service.create_jira_tasks(assigned_tasks)
        
        return final_tasks
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
>>>>>>> 1f8cfe1 (feat: Implement new Scrum Master service with AI-powered hierarchical task decomposition, file parsing, and organization integration.)
