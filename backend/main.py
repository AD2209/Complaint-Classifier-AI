import uuid
import os
import shutil
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .database import engine, get_db
from .llm_utils import analyze_complaint

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bank Complaint Routing API")

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount the uploads directory to serve static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")
    
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Return the relative URL path to access the image
    return {"attachment_path": f"/uploads/{unique_filename}"}

@app.post("/complaints/", response_model=schemas.ComplaintResponse)
def create_complaint(complaint: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    # Analyze using Groq LLM
    analysis = analyze_complaint(complaint.description)
    
    category = analysis.get("category", "General Support Portal")
    urgency = analysis.get("urgency", "Low")
    advice = analysis.get("advice", "Please monitor your account.")
    action_taken = analysis.get("action_to_take", "None")
    translated_desc = analysis.get("translated_description", complaint.description)
    
    if action_taken.lower() == "none":
        action_taken = None

    # Generate unique ID
    complaint_id = f"REF-{str(uuid.uuid4())[:8].upper()}"
    
    if category == "Rejected":
        raise HTTPException(
            status_code=400, 
            detail="Your issue appears to be unrelated to banking services. We only accept complaints regarding Fraud, Account Services, and Loans."
        )
    
    db_complaint = models.Complaint(
        id=complaint_id,
        user_details=complaint.user_details,
        description=translated_desc,
        category=category,
        urgency=urgency,
        advice=advice,
        action_taken=action_taken,
        attachment_path=complaint.attachment_path,
        status="Pending"
    )
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint

@app.get("/complaints/", response_model=List[schemas.ComplaintResponse])
def get_complaints(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    complaints = db.query(models.Complaint).order_by(models.Complaint.created_at.desc()).offset(skip).limit(limit).all()
    return complaints

@app.get("/complaints/{complaint_id}", response_model=schemas.ComplaintResponse)
def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@app.patch("/complaints/{complaint_id}/resolve", response_model=schemas.ComplaintResponse)
def resolve_complaint(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint.status = "Resolved"
    db.commit()
    db.refresh(complaint)
    return complaint
