# EduSync: Project Overview and Architecture

**Purpose:** This document explains EduSync in detail—file roles, connections, data flows, and how the system works. Use it to onboard teammates, share with collaborators, or provide context to AI coding assistants.

---

## 1. What EduSync Is

EduSync is an **AI-powered Learning Management System (LMS)** designed for an **edge deployment** (local server or laptop, no cloud). Key characteristics:

- **Teacher role:** Upload materials (PDF, images, PPT), create classrooms, share join codes, post quiz assignments, monitor progress
- **Student role:** Join classrooms, view materials, use AI summaries/flashcards, take quizzes
- **AI pipeline:** Llama-3 (GPU) for quiz/summary/flashcard generation; EasyOCR (CPU) for OCR
- **Attention monitoring:** Vision-based head pose estimation (MediaPipe + OpenCV) during quizzes—runs on CPU to leave GPU free for Llama
- **Research focus:** BTech ECE project; metrics logged for conference paper

---

## 2. Research objectives and data

Two main objectives for the ECE capstone and conference paper:

1. **Objective 1 — Edge AI performance and vision-based attention:** Demonstrate measurable inference performance (OCR, LLM) and vision-based head-pose attention monitoring with summary statistics and time-series/distribution figures.
2. **Objective 2 — Multimodal engagement and correlation with quiz performance:** Demonstrate that scroll engagement (DSP) and vision-based attention (focused ratio) correlate with quiz score across users/sessions (scatter plots, Pearson r).

For evaluation when multi-user testing is not feasible, synthetic multi-user data can be generated: run `backend/scripts/generate_synthetic_research_data.py` (seed 42), then `export_research_csv.py`, `analyze_attention.py`, and `visualize_research_data.py`. See [PROJECT_REPORT.md](PROJECT_REPORT.md) and [RESEARCH_PAPER_BRIEF.md](RESEARCH_PAPER_BRIEF.md).

---

## 3. Project Structure

```
EduSync/
├── backend/                    # FastAPI Python backend
│   ├── main.py                 # REST API, routes, wires all services
│   ├── database.py             # SQLAlchemy models, SQLite
│   ├── auth.py                 # Password hashing, JWT validation
│   ├── jwt_utils.py            # JWT create/decode
│   ├── llm_service.py          # Llama-3 (GPU) - quiz, summary, flashcards
│   ├── parser_service.py       # OCR (EasyOCR, pypdf) - text extraction
│   ├── vision_service.py       # MediaPipe + cv2.solvePnP - head pose
│   ├── signal_processor.py     # DSP - scroll engagement (FIR, ZCR, FFT)
│   ├── metrics_logger.py       # Inference/engagement/system metrics
│   ├── requirements.txt        # Python dependencies
│   ├── uploads/                # Stored uploaded files
│   ├── models/                 # Llama GGUF model files
│   ├── research_data/          # JSONL, CSV, figures for research
│   └── scripts/                # Export, analyze, visualize
│       ├── export_research_csv.py
│       ├── analyze_attention.py
│       └── visualize_research_data.py
├── EduSyncApp/                 # Expo / React Native app
│   ├── app/                    # Expo Router screens
│   │   ├── _layout.tsx         # Root layout, auth, intro
│   │   ├── index.tsx           # Entry (redirect)
│   │   ├── intro.tsx           # Onboarding intro
│   │   ├── register.tsx        # Registration
│   │   ├── (tabs)/             # Tab navigation
│   │   │   ├── _layout.tsx     # Tab bar (Classrooms, Materials, Assignments, Progress)
│   │   │   ├── explore.tsx     # Classrooms screen
│   │   │   ├── index.tsx       # Materials (teachers) / Study (students)
│   │   │   ├── assignments.tsx # Assignments list
│   │   │   └── progress.tsx    # Dashboard (teachers) / My Scores (students)
│   │   ├── classroom/[id].tsx  # Classroom detail
│   │   ├── material/[id].tsx   # Material detail (doc, summary, flashcards)
│   │   └── assignment/[id].tsx # Quiz screen (AttentionTracker here)
│   ├── components/
│   │   ├── AttentionTracker.tsx # Camera, 2s capture, POST /analyze-attention
│   │   └── ...
│   ├── context/
│   │   ├── AuthContext.tsx     # Login state, JWT, api.setAuthHeader
│   │   └── IntroContext.tsx    # Intro overlay control
│   ├── hooks/
│   │   └── useScrollTracker.ts # Scroll analytics (1 Hz) for multimodal engagement
│   ├── lib/
│   │   ├── api.ts              # Axios client, all API calls
│   │   ├── config.ts           # API_URL (BACKEND_IP)
│   │   └── authErrors.ts       # Auth error messages
│   └── app.json                # Expo config, camera permissions
├── docs/
│   ├── PROJECT_OVERVIEW.md     # This file
│   └── PROJECT_REPORT.md       # Paper template
├── venv/                       # Python virtual environment
└── README.md
```

