# EduSync Project Pivot: "Vision-Based Attention Monitoring"
## Master Instruction File for AI Agent

### 1. Project Context & Objective
**Current State:** We have a functioning LMS ("EduSync") with a FastAPI backend (Python) and a React Native frontend (Expo). It currently uses Llama-3 (GPU) for text generation and EasyOCR (CPU) for text extraction.

**The Pivot (New Objective):**
We are adding a **Real-Time Biometric Engagement Analysis** module. 
Instead of tracking scrolling, we will track **Head Pose (Yaw/Pitch)** using the device's camera during quizzes.
- **Goal:** Quantify student attention by analyzing head stability.
- **Constraint:** The Vision model must run on **CPU** (using MediaPipe) to leave the **GPU** free for Llama-3.

---

### 2. Implementation Plan

#### Phase A: Backend Implementation (Python/FastAPI)

**Task 1: Install Dependencies**
Add `mediapipe` and `opencv-python` to `backend/requirements.txt`.

**Task 2: Create `backend/vision_service.py`**
Create a new service file responsible for Head Pose Estimation.
* **Library:** Use `mediapipe.solutions.face_mesh`.
* **Input:** Receive a base64 encoded image or raw bytes.
* **Logic (The "ECE" Math):**
    1.  Extract 2D Face Landmarks (Nose, Chin, Eyes, Mouth edges).
    2.  Map to a generic 3D Face Model.
    3.  Use `cv2.solvePnP` to calculate the Rotation Vector.
    4.  Convert Rotation Vector to **Euler Angles (Pitch, Yaw, Roll)**.
* **Output:** Return a dictionary: `{"yaw": float, "pitch": float, "attention_score": int}`.
    * *Logic:* If `abs(yaw) > 20` OR `abs(pitch) > 15`, `attention_score = 0`. Else `100`.

**Task 3: Create API Endpoint in `backend/main.py`**
* **Endpoint:** `POST /analyze-attention`
* **Payload:** `{"image": "base64_string", "student_id": "xyz", "timestamp": 12345}`
* **Action:** Call `vision_service.estimate_pose(image)`.
* **Data Logging:** Append the result `[timestamp, yaw, pitch, score]` to a CSV file named `backend/research_data/attention_log.csv`. (This is crucial for the conference paper).

---

#### Phase B: Frontend Implementation (React Native/Expo)

**Task 1: Camera Integration**
* Install `expo-camera`.
* In `EduSyncApp/app.json`, ensure camera permissions are requested.

**Task 2: Create `AttentionTracker` Component**
Create `EduSyncApp/components/AttentionTracker.tsx`.
* **UI:** A hidden or small preview `Camera` view (1x1 pixel or minimized) active *only* during quizzes.
* **Logic:**
    1.  Every **2 seconds**, take a picture (`cameraRef.takePictureAsync({ quality: 0.3, base64: true })`).
    2.  Send the `base64` string to `POST /analyze-attention`.
    3.  Receive the `attention_score`.
    4.  (Optional) Show a "Warning: Please Focus" toast if score is 0.

**Task 3: Integrate into Quiz Screen**
* Modify `EduSyncApp/app/(tabs)/assignment/[id].tsx`.
* Mount the `<AttentionTracker />` component when the quiz starts.
* Unmount when the quiz ends.

---

### 3. Technical Constraints & Guidelines (Strict Rules)

1.  **CPU Only for Vision:** explicitly set `min_detection_confidence=0.5` in MediaPipe. Do not attempt to use CUDA for this; save CUDA for Llama-3.
2.  **Latency Handling:** The Frontend must *not* wait for the API response. Fire and forget. We need the data log, not instant UI updates.
3.  **Data Logging:** The CSV format must be rigorous.
    * Header: `timestamp, student_id, yaw, pitch, roll, attention_state`
    * `attention_state`: Binary (1 for Focused, 0 for Distracted).

### 4. Verification Step (How to test)

1.  Start the Backend (`uvicorn main:app`).
2.  Start the App. Open a Quiz.
3.  **Test A:** Look at the screen for 10 seconds. Check `attention_log.csv`. Expect `yaw` near 0.
4.  **Test B:** Look left/right for 10 seconds. Check `attention_log.csv`. Expect `yaw` > 20.

**Generate the code for `backend/vision_service.py` and `EduSyncApp/components/AttentionTracker.tsx` now.**
