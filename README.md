# EduSync - AI-Powered LMS

EduSync is a Learning Management System with an AI pipeline that generates quizzes, summaries, and flashcards from study materials. Teachers can upload materials, create assignments, and monitor student progress. Students can study with AI-generated summaries and flashcards, and take quizzes.

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
│   ├── database.py      # SQLite models
│   └── auth.py          # Auth utilities
└── EduSyncApp/       # Expo/React Native frontend
    ├── app/          # Screens (expo-router)
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

3. Start the server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend

1. Install dependencies:
   ```bash
   cd EduSyncApp
   npm install
   ```

2. Configure API URL in `EduSyncApp/lib/config.ts`:
   - For web: `localhost` works
   - For Android emulator: `10.0.2.2` (default)
   - For physical device: your computer's IP (e.g. `192.168.1.100`)

3. Start the app:
   ```bash
   npx expo start
   ```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/login` | POST | Login |
| `/register` | POST | Register (teacher/student) |
| `/extract-text` | POST | OCR from file |
| `/generate-quiz` | POST | AI quiz from text |
| `/generate-summary` | POST | AI summary from text |
| `/generate-flashcards` | POST | AI flashcards from text |
| `/classrooms` | GET/POST | List/create classrooms |
| `/classrooms/join` | POST | Join classroom by code |
| `/materials` | GET/POST | List/create materials |
| `/assignments` | GET/POST | List/create assignments |
| `/assignments/{id}/submit` | POST | Submit quiz |

## Auth

The app uses simple token-based auth. On login/register, the backend returns `user_id`. The frontend sends `X-User-Id` header with API requests. For production, replace with JWT.