---

## 4. Backend: File-by-File

### 3.1 `main.py`
- FastAPI app, CORS, startup (creates test accounts)
- **Routes:** auth, classrooms, materials, assignments, quiz submit, analyze-attention, submit-analytics, teacher dashboard, research metrics
- **Imports:** llm_service, parser_service, vision_service, signal_processor, database, auth, jwt_utils, metrics_logger
- **Pydantic schemas:** RegisterRequest, LoginRequest, AnalyzeAttentionRequest, etc.
- **Key endpoints:**
  - `POST /upload-material` → save file, OCR, create Material (no AI yet)
  - `POST /materials/{id}/generate-summary` → Llama summary, cache in DB
  - `POST /materials/{id}/generate-flashcards` → Llama flashcards
  - `POST /materials/{id}/generate-quiz` → Llama quiz
  - `POST /analyze-attention` → vision_service.estimate_pose(), append to attention_log.csv
  - `POST /submit-analytics` → signal_processor.calculate_engagement(), save LearningSession

### 3.2 `database.py`
- SQLite `edusync.db`
- **Tables:** User, Classroom, ClassroomEnrollment, Material, Assignment, QuizSubmission, LearningSession
- **Relations:** teacher→classrooms, classroom→materials, assignment→quiz_json, material→assignments, user→quiz_submissions

### 3.3 `auth.py`
- `get_password_hash`, `verify_password` (bcrypt)
- `get_current_user(Authorization: Bearer <token>)` → validates JWT, returns User from DB

### 3.4 `jwt_utils.py`
- `create_access_token(user_id, email, role)` → JWT
- `decode_access_token(token)` → payload or None
- Secret from `EDUSYNC_JWT_SECRET` env

### 3.5 `llm_service.py`
- Loads Llama-3 GGUF from `models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf`
- GPU: `n_gpu_layers=-1`
- `generate_quiz(text)` → 5 MCQ JSON
- `generate_summary(text)` → summary string
- `generate_flashcards(text)` → JSON array

### 3.6 `parser_service.py`
- EasyOCR (CPU), pypdf, pdf2image
- `extract_text_from_document(bytes, ext)` → raw text
- PDF: native extraction first; if scanned, OCR first 5 pages

### 3.7 `vision_service.py`
- MediaPipe Face Mesh (CPU, `min_detection_confidence=0.5`)
- 2D landmarks → 3D model → cv2.solvePnP → Euler angles (yaw, pitch, roll)
- **HeadPoseSmoother:** Moving Average filter over last N frames (default 10) per student to reduce jitter
- Thresholds applied to *averaged* yaw/pitch: `|yaw_avg| > 20°` or `|pitch_avg| > 15°` → distracted (0); else focused (100)
- Input: base64 image string or bytes; optional `student_id` enables smoothing
- Output: `{yaw, pitch, roll, attention_score}` (yaw/pitch are smoothed when student_id provided)

### 3.8 `signal_processor.py`
- DSP on scroll delta (px/s at 1 Hz): FIR low-pass filter, energy, ZCR, FFT
- Returns **Scroll Engagement Score** (0–100) and `metrics_dict` for LearningSession / engagement_metrics
- `scroll_engagement_score` field enables multimodal correlation with vision data

### 3.9 `metrics_logger.py`
- Logs to `research_data/*.jsonl`: inference_metrics, engagement_metrics, system_metrics
- `Timer` context manager for timing
- `get_metrics_summary()` → aggregated stats for `GET /research/metrics-summary`

