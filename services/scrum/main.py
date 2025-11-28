from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from service import JiraScrumMasterService
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime as DateTime

app = FastAPI(title="Jira AI Scrum Master")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = JiraScrumMasterService()

@app.post("/decompose", response_model=List[Dict[str, Any]])
async def decompose_document(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        text = await service.parse_file(file)
        
        token = authorization.split(" ")[1] if " " in authorization else authorization
        organization = await service.get_organization_info(token)
        
        tasks = await service.decompose_tasks(text)
        
        assigned_tasks = service.assign_tasks(tasks, organization)
        
        final_tasks = await service.create_jira_tasks(assigned_tasks, token)
        
        return final_tasks
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class Person(BaseModel):
    name: str
    email: Optional[str] = None

class ActionItem(BaseModel):
    text: str

class KeyQuestion(BaseModel):
    text: str

class Topic(BaseModel):
    text: str

class ChapterSummary(BaseModel):
    title: str
    description: str
    topics: List[Topic]

class Speaker(BaseModel):
    name: str

class SpeakerBlock(BaseModel):
    start_time: str
    end_time: str
    speaker: Speaker
    words: str

class Transcript(BaseModel):
    speakers: List[Speaker]
    speaker_blocks: List[SpeakerBlock]

class TranscriptionRequest(BaseModel):
    session_id: str
    trigger: str
    title: str
    start_time: DateTime
    end_time: DateTime
    participants: List[Person]
    owner: Person
    summary: str
    action_items: List[ActionItem]
    key_questions: List[KeyQuestion]
    topics: List[Topic]
    report_url: str
    chapter_summaries: List[ChapterSummary]
    transcript: Transcript

@app.post("/analyze-transcription")
async def analyze_transcription(request: TranscriptionRequest):
    try:
        result = await service.analyze_transcription(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(
    message: str = Form(...),
    session_id: str = Form(...),
    file: UploadFile = File(None),
    authorization: Optional[str] = Header(None)
):
    try:
        return StreamingResponse(service.chat(message, session_id, file, authorization), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    await service.sync_jira_data()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, debug=True)