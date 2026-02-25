#!/usr/bin/env python3
"""
Generate synthetic multi-user research data for EduSync conference paper evaluation.

Reproducible with seed 42. Seeds the SQLite DB with synthetic users, classrooms,
materials, assignments, and quiz submissions; writes attention_log.csv and
engagement_metrics.jsonl so that engagement/attention correlate with quiz score.

Run from the backend directory:
    python scripts/generate_synthetic_research_data.py

Then run (in order):
    python scripts/export_research_csv.py
    python scripts/analyze_attention.py
    python scripts/visualize_research_data.py

Optionally backup research_data/ and edusync.db before running.
"""

import csv
import json
import os
import random
import sys
from datetime import datetime, timedelta
from typing import List, Tuple

# Fixed seed for reproducibility (document for paper)
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
RESEARCH_DIR = os.path.join(BACKEND_DIR, "research_data")
ATTENTION_LOG_PATH = os.path.join(RESEARCH_DIR, "attention_log.csv")
ENGAGEMENT_JSONL_PATH = os.path.join(RESEARCH_DIR, "engagement_metrics.jsonl")

# Config: scale for conference paper (N >= 20-30 pairs)
NUM_STUDENTS = 30
NUM_MATERIALS = 2
NUM_ASSIGNMENTS_PER_MATERIAL = 2  # 2 for material 1, 2 for material 2 -> 4 assignments total
FRAMES_PER_QUIZ_SESSION = (20, 45)  # min, max frames per (student, assignment)
ENGAGEMENT_SESSIONS_PER_USER_MATERIAL = (1, 2)  # min, max
# Correlation design: latent "effort" drives quiz score, focus ratio, and engagement
TARGET_PEARSON_RANGE = (0.4, 0.6)

# Vision thresholds (match vision_service.py)
YAW_THRESHOLD = 20.0
PITCH_THRESHOLD = 15.0


def _ensure_research_dir():
    os.makedirs(RESEARCH_DIR, exist_ok=True)


