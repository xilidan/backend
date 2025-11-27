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
