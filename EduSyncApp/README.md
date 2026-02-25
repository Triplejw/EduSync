# EduSync — Edge AI Research Platform (Mobile Client)

Expo/React Native frontend for the EduSync research testbed. This app serves as the **signal acquisition and user interaction layer** for validating an Edge AI architecture and DSP-based engagement detection algorithms.

## Research Role

- **Signal Acquisition:** The `useScrollTracker` hook samples scroll velocity at 1 Hz, producing the discrete-time signal `x[n]` that feeds the backend DSP pipeline.
- **Data Collection:** During multi-user sessions, each participant's scroll telemetry and quiz responses are logged for offline Pearson correlation analysis (Experiment B).
- **Edge Client:** All API calls target the local edge node (`0.0.0.0:8000`) — no cloud services are contacted.

## Quick Setup

### 1. Configure the Backend IP

Edit `BACKEND_IP` in `lib/config.ts`, or use the env var override:

```bash
# Find your LAN IP (from the project root):
./find_backend_ip.sh

# Option A: env var (no code change)
EXPO_PUBLIC_API_URL=http://<YOUR_IP>:8000 npx expo start

# Option B: edit lib/config.ts directly
```

### 2. Start the Backend

```bash
cd backend && python main.py
# Binds to http://0.0.0.0:8000 (all LAN interfaces)
```

### 3. Install Dependencies and Start

```bash
cd EduSyncApp
npm install
npx expo start
```

Scan the QR code with **Expo Go** on a phone connected to the same network.

## Multi-User Data Collection (Experiment B)

1. Connect your PC and all participant phones to the **same WiFi network**.
2. Run `./find_backend_ip.sh` from the project root to get the correct IP.
3. Start backend + Expo with the detected IP.
4. Participants scan QR code, register as students, read materials, and take quizzes.
5. Engagement signals are logged to `backend/research_data/engagement_metrics.jsonl`.
6. Export paired data: `python backend/scripts/export_research_csv.py`.

## Project Structure

```
EduSyncApp/
├── app/                    # Expo Router screens
│   ├── _layout.tsx         # Root layout with providers
│   ├── index.tsx           # Login screen
│   ├── register.tsx        # Registration screen
│   ├── intro.tsx           # Animated intro screen
│   ├── (tabs)/             # Main tab navigation
│   │   ├── explore.tsx     # Classrooms list
│   │   ├── index.tsx       # Materials list
│   │   ├── assignments.tsx # Assignments list
│   │   └── progress.tsx    # Dashboard (engagement + DSP metrics)
│   ├── classroom/[id].tsx  # Classroom detail
│   ├── material/[id].tsx   # Material viewer + AI tools + scroll tracking
│   └── assignment/[id].tsx # Quiz interface
├── context/
│   ├── AuthContext.tsx      # JWT authentication state
│   └── IntroContext.tsx     # Intro screen control
├── lib/
│   ├── api.ts              # Axios API client (25+ functions)
│   └── config.ts           # LAN-aware API URL configuration
└── hooks/
    └── useScrollTracker.ts # 1 Hz scroll signal acquisition (DSP input)
```

## Auth

Login/register return a JWT. The Axios client sends `Authorization: Bearer <token>` on every request via an interceptor.