### 3.10 Scripts
- **export_research_csv.py:** JSONL → inference_metrics.csv, engagement_metrics.csv, paired_engagement_quiz.csv, latency_percentiles.csv
- **analyze_attention.py:** attention_log.csv → attention_summary.csv, attention_vs_quiz.csv; prints overall stats
- **visualize_research_data.py:** CSVs → figures (engagement vs quiz, attention timeseries, attention distribution, attention vs quiz scatter)

---

## 5. Frontend: File-by-File

### 4.1 Routing and Layout
- **app/_layout.tsx:** AuthProvider, IntroProvider, Stack (index, register, tabs, classroom/[id], material/[id], assignment/[id])
- **app/(tabs)/_layout.tsx:** Tabs: Classrooms, Materials/Study, Assignments, Progress. Guards: loading or !user → spinner

### 4.2 Context
- **AuthContext:** user, loading, login, register, logout; persists JWT in localStorage; sets `api.setAuthHeader(token)`
- **IntroContext:** showIntro, hideIntro, triggerIntro; controls intro overlay

### 4.3 API Client (`lib/api.ts`)
- Axios instance with `baseURL: API_URL`
- `setAuthHeader`, `clearAuthHeader`, `getAuthToken`
- Methods: login, register, listClassrooms, createClassroom, joinClassroom, uploadMaterial, listMaterials, getMaterial, generateMaterialSummary/Flashcards/Quiz, listAssignments, getAssignment, submitQuiz, submitAttention, submitAnalytics, getTeacherDashboardStats, etc.

### 4.4 Config (`lib/config.ts`)
- `BACKEND_IP`, `BACKEND_PORT`
- `API_URL` from `EXPO_PUBLIC_API_URL` or `http://${BACKEND_IP}:${PORT}` (web: localhost)

### 4.5 Screens
- **explore.tsx (Classrooms):** List classrooms; teachers create, students join by code
- **index.tsx (Materials/Study):** List materials, group by classroom; teachers upload (DocumentPicker → uploadMaterial)
- **assignments.tsx:** List assignments, filter by classroom; tap → assignment/[id]
- **progress.tsx:** Teachers: dashboard stats; students: my scores
- **material/[id].tsx:** Tabs: document (PDF WebView), summary, flashcards; useScrollTracker for multimodal scroll analytics (submits on leave)
- **assignment/[id].tsx:** Quiz UI for students; teacher view: submissions. Mounts `AttentionTracker` for students with `assignmentId`

### 4.6 AttentionTracker
- Props: `studentId`, `assignmentId` (optional)
- Uses `expo-camera` CameraView (front-facing, hidden 64×64)
- Every 2s: `takePictureAsync({ quality: 0.3, base64: true })` → `submitAttention(base64, studentId, timestamp, assignmentId)` (fire-and-forget)
- POST /analyze-attention with `{ image, student_id, timestamp, assignment_id? }`

---

## 6. Data Flows

### 5.1 Material Pipeline
1. Teacher selects file → `uploadMaterial()` → POST /upload-material
2. Backend saves to `uploads/`, runs OCR (parser_service), creates Material with raw_text
3. User opens material → on-demand: generate-summary / generate-flashcards / generate-quiz → Llama (GPU)
4. Result cached in Material; metrics logged to inference_metrics.jsonl

### 5.2 Attention Pipeline (Quiz)
1. Student opens quiz → `assignment/[id].tsx` mounts AttentionTracker(studentId, assignmentId)
2. Camera captures every 2s → base64 → POST /analyze-attention
3. vision_service.estimate_pose(image, student_id) → Moving Average smoothing → yaw, pitch, roll, attention_score
4. Row appended to attention_log.csv: timestamp, timestamp_iso, student_id, yaw, pitch, roll, attention_state (0/1), assignment_id

### 5.3 Quiz Submission
1. Student submits → POST /assignments/{id}/submit
2. Backend scores, creates QuizSubmission
3. attention_log rows with assignment_id can be joined to quiz scores for research (attention vs quiz correlation)