def seed_database() -> Tuple[List[int], List[int], List[int], List[Tuple[int, int, float]]]:
    """
    Seed DB with synthetic teacher, students, classroom, materials, assignments, quiz submissions.
    Returns (student_ids, material_ids, assignment_ids, list of (user_id, assignment_id, quiz_score)).
    If synthetic users already exist (eval_teacher@edusync.local), reuses them and returns existing data.
    """
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)
    from database import (
        SessionLocal,
        User,
        Classroom,
        ClassroomEnrollment,
        Material,
        Assignment,
        QuizSubmission,
        Base,
        engine,
    )
    from auth import get_password_hash

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Reuse existing synthetic data if present
        existing = db.query(User).filter(User.email == "eval_teacher@edusync.local").first()
        if existing:
            teacher_id = existing.id
            classroom = db.query(Classroom).filter(Classroom.teacher_id == teacher_id).first()
            if not classroom:
                classroom = db.query(Classroom).order_by(Classroom.id.desc()).first()
            student_ids = [u.id for u in db.query(User).filter(User.email.like("eval_student_%@edusync.local")).all()]
            material_ids = [m.id for m in db.query(Material).filter(Material.classroom_id == classroom.id).all()]
            assignment_ids = [a.id for a in db.query(Assignment).filter(Assignment.classroom_id == classroom.id).all()]
            submissions_data = [
                (s.user_id, s.assignment_id, s.score)
                for s in db.query(QuizSubmission).filter(
                    QuizSubmission.user_id.in_(student_ids),
                    QuizSubmission.assignment_id.in_(assignment_ids),
                ).all()
            ]
            if student_ids and submissions_data:
                print("  Reusing existing synthetic users and submissions")
                return student_ids, material_ids, assignment_ids, submissions_data
        # 1. Synthetic teacher
        teacher = User(
            email="eval_teacher@edusync.local",
            hashed_password=get_password_hash("eval"),
            role="teacher",
            full_name="Eval Teacher",
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        teacher_id = teacher.id

        # 2. Classroom
        classroom = Classroom(
            code="EVAL" + str(random.randint(1000, 9999)),
            name="Evaluation Classroom",
            subject_name="ECE Capstone",
            teacher_id=teacher_id,
        )
        db.add(classroom)
        db.commit()
        db.refresh(classroom)
        classroom_id = classroom.id

        # 3. Materials
        material_ids = []
        for i in range(NUM_MATERIALS):
            m = Material(
                title=f"Evaluation Material {i+1}",
                file_path=None,
                raw_text="Synthetic content for research evaluation.",
                classroom_id=classroom_id,
            )
            db.add(m)
            db.commit()
            db.refresh(m)
            material_ids.append(m.id)

        # 4. Assignments (link to materials: 2 per material)
        assignment_ids = []
        assignment_to_material = {}
        for mid in material_ids:
            for j in range(NUM_ASSIGNMENTS_PER_MATERIAL):
                a = Assignment(
                    title=f"Quiz M{mid} A{j+1}",
                    quiz_json='[{"question":"Q1","options":["A","B","C","D"],"correct_answer":0}]',
                    classroom_id=classroom_id,
                    material_id=mid,
                )
                db.add(a)
                db.commit()
                db.refresh(a)
                assignment_ids.append(a.id)
                assignment_to_material[a.id] = mid

        # 5. Students and enrollments
        student_ids = []
        for i in range(NUM_STUDENTS):
            u = User(
                email=f"eval_student_{i+1}@edusync.local",
                hashed_password=get_password_hash("eval"),
                role="student",
                full_name=f"Student {i+1}",
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            student_ids.append(u.id)
            db.add(ClassroomEnrollment(classroom_id=classroom_id, user_id=u.id))
        db.commit()

        # 6. Latent "effort" per student (0-1) for correlation
        effort = [random.random() for _ in student_ids]

        # 7. Quiz submissions: score = 35 + 55*effort + noise -> [0,100]
        submissions_data = []
        for idx, uid in enumerate(student_ids):
            for aid in assignment_ids:
                score = 35 + 55 * effort[idx] + random.gauss(0, 8)
                score = max(0, min(100, round(score, 2)))
                sub = QuizSubmission(
                    assignment_id=aid,
                    user_id=uid,
                    score=score,
                    answers_json="[]",
                )
                db.add(sub)
                submissions_data.append((uid, aid, score))
        db.commit()

        return student_ids, material_ids, assignment_ids, submissions_data
    finally:
        db.close()


def write_attention_log(
    submissions_data: List[Tuple[int, int, float]],
) -> None:
    """
    Write attention_log.csv with rows per (student_id, assignment_id).
    Focused ratio per (student, assignment) is correlated with quiz score.
    """
    _ensure_research_dir()
    t0_ms = int(datetime.utcnow().timestamp() * 1000) - 3600 * 1000

    with open(ATTENTION_LOG_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "timestamp",
                "timestamp_iso",
                "student_id",
                "yaw",
                "pitch",
                "roll",
                "attention_state",
                "assignment_id",
            ]
        )

        for user_id, assignment_id, quiz_score in submissions_data:
            # Target focused ratio: correlate with quiz score (0.25 to 0.95)
            target_focused = 0.25 + 0.65 * (quiz_score / 100.0) + random.gauss(0, 0.06)
            target_focused = max(0.15, min(0.95, target_focused))

            n_frames = random.randint(*FRAMES_PER_QUIZ_SESSION)
            for i in range(n_frames):
                if random.random() < target_focused:
                    # Focused: yaw/pitch within thresholds
                    yaw = random.uniform(-YAW_THRESHOLD + 2, YAW_THRESHOLD - 2)
                    pitch = random.uniform(-PITCH_THRESHOLD + 2, PITCH_THRESHOLD - 2)
                    attention_state = 1
                else:
                    # Distracted: exceed threshold
                    yaw = random.choice([-1, 1]) * random.uniform(YAW_THRESHOLD + 5, 50)
                    pitch = random.choice([-1, 1]) * random.uniform(PITCH_THRESHOLD + 5, 40)
                    attention_state = 0
                roll = random.uniform(-180, 180)
                ts_ms = t0_ms + (i * 2100)
                ts_iso = (
                    datetime.utcfromtimestamp(ts_ms / 1000.0).strftime("%Y-%m-%dT%H:%M:%S.")
                    + f"{(ts_ms % 1000):03d}Z"
                )
                w.writerow(
                    [
                        ts_ms,
                        ts_iso,
                        user_id,
                        round(yaw, 2),
                        round(pitch, 2),
                        round(roll, 2),
                        attention_state,
                        assignment_id,
                    ]
                )

    print(f"  Wrote {ATTENTION_LOG_PATH}")


def _make_engagement_row(
    user_id: int,
    material_id: int,
    engagement_score: float,
    session_duration_s: int,
    timestamp_iso: str,
) -> dict:
    """Build one engagement_metrics.jsonl row with DSP-like fields."""
    n = session_duration_s
    reading_ratio = max(0, min(1, (engagement_score / 100.0) * 0.7 + random.gauss(0, 0.05)))
    idle_ratio = max(0, min(1, (1 - reading_ratio) * random.uniform(0.3, 0.7)))
    skimming_ratio = max(0, 1 - reading_ratio - idle_ratio)
    base_score = reading_ratio * 60
    energy = 1000 * (engagement_score / 100.0) + random.uniform(0, 500)
    zcr = 0.15 + (engagement_score / 100.0) * 0.2 + random.gauss(0, 0.03)
    zcr = max(0.04, min(0.5, zcr))
    energy_bonus = min(25, energy / 1000 * 25)
    optimal_zcr = 0.3
    zcr_factor = max(0, 1 - abs(zcr - optimal_zcr) / optimal_zcr)
    zcr_bonus = zcr_factor * 15
    final_score = min(100, base_score + energy_bonus + zcr_bonus)
    return {
        "timestamp": timestamp_iso,
        "user_id": user_id,
        "material_id": material_id,
        "engagement_score": round(engagement_score, 2),
        "session_duration_s": n,
        "signal_length": n,
        "sampling_rate_hz": 1.0,
        "mean": round(100 + engagement_score * 2 + random.uniform(-20, 20), 2),
        "std": round(200 + random.uniform(0, 300), 2),
        "max": round(500 + random.uniform(0, 500), 2),
        "min": 0.0,
        "energy": round(energy, 2),
        "power": round(energy, 2),
        "zero_crossings": int(n * zcr),
        "zcr": round(zcr, 4),
        "dominant_freq_hz": round(random.uniform(0.01, 0.1), 4),
        "spectral_centroid": round(random.uniform(0.12, 0.2), 4),
        "reading_ratio": round(reading_ratio, 4),
        "idle_ratio": round(idle_ratio, 4),
        "skimming_ratio": round(skimming_ratio, 4),
        "base_score": round(base_score, 2),
        "energy_bonus": round(energy_bonus, 2),
        "zcr_bonus": round(zcr_bonus, 2),
        "final_score": round(final_score, 2),
        "filter_type": "FIR_moving_average",
        "filter_order": 5,
        "scipy_available": True,
        "scroll_engagement_score": round(engagement_score, 2),
    }


def write_engagement_metrics(
    student_ids: List[int],
    material_ids: List[int],
    assignment_ids: List[int],
    submissions_data: List[Tuple[int, int, float]],
) -> None:
    """
    Write engagement_metrics.jsonl. For each (user_id, material_id) we need
    avg quiz score on assignments for that material; then engagement_score
    correlated with that avg.
    """
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)
    from database import SessionLocal, Assignment

    db = SessionLocal()
    try:
        mat_to_assignments = {}
        for a in db.query(Assignment).filter(Assignment.material_id.isnot(None)).all():
            mat_to_assignments.setdefault(a.material_id, []).append(a.id)
    finally:
        db.close()

    # (user_id, material_id) -> list of quiz scores
    user_mat_scores = {}
    for uid, aid, score in submissions_data:
        for mid, aids in mat_to_assignments.items():
            if aid in aids:
                user_mat_scores.setdefault((uid, mid), []).append(score)
                break

    _ensure_research_dir()
    base_time = datetime.utcnow() - timedelta(days=1)
    rows_written = 0

    with open(ENGAGEMENT_JSONL_PATH, "w") as f:
        for (user_id, material_id), scores in user_mat_scores.items():
            avg_quiz = sum(scores) / len(scores)
            # Engagement score correlated with quiz: 28 + 0.5*avg_quiz + noise
            engagement_score = 28 + 0.5 * avg_quiz + random.gauss(0, 6)
            engagement_score = max(25, min(75, round(engagement_score, 2)))

            n_sessions = random.randint(*ENGAGEMENT_SESSIONS_PER_USER_MATERIAL)
            for _ in range(n_sessions):
                session_s = random.randint(30, min(450, 200 + int(avg_quiz)))
                ts = base_time + timedelta(seconds=random.randint(0, 86400))
                ts_iso = ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                row = _make_engagement_row(
                    user_id, material_id, engagement_score, session_s, ts_iso
                )
                f.write(json.dumps(row) + "\n")
                rows_written += 1

    print(f"  Wrote {ENGAGEMENT_JSONL_PATH} ({rows_written} rows)")


def main():
    import sys
    sys.path.insert(0, BACKEND_DIR)

    print("Generating synthetic research data (seed={})...".format(RANDOM_SEED))
    print()

    student_ids, material_ids, assignment_ids, submissions_data = seed_database()
    print(f"  Seeded DB: {len(student_ids)} students, {len(material_ids)} materials, "
          f"{len(assignment_ids)} assignments, {len(submissions_data)} quiz submissions")

    write_attention_log(submissions_data)
    write_engagement_metrics(
        student_ids, material_ids, assignment_ids, submissions_data
    )

    print()
    print("Done. Next run:")
    print("  python scripts/export_research_csv.py")
    print("  python scripts/analyze_attention.py")
    print("  python scripts/visualize_research_data.py")


if __name__ == "__main__":
    main()
