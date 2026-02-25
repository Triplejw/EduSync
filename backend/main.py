import json
import os
import secrets
import string
import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Directory to store uploaded files
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Import our custom services
from llm_service import generate_quiz, generate_summary, generate_flashcards
from parser_service import extract_text_from_document
from database import (
    SessionLocal,
    User,
    Classroom,
    ClassroomEnrollment,
    Material,
    Assignment,
    QuizSubmission,
    LearningSession,
    get_db,
)
from auth import get_password_hash, verify_password, get_current_user
from jwt_utils import create_access_token
from signal_processor import calculate_engagement
from vision_service import estimate_pose
from metrics_logger import Timer, log_inference_metrics, log_engagement_metrics, get_metrics_summary

app = FastAPI(title="EduSync API")

# CORS configuration: restrict origins in production
# Set EDUSYNC_CORS_ORIGINS="https://app.example.com,https://example.com" for production
_cors_origins_env = os.environ.get("EDUSYNC_CORS_ORIGINS", "")
if _cors_origins_env:
    ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
else:
    # Development default: allow all (with warning logged at startup)
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Create Test Accounts on Startup (Gated by Environment Variable) ---
@app.on_event("startup")
def create_test_accounts():
    """
    Create test accounts only when EDUSYNC_CREATE_TEST_ACCOUNTS=1.
    This prevents backdoor access in production deployments.
    """
    if os.environ.get("EDUSYNC_CREATE_TEST_ACCOUNTS") != "1":
        return  # Skip test account creation in production

    db = SessionLocal()
    try:
        test_accounts = [
            {"email": "teacher@test.com", "full_name": "Test Teacher", "role": "teacher"},
            {"email": "student@test.com", "full_name": "Test Student", "role": "student"},
        ]
        for account in test_accounts:
            existing = db.query(User).filter(User.email == account["email"]).first()
            if not existing:
                user = User(
                    email=account["email"],
                    hashed_password=get_password_hash("test123"),  # Default password
                    full_name=account["full_name"],
                    role=account["role"],
                )
                db.add(user)
                print(f"✅ Created test account: {account['email']} ({account['role']})")
            else:
                print(f"ℹ️ Test account exists: {account['email']}")
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def log_security_warnings():
    """Log security configuration warnings at startup."""
    if ALLOWED_ORIGINS == ["*"]:
        print("⚠️  CORS allows all origins. Set EDUSYNC_CORS_ORIGINS for production.")
    if not os.environ.get("EDUSYNC_JWT_SECRET"):
        print("⚠️  JWT secret not set. Set EDUSYNC_JWT_SECRET for production.")


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
    subject_name: Optional[str] = None


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


class SubmitAnalyticsRequest(BaseModel):
    material_id: int
    scroll_signal: list  # List of scroll deltas (pixels per second) at 1Hz


class AnalyzeAttentionRequest(BaseModel):
    image: str  # Base64-encoded image
    student_id: str
    timestamp: int
    assignment_id: Optional[int] = None  # For quiz-attention correlation


# --- Health ---

@app.get("/")
def read_root():
    return {"status": "EduSync API Online"}