### 5.4 Scroll Analytics (Multimodal Engagement)
1. Material screen (`material/[id].tsx`) uses useScrollTracker; scroll sampled at 1 Hz (native ScrollView or PDF WebView via postMessage)
2. On screen leave (useFocusEffect cleanup), submitAnalytics(materialId, scrollSignal) sends scroll deltas
3. POST /submit-analytics → signal_processor.calculate_engagement() → LearningSession + engagement_metrics.jsonl

---

## 7. Database Schema

| Table | Key Columns |
|-------|-------------|
| users | id, email, hashed_password, role, full_name |
| classrooms | id, code, name, subject_name, teacher_id |
| classroom_enrollments | classroom_id, user_id |
| materials | id, title, file_path, raw_text, summary, flashcards_json, quiz_json, classroom_id |
| assignments | id, title, quiz_json, classroom_id, material_id |
| quiz_submissions | id, assignment_id, user_id, score, answers_json |
| sessions | id, user_id, material_id, scroll_signal, engagement_score |

---

## 8. Research Data Files

| File | Content |
|------|---------|
| attention_log.csv | Vision: timestamp, timestamp_iso, student_id, yaw, pitch, roll, attention_state, assignment_id |
| attention_summary.csv | Per-student/assignment: mean yaw/pitch/roll, focused_ratio |
| attention_vs_quiz.csv | Paired focused_ratio, quiz_score for correlation |
| inference_metrics.jsonl | Per-call: operation, duration_ms, input/output size |
| engagement_metrics.jsonl | Scroll: timestamp (ISO), user_id, material_id, engagement_score, scroll_engagement_score, DSP metrics |
| research_data/figures/ | PNG plots for paper |

**Multimodal correlation:** Join `attention_log.csv` and `engagement_metrics.jsonl` by `student_id` (vision) = `user_id` (scroll) for side-by-side analysis. Both include timestamps (ISO) for temporal alignment.

---

## 9. API Endpoints Summary

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /, /health | No | Health check |
| POST | /register, /login | No | Auth |
| GET/POST | /classrooms | Yes | CRUD, join |
| GET | /classrooms/{id} | Yes | Classroom detail |
| GET/POST | /materials | Yes | List, create |
| GET | /materials/{id} | Yes | Material detail |
| GET | /materials/{id}/file | Yes | Download file |
| POST | /upload-material | Yes | Upload + OCR |
| POST | /materials/{id}/generate-summary | Yes | Llama summary |
| POST | /materials/{id}/generate-flashcards | Yes | Llama flashcards |
| POST | /materials/{id}/generate-quiz | Yes | Llama quiz |
| GET/POST | /assignments | Yes | List, create |
| GET | /assignments/{id} | Yes | Assignment detail |
| POST | /assignments/{id}/submit | Yes | Submit quiz |
| POST | /analyze-attention | No | Vision head pose (fire-and-forget) |
| POST | /submit-analytics | Yes | Scroll engagement (DSP → engagement_metrics.jsonl) |
| GET | /teacher/dashboard-stats | Yes | Teacher aggregate stats |
| GET | /research/metrics-summary | No | Aggregated research metrics |

---

## 10. Setup and Run

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd EduSyncApp
npm install
# Set API_URL / BACKEND_IP in lib/config.ts for your LAN
npx expo start
```

**Research scripts:**
```bash
cd backend
python scripts/analyze_attention.py
python scripts/visualize_research_data.py
```

---

## 11. Dependencies (Key)

**Backend:** FastAPI, uvicorn, SQLAlchemy, python-jose, passlib, easyocr, llama-cpp-python, mediapipe==0.10.9, opencv-python, numpy, scipy, pandas, matplotlib

**Frontend:** Expo, expo-router, expo-camera, axios, react-native-webview

---

## 12. Notes for AI Assistants

- Vision uses MediaPipe 0.10.9 (legacy solutions API); newer versions require migration to MediaPipe Tasks.
- Password verification is currently bypassed (DEBUG) in auth.py.
- BACKEND_IP in config.ts must match the machine running the backend for physical devices.
- assignment_id in attention_log enables attention–quiz correlation; older logs may not have it.
- Both attention_log (vision) and engagement_metrics.jsonl (scroll) support multimodal engagement research.
