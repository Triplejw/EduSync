import json
import secrets
import string
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import our custom services
from llm_service import generate_quiz, generate_summary, generate_flashcards
from parser_service import extract_text_from_image
from database import (
    SessionLocal,
    User,
    Classroom,
    ClassroomEnrollment,
    Material,
    Assignment,
    QuizSubmission,
    get_db,
)
from auth import get_password_hash, verify_password, get_current_user

app = FastAPI(title="EduSync API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_class_code():
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


# --- Pydantic Schemas ---

class TextRequest(BaseModel):
    text: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # "teacher" or "student"


class LoginRequest(BaseModel):
    email: str
    password: str


class ClassroomCreate(BaseModel):
    name: str


class ClassroomJoin(BaseModel):
    code: str


class MaterialCreate(BaseModel):
    title: str
    summary: str = ""
    flashcards_json: str = "[]"
    quiz_json: str = "[]"
    classroom_id: Optional[int] = None
    raw_text: str = ""


class AssignmentCreate(BaseModel):
    title: str
    quiz_json: str
    classroom_id: int
    material_id: Optional[int] = None


class QuizSubmit(BaseModel):
    assignment_id: int
    answers: list  # List of {question_index, selected_answer_index}


# --- Health ---

@app.get("/")
def read_root():
    return {"status": "EduSync API Online"}


# --- Auth ---

@app.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=req.email,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = secrets.token_urlsafe(32)
    # Simple token storage (in production use Redis/DB)
    return {"user_id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name, "token": token}


@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    token = secrets.token_urlsafe(32)
    return {"user_id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name, "token": token}


# --- AI Endpoints (Core Pipeline - unchanged) ---

@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    contents = await file.read()
    extracted_text = extract_text_from_image(contents)
    return {"extracted_text": extracted_text}


@app.post("/generate-quiz")
def create_quiz(request: TextRequest):
    quiz_json = generate_quiz(request.text)
    return {"quiz": quiz_json}


@app.post("/generate-summary")
def create_summary(request: TextRequest):
    summary = generate_summary(request.text)
    return {"summary": summary}


@app.post("/generate-flashcards")
def create_flashcards(request: TextRequest):
    flashcards = generate_flashcards(request.text)
    return {"flashcards": flashcards}


# --- Classrooms ---

@app.post("/classrooms", dependencies=[Depends(get_current_user)])
def create_classroom(req: ClassroomCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(403, "Only teachers can create classrooms")
    code = generate_class_code()
    classroom = Classroom(name=req.name, code=code, teacher_id=user.id)
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return {"id": classroom.id, "name": classroom.name, "code": classroom.code}


@app.get("/classrooms", dependencies=[Depends(get_current_user)])
def list_classrooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "teacher":
        rooms = db.query(Classroom).filter(Classroom.teacher_id == user.id).all()
    else:
        enrollments = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.user_id == user.id).all()
        room_ids = [e.classroom_id for e in enrollments]
        rooms = db.query(Classroom).filter(Classroom.id.in_(room_ids)).all()
    return [{"id": r.id, "name": r.name, "code": r.code} for r in rooms]


@app.post("/classrooms/join", dependencies=[Depends(get_current_user)])
def join_classroom(req: ClassroomJoin, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    classroom = db.query(Classroom).filter(Classroom.code == req.code.upper()).first()
    if not classroom:
        raise HTTPException(404, "Classroom not found")
    existing = db.query(ClassroomEnrollment).filter(
        ClassroomEnrollment.classroom_id == classroom.id,
        ClassroomEnrollment.user_id == user.id,
    ).first()
    if existing:
        return {"message": "Already enrolled", "classroom_id": classroom.id}
    enrollment = ClassroomEnrollment(classroom_id=classroom.id, user_id=user.id)
    db.add(enrollment)
    db.commit()
    return {"message": "Joined", "classroom_id": classroom.id, "name": classroom.name}


# --- Materials ---

@app.post("/materials", dependencies=[Depends(get_current_user)])
def create_material(req: MaterialCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = Material(
        title=req.title,
        summary=req.summary,
        flashcards_json=req.flashcards_json,
        quiz_json=req.quiz_json,
        classroom_id=req.classroom_id,
        raw_text=req.raw_text,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return {"id": material.id, "title": material.title}


@app.get("/materials", dependencies=[Depends(get_current_user)])
def list_materials(classroom_id: Optional[int] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Material)
    if user.role == "teacher":
        # Teachers see materials from their classrooms or unassigned materials
        teacher_room_ids = [r.id for r in db.query(Classroom).filter(Classroom.teacher_id == user.id).all()]
        q = q.filter(
            (Material.classroom_id.in_(teacher_room_ids)) | (Material.classroom_id.is_(None))
        )
    else:
        # Students see materials from classrooms they're enrolled in
        enrollments = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.user_id == user.id).all()
        room_ids = [e.classroom_id for e in enrollments]
        q = q.filter(Material.classroom_id.in_(room_ids))
    if classroom_id:
        q = q.filter(Material.classroom_id == classroom_id)
    materials = q.order_by(Material.created_at.desc()).all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "summary": m.summary[:200] + "..." if len(m.summary or "") > 200 else (m.summary or ""),
            "flashcards_json": m.flashcards_json,
            "quiz_json": m.quiz_json,
            "classroom_id": m.classroom_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in materials
    ]


@app.get("/materials/{material_id}", dependencies=[Depends(get_current_user)])
def get_material(material_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, "Material not found")
    return {
        "id": material.id,
        "title": material.title,
        "summary": material.summary,
        "flashcards_json": material.flashcards_json,
        "quiz_json": material.quiz_json,
        "raw_text": material.raw_text,
        "classroom_id": material.classroom_id,
    }


# --- Assignments ---

@app.post("/assignments", dependencies=[Depends(get_current_user)])
def create_assignment(req: AssignmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(403, "Only teachers can create assignments")
    classroom = db.query(Classroom).filter(Classroom.id == req.classroom_id, Classroom.teacher_id == user.id).first()
    if not classroom:
        raise HTTPException(404, "Classroom not found")
    assignment = Assignment(
        title=req.title,
        quiz_json=req.quiz_json,
        classroom_id=req.classroom_id,
        material_id=req.material_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {"id": assignment.id, "title": assignment.title}


@app.get("/assignments", dependencies=[Depends(get_current_user)])
def list_assignments(classroom_id: Optional[int] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "teacher":
        q = db.query(Assignment)
        if classroom_id:
            q = q.filter(Assignment.classroom_id == classroom_id)
        assignments = q.order_by(Assignment.created_at.desc()).all()
    else:
        enrollments = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.user_id == user.id).all()
        room_ids = [e.classroom_id for e in enrollments]
        q = db.query(Assignment).filter(Assignment.classroom_id.in_(room_ids))
        if classroom_id:
            q = q.filter(Assignment.classroom_id == classroom_id)
        assignments = q.order_by(Assignment.created_at.desc()).all()

    result = []
    for a in assignments:
        submissions = db.query(QuizSubmission).filter(QuizSubmission.assignment_id == a.id).all()
        my_sub = db.query(QuizSubmission).filter(
            QuizSubmission.assignment_id == a.id,
            QuizSubmission.user_id == user.id,
        ).first()
        result.append({
            "id": a.id,
            "title": a.title,
            "quiz_json": a.quiz_json,
            "classroom_id": a.classroom_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "submission_count": len(submissions),
            "my_score": my_sub.score if my_sub else None,
        })
    return result


@app.get("/assignments/{assignment_id}", dependencies=[Depends(get_current_user)])
def get_assignment(assignment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    return {
        "id": assignment.id,
        "title": assignment.title,
        "quiz_json": assignment.quiz_json,
        "classroom_id": assignment.classroom_id,
    }


@app.post("/assignments/{assignment_id}/submit", dependencies=[Depends(get_current_user)])
def submit_quiz(assignment_id: int, req: QuizSubmit, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    existing = db.query(QuizSubmission).filter(
        QuizSubmission.assignment_id == assignment_id,
        QuizSubmission.user_id == user.id,
    ).first()
    if existing:
        raise HTTPException(400, "Already submitted")

    try:
        quiz = json.loads(assignment.quiz_json)
    except Exception:
        quiz = []
    correct = 0
    for i, ans in enumerate(req.answers):
        if i < len(quiz) and quiz[i].get("correct_answer") == ans.get("selected_answer_index"):
            correct += 1
    score = (correct / len(quiz) * 100) if quiz else 0

    sub = QuizSubmission(
        assignment_id=assignment_id,
        user_id=user.id,
        score=score,
        answers_json=json.dumps(req.answers),
    )
    db.add(sub)
    db.commit()
    return {"score": score, "correct": correct, "total": len(quiz)}


# --- Student Progress (Teacher Dashboard) ---

@app.get("/progress/classroom/{classroom_id}", dependencies=[Depends(get_current_user)])
def get_classroom_progress(classroom_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(403, "Teachers only")
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id, Classroom.teacher_id == user.id).first()
    if not classroom:
        raise HTTPException(404, "Classroom not found")

    enrollments = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.classroom_id == classroom_id).all()
    assignments = db.query(Assignment).filter(Assignment.classroom_id == classroom_id).all()

    students = []
    for e in enrollments:
        u = db.query(User).filter(User.id == e.user_id).first()
        if not u:
            continue
        submissions = db.query(QuizSubmission).filter(
            QuizSubmission.user_id == u.id,
            QuizSubmission.assignment_id.in_([a.id for a in assignments]),
        ).all()
        avg_score = sum(s.score for s in submissions) / len(submissions) if submissions else 0
        students.append({
            "user_id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "submissions_count": len(submissions),
            "average_score": round(avg_score, 1),
            "scores": [{"assignment_id": s.assignment_id, "score": s.score} for s in submissions],
        })
    return {"classroom": {"id": classroom.id, "name": classroom.name}, "students": students}


@app.get("/progress/submissions/{assignment_id}", dependencies=[Depends(get_current_user)])
def get_assignment_submissions(assignment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(403, "Teachers only")
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    classroom = db.query(Classroom).filter(Classroom.id == assignment.classroom_id, Classroom.teacher_id == user.id).first()
    if not classroom:
        raise HTTPException(403, "Not your classroom")

    submissions = db.query(QuizSubmission).filter(QuizSubmission.assignment_id == assignment_id).all()
    result = []
    for s in submissions:
        u = db.query(User).filter(User.id == s.user_id).first()
        result.append({
            "user_id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "score": s.score,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        })
    return {"assignment_title": assignment.title, "submissions": result}
