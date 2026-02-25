<p align="center">
  <img src="edusync.jpeg" alt="EduSync Logo" width="200" />
</p>

<h1 align="center">EduSync</h1>

<p align="center">
  <strong>AI-Powered Learning Management System with Edge Computing</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Expo-SDK_54-blue?logo=expo" alt="Expo SDK 54" />
  <img src="https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Llama_3-8B_Quantized-purple" alt="Llama 3" />
  <img src="https://img.shields.io/badge/Platform-iOS_%7C_Android-lightgrey?logo=react" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License" />
</p>

<p align="center">
  <em>A mobile-first LMS that runs AI inference entirely on local hardware — no cloud required.</em>
</p>

---

## About

EduSync is an edge-deployed Learning Management System built as a **BTech ECE Final Year Project (12 Credits)**. Teachers upload study materials and the system automatically generates quizzes, summaries, and flashcards using a locally running Llama-3 model. Students take quizzes with real-time camera-based attention monitoring, while scroll engagement is quantified through DSP signal processing.

### Why Edge AI?

All AI processing happens on your local machine — OCR, quiz generation, attention analysis — ensuring **data sovereignty** and **zero cloud dependency**. The entire pipeline runs on consumer hardware (NVIDIA RTX 3060, 6GB VRAM).

---

## Features

### For Teachers

| Feature | Description |
|---------|-------------|
| **Material Upload** | Upload PDFs, images, or PPTs — AI extracts text via OCR |
| **AI Content Generation** | Auto-generate summaries, flashcards, and quizzes from materials |
| **Classroom Management** | Create classrooms and share join codes with students |
| **Student Analytics** | Monitor quiz scores, engagement metrics, and attention data |

### For Students

| Feature | Description |
|---------|-------------|
| **Smart Study** | Access AI-generated summaries and flashcards for each material |
| **Quiz Assignments** | Take teacher-posted quizzes with instant scoring |
| **Attention Tracking** | Camera-based head pose estimation monitors focus during quizzes |
| **Progress Dashboard** | View scores and track learning progress |

### AI & Signal Processing Pipeline

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Text Extraction** | EasyOCR (CPU) | OCR from PDFs, images, and slides |
| **Content Generation** | Llama-3 8B, 4-bit quantized (GPU) | Quiz, summary, and flashcard generation |
| **Attention Monitoring** | MediaPipe Face Mesh + cv2.solvePnP (CPU) | Head pose estimation (yaw/pitch) during quizzes |
| **Engagement Scoring** | FIR filter, ZCR, FFT (CPU) | DSP-based scroll behavior analysis |

---

## Tech Stack

<table>
<tr>
<td align="center" width="50%">

**Frontend**

React Native (Expo SDK 54)
Expo Router
expo-camera
TypeScript

</td>
<td align="center" width="50%">

**Backend**

FastAPI
SQLite + SQLAlchemy
llama-cpp-python
MediaPipe + OpenCV
EasyOCR

</td>
</tr>
</table>

---

## Project Structure

```
EduSync/
├── backend/                    # FastAPI backend (edge node)
│   ├── main.py                 # REST API endpoints
│   ├── llm_service.py          # Llama-3 inference (quiz/summary/flashcards)
│   ├── parser_service.py       # OCR pipeline (EasyOCR + pypdf)
│   ├── vision_service.py       # Head pose attention (MediaPipe + solvePnP)
│   ├── signal_processor.py     # DSP scroll engagement (FIR, ZCR, FFT)
│   ├── database.py             # SQLite models & schema
│   ├── auth.py                 # JWT authentication
│   ├── metrics_logger.py       # Research metrics collection
│   ├── research_data/          # Collected metrics & figures
│   └── scripts/                # Analysis & visualization scripts
│
├── EduSyncApp/                 # Expo/React Native mobile app
│   ├── app/                    # Screens (expo-router file-based routing)
│   │   ├── index.tsx           # Login screen
│   │   ├── register.tsx        # Registration screen
│   │   ├── intro.tsx           # Onboarding video
│   │   ├── (tabs)/             # Main tab navigation
│   │   │   ├── explore.tsx     # Classrooms (create/join)
│   │   │   ├── index.tsx       # Materials & study
│   │   │   ├── assignments.tsx # Quiz assignments
│   │   │   └── progress.tsx    # Analytics dashboard
│   │   ├── classroom/[id].tsx  # Classroom detail
│   │   ├── material/[id].tsx   # Material viewer
│   │   └── assignment/[id].tsx # Quiz with attention tracking
│   ├── components/
│   │   ├── AttentionTracker.tsx # Camera-based attention monitoring
│   │   ├── PrivacyConsent.tsx   # Analytics consent modal
│   │   └── Skeleton.tsx        # Loading skeleton
│   ├── context/
│   │   ├── AuthContext.tsx     # Authentication state
│   │   └── IntroContext.tsx    # Onboarding state
│   └── lib/
│       ├── api.ts              # API client (axios)
│       └── config.ts           # Backend URL config
│
├── docs/                       # Documentation
│   ├── PROJECT_REPORT.md       # Full project report
│   ├── PROJECT_OVERVIEW.md     # Architecture overview
│   └── RESEARCH_PAPER_BRIEF.md # Conference paper brief
│
└── paper/                      # LaTeX paper & presentation
    ├── edusync_ieee_paper.tex
    └── edusync_presentation.tex
```

