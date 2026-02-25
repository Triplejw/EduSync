# EduSync - AI-Powered LMS

EduSync is a Learning Management System with an AI pipeline that generates quizzes, summaries, and flashcards from study materials. Teachers can upload materials, create assignments, and monitor student progress. Students can study with AI-generated summaries and flashcards, and take quizzes.

## ECE Final Year Project (12 Credits)

This project serves as a 12-credit BTech ECE final year project. **Technical highlights:**

- **Vision-based attention monitoring:** Head pose (yaw/pitch) via MediaPipe Face Mesh and cv2.solvePnP. Moving Average filter (last 10 frames) smooths angles before thresholding to reduce jitter. See `backend/vision_service.py`.
- **DSP-based scroll engagement:** FIR filter, energy, ZCR, FFT on scroll velocity (1 Hz). Scroll Engagement Score (0–100) for multimodal research. See `backend/signal_processor.py`.
- **Multimodal engagement tracking:** Vision data in `attention_log.csv` and scroll data in `engagement_metrics.jsonl` can be correlated by `student_id`/`user_id` and time for thesis analysis.
- **Project report:** Abstract, architecture, methodology, and results in [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md).

### Research & evaluation

Two main objectives for the capstone and conference paper:

1. **Objective 1 — Edge AI performance and vision-based attention:** Demonstrate measurable inference performance (latency, throughput) for OCR and LLM operations, and vision-based head-pose attention monitoring with summary statistics and time-series/distribution figures.
2. **Objective 2 — Multimodal engagement and correlation with quiz performance:** Demonstrate that scroll-based engagement (DSP) and vision-based attention correlate with quiz score across users/sessions, with scatter plots and Pearson correlation.

**Synthetic data:** For evaluation when multi-user testing is not feasible, run `backend/scripts/generate_synthetic_research_data.py` (seed 42), then `export_research_csv.py`, `analyze_attention.py`, and `visualize_research_data.py`. See [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) and [docs/RESEARCH_PAPER_BRIEF.md](docs/RESEARCH_PAPER_BRIEF.md) for data collection and paper context.

## Features

- **Teacher Dashboard**
  - Upload study materials (PDF, images) → AI extracts text (OCR) and generates summary, flashcards, and quiz
  - Create classrooms and share join codes
  - Post quizzes as assignments to students
  - Monitor student progress and scores

- **Student Dashboard**
  - View study materials from teachers
  - AI summary and flashcards for each material
  - Take quiz assignments and see scores
  - Real-time head pose attention tracking during quizzes (CPU-only vision, GPU reserved for Llama-3)

- **Core AI Pipeline** (preserved)
  - Llama-3 on GPU for quiz/summary/flashcard generation
  - EasyOCR on CPU for text extraction from PDFs and images

## Project Structure

```
EduSync/
├── backend/          # FastAPI backend
│   ├── main.py       # REST API
│   ├── llm_service.py    # Llama-3 (quiz, summary, flashcards)
│   ├── parser_service.py # OCR (EasyOCR, pypdf)
│   ├── vision_service.py # Head pose (MediaPipe + cv2.solvePnP)
│   ├── database.py      # SQLite models
│   └── auth.py          # Auth utilities
└── EduSyncApp/       # Expo/React Native frontend
    ├── app/          # Screens (expo-router)
    ├── components/   # AttentionTracker, etc.
    ├── lib/          # API client, config
    └── context/      # AuthContext
```

## Setup

### Backend

1. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Ensure models are downloaded (Llama-3 GGUF, EasyOCR):
   ```bash
   python download_models.py  # if needed
   ```

3. Start the server (bind to all interfaces so mobile devices can reach it):
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   Use `--host 0.0.0.0` so the edge node accepts connections from your phone (Ethernet/Wi-Fi).

### Frontend

1. Install dependencies:
   ```bash
   cd EduSyncApp
   npm install
   ```

2. Configure API URL in `EduSyncApp/lib/config.ts`:
   - For web: `localhost` works
   - For Android emulator: `10.0.2.2` (default)
   - For physical device on same network: your computer's IP (e.g. `10.222.250.96` when using Ethernet)

3. Start the app:
   ```bash
   npx expo start
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health (no auth) |
| `/health` | GET | Light health check (no auth) |
| `/login` | POST | Login (returns JWT) |
| `/register` | POST | Register teacher/student (returns JWT) |
| `/extract-text` | POST | OCR from file |
| `/generate-quiz` | POST | AI quiz from text |
| `/generate-summary` | POST | AI summary from text |
| `/generate-flashcards` | POST | AI flashcards from text |
| `/classrooms` | GET/POST | List/create classrooms |
| `/classrooms/join` | POST | Join classroom by code |
| `/materials` | GET/POST | List/create materials |
| `/assignments` | GET/POST | List/create assignments |
| `/assignments/{id}/submit` | POST | Submit quiz |
| `/analyze-attention` | POST | Submit base64 image for head pose attention (fire-and-forget) |
| `/submit-analytics` | POST | Submit scroll signal, get engagement score (legacy) |
| `/teacher/dashboard-stats` | GET | Aggregate engagement and quiz stats (teacher) |
| `/research/metrics-summary` | GET | Aggregated inference and engagement metrics (for report) |

## Auth

The app uses **JWT (JSON Web Tokens)**. On login/register, the backend returns `access_token` and `user`. The mobile client stores the token and sends `Authorization: Bearer <access_token>` on every request. Set `EDUSYNC_JWT_SECRET` in the environment for production.
