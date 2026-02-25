# EduSync: Edge AI Architecture Validation and DSP-Based Engagement Analysis

## Technical Documentation for ECE Panel Review

**Version:** 2.0  
**Project Type:** BTech ECE Final Year Project (12 Credits)  
**Research Focus:** Validating an Edge AI Architecture for Data-Sovereign Inference and DSP-Based Student Engagement Quantification

---

## Table of Contents

1. [Executive Summary and Research Objectives](#1-executive-summary-and-research-objectives)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [AI Pipeline](#4-ai-pipeline)
5. [DSP-Based Engagement Detection](#5-dsp-based-engagement-detection)
6. [Database Schema](#6-database-schema)
7. [API Specification](#7-api-specification)
8. [Research Metrics Collection](#8-research-metrics-collection)
9. [Research Methodology and Publication Potential](#9-research-methodology-and-publication-potential)
10. [Experimental Validation](#10-experimental-validation)
11. [Performance Characteristics](#11-performance-characteristics)
12. [Dependencies and Requirements](#12-dependencies-and-requirements)

---

## 1. Executive Summary and Research Objectives

### 1.1 Project Overview

EduSync is an engineering research platform designed to validate two core hypotheses at the intersection of Edge Computing and Digital Signal Processing. Rather than a conventional application, EduSync serves as a **controlled testbed** in which a locally deployed Large Language Model (Llama-3-8B, 4-bit quantized) performs inference entirely on consumer-grade hardware (NVIDIA RTX 3060, 6GB VRAM), while a DSP pipeline quantifies student engagement from scroll-behavior signals in real time.

The platform provides:

- **A data-sovereign inference environment** where all AI processing occurs on-premise with zero reliance on cloud APIs, enabling rigorous data locality validation via network traffic analysis.
- **A signal acquisition and processing pipeline** that treats mobile scroll telemetry as a discrete-time signal, applying FIR filtering, energy analysis, and Zero-Crossing Rate (ZCR) to produce a quantitative engagement score.
- **A research data collection framework** logging inference latency, engagement metrics, and system telemetry to JSONL files for offline statistical analysis.

### 1.2 Research Objectives

**Objective 1 — Architecture and Data Sovereignty:**
> To implement and evaluate an offline, latency-optimized Edge AI architecture that ensures Data Sovereignty through local inference.

This objective is validated by demonstrating that during a complete inference cycle (OCR + LLM generation), **zero packets egress** to any non-LAN destination. Validation is performed using Wireshark/tshark packet capture on the edge node's active network interface.

**Objective 2 — Signal Processing:**
> To design and validate a DSP-based algorithm for quantifying student engagement using real-time scroll signal analysis (Energy and Zero-Crossing Rate).

This objective is validated by correlating DSP-computed engagement scores with independent quiz performance data (Pearson correlation coefficient) across a multi-user data collection study.

### 1.3 Research Significance

This project bridges Electronics & Communication Engineering (ECE) fundamentals with modern AI deployment by:

1. **Proving edge viability:** Demonstrating that a quantized 8B-parameter LLM can serve educational content generation on a single consumer GPU with acceptable latency, eliminating cloud dependency.
2. **Formalizing scroll-based engagement detection:** Applying classical DSP techniques (FIR filtering, spectral analysis, ZCR) to a novel signal domain — mobile scroll telemetry — and validating the resulting metric against ground-truth academic performance.
3. **Establishing a data-locality-by-architecture model:** Providing empirical evidence (packet-level) that on-device inference achieves data sovereignty without requiring encryption, anonymization, or trust in third-party processors.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EduSync Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐         ┌─────────────────────────────────────────┐   │
│  │                 │         │           EDGE NODE (Backend)            │   │
│  │   Mobile App    │  HTTP   │  ┌─────────────────────────────────────┐ │   │
│  │  (React Native) │◄───────►│  │         FastAPI Server              │ │   │
│  │                 │  REST   │  │         (main.py)                   │ │   │
│  │  - Teacher UI   │   +     │  └─────────────┬───────────────────────┘ │   │
│  │  - Student UI   │  JWT    │                │                         │   │
│  │  - Analytics    │         │    ┌───────────┴───────────┐             │   │
│  │                 │         │    │                       │             │   │
│  └─────────────────┘         │    ▼                       ▼             │   │
│                              │  ┌───────────┐     ┌─────────────────┐   │   │
│                              │  │  SQLite   │     │   AI Pipeline   │   │   │
│                              │  │  Database │     │                 │   │   │
│                              │  └───────────┘     │  ┌───────────┐  │   │   │
│                              │                    │  │  EasyOCR  │  │   │   │
│                              │                    │  │   (CPU)   │  │   │   │
│                              │                    │  └───────────┘  │   │   │
│                              │                    │        │        │   │   │
│                              │                    │        ▼        │   │   │
│                              │                    │  ┌───────────┐  │   │   │
│                              │                    │  │ Llama-3   │  │   │   │
│                              │                    │  │   (GPU)   │  │   │   │
│                              │                    │  └───────────┘  │   │   │
│                              │                    └─────────────────┘   │   │
│                              └─────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Overview

| Component | Technology | Role |
|-----------|------------|------|
| Mobile App | React Native / Expo | User interface for teachers and students |
| API Server | FastAPI (Python) | REST API, authentication, business logic |
| Database | SQLite + SQLAlchemy | Persistent storage for users, materials, assignments |
| OCR Engine | EasyOCR | Text extraction from images and PDFs (CPU) |
| LLM Engine | Llama-3-8B-Instruct | Content generation: summaries, flashcards, quizzes (GPU) |
| DSP Module | NumPy/SciPy | Engagement score calculation from scroll signals |

### 2.3 Hardware Requirements

**Minimum Edge Node Specifications:**

| Component | Specification | Purpose |
|-----------|---------------|---------|
| GPU | NVIDIA RTX 3060 (6GB VRAM) | LLM inference with full model offload |
| CPU | AMD Ryzen 7 5800H (8 cores) | OCR processing, API serving, DSP calculations |
| RAM | 16GB DDR4 | Model loading, concurrent request handling |
| Storage | SSD (recommended) | Fast model loading, database I/O |

### 2.4 Edge vs Cloud Rationale

| Aspect | Edge Deployment (EduSync) | Cloud Deployment |
|--------|---------------------------|------------------|
| Latency | Low (local inference) | Variable (network-dependent) |
| Data Locality | Data stays on-premise | Data transmitted to third-party |
| Cost | One-time hardware cost | Recurring API costs |
| Offline | Works without internet | Requires connectivity |
| Scalability | Limited by hardware | Elastic scaling |

EduSync prioritizes **data locality**, **low latency**, and **cost-effectiveness** for educational institutions that may have limited budgets or data sovereignty requirements.

---

## 3. Technology Stack

### 3.1 Backend Technologies

```
backend/
├── main.py              # FastAPI application (30+ endpoints)
├── database.py          # SQLAlchemy ORM models (7 tables)
├── llm_service.py       # Llama-3 integration (llama-cpp-python)
├── parser_service.py    # OCR pipeline (EasyOCR, PyPDF, pdf2image)
├── signal_processor.py  # DSP engagement detection (NumPy/SciPy)
├── metrics_logger.py    # Research data collection (JSONL)
├── auth.py              # Password hashing (bcrypt)
├── jwt_utils.py         # JWT token management (python-jose)
└── models/
    └── Meta-Llama-3-8B-Instruct-Q4_K_M.gguf  # Quantized LLM (4.7GB)
```

**Key Libraries:**

| Library | Version | Purpose |
|---------|---------|---------|
| FastAPI | 0.100+ | Async REST API framework |
| SQLAlchemy | 2.0+ | ORM for database operations |
| llama-cpp-python | 0.2+ | Python bindings for llama.cpp |
| EasyOCR | 1.7+ | Deep learning OCR |
| NumPy | 1.24+ | Numerical computing for DSP |
| SciPy | 1.11+ | Signal processing functions |
| python-jose | 3.3+ | JWT encoding/decoding |
| passlib | 1.7+ | Password hashing (bcrypt) |

### 3.2 Frontend Technologies

```
EduSyncApp/
├── app/                 # Expo Router screens
│   ├── _layout.tsx      # Root layout with providers
│   ├── index.tsx        # Login screen
│   ├── register.tsx     # Registration screen
│   ├── intro.tsx        # Animated intro screen
│   ├── (tabs)/          # Main tab navigation
│   │   ├── explore.tsx  # Classrooms list
│   │   ├── index.tsx    # Materials list
│   │   ├── assignments.tsx
│   │   └── progress.tsx # Dashboard with charts
│   ├── classroom/[id].tsx   # Classroom detail
│   ├── material/[id].tsx    # Material viewer + AI tools
│   └── assignment/[id].tsx  # Quiz interface
├── context/
│   ├── AuthContext.tsx  # Authentication state
│   └── IntroContext.tsx # Intro screen control
├── lib/
│   ├── api.ts           # Axios API client (25+ functions)
│   └── config.ts        # Platform-aware API URL
└── hooks/
    └── useScrollTracker.ts  # Engagement signal collection
```

**Key Libraries:**

| Library | Purpose |
|---------|---------|
| Expo SDK 53 | React Native development platform |
| Expo Router | File-based navigation |
| Axios | HTTP client with interceptors |
| expo-file-system | Local file caching |
| expo-sharing | Native file sharing |
| expo-image | Optimized image display |

### 3.3 Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Data Flow Pipeline                              │
└──────────────────────────────────────────────────────────────────────────┘

[Teacher Upload]
      │
      ▼
┌─────────────────┐
│  Document File  │ (PDF / Image / PPT)
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   File Storage  │────►│  OCR Pipeline   │
│  (uploads/)     │     │  (EasyOCR/PDF)  │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Raw Text      │
                        │  (stored in DB) │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
     │  Summary    │    │ Flashcards  │    │    Quiz     │
     │ Generation  │    │ Generation  │    │ Generation  │
     │ (On-Demand) │    │ (On-Demand) │    │ (On-Demand) │
     └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │  Student View   │
                      │  + Analytics    │
                      └─────────────────┘
```

---

## 4. AI Pipeline

### 4.1 Document Ingestion

The system accepts three document formats:

| Format | Processing Method | Notes |
|--------|-------------------|-------|
| PDF | Native PyPDF → OCR fallback | Fast path for text PDFs, OCR for scanned |
| Images | Direct EasyOCR | PNG, JPG, JPEG, GIF, WebP |
| PPT/PPTX | LibreOffice → PDF → OCR | Requires LibreOffice installation |

**Processing Flow:**

```python
def extract_text_from_document(file_bytes, file_ext):
    if file_ext in [".ppt", ".pptx"]:
        return extract_text_from_ppt(file_bytes, file_ext)
    return extract_text_from_image(file_bytes)

def extract_text_from_image(file_bytes):
    # 1. Check if PDF
    if file_bytes[:4] == b'%PDF':
        # Fast path: native text extraction (up to 10 pages)
        text = extract_text_from_pdf_native(file_bytes)
        if text and len(text) > 500:
            return text
        # Slow path: OCR (up to 5 pages)
        return ocr_pdf_pages(file_bytes)
    
    # 2. Direct image OCR
    return easyocr_reader.readtext(image, detail=0)
```

### 4.2 OCR Configuration

**EasyOCR Setup:**

```python
import easyocr

# Initialize reader (CPU mode for memory efficiency)
reader = easyocr.Reader(['en'], gpu=False)

# Processing limits
MAX_PDF_PAGES_NATIVE = 10  # PyPDF text extraction
MAX_PDF_PAGES_OCR = 5      # Image-based OCR (slower)
```

**Why CPU for OCR:**
- OCR is I/O bound (image decoding)
- GPU VRAM reserved for LLM
- Acceptable performance for document processing

### 4.3 LLM Configuration

**Model Specification:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Model | Meta-Llama-3-8B-Instruct | Best open-source instruction-following |
| Quantization | Q4_K_M (4-bit) | Fits in 6GB VRAM with good quality |
| Context Window | 4096 tokens | Sufficient for educational content |
| GPU Layers | -1 (all) | Full GPU offload for speed |
| CPU Threads | 8 | Matches Ryzen 7 core count |
| Batch Size | 512 | Optimal for prompt processing |
| Memory Lock | True | Prevents swapping |

**Initialization Code:**

```python
from llama_cpp import Llama

llm = Llama(
    model_path="models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
    n_gpu_layers=-1,      # All layers on GPU
    n_ctx=4096,           # Context window
    n_threads=8,          # CPU threads for non-GPU ops
    n_batch=512,          # Batch size for prompt processing
    use_mlock=True,       # Lock model in RAM
    verbose=False
)
```

### 4.4 Content Generation Functions

#### 4.4.1 Summary Generation

**Purpose:** Generate 3-5 paragraph educational summaries

**Prompt Template:**

```
<|start_header_id|>system<|end_header_id|>

You are an educational assistant. Summarize the following study material in 3-5 clear paragraphs. 
Focus on key concepts, main ideas, and important details. Use simple, clear language.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{content_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
```

**Parameters:**
- `max_tokens`: 512
- `temperature`: 0.5 (moderate creativity)
- `stop`: `["<|eot_id|>"]`

#### 4.4.2 Flashcard Generation

**Purpose:** Generate 5 question-answer pairs for spaced repetition

**Output Format:**

```json
[
  {"front": "What is photosynthesis?", "back": "The process by which plants convert sunlight into energy"},
  {"front": "What is the formula for photosynthesis?", "back": "6CO2 + 6H2O + light → C6H12O6 + 6O2"}
]
```

**Parameters:**
- `max_tokens`: 512
- `temperature`: 0.4 (deterministic JSON)
- `stop`: `["<|eot_id|>"]`

#### 4.4.3 Quiz Generation

**Purpose:** Generate 3 multiple-choice questions for assessment

**Output Format:**

```json
[
  {
    "question": "What is the primary function of mitochondria?",
    "options": ["Protein synthesis", "Energy production", "Cell division", "Waste removal"],
    "correct_answer": 1
  }
]
```

**Parameters:**
- `max_tokens`: 512
- `temperature`: 0.4 (deterministic JSON)
- `stop`: `["<|eot_id|>"]`

### 4.5 Text Truncation Strategy

To ensure reliable generation within the context window:

```python
MAX_INPUT_CHARS = 8000  # ~2000 tokens

if len(content_text) > MAX_INPUT_CHARS:
    content_text = content_text[:MAX_INPUT_CHARS] + "... [Text Truncated]"
```

**Rationale:**
- 8000 characters ≈ 2000 tokens
- Leaves ~2000 tokens for system prompt + generation
- Prioritizes beginning of document (usually contains key concepts)

---

## 5. DSP-Based Engagement Detection

### 5.1 Overview

The engagement detection module applies classical Digital Signal Processing techniques to analyze student scroll behavior, computing an engagement score that reflects attention and reading patterns.

**Research Title:** *"Edge AI-Powered Learning Analytics: A DSP Approach for Student Engagement Detection"*

### 5.2 Signal Acquisition

**Data Collection:**

```typescript
// Frontend: useScrollTracker.ts
const SAMPLE_INTERVAL = 1000; // 1 second (1 Hz sampling)

const handleScroll = (event) => {
  const currentPosition = event.nativeEvent.contentOffset.y;
  const delta = Math.abs(currentPosition - lastPosition);
  const pixelsPerSecond = delta; // Since interval is 1 second
  
  scrollSignal.push(pixelsPerSecond);
  lastPosition = currentPosition;
};
```

**Signal Properties:**
- Sampling Rate: 1 Hz (one sample per second)
- Unit: pixels per second (px/s)
- Typical session: 30-300 samples (30s to 5min reading)

### 5.3 DSP Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DSP Engagement Detection Pipeline                     │
└─────────────────────────────────────────────────────────────────────────┘

  Input: scroll_signal[] (px/s at 1 Hz)
                │
                ▼
  ┌─────────────────────────────────┐
  │  1. Time Domain Statistics      │
  │     - Mean, Std, Max, Min       │
  └─────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────┐
  │  2. Signal Energy               │
  │     E = Σ|x[n]|² / N            │
  └─────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────┐
  │  3. FIR Low-Pass Filter         │
  │     5-tap Moving Average        │
  │     h[n] = [1/5, 1/5, ..., 1/5] │
  └─────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────┐
  │  4. Zero-Crossing Rate (ZCR)    │
  │     ZCR = crossings / (N-1)     │
  └─────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────┐
  │  5. FFT Spectral Analysis       │
  │     - Dominant Frequency        │
  │     - Spectral Centroid         │
  └─────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────┐
  │  6. Behavior Classification     │
  │     - Reading (2-100 px/s)      │
  │     - Idle (≤ 2 px/s)           │
  │     - Skimming (> 100 px/s)     │
  └─────────────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────┐
  │  7. Engagement Score            │
  │     Score = 0.6*reading_ratio   │
  │            + 0.25*energy_norm   │
  │            + 0.15*zcr_factor    │
  └─────────────────────────────────┘
                │
                ▼
  Output: engagement_score (0-100)
          + DSP metrics dictionary
```

### 5.4 Mathematical Formulations

#### 5.4.1 Discrete Time Signal Representation

```
x[n] = scroll_delta at time n, where n ∈ {0, 1, 2, ..., N-1}
fs = 1 Hz (sampling frequency)
```

#### 5.4.2 Signal Energy (Parseval's Theorem)

```
Energy = (1/N) × Σ|x[n]|²  for n = 0 to N-1

Power = Energy (for normalized signals)
```

**Interpretation:** Higher energy indicates more scroll activity.

#### 5.4.3 FIR Low-Pass Filter

A 5-tap moving average filter removes high-frequency noise:

```
h[n] = [1/5, 1/5, 1/5, 1/5, 1/5]

y[n] = Σ h[k] × x[n-k]  for k = 0 to 4
```

**Implementation:**

```python
if SCIPY_AVAILABLE:
    b = np.ones(5) / 5  # Filter coefficients
    filtered = scipy_signal.lfilter(b, 1, x)
else:
    filtered = np.convolve(x, np.ones(5)/5, mode='same')
```

#### 5.4.4 Zero-Crossing Rate (ZCR)

```
ZCR = (1/(N-1)) × Σ |sign(x[n] - μ) - sign(x[n-1] - μ)|  for n = 1 to N-1

where μ = mean(x)
```

**Interpretation:**
- High ZCR → Oscillating signal (active scrolling back and forth)
- Low ZCR → Steady signal (consistent direction or idle)

#### 5.4.5 FFT Spectral Analysis

```python
X = FFT(x)                    # Frequency domain representation
freqs = fftfreq(N, 1/fs)      # Frequency bins

# Dominant frequency (excluding DC)
dominant_freq = freqs[argmax(|X[1:]|) + 1]

# Spectral centroid (center of mass)
spectral_centroid = Σ(freqs × |X|) / Σ|X|
```

#### 5.4.6 Behavior Classification

The lower bound of 2 px/s is used so that very slow scrolling (e.g. careful document reading) is classified as reading rather than idle, improving alignment with observed engagement and quiz performance.

```python
# Band-pass classification based on filtered signal
reading_mask = (filtered > 2) & (filtered < 100)   # 2-100 px/s: active reading
idle_mask = filtered <= 2                           # ≤ 2 px/s: idle
skimming_mask = filtered > 100                      # > 100 px/s: skimming

reading_ratio = sum(reading_mask) / N
idle_ratio = sum(idle_mask) / N
skimming_ratio = sum(skimming_mask) / N
```

#### 5.4.7 Engagement Score Computation

```
base_score = reading_ratio × 60                    (0-60 points)

energy_normalized = min(energy / 1000, 1.0)
energy_bonus = energy_normalized × 25              (0-25 points)

optimal_zcr = 0.3
zcr_factor = max(0, 1 - |ZCR - optimal_zcr| / optimal_zcr)
zcr_bonus = zcr_factor × 15                        (0-15 points)

engagement_score = clamp(base_score + energy_bonus + zcr_bonus, 0, 100)
```

### 5.5 DSP Metrics Output

The function returns a comprehensive metrics dictionary:

```python
{
    # Signal Properties
    'signal_length': 120,
    'sampling_rate_hz': 1.0,
    
    # Time Domain Statistics
    'mean': 45.23,
    'std': 28.15,
    'max': 150.0,
    'min': 0.0,
    
    # Energy Analysis
    'energy': 2847.56,
    'power': 2847.56,
    
    # Zero-Crossing Analysis
    'zero_crossings': 35,
    'zcr': 0.2941,
    
    # Spectral Analysis
    'dominant_freq_hz': 0.0833,
    'spectral_centroid': 0.0421,
    
    # Behavior Classification
    'reading_ratio': 0.6833,
    'idle_ratio': 0.1500,
    'skimming_ratio': 0.1667,
    
    # Score Components
    'base_score': 41.0,
    'energy_bonus': 7.12,
    'zcr_bonus': 14.85,
    'final_score': 62.97,
    
    # DSP Info
    'filter_type': 'FIR_moving_average',
    'filter_order': 5,
    'scipy_available': True
}
```

---

## 6. Database Schema

### 6.1 Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EduSync Database Schema                            │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │    User      │
  ├──────────────┤
  │ id (PK)      │
  │ email        │◄─────────────────────────────────────────┐
  │ hashed_pw    │                                          │
  │ role         │                                          │
  │ full_name    │                                          │
  └──────┬───────┘                                          │
         │                                                  │
         │ 1:N (teacher creates)                            │
         ▼                                                  │
  ┌──────────────────┐        ┌─────────────────────┐      │
  │    Classroom     │        │ ClassroomEnrollment │      │
  ├──────────────────┤        ├─────────────────────┤      │
  │ id (PK)          │◄──────►│ id (PK)             │      │
  │ code (unique)    │  1:N   │ classroom_id (FK)   │      │
  │ name             │        │ user_id (FK)        │──────┘
  │ subject_name     │        └─────────────────────┘   N:M (student joins)
  │ teacher_id (FK)  │
  └──────┬───────────┘
         │
         │ 1:N
         ▼
  ┌──────────────────┐        ┌─────────────────────┐
  │    Material      │        │    Assignment       │
  ├──────────────────┤        ├─────────────────────┤
  │ id (PK)          │◄──────►│ id (PK)             │
  │ title            │  1:N   │ title               │
  │ file_path        │        │ quiz_json           │
  │ raw_text         │        │ classroom_id (FK)   │
  │ summary          │        │ material_id (FK)    │
  │ flashcards_json  │        │ created_at          │
  │ quiz_json        │        │ due_date            │
  │ classroom_id(FK) │        └──────────┬──────────┘
  │ created_at       │                   │
  └──────────────────┘                   │ 1:N
         │                               ▼
         │                   ┌─────────────────────┐
         │                   │   QuizSubmission    │
         │                   ├─────────────────────┤
         │                   │ id (PK)             │
         │                   │ assignment_id (FK)  │
         │                   │ user_id (FK)        │
         │                   │ score               │
         │                   │ answers_json        │
         │                   │ submitted_at        │
         │                   └─────────────────────┘
         │
         │ 1:N
         ▼
  ┌──────────────────┐
  │ LearningSession  │
  ├──────────────────┤
  │ id (PK)          │
  │ user_id (FK)     │
  │ material_id (FK) │
  │ scroll_signal    │
  │ engagement_score │
  │ timestamp        │
  └──────────────────┘
```

### 6.2 Table Definitions

#### User

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- 'teacher' or 'student'
    full_name VARCHAR
);
```

#### Classroom

```sql
CREATE TABLE classrooms (
    id INTEGER PRIMARY KEY,
    code VARCHAR(6) UNIQUE NOT NULL,  -- Join code (e.g., 'ABC123')
    name VARCHAR NOT NULL,
    subject_name VARCHAR,
    teacher_id INTEGER REFERENCES users(id)
);
```

#### Material

```sql
CREATE TABLE materials (
    id INTEGER PRIMARY KEY,
    title VARCHAR NOT NULL,
    file_path VARCHAR,          -- Uploaded file location
    raw_text TEXT DEFAULT '',   -- OCR-extracted text
    summary TEXT DEFAULT '',    -- AI-generated summary
    flashcards_json TEXT DEFAULT '[]',
    quiz_json TEXT DEFAULT '[]',
    classroom_id INTEGER REFERENCES classrooms(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### LearningSession

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    material_id INTEGER REFERENCES materials(id),
    scroll_signal TEXT,         -- JSON array of scroll deltas
    engagement_score FLOAT,     -- DSP-computed score (0-100)
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. API Specification

### 7.1 Authentication

**JWT Token Structure:**

```json
{
  "sub": 1,
  "email": "teacher@edu.com",
  "role": "teacher",
  "exp": 1735689600
}
```

**Token Configuration:**
- Algorithm: HS256
- Expiration: 7 days
- Header: `Authorization: Bearer <token>`

### 7.2 Core Endpoints

#### Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/register` | POST | No | Create account, returns JWT |
| `/login` | POST | No | Authenticate, returns JWT |

#### Materials

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/upload-material` | POST | Teacher | Upload file + OCR (no AI) |
| `/materials` | GET | Yes | List materials (role-filtered) |
| `/materials/{id}` | GET | Yes | Get material details |
| `/materials/{id}/file` | GET | Yes | Download original file |
| `/materials/{id}/generate-summary` | POST | Yes | On-demand summary |
| `/materials/{id}/generate-flashcards` | POST | Yes | On-demand flashcards |
| `/materials/{id}/generate-quiz` | POST | Yes | On-demand quiz |

#### Classrooms

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/classrooms` | POST | Teacher | Create classroom (generates code) |
| `/classrooms` | GET | Yes | List user's classrooms |
| `/classrooms/{id}` | GET | Yes | Get classroom details |
| `/classrooms/join` | POST | Student | Join by code |

#### Analytics

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/submit-analytics` | POST | Student | Submit scroll signal → engagement score |
| `/progress/classroom/{id}` | GET | Teacher | Student progress data |
| `/progress/classroom/{id}/dsp-metrics` | GET | Teacher | DSP metrics per student |
| `/teacher/dashboard-stats` | GET | Teacher | Aggregate statistics |
| `/research/metrics-summary` | GET | No | Research data summary |

### 7.3 Sample Request/Response

**Submit Analytics:**

```http
POST /submit-analytics
Authorization: Bearer eyJ...

{
  "material_id": 5,
  "scroll_signal": [0, 15, 25, 30, 45, 20, 10, 5, 0, 0, 50, 60, 40, 30, 20]
}
```

**Response:**

```json
{
  "engagement_score": 62.97,
  "dsp_metrics": {
    "signal_length": 15,
    "reading_ratio": 0.6833,
    "zcr": 0.2941,
    "energy": 2847.56,
    "dominant_freq_hz": 0.0833
  },
  "session_id": 42
}
```

---

## 8. Research Metrics Collection

### 8.1 Metrics Categories

The system collects three categories of metrics for research analysis:

#### 8.1.1 Inference Metrics

**File:** `backend/research_data/inference_metrics.jsonl`

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "operation": "summary",
  "duration_ms": 8542.31,
  "duration_s": 8.542,
  "input_chars": 5000,
  "output_chars": 1200,
  "chars_per_second": 140.47,
  "model": "llama-3-8b-q4",
  "gpu_layers": -1,
  "platform": "edge"
}
```

**Captured Operations:**
- `ocr` - Text extraction timing
- `summary` - Summary generation timing
- `flashcards` - Flashcard generation timing
- `quiz` - Quiz generation timing

#### 8.1.2 Engagement Metrics

**File:** `backend/research_data/engagement_metrics.jsonl`

```json
{
  "timestamp": "2024-01-15T10:35:22.456Z",
  "user_id": 5,
  "material_id": 12,
  "engagement_score": 72.45,
  "session_duration_s": 180,
  "signal_length": 180,
  "reading_ratio": 0.72,
  "idle_ratio": 0.15,
  "skimming_ratio": 0.13,
  "zcr": 0.28,
  "energy": 3200.45,
  "dominant_freq_hz": 0.05
}
```

#### 8.1.3 System Metrics

**File:** `backend/research_data/system_metrics.jsonl`

```json
{
  "timestamp": "2024-01-15T10:00:00.000Z",
  "event": "model_load",
  "model_load_time_ms": 12500
}
```

### 8.2 Research Data API

**Endpoint:** `GET /research/metrics-summary`

**Response:**

```json
{
  "inference_metrics": {
    "count": 245,
    "operations": {
      "ocr": {"count": 50, "avg_ms": 2500, "std_ms": 800},
      "summary": {"count": 65, "avg_ms": 8500, "std_ms": 1200},
      "flashcards": {"count": 65, "avg_ms": 7800, "std_ms": 1100},
      "quiz": {"count": 65, "avg_ms": 6200, "std_ms": 900}
    }
  },
  "engagement_metrics": {
    "count": 1250
  },
  "system_metrics": {
    "count": 15
  }
}
```

### 8.3 Visualizing Exported Data

After exporting research data to CSV (see export script below), the researcher can generate figures for reports and calibration. From the backend directory, run:

```bash
python scripts/visualize_research_data.py
```

**Inputs** (under `backend/research_data/`): the script reads `paired_engagement_quiz.csv` (engagement vs quiz pairs), optionally `engagement_metrics.csv` (per-session engagement), and `latency_percentiles.csv` or `inference_metrics.csv` (latency by operation).

**Outputs:** Figures are saved under `backend/research_data/figures/`:
- **engagement_vs_quiz_scatter.png** — Scatter plot of average engagement score (x) vs quiz score (y), with point labels when few points, optional linear regression line, and Pearson *r* (and *p*-value when computed).
- **engagement_distribution.png** — Histogram of engagement scores across sessions (if `engagement_metrics.csv` is available).
- **latency_by_operation.png** — Bar chart of average or median latency per operation (if latency data is available).

If a CSV is missing or empty, the script skips the corresponding plot and prints a short message. Dependencies: matplotlib and pandas (see `backend/requirements.txt`).

---

## 9. Research Methodology and Publication Potential

### 9.1 Methodology for Objective 1: Data Locality Validation via Network Isolation

The core claim of Objective 1 is that EduSync's edge architecture achieves **data sovereignty by construction** — no user data or document content leaves the local machine during inference. This is validated empirically using packet-level network analysis.

**Protocol — Network Traffic Analysis:**

1. **Tool:** Wireshark (GUI) or `tshark` (CLI) is run on the edge node's active network interface (`enp5s0f3u1` for Ethernet/tethered, or `wlp4s0` for WiFi).
2. **Capture Window:** A full inference cycle is triggered from the mobile client: upload a document → OCR extraction → LLM summary generation → return response to client.
3. **Filter:** All packets are captured. Post-capture, a display filter isolates outbound traffic to non-LAN destinations:
   ```
   !(ip.dst == 10.0.0.0/8) && !(ip.dst == 172.16.0.0/12) && !(ip.dst == 192.168.0.0/16) && ip.src == <EDGE_NODE_IP>
   ```
4. **Null Hypothesis ($H_0$):** The number of outbound packets to non-LAN destinations during inference is **zero**.
5. **Comparison Baseline:** The same document is processed via a cloud LLM API (e.g., OpenAI). The packet count to `api.openai.com` is recorded as the positive control, demonstrating the traffic that edge deployment eliminates.

**Expected Outcome:** A PCAP file demonstrating zero egress during edge inference, contrasted with measurable egress during cloud API inference. This constitutes empirical proof of data sovereignty.

**Architecture Enablers:**
- The Llama-3-8B-Instruct model (Q4_K_M, 4.7 GB) is loaded entirely into GPU VRAM via `llama-cpp-python` with `n_gpu_layers=-1`.
- EasyOCR runs on CPU with pre-downloaded models. No network call is made during OCR.
- The FastAPI server binds to `0.0.0.0:8000` and serves only LAN clients. No telemetry, analytics, or update checks are performed.

### 9.2 Methodology for Objective 2: DSP-Based Engagement Quantification

Student scroll behavior is modeled as a discrete-time signal and processed using classical DSP techniques to produce a quantitative engagement score.

**Signal Model:**

Scroll velocity is treated as a continuous-time signal discretized at the mobile client:

$$v(t) = \frac{dx}{dt}$$

where $x(t)$ is the vertical scroll position in pixels. The client samples this at $f_s = 1\text{ Hz}$, producing the discrete-time signal:

$$x[n] = v(nT_s), \quad T_s = 1\text{s}, \quad n \in \{0, 1, 2, \ldots, N-1\}$$

**Step 1 — Noise Reduction (5-tap FIR Low-Pass Filter):**

A 5-tap moving average FIR filter is applied to remove high-frequency noise (e.g., jitter from touch events):

$$h[n] = \left[\frac{1}{5}, \frac{1}{5}, \frac{1}{5}, \frac{1}{5}, \frac{1}{5}\right]$$

$$y[n] = \sum_{k=0}^{4} h[k] \cdot x[n-k]$$

Implementation uses `scipy.signal.lfilter(b, 1, x)` where `b = np.ones(5) / 5`.

**Step 2 — Signal Energy:**

The normalized signal energy quantifies overall scroll activity:

$$E = \frac{1}{N} \sum_{n=0}^{N-1} |x[n]|^2$$

Higher energy indicates more scroll movement. This metric is normalized against a reference ceiling of 1000 px²/s² for scoring.

**Step 3 — Zero-Crossing Rate (ZCR):**

ZCR measures how often the signal crosses its mean, indicating oscillatory (back-and-forth) scroll behavior:

$$\text{ZCR} = \frac{1}{N-1} \sum_{n=1}^{N-1} \left| \text{sign}(x[n] - \mu) - \text{sign}(x[n-1] - \mu) \right|$$

An optimal ZCR of ~0.3 corresponds to engaged reading with natural re-reading patterns. Very high ZCR suggests erratic behavior; very low ZCR suggests idle or linear skimming.

**Step 4 — Behavior Classification (Band-Pass Thresholding):**

The filtered signal $y[n]$ is classified into three behavioral bands:

| Band | Range (px/s) | Interpretation |
|------|-------------|----------------|
| Idle | $y[n] \leq 2$ | Not scrolling / paused |
| Reading | $2 < y[n] < 100$ | Active, attentive reading |
| Skimming | $y[n] \geq 100$ | Fast scrolling / skipping |

The **reading ratio** ($r$) — the fraction of samples in the Reading band — is the primary engagement indicator.

**Step 5 — Engagement Score Computation:**

$$S = \underbrace{r \times 60}_{\text{base (0–60)}} + \underbrace{\min\!\left(\frac{E}{1000}, 1\right) \times 25}_{\text{energy bonus (0–25)}} + \underbrace{\max\!\left(0,\ 1 - \frac{|\text{ZCR} - 0.3|}{0.3}\right) \times 15}_{\text{ZCR bonus (0–15)}}$$

$$S_{\text{final}} = \text{clamp}(S, 0, 100)$$

The full implementation is in `backend/signal_processor.py`, which also computes FFT spectral analysis (dominant frequency, spectral centroid) for additional research features.

### 9.3 Novel Contributions

1. **Edge AI Viability for Education** — Empirical benchmarks proving that a quantized 8B-parameter LLM on a consumer GPU can serve educational content generation with acceptable latency and zero cloud dependency.
2. **DSP-Based Non-Invasive Engagement Detection** — A formal signal processing pipeline (FIR → Energy → ZCR → Score) applied to scroll telemetry, validated against quiz performance via Pearson correlation.
3. **Data-Locality-by-Architecture** — Packet-level empirical evidence that on-device inference achieves data sovereignty without requiring encryption or trust in third-party processors.

### 9.4 Potential Publication Topics

| Topic | Target Venues | Key Contribution |
|-------|---------------|------------------|
| "Edge-Deployed LLMs for Automated Educational Content Generation" | IEEE Access, Education and Information Technologies | Performance benchmarks of quantized LLMs on edge devices |
| "DSP-Based Student Engagement Detection Using Scroll Behavior Analysis" | Computers & Education, IEEE Trans. on Learning Technologies | Novel signal processing approach for non-invasive engagement tracking |
| "Edge-Deployed Learning Analytics with On-Device AI" | Journal of Educational Data Mining | Packet-level proof of data sovereignty via edge deployment |

### 9.5 Limitations and Future Work

**Current Limitations:**

1. Single-language support (English only for OCR and LLM)
2. Limited to document-based content (no video/audio analysis)
3. Engagement model validation requires sufficient sample size ($N \geq 30$) for statistical power
4. Quantized model may exhibit reduced generation quality vs. full-precision or cloud models

**Future Directions:**

1. Multi-modal content analysis (video lectures, audio signals)
2. Adaptive learning path recommendation based on engagement trajectories
3. Real-time engagement feedback to teachers via WebSocket
4. Federated learning for edge-based model improvement across institutions

---

## 10. Experimental Validation

This section defines the three primary experiments that constitute the empirical validation of EduSync's research objectives. All experiments are designed to produce quantitative, reproducible results suitable for an ECE panel review.

### 10.1 Experiment A: Network Traffic Analysis (Packet Egress Count vs. Cloud APIs)

**Objective:** Prove that edge inference produces zero data egress to external servers.

**Setup:**
1. Start a `tshark` packet capture on the active interface (e.g., `enp5s0f3u1` or `wlp4s0`):
   ```bash
   tshark -i enp5s0f3u1 -w edge_inference_capture.pcap -f "host <EDGE_IP>"
   ```
2. From the mobile client, trigger a full inference cycle: upload a PDF → OCR → generate summary.
3. Stop capture. Count outbound packets to non-LAN IPs:
   ```bash
   tshark -r edge_inference_capture.pcap -Y "!(ip.dst == 10.0.0.0/8) && !(ip.dst == 172.16.0.0/12) && !(ip.dst == 192.168.0.0/16) && ip.src == <EDGE_IP>" | wc -l
   ```

**Control Experiment:** Repeat with a cloud LLM API (e.g., OpenAI `gpt-3.5-turbo`). Count outbound packets to `api.openai.com`.

**Expected Results:**

| Condition | Outbound Non-LAN Packets | Data Sovereignty |
|-----------|--------------------------|------------------|
| Edge Inference (EduSync) | 0 | Preserved |
| Cloud API (OpenAI) | $> 0$ (typically 10-50) | Violated |

**Deliverable:** PCAP files and a summary table in the final report.

### 10.2 Experiment B: DSP Calibration — Engagement Score vs. Quiz Performance (Pearson Correlation)

**Objective:** Validate that the DSP-computed engagement score is a meaningful predictor of learning outcomes.

**Setup:**
1. Recruit $N \geq 15$ participants (students) for a controlled reading + quiz session using the EduSync mobile app.
2. Each participant reads study material on the app. The `useScrollTracker` hook logs scroll signals at 1 Hz and submits them to `/submit-analytics`.
3. After reading, participants complete an AI-generated quiz via the app (score recorded in `QuizSubmission`).
4. Collect paired data: $(S_i, Q_i)$ where $S_i$ is the engagement score and $Q_i$ is the quiz score for participant $i$.

**Analysis:**

Compute the Pearson correlation coefficient:

$$r = \frac{\sum_{i=1}^{N}(S_i - \bar{S})(Q_i - \bar{Q})}{\sqrt{\sum_{i=1}^{N}(S_i - \bar{S})^2 \cdot \sum_{i=1}^{N}(Q_i - \bar{Q})^2}}$$

Report: $r$, $p$-value, 95% confidence interval, and a scatter plot of $(S, Q)$ pairs.

**Hypothesis:** A statistically significant positive correlation ($r > 0.3$, $p < 0.05$) indicates the DSP engagement score captures meaningful reading behavior.

**Data Sources:**
- Engagement scores: `backend/research_data/engagement_metrics.jsonl`
- Quiz scores: `QuizSubmission` table in SQLite (via `/progress/classroom/{id}` API)

### 10.3 Experiment C: Inference Latency Benchmarking on RTX 3060 (4-bit Quantization)

**Objective:** Characterize the inference performance of the edge LLM across all generation tasks.

**Setup:**
1. Process $\geq 50$ documents through each AI pipeline (summary, flashcards, quiz).
2. Each inference is automatically timed by the `metrics_logger.py` `Timer` class and logged to `backend/research_data/inference_metrics.jsonl`.

**Metrics Collected:**

| Metric | Description |
|--------|-------------|
| `duration_ms` | Wall-clock time per inference |
| `input_chars` | Input document length (characters) |
| `output_chars` | Generated output length (characters) |
| `chars_per_second` | Throughput: output_chars / duration_s |

**Analysis:**
- Report p50 (median) and p95 latency for each operation type (OCR, summary, flashcards, quiz).
- Plot latency distribution (histogram) and throughput vs. input size (scatter).
- Compare with cloud API latency benchmarks (literature values or measured).

**Expected Results:**

| Operation | Target p50 Latency | Target p95 Latency |
|-----------|-------------------|-------------------|
| OCR (5-page PDF) | < 25s | < 40s |
| Summary Generation | < 45s | < 70s |
| Flashcard Generation | < 40s | < 60s |
| Quiz Generation | < 35s | < 50s |

### 10.4 Data Collection Protocol

This subsection provides step-by-step instructions for conducting multi-user data collection sessions (Experiment B).

**Prerequisites:**
- Backend PC connected to a WiFi network (preferred) or Ethernet with LAN access
- Participants' phones on the **same WiFi network** as the backend PC
- Expo Go app installed on each participant's phone

**Step-by-Step Protocol:**

1. **Identify the backend IP address:**
   ```bash
   # Run the helper script from the project root:
   ./find_backend_ip.sh
   
   # Or manually:
   ip -4 addr show wlp4s0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'    # WiFi (preferred)
   ip -4 addr show enp5s0f3u1 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'  # Ethernet fallback
   ```

2. **Start the backend server:**
   ```bash
   cd backend
   python main.py
   # Server starts on http://0.0.0.0:8000
   ```

3. **Start the Expo development server with the correct IP:**
   ```bash
   cd EduSyncApp
   EXPO_PUBLIC_API_URL=http://<YOUR_IP>:8000 npx expo start
   ```
   Alternatively, edit `BACKEND_IP` in `EduSyncApp/lib/config.ts` to the current IP.

4. **Participants join:**
   - Each participant opens the **Expo Go** app and scans the QR code displayed in the terminal.
   - The app loads and participants register as "student" accounts.
   - A teacher account joins participants to a classroom and assigns materials + quizzes.

5. **Data flows:**
   - Scroll signals are logged to `backend/research_data/engagement_metrics.jsonl`
   - Quiz submissions are stored in the SQLite database
   - Inference metrics are logged to `backend/research_data/inference_metrics.jsonl`

6. **Post-session:** Export paired $(S_i, Q_i)$ data using:
   ```bash
   python backend/scripts/export_research_csv.py
   ```

---

## 11. Performance Characteristics

### 11.1 Measured Benchmarks

**Test Hardware:** RTX 3060 6GB, Ryzen 7 5800H, 16GB RAM

| Operation | Avg Time | Input Size | Output Size | Notes |
|-----------|----------|------------|-------------|-------|
| Model Load | 12-15s | - | - | One-time at startup |
| OCR (PDF, 5 pages) | 15-30s | 5 pages | ~5000 chars | CPU-bound |
| OCR (single image) | 2-5s | 1 image | ~500 chars | - |
| Summary Generation | 30-60s | 8000 chars | ~1000 chars | GPU-bound |
| Flashcard Generation | 25-50s | 8000 chars | ~800 chars | GPU-bound |
| Quiz Generation | 20-40s | 8000 chars | ~600 chars | GPU-bound |
| Engagement Calculation | <10ms | 100+ samples | 1 score | CPU (NumPy) |

### 11.2 Resource Utilization

| Resource | Idle | OCR Processing | LLM Generation |
|----------|------|----------------|----------------|
| GPU Memory | 4.5GB | 4.5GB | 5.8GB |
| GPU Utilization | 0% | 0% | 95-100% |
| CPU Utilization | 5% | 60-80% | 10-20% |
| RAM Usage | 6GB | 7GB | 6GB |

### 11.3 Scalability Considerations

**Single User:** Excellent performance, all operations complete within acceptable times

**Concurrent Users:** Limited by:
- Sequential LLM inference (GPU bottleneck)
- OCR parallelization possible (CPU-bound)
- Database queries scale well (SQLite with WAL mode)

**Recommendations for Scale:**
- Queue-based LLM requests for fairness
- Horizontal scaling requires multiple GPU nodes
- Consider model sharding for larger deployments

---

## 12. Dependencies and Requirements

### 12.1 Backend Dependencies

```
# Core Framework
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0

# AI/ML
llama-cpp-python>=0.2.0
easyocr>=1.7.0
pdf2image>=1.16.0
pypdf>=3.0.0

# DSP
numpy>=1.24.0
scipy>=1.11.0

# Auth
python-jose>=3.3.0
passlib>=1.7.0
bcrypt>=4.0.0

# Utilities
python-multipart>=0.0.6
pillow>=10.0.0
```

### 12.2 Frontend Dependencies

```json
{
  "expo": "~53.0.0",
  "react-native": "0.79.2",
  "expo-router": "~5.0.0",
  "axios": "^1.6.0",
  "expo-file-system": "~19.0.0",
  "expo-sharing": "~13.0.0",
  "expo-image": "~2.0.0"
}
```

### 12.3 System Requirements

| Requirement | Specification |
|-------------|---------------|
| OS | Linux (Ubuntu 22.04+), Windows 10/11 |
| CUDA | 11.7+ (for GPU acceleration) |
| Python | 3.10+ |
| Node.js | 18+ |
| LibreOffice | For PPT conversion (optional) |

### 12.4 Model Files

| Model | Size | Source |
|-------|------|--------|
| Meta-Llama-3-8B-Instruct-Q4_K_M.gguf | 4.7GB | HuggingFace (TheBloke) |
| EasyOCR English Model | ~100MB | Auto-downloaded |

---

## Appendix A: API Quick Reference

```
Authentication:
  POST /register          Create account
  POST /login             Login

Materials:
  POST /upload-material   Upload document
  GET  /materials         List materials
  GET  /materials/{id}    Get material
  POST /materials/{id}/generate-summary
  POST /materials/{id}/generate-flashcards
  POST /materials/{id}/generate-quiz

Classrooms:
  POST /classrooms        Create classroom
  GET  /classrooms        List classrooms
  POST /classrooms/join   Join classroom

Assignments:
  POST /assignments              Create assignment
  GET  /assignments              List assignments
  POST /assignments/{id}/submit  Submit quiz

Analytics:
  POST /submit-analytics                  Submit scroll signal
  GET  /progress/classroom/{id}           Get progress
  GET  /progress/classroom/{id}/dsp-metrics
  GET  /research/metrics-summary          Research data
```

---

## Appendix B: File Structure

```
EduSync/
├── backend/
│   ├── main.py                 # FastAPI app (30+ endpoints)
│   ├── database.py             # SQLAlchemy models
│   ├── llm_service.py          # Llama-3 integration
│   ├── parser_service.py       # OCR pipeline
│   ├── signal_processor.py     # DSP engagement detection
│   ├── metrics_logger.py       # Research data collection
│   ├── auth.py                 # Password utilities
│   ├── jwt_utils.py            # JWT management
│   ├── models/                 # LLM model files
│   ├── uploads/                # Uploaded documents
│   ├── research_data/          # Metrics JSONL, exported CSVs, figures/
│   └── scripts/
│       ├── export_research_csv.py      # Export JSONL → CSV
│       └── visualize_research_data.py  # Plot engagement vs quiz, distributions, latency
│
├── EduSyncApp/
│   ├── app/                    # Expo Router screens
│   ├── context/                # React Context providers
│   ├── lib/                    # API client, config
│   ├── hooks/                  # Custom hooks
│   └── components/             # Reusable components
│
├── EduSync.md                  # This documentation
└── README.md                   # Quick start guide
```

---

**Document Version:** 2.0  
**Last Updated:** February 2026  
**Authors:** EduSync Research Team