---

## Getting Started

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **NVIDIA GPU** with CUDA (for Llama-3 inference)
- **Expo Go** app on your phone ([iOS](https://apps.apple.com/app/expo-go/id982107779) / [Android](https://play.google.com/store/apps/details?id=host.exp.exponent))

### 1. Backend Setup

```bash
# Clone the repo
git clone https://github.com/Triplejw/EduSync.git
cd EduSync/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server (bind to all interfaces for mobile access)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd EduSyncApp

# Install dependencies
npm install

# Start Expo
npx expo start
```

### 3. Connect Your Phone

1. Open **Expo Go** on your phone
2. Scan the QR code from the terminal
3. Configure the backend URL in `EduSyncApp/lib/config.ts`:

```typescript
// Use your computer's local IP address
const API_URL = 'http://192.168.x.x:8000';
```

> **Tip:** Run `find_backend_ip.sh` to find your machine's IP address on the local network.

---

## API Reference

<details>
<summary><strong>Authentication</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/login` | Login with email/password, returns JWT |
| `POST` | `/register` | Register as teacher/student, returns JWT |

</details>

<details>
<summary><strong>AI Pipeline</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/extract-text` | OCR text extraction from uploaded file |
| `POST` | `/generate-quiz` | Generate quiz questions from text |
| `POST` | `/generate-summary` | Generate summary from text |
| `POST` | `/generate-flashcards` | Generate flashcards from text |

</details>

<details>
<summary><strong>Classrooms & Materials</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/classrooms` | List or create classrooms |
| `POST` | `/classrooms/join` | Join classroom by code |
| `GET/POST` | `/materials` | List or upload materials |
| `GET/POST` | `/assignments` | List or create assignments |
| `POST` | `/assignments/{id}/submit` | Submit quiz answers |

</details>

<details>
<summary><strong>Analytics & Research</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze-attention` | Submit camera frame for attention analysis |
| `POST` | `/submit-analytics` | Submit scroll engagement data |
| `GET` | `/teacher/dashboard-stats` | Aggregate student metrics |
| `GET` | `/research/metrics-summary` | Research metrics for report |

</details>

---

## Research Context

This project validates two research objectives for an ECE capstone and conference paper:

> **Objective 1 — Edge AI Performance:** Demonstrate measurable inference performance (latency, throughput) for OCR and LLM operations on consumer-grade hardware, with vision-based head-pose attention monitoring.

> **Objective 2 — Multimodal Engagement Correlation:** Demonstrate that scroll-based engagement (DSP) and vision-based attention correlate with quiz performance across users and sessions.

Research data, analysis scripts, and visualization tools are in `backend/research_data/` and `backend/scripts/`. See the [Project Report](docs/PROJECT_REPORT.md) and [Research Paper Brief](docs/RESEARCH_PAPER_BRIEF.md) for methodology and results.

---

## Architecture

```
┌─────────────────────┐         ┌─────────────────────────────────┐
│   Mobile App        │         │   Edge Node (Local Server)      │
│   (Expo/React       │  HTTP   │                                 │
│    Native)          │◄───────►│   FastAPI Backend                │
│                     │   JWT   │   ├── Llama-3 8B (GPU)          │
│  ┌───────────────┐  │         │   ├── EasyOCR (CPU)             │
│  │ Camera Feed   │──┼────────►│   ├── MediaPipe Face Mesh (CPU) │
│  │ (2s interval) │  │  Base64 │   ├── DSP Signal Processor      │
│  └───────────────┘  │         │   └── SQLite Database           │
│                     │         │                                 │
│  ┌───────────────┐  │         │   All AI runs locally —         │
│  │ Scroll Events │──┼────────►│   no cloud dependency           │
│  └───────────────┘  │         │                                 │
└─────────────────────┘         └─────────────────────────────────┘
```

---

## Authentication

EduSync uses **JWT (JSON Web Tokens)** for authentication. On login or registration, the backend returns an `access_token` and `user` object. The mobile app stores the token in AsyncStorage and sends `Authorization: Bearer <token>` on every request.

Set `EDUSYNC_JWT_SECRET` as an environment variable for production deployments.

---

<p align="center">
  Built with Edge AI for data-sovereign learning
  <br />
  <strong>BTech ECE Final Year Project</strong>
</p>