@app.get("/health")
def health():
    """Light health check for connectivity (no auth)."""
    return {"status": "ok"}


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
    access_token = create_access_token(user.id, user.email, user.role)
    return {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    access_token = create_access_token(user.id, user.email, user.role)
    return {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


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


# --- Upload Material (Combined Pipeline) ---

# Upload validation settings
UPLOAD_MAX_SIZE_MB = int(os.environ.get("EDUSYNC_UPLOAD_MAX_MB", "50"))
UPLOAD_MAX_SIZE_BYTES = UPLOAD_MAX_SIZE_MB * 1024 * 1024
UPLOAD_ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt", ".jpg", ".jpeg", ".png"}


@app.post("/upload-material", dependencies=[Depends(get_current_user)])
async def upload_material(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    classroom_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upload a file (PDF/image/PPT), extract text via OCR, and save.
    AI content (summary, flashcards, quiz) is generated on-demand via separate endpoints.

    Validation:
        - Max file size: 50MB (configurable via EDUSYNC_UPLOAD_MAX_MB)
        - Allowed extensions: .pdf, .pptx, .ppt, .jpg, .jpeg, .png
    """
    if user.role != "teacher":
        raise HTTPException(403, "Only teachers can upload materials")

    # Validate file extension
    file_ext = (os.path.splitext(file.filename or "")[-1] or "").lower()
    if file_ext not in UPLOAD_ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Invalid file type '{file_ext}'. Allowed: {', '.join(sorted(UPLOAD_ALLOWED_EXTENSIONS))}"
        )

    print(f"📤 Upload started: {file.filename} by {user.email}")

    # Read file with size validation
    contents = await file.read()
    if len(contents) > UPLOAD_MAX_SIZE_BYTES:
        raise HTTPException(
            400,
            f"File too large ({len(contents) / 1024 / 1024:.1f}MB). Maximum: {UPLOAD_MAX_SIZE_MB}MB"
        )

    # 1. Save the file to disk
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    print(f"   ✅ File saved: {unique_filename} ({len(contents)} bytes)")

    # 2. Extract text via OCR (with metrics logging)
    print("   🔍 Running OCR...")
    with Timer("ocr") as ocr_timer:
        try:
            raw_text = extract_text_from_document(contents, file_ext)
            print(f"   ✅ OCR complete: {len(raw_text)} characters extracted")
        except Exception as e:
            print(f"   ❌ OCR error: {e}")
            raw_text = f"Error extracting text: {e}"
    log_inference_metrics("ocr", ocr_timer.duration_ms, len(contents), len(raw_text))

    # 3. Create the Material record (NO AI generation - that's on-demand now)
    decoded_filename = unquote(file.filename or "Untitled")
    material_title = title or decoded_filename.rsplit(".", 1)[0]
    material = Material(
        title=material_title,
        file_path=unique_filename,
        raw_text=raw_text,
        summary="",
        flashcards_json="[]",
        quiz_json="[]",
        classroom_id=classroom_id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    print(f"   ✅ Material saved to DB: ID={material.id}, title={material.title}")
    print(f"📤 Upload complete!")

    return {
        "id": material.id,
        "title": material.title,
        "file_path": material.file_path,
        "has_raw_text": len(raw_text) > 50,
    }


# --- On-Demand AI Generation Endpoints ---

@app.post("/materials/{material_id}/generate-summary", dependencies=[Depends(get_current_user)])
def generate_material_summary(material_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Generate summary for a material on-demand. Returns cached if already generated."""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, "Material not found")
    
    # Return cached if exists
    if material.summary and len(material.summary) > 10:
        return {"summary": material.summary, "cached": True}
    
    if not material.raw_text or len(material.raw_text) < 50:
        raise HTTPException(400, "Material has no extractable text")
    
    print(f"🤖 Generating summary for material {material_id}...")
    with Timer("summary") as summary_timer:
        try:
            summary = generate_summary(material.raw_text)
            print(f"   ✅ Summary generated: {len(summary)} chars")
        except Exception as e:
            print(f"   ❌ Summary error: {e}")
            raise HTTPException(500, f"Failed to generate summary: {e}")
    log_inference_metrics("summary", summary_timer.duration_ms, len(material.raw_text), len(summary))
    
    material.summary = summary
    db.commit()
    return {"summary": summary, "cached": False}


@app.post("/materials/{material_id}/generate-flashcards", dependencies=[Depends(get_current_user)])
def generate_material_flashcards(material_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Generate flashcards for a material on-demand. Returns cached if already generated."""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, "Material not found")
    
    # Return cached if exists (not empty array)
    try:
        existing = json.loads(material.flashcards_json) if material.flashcards_json else []
        if len(existing) > 0:
            return {"flashcards": material.flashcards_json, "cached": True}
    except:
        pass
    
    if not material.raw_text or len(material.raw_text) < 50:
        raise HTTPException(400, "Material has no extractable text")
    
    print(f"🤖 Generating flashcards for material {material_id}...")
    with Timer("flashcards") as flashcards_timer:
        try:
            flashcards_json = generate_flashcards(material.raw_text)
            if not isinstance(flashcards_json, str):
                flashcards_json = json.dumps(flashcards_json)
            print(f"   ✅ Flashcards generated")
        except Exception as e:
            print(f"   ❌ Flashcards error: {e}")
            raise HTTPException(500, f"Failed to generate flashcards: {e}")
    log_inference_metrics("flashcards", flashcards_timer.duration_ms, len(material.raw_text), len(flashcards_json))
    
    material.flashcards_json = flashcards_json
    db.commit()
    return {"flashcards": flashcards_json, "cached": False}


@app.post("/materials/{material_id}/generate-quiz", dependencies=[Depends(get_current_user)])
def generate_material_quiz(material_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Generate quiz for a material on-demand. Returns cached if already generated."""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, "Material not found")
    
    # Return cached if exists (not empty array)
    try:
        existing = json.loads(material.quiz_json) if material.quiz_json else []
        if len(existing) > 0:
            return {"quiz": material.quiz_json, "cached": True}
    except:
        pass
    
    if not material.raw_text or len(material.raw_text) < 50:
        raise HTTPException(400, "Material has no extractable text")
    
    print(f"🤖 Generating quiz for material {material_id}...")
    with Timer("quiz") as quiz_timer:
        try:
            quiz_json = generate_quiz(material.raw_text)
            if not isinstance(quiz_json, str):
                quiz_json = json.dumps(quiz_json)
            print(f"   ✅ Quiz generated")
        except Exception as e:
            print(f"   ❌ Quiz error: {e}")
            raise HTTPException(500, f"Failed to generate quiz: {e}")
    log_inference_metrics("quiz", quiz_timer.duration_ms, len(material.raw_text), len(quiz_json))
    
    material.quiz_json = quiz_json
    db.commit()
    return {"quiz": quiz_json, "cached": False}


@app.get("/materials/{material_id}/file", dependencies=[Depends(get_current_user)])
def get_material_file(material_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Serve the original uploaded file."""
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material or not material.file_path:
        raise HTTPException(404, "File not found")
    full_path = os.path.join(UPLOAD_DIR, material.file_path)
    if not os.path.exists(full_path):
        raise HTTPException(404, "File not found on disk")
    return FileResponse(full_path, filename=f"{material.title}{os.path.splitext(material.file_path)[-1]}")


# --- Classrooms ---

@app.post("/classrooms", dependencies=[Depends(get_current_user)])
def create_classroom(req: ClassroomCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(403, "Only teachers can create classrooms")
    code = generate_class_code()
    classroom = Classroom(name=req.name, subject_name=req.subject_name, code=code, teacher_id=user.id)
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return {"id": classroom.id, "name": classroom.name, "code": classroom.code, "subject_name": classroom.subject_name}


@app.get("/classrooms", dependencies=[Depends(get_current_user)])
def list_classrooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "teacher":
        rooms = db.query(Classroom).filter(Classroom.teacher_id == user.id).all()
    else:
        enrollments = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.user_id == user.id).all()
        room_ids = [e.classroom_id for e in enrollments]
        rooms = db.query(Classroom).filter(Classroom.id.in_(room_ids)).all()
    result = []
    for r in rooms:
        teacher = db.query(User).filter(User.id == r.teacher_id).first()
        result.append({
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "subject_name": r.subject_name,
            "teacher_name": teacher.full_name if teacher else None,
        })
    return result


@app.get("/classrooms/{classroom_id}", dependencies=[Depends(get_current_user)])
def get_classroom(classroom_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get a single classroom with details."""
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(404, "Classroom not found")
    # Check access
    if user.role == "teacher":
        if classroom.teacher_id != user.id:
            raise HTTPException(403, "Not your classroom")
    else:
        enrollment = db.query(ClassroomEnrollment).filter(
            ClassroomEnrollment.classroom_id == classroom_id,
            ClassroomEnrollment.user_id == user.id,
        ).first()
        if not enrollment:
            raise HTTPException(403, "Not enrolled in this classroom")
    teacher = db.query(User).filter(User.id == classroom.teacher_id).first()
    student_count = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.classroom_id == classroom_id).count()
    material_count = db.query(Material).filter(Material.classroom_id == classroom_id).count()
    return {
        "id": classroom.id,
        "name": classroom.name,
        "code": classroom.code,
        "subject_name": classroom.subject_name,
        "teacher_name": teacher.full_name if teacher else None,
        "student_count": student_count,
        "material_count": material_count,
    }


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
def list_materials(
    classroom_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List materials with pagination.

    Args:
        classroom_id: Filter by classroom (optional)
        skip: Number of items to skip (offset)
        limit: Maximum items to return (default 50, max 200)

    Returns:
        {"items": [...], "total": N, "skip": N, "limit": N}
    """
    # Validate pagination params
    limit = min(max(1, limit), 200)  # Clamp to 1-200
    skip = max(0, skip)

    q = db.query(Material)
    if user.role == "teacher":
        # Teachers see materials from their classrooms or unassigned materials
        teacher_room_ids = [r.id for r in db.query(Classroom).filter(Classroom.teacher_id == user.id).all()]
        q = q.filter(
            (Material.classroom_id.in_(teacher_room_ids)) | (Material.classroom_id.is_(None))
        )
    else:
        # Students see materials from classrooms they're enrolled in OR materials linked to assignments in those classrooms
        enrollments = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.user_id == user.id).all()
        room_ids = [e.classroom_id for e in enrollments]
        if room_ids:
            assignment_material_ids = [
                r[0] for r in db.query(Assignment.material_id).filter(
                    Assignment.classroom_id.in_(room_ids),
                    Assignment.material_id.isnot(None),
                ).distinct().all()
            ]
            q = q.filter(
                (Material.classroom_id.in_(room_ids)) | (Material.id.in_(assignment_material_ids))
            )
        else:
            q = q.filter(Material.id == -1)  # No enrollments -> no materials
    if classroom_id:
        q = q.filter(Material.classroom_id == classroom_id)

    # Get total count before pagination
    total = q.count()

    # Apply pagination
    materials = q.order_by(Material.created_at.desc()).offset(skip).limit(limit).all()
    items = [
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
    return {"items": items, "total": total, "skip": skip, "limit": limit}


def _student_can_access_material(material: Material, user: User, db: Session) -> bool:
    """True if student is allowed to see this material (enrolled classroom or assignment-linked)."""
    enrollments = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.user_id == user.id).all()
    room_ids = [e.classroom_id for e in enrollments]
    if not room_ids:
        return False
    if material.classroom_id in room_ids:
        return True
    exists = db.query(Assignment).filter(
        Assignment.classroom_id.in_(room_ids),
        Assignment.material_id == material.id,
    ).first()
    return exists is not None


@app.get("/materials/{material_id}", dependencies=[Depends(get_current_user)])
def get_material(material_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, "Material not found")
    if user.role == "student" and not _student_can_access_material(material, user, db):
        raise HTTPException(403, "You do not have access to this material")
    return {
        "id": material.id,
        "title": material.title,
        "summary": material.summary,
        "flashcards_json": material.flashcards_json,
        "quiz_json": material.quiz_json,
        "raw_text": material.raw_text,
        "classroom_id": material.classroom_id,
        "file_path": material.file_path,
    }


# --- Assignments ---

def _normalize_quiz_json(raw: str) -> str:
    """Parse quiz JSON, keep only valid question objects (up to 15), re-serialize. Raises ValueError if invalid."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid quiz JSON (quiz may have been truncated during generation): {e}")
    if not isinstance(data, list):
        raise ValueError("Quiz must be a JSON array of questions")
    out = []
    for i, item in enumerate(data):
        if i >= 15:
            break
        if not isinstance(item, dict):
            continue
        q = item.get("question")
        opts = item.get("options")
        ca = item.get("correct_answer")
        if not q or not isinstance(opts, list) or len(opts) != 4:
            continue
        try:
            idx = int(ca) if isinstance(ca, int) else int(ca)
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx > 3:
            continue
        out.append({"question": str(q)[:2000], "options": [str(o)[:500] for o in opts], "correct_answer": idx})
    if not out:
        raise ValueError("No valid questions found in quiz (quiz may have been truncated). Try generating again or use a shorter material.")
    return json.dumps(out)


@app.post("/assignments", dependencies=[Depends(get_current_user)])
def create_assignment(req: AssignmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "teacher":
        raise HTTPException(403, "Only teachers can create assignments")
    classroom = db.query(Classroom).filter(Classroom.id == req.classroom_id, Classroom.teacher_id == user.id).first()
    if not classroom:
        raise HTTPException(404, "Classroom not found")
    try:
        quiz_json = _normalize_quiz_json(req.quiz_json)
    except ValueError as e:
        raise HTTPException(400, str(e))
    assignment = Assignment(
        title=req.title,
        quiz_json=quiz_json,
        classroom_id=req.classroom_id,
        material_id=req.material_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {"id": assignment.id, "title": assignment.title}


@app.get("/assignments", dependencies=[Depends(get_current_user)])
def list_assignments(
    classroom_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List assignments with pagination.

    Args:
        classroom_id: Filter by classroom (optional)
        skip: Number of items to skip (offset)
        limit: Maximum items to return (default 50, max 200)

    Returns:
        {"items": [...], "total": N, "skip": N, "limit": N}
    """
    # Validate pagination params
    limit = min(max(1, limit), 200)
    skip = max(0, skip)

    if user.role == "teacher":
        q = db.query(Assignment)
        if classroom_id:
            q = q.filter(Assignment.classroom_id == classroom_id)
    else:
        enrollments = db.query(ClassroomEnrollment).filter(ClassroomEnrollment.user_id == user.id).all()
        room_ids = [e.classroom_id for e in enrollments]
        q = db.query(Assignment).filter(Assignment.classroom_id.in_(room_ids))
        if classroom_id:
            q = q.filter(Assignment.classroom_id == classroom_id)

    # Get total count before pagination
    total = q.count()

    # Apply pagination
    assignments = q.order_by(Assignment.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for a in assignments:
        # Use count() instead of fetching all submissions (more efficient)
        submission_count = db.query(QuizSubmission).filter(QuizSubmission.assignment_id == a.id).count()
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
            "submission_count": submission_count,
            "my_score": my_sub.score if my_sub else None,
        })
    return {"items": result, "total": total, "skip": skip, "limit": limit}


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
    materials = db.query(Material).filter(Material.classroom_id == classroom_id).all()
    material_ids = [m.id for m in materials]

    students = []
    total_quiz_scores = []
    total_engagement_scores = []

    for e in enrollments:
        u = db.query(User).filter(User.id == e.user_id).first()
        if not u:
            continue
        # Quiz submissions
        submissions = db.query(QuizSubmission).filter(
            QuizSubmission.user_id == u.id,
            QuizSubmission.assignment_id.in_([a.id for a in assignments]),
        ).all() if assignments else []
        avg_quiz_score = sum(s.score for s in submissions) / len(submissions) if submissions else 0

        # Engagement scores from LearningSession
        sessions = db.query(LearningSession).filter(
            LearningSession.user_id == u.id,
            LearningSession.material_id.in_(material_ids),
        ).all() if material_ids else []
        avg_engagement = sum(s.engagement_score for s in sessions) / len(sessions) if sessions else 0

        students.append({
            "user_id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "submissions_count": len(submissions),
            "average_score": round(avg_quiz_score, 1),
            "average_engagement": round(avg_engagement, 1),
            "sessions_count": len(sessions),
            "scores": [{"assignment_id": s.assignment_id, "score": s.score} for s in submissions],
        })

        if submissions:
            total_quiz_scores.extend([s.score for s in submissions])
        if sessions:
            total_engagement_scores.extend([s.engagement_score for s in sessions])

    # Aggregate stats for the classroom
    overall_avg_quiz = sum(total_quiz_scores) / len(total_quiz_scores) if total_quiz_scores else 0
    overall_avg_engagement = sum(total_engagement_scores) / len(total_engagement_scores) if total_engagement_scores else 0

    return {
        "classroom": {"id": classroom.id, "name": classroom.name},
        "stats": {
            "students_count": len(students),
            "average_quiz_score": round(overall_avg_quiz, 1),
            "average_engagement": round(overall_avg_engagement, 1),
            "total_submissions": len(total_quiz_scores),
            "total_sessions": len(total_engagement_scores),
        },
        "students": students,
    }


@app.get("/progress/classroom/{classroom_id}/dsp-metrics", dependencies=[Depends(get_current_user)])
def get_classroom_dsp_metrics(classroom_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return per-student DSP metrics (ZCR, energy, reading_ratio) from engagement logs for ECE demo."""
    if user.role != "teacher":
        raise HTTPException(403, "Teachers only")
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id, Classroom.teacher_id == user.id).first()
    if not classroom:
        raise HTTPException(404, "Classroom not found")
    materials = db.query(Material).filter(Material.classroom_id == classroom_id).all()
    material_ids = {m.id for m in materials}
    if not material_ids:
        return {"classroom_id": classroom_id, "students": []}

    from metrics_logger import get_metrics_file_paths
    paths = get_metrics_file_paths()
    engagement_file = paths.get("engagement")
    if not engagement_file or not os.path.exists(engagement_file):
        return {"classroom_id": classroom_id, "students": []}

    # Group engagement log rows by user_id (filter by material_id in classroom)
    by_user = {}
    with open(engagement_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            mid = row.get("material_id")
            if mid not in material_ids:
                continue
            uid = row.get("user_id")
            if uid not in by_user:
                by_user[uid] = []
            by_user[uid].append(row)

    # Build per-student aggregates (avg engagement, zcr, energy, reading_ratio)
    students = []
    for uid, rows in by_user.items():
        u = db.query(User).filter(User.id == uid).first()
        if not u:
            continue
        scores = [r.get("engagement_score") for r in rows if r.get("engagement_score") is not None]
        zcr_vals = [r.get("zcr") for r in rows if r.get("zcr") is not None]
        energy_vals = [r.get("energy") for r in rows if r.get("energy") is not None]
        rr_vals = [r.get("reading_ratio") for r in rows if r.get("reading_ratio") is not None]
        students.append({
            "user_id": uid,
            "full_name": u.full_name,
            "email": u.email,
            "sessions_count": len(rows),
            "avg_engagement": round(sum(scores) / len(scores), 1) if scores else None,
            "avg_zcr": round(sum(zcr_vals) / len(zcr_vals), 4) if zcr_vals else None,
            "avg_energy": round(sum(energy_vals) / len(energy_vals), 2) if energy_vals else None,
            "avg_reading_ratio": round(sum(rr_vals) / len(rr_vals), 4) if rr_vals else None,
        })
    return {"classroom_id": classroom_id, "students": students}


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


# --- Analytics ---

RESEARCH_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research_data")
ATTENTION_LOG_PATH = os.path.join(RESEARCH_DATA_DIR, "attention_log.csv")


def _append_attention_log(
    timestamp: int, student_id: str, yaw: float, pitch: float, roll: float, attention_state: int,
    assignment_id: Optional[int] = None,
    timestamp_iso: Optional[str] = None,
):
    """Append one row to attention_log.csv. Header written on first write.
    Uses timestamp_iso for alignment with engagement_metrics.jsonl (multimodal correlation)."""
    os.makedirs(RESEARCH_DATA_DIR, exist_ok=True)
    file_exists = os.path.isfile(ATTENTION_LOG_PATH)
    aid = "" if assignment_id is None else str(assignment_id)
    ts_iso = timestamp_iso or datetime.utcnow().isoformat() + "Z"

    # Check if existing file has new format (timestamp_iso column)
    use_new_format = True
    if file_exists:
        with open(ATTENTION_LOG_PATH, "r") as f:
            first_line = f.readline()
        use_new_format = "timestamp_iso" in first_line

    with open(ATTENTION_LOG_PATH, "a") as f:
        if not file_exists:
            f.write("timestamp,timestamp_iso,student_id,yaw,pitch,roll,attention_state,assignment_id\n")
        if use_new_format:
            f.write(f"{timestamp},{ts_iso},{student_id},{yaw},{pitch},{roll},{attention_state},{aid}\n")
        else:
            # Backward compat: old 7-column format
            f.write(f"{timestamp},{student_id},{yaw},{pitch},{roll},{attention_state},{aid}\n")


@app.post("/analyze-attention")
def analyze_attention(req: AnalyzeAttentionRequest):
    """
    Vision-based attention: head pose (yaw/pitch) from camera image.
    Fire-and-forget: logs to CSV for research. CPU-only (MediaPipe).
    Uses Moving Average smoothing when student_id is provided.
    """
    result = estimate_pose(req.image, student_id=req.student_id)
    yaw = result["yaw"]
    pitch = result["pitch"]
    roll = result["roll"]
    attention_state = 1 if result["attention_score"] == 100 else 0
    timestamp_iso = datetime.utcnow().isoformat() + "Z"
    _append_attention_log(
        req.timestamp, req.student_id, yaw, pitch, roll, attention_state, req.assignment_id,
        timestamp_iso=timestamp_iso,
    )
    return {"ok": True}


@app.post("/submit-analytics", dependencies=[Depends(get_current_user)])
def submit_analytics(req: SubmitAnalyticsRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Receive raw scroll signal from client, compute engagement score using DSP, save to LearningSession."""
    # Enhanced DSP-based engagement calculation (returns score and metrics)
    engagement_score, dsp_metrics = calculate_engagement(req.scroll_signal)
    
    session = LearningSession(
        user_id=user.id,
        material_id=req.material_id,
        scroll_signal=json.dumps(req.scroll_signal),
        engagement_score=engagement_score,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Log engagement metrics for research paper
    log_engagement_metrics(
        user_id=user.id,
        material_id=req.material_id,
        engagement_score=engagement_score,
        dsp_metrics=dsp_metrics,
        session_duration_s=len(req.scroll_signal)  # 1 sample per second
    )
    
    # Return score, DSP metrics, and session ID for research/debugging
    return {
        "engagement_score": engagement_score,
        "dsp_metrics": dsp_metrics,  # Includes FFT, ZCR, energy, etc.
        "session_id": session.id,
    }


@app.get("/teacher/dashboard-stats", dependencies=[Depends(get_current_user)])
def teacher_dashboard_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Aggregate engagement and quiz scores for teacher dashboard."""
    if user.role != "teacher":
        raise HTTPException(403, "Teachers only")
    classrooms = db.query(Classroom).filter(Classroom.teacher_id == user.id).all()
    classroom_ids = [c.id for c in classrooms]
    materials = db.query(Material).filter(Material.classroom_id.in_(classroom_ids)).all() if classroom_ids else []
    material_ids = [m.id for m in materials]
    sessions = db.query(LearningSession).filter(LearningSession.material_id.in_(material_ids)).all() if material_ids else []
    assignments = db.query(Assignment).filter(Assignment.classroom_id.in_(classroom_ids)).all() if classroom_ids else []
    submissions = db.query(QuizSubmission).filter(
        QuizSubmission.assignment_id.in_([a.id for a in assignments])
    ).all() if assignments else []
    avg_engagement = sum(s.engagement_score for s in sessions) / len(sessions) if sessions else 0.0
    avg_quiz_score = sum(s.score for s in submissions) / len(submissions) if submissions else 0.0
    return {
        "classrooms_count": len(classrooms),
        "materials_count": len(materials),
        "sessions_count": len(sessions),
        "submissions_count": len(submissions),
        "average_engagement_score": round(avg_engagement, 1),
        "average_quiz_score": round(avg_quiz_score, 1),
    }


# --- Research Metrics API ---

@app.get("/research/metrics-summary")
def get_research_metrics_summary():
    """
    Get aggregated performance metrics for research paper analysis.
    Returns inference times, engagement metrics, and system statistics.
    """
    return get_metrics_summary()


# --- Entry Point (convenience: `python main.py` binds to 0.0.0.0 for LAN access) ---

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
