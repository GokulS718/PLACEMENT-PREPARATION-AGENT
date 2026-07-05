import os
import json
import logging
from typing import Dict, Any, List, Optional
import uuid
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import project modules
from models import init_db, get_db, User, SessionState, PerformanceLog, ResourceRecommendation
from graph import placement_graph, AgentState
from utils import parse_resume

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FastAPIBackend")

# Redis Caches
try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    HAS_REDIS = True
except Exception as e:
    redis_client = None
    HAS_REDIS = False

app = FastAPI(
    title="Placement Prep Agent API",
    description="Agentic placement assistant using LangGraph, Pinecone, and Google Gemini."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup migration
@app.on_event("startup")
def startup_event():
    init_db()
    logger.info("Relational database schemas initialized successfully.")

# Pydantic validation schemas
class StartAssessmentRequest(BaseModel):
    subject: str = "Coding"
    companies: List[str] = Field(default_factory=list)
    difficulty: Optional[str] = "Easy"
    language: Optional[str] = "Python"
    skills: Optional[str] = ""
    weak_areas: Optional[str] = ""
    resume_text: Optional[str] = ""

class SubmitAnswerRequest(BaseModel):
    answer: str
    question: Optional[Dict[str, Any]] = None

# Helper functions to persist state
def persist_state(user_id: str, state: Dict[str, Any], db: Session):
    if HAS_REDIS and redis_client:
        try:
            redis_client.setex(f"state:{user_id}", 3600, json.dumps(state))
        except Exception:
            pass

    db_state = db.query(SessionState).filter(SessionState.user_id == user_id).first()
    if not db_state:
        db_state = SessionState(user_id=user_id, state_data=state)
        db.add(db_state)
    else:
        db_state.state_data = state
    db.commit()

def retrieve_state(user_id: str, db: Session) -> Optional[Dict[str, Any]]:
    if HAS_REDIS and redis_client:
        try:
            cached = redis_client.get(f"state:{user_id}")
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    db_state = db.query(SessionState).filter(SessionState.user_id == user_id).first()
    if db_state:
        return db_state.state_data
    return None

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    try:
        secret_key = os.environ.get("JWT_SECRET", "super-secret-default-key")
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

from fastapi.responses import HTMLResponse, FileResponse, Response

# Static Files serving endpoints directly at root for browser ease
@app.get("/")
def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/styles.css")
def read_css():
    with open("styles.css", "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="text/css", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/app.js")
def read_js():
    with open("app.js", "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="application/javascript", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

class AuthLoginRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    is_google: Optional[bool] = False

import jwt # Assuming jwt is available, or we generate a mock token
import time

@app.post("/auth/login")
def auth_login(req: AuthLoginRequest, db: Session = Depends(get_db)):
    if not req.email:
        return {"success": False, "message": "Email is required."}
        
    user = db.query(User).filter(User.email == req.email).first()
    
    if user:
        if not req.is_google:
            if user.password and user.password != req.password:
                return {"success": False, "message": "Incorrect password for this Email."}
        if not user.password and not req.is_google:
            user.password = req.password
        if req.name and not user.name:
            user.name = req.name
        db.commit()
    else:
        user = User(
            email=req.email,
            password=req.password if not req.is_google else None,
            name=req.name or "Google User" if req.is_google else "Student"
        )
        db.add(user)
        db.commit()
    
    # Create JWT Token
    jwt_payload = {
        "sub": user.email,
        "name": user.name,
        "iat": time.time(),
        "exp": time.time() + (24 * 60 * 60) # 24 hours expiry
    }
    secret_key = os.environ.get("JWT_SECRET", "super-secret-default-key")
    real_token = jwt.encode(jwt_payload, secret_key, algorithm="HS256")
    
    return {
        "success": True,
        "message": "Authentication successful",
        "email": user.email,
        "name": user.name,
        "token": real_token
    }

@app.post("/resume/upload")
async def upload_resume_file(file: UploadFile = File(...)):
    try:
        content_bytes = await file.read()
        extracted_text = parse_resume(content_bytes, file.filename)
        
        ats_analysis = placement_graph.analyze_resume_ats(extracted_text)
        
        return {
            "filename": file.filename, 
            "extracted_text": extracted_text,
            "ats_analysis": ats_analysis
        }
    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse resume.")

@app.post("/assessment/start")
def start_assessment(req: StartAssessmentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("--- START ASSESSMENT ENDPOINT CALLED ---")
    logger.info(f"Raw Request Payload dict: {req.dict()}")
    logger.info(f"[PAYLOAD RECEIVED] companies={req.companies}, topic={req.subject}, difficulty={req.difficulty}")
    user = current_user
    session_id = str(uuid.uuid4())

    initial_state: AgentState = {
        "user_id": user.email,
        "current_stage": "question_generation",
        "resume_data": {
            "prep_level": req.difficulty,
            "companies": req.companies,
            "skills": req.skills,
            "resume_text": req.resume_text,
            "subject": req.subject
        },
        "performance_history": [],
        "weak_areas": [w.strip() for w in req.weak_areas.split(',')] if req.weak_areas else [],
        "resume_rating": None,
        "resume_rating_label": None,
        "resume_feedback": None,
        "confidence_score": 0.0,
        "next_action": "generate_question",
        "current_difficulty": req.difficulty,
        "consecutive_high_scores": 0,
        "consecutive_low_scores": 0,
        "current_question": None,
        "current_answer": None,
        "latest_score": 0.0,
        "recommended_resources": []
    }

    # Run resume_analyzer in background (LLM call can be slow)
    # We still update the persisted state but don't block the HTTP response
    import threading
    
    def run_resume_analysis():
        try:
            updated_state = placement_graph.resume_analyzer(initial_state)
            initial_state.update(updated_state)
            from models import get_db as _get_db
            _db = next(_get_db())
            persist_state(user.email, initial_state, _db)
            _db.close()
        except Exception as e:
            logger.warning(f"Background resume analysis failed (non-blocking): {e}")

    # Persist basic state immediately so /question/next works right away
    persist_state(user.email, initial_state, db)
    
    # Launch LLM resume analysis in background
    t = threading.Thread(target=run_resume_analysis, daemon=True)
    t.start()

    return {
        "status": "initialized",
        "user_id": user.email,
        "resume_analysis": "Analysis running in background — fetch your first question!",
        "gaps": initial_state["weak_areas"]
    }

@app.get("/assessment/status")
def get_assessment_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = retrieve_state(current_user.email, db)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found.")
    
    return {
        "status": "active",
        "resume_rating": state.get("resume_rating"),
        "resume_rating_label": state.get("resume_rating_label"),
        "resume_feedback": state.get("resume_feedback")
    }

@app.get("/question/next")
def get_next_question(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = retrieve_state(current_user.email, db)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found. Start assessment first.")

    if state.get("current_question") and state.get("current_stage") == "questioning":
        return state["current_question"]

    updated = placement_graph.question_generator(state)
    state.update(updated)
    persist_state(current_user.email, state, db)
    return state["current_question"]

@app.get("/question/batch")
def get_question_batch(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = retrieve_state(current_user.email, db)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found. Start assessment first.")
    
    questions = placement_graph.question_generator_batch(state)
    return questions

@app.post("/answer/submit")
def submit_answer(req: SubmitAnswerRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = retrieve_state(current_user.email, db)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found.")

    if req.question:
        state["current_question"] = req.question

    if not state.get("current_question"):
        raise HTTPException(status_code=400, detail="No active question available to grade.")

    state["current_answer"] = req.answer
    state["current_stage"] = "evaluating"

    eval_updates = placement_graph.answer_evaluator(state)
    state.update(eval_updates)

    weakness_updates = placement_graph.weakness_analyzer(state)
    state.update(weakness_updates)

    rec_updates = placement_graph.resource_recommender(state)
    state.update(rec_updates)

    eval_res = state["performance_history"][-1]
    log = PerformanceLog(
        user_id=current_user.email,
        question_id=eval_res.get("question_id"),
        topic=eval_res.get("topic"),
        difficulty=state.get("current_difficulty"),
        question_text=state["current_question"]["question"],
        user_answer=req.answer,
        score=eval_res.get("score"),
        feedback=eval_res.get("feedback"),
        expected_answer=state["current_question"].get("expected_answer")
    )
    db.add(log)

    for item in state["recommended_resources"]:
        existing = db.query(ResourceRecommendation).filter(
            ResourceRecommendation.user_id == current_user.email,
            ResourceRecommendation.topic == item["topic"]
        ).first()
        if not existing:
            db.add(ResourceRecommendation(
                user_id=current_user.email,
                topic=item["topic"],
                resources=item["resources"]
            ))
    db.commit()

    next_action = state.get("next_action")
    if next_action == "track_progress":
        progress_updates = placement_graph.progress_tracker(state)
        state.update(progress_updates)
        next_action = "complete"
    elif next_action in ["concept_review", "next_question", "resource_recommender"]:
        state["current_question"] = None

    persist_state(current_user.email, state, db)

    return {
        "evaluation": {
            "score": eval_updates["latest_score"],
            "feedback": eval_res.get("feedback")
        },
        "next_step": next_action,
        "difficulty": state["current_difficulty"]
    }

@app.get("/progress")
def get_progress(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.email
    user = db.query(User).filter(User.email == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found.")

    logs = db.query(PerformanceLog).filter(PerformanceLog.user_id == user_id).order_by(PerformanceLog.timestamp.desc()).all()
    recs = db.query(ResourceRecommendation).filter(ResourceRecommendation.user_id == user_id).all()

    scores = [l.score for l in logs if l.score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    state = retrieve_state(user_id, db)
    confidence = state.get("confidence_score", 50.0) if state else 50.0

    history = [{
        "timestamp": l.timestamp.isoformat(),
        "question": l.question_text,
        "answer": l.user_answer,
        "score": l.score,
        "feedback": l.feedback,
        "topic": l.topic,
        "difficulty": l.difficulty
    } for l in logs]

    resources = [{
        "topic": r.topic,
        "links": r.resources
    } for r in recs]

    return {
        "user_id": user_id,
        "name": user.name,
        "readiness_score": avg_score,
        "placement_probability": confidence,
        "weak_areas": state.get("weak_areas", []) if state else [],
        "history": history,
        "recommendations": resources
    }

@app.get("/weakness")
def get_weakness(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.email
    logs = db.query(PerformanceLog).filter(PerformanceLog.user_id == user_id).all()
    if not logs:
        return {"user_id": user_id, "breakdown": []}

    topic_groups = {}
    for l in logs:
        if l.topic not in topic_groups:
            topic_groups[l.topic] = []
        topic_groups[l.topic].append(l.score)

    breakdown = []
    for topic, scores in topic_groups.items():
        avg = sum(scores) / len(scores)
        status = "Needs Improvement" if avg < 60 else ("Mastered" if avg >= 80 else "Developing")
        breakdown.append({
            "topic": topic,
            "average_score": round(avg, 2),
            "attempts": len(scores),
            "status": status
        })

    return {
        "user_id": user_id,
        "breakdown": breakdown
    }

@app.post("/mock/start")
def start_mock_interview(req: StartAssessmentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(SessionState).filter(SessionState.user_id == current_user.email).delete()
    db.query(PerformanceLog).filter(PerformanceLog.user_id == current_user.email).delete()
    db.commit()
    return start_assessment(req, current_user, db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
