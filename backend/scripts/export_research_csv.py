#!/usr/bin/env python3
"""
Export research metrics from JSONL + SQLite to CSV for thesis/report tables.

Run from the backend directory:
    python scripts/export_research_csv.py

Outputs (all in backend/research_data/):
    inference_metrics.csv        — raw per-inference rows
    engagement_metrics.csv       — raw per-session engagement rows
    metrics_summary.csv          — aggregated stats per operation type
    paired_engagement_quiz.csv   — (S_i, Q_i) pairs for Experiment B (Pearson r)
    latency_percentiles.csv      — p50/p95 latency per operation for Experiment C
"""

import json
import math
import os
import sys
import csv
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
RESEARCH_DIR = os.path.join(BACKEND_DIR, "research_data")

INFERENCE_JSONL = os.path.join(RESEARCH_DIR, "inference_metrics.jsonl")
ENGAGEMENT_JSONL = os.path.join(RESEARCH_DIR, "engagement_metrics.jsonl")

INFERENCE_CSV = os.path.join(RESEARCH_DIR, "inference_metrics.csv")
ENGAGEMENT_CSV = os.path.join(RESEARCH_DIR, "engagement_metrics.csv")
SUMMARY_CSV = os.path.join(RESEARCH_DIR, "metrics_summary.csv")
PAIRED_CSV = os.path.join(RESEARCH_DIR, "paired_engagement_quiz.csv")
LATENCY_CSV = os.path.join(RESEARCH_DIR, "latency_percentiles.csv")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_jsonl(path):
    """Load lines from a JSONL file; return list of dicts."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def percentile(sorted_values, p):
    """Return the p-th percentile (0-100) from an already-sorted list."""
    if not sorted_values:
        return None
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


# ---------------------------------------------------------------------------
# 1. Raw inference metrics CSV
# ---------------------------------------------------------------------------

def write_inference_csv():
    """Export inference_metrics.jsonl to inference_metrics.csv."""
    rows = load_jsonl(INFERENCE_JSONL)
    if not rows:
        print("No inference metrics found; skipping inference_metrics.csv")
        return
    fieldnames = [
        "timestamp", "operation", "duration_ms", "duration_s",
        "input_chars", "output_chars", "chars_per_second",
        "model", "gpu_layers", "platform",
    ]
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with open(INFERENCE_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  inference_metrics.csv       — {len(rows)} rows")


# ---------------------------------------------------------------------------
# 2. Raw engagement metrics CSV
# ---------------------------------------------------------------------------

def write_engagement_csv():
    """Export engagement_metrics.jsonl to engagement_metrics.csv."""
    rows = load_jsonl(ENGAGEMENT_JSONL)
    if not rows:
        print("No engagement metrics found; skipping engagement_metrics.csv")
        return
    fixed = ["timestamp", "user_id", "material_id", "engagement_score", "session_duration_s"]
    all_keys = list(fixed)
    for r in rows:
        for k in r:
            if k not in all_keys:
                all_keys.append(k)
    with open(ENGAGEMENT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  engagement_metrics.csv      — {len(rows)} rows")


# ---------------------------------------------------------------------------
# 3. Summary stats CSV
# ---------------------------------------------------------------------------

def write_summary_csv():
    """Compute summary stats and write metrics_summary.csv."""
    sys.path.insert(0, BACKEND_DIR)
    try:
        from metrics_logger import get_metrics_summary
    except ImportError:
        print("Could not import get_metrics_summary; skipping metrics_summary.csv")
        return
    summary = get_metrics_summary()
    rows = []
    ops = summary.get("inference_metrics", {}).get("operations", {})
    for op, data in ops.items():
        rows.append({
            "metric_type": "inference",
            "operation": op,
            "count": data.get("count", 0),
            "avg_ms": data.get("avg_ms"),
            "std_ms": data.get("std_ms"),
            "min_ms": data.get("min_ms"),
            "max_ms": data.get("max_ms"),
        })
    eng = summary.get("engagement_metrics", {})
    if eng.get("count", 0) > 0:
        rows.append({
            "metric_type": "engagement",
            "operation": "sessions",
            "count": eng["count"],
            "avg_ms": None, "std_ms": None, "min_ms": None, "max_ms": None,
        })
    if not rows:
        print("No summary data; skipping metrics_summary.csv")
        return
    fieldnames = ["metric_type", "operation", "count", "avg_ms", "std_ms", "min_ms", "max_ms"]
    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  metrics_summary.csv         — {len(rows)} rows")


# ---------------------------------------------------------------------------
# 4. Paired (engagement_score, quiz_score) CSV  — Experiment B
# ---------------------------------------------------------------------------

def write_paired_csv():
    """
    Join engagement scores with quiz scores per (user_id, material_id) to
    produce paired (S_i, Q_i) data for Pearson correlation analysis.

    Data sources:
        - Engagement scores: engagement_metrics.jsonl  (JSONL)
        - Quiz scores: SQLite QuizSubmission + Assignment tables

    Output columns:
        user_id, material_id, avg_engagement_score, quiz_score, full_name
    """
    # --- Load engagement data from JSONL ----------------------------------
    engagement_rows = load_jsonl(ENGAGEMENT_JSONL)
    if not engagement_rows:
        print("No engagement data; skipping paired_engagement_quiz.csv")
        return

    # Group engagement scores by (user_id, material_id), take average
    eng_by_user_mat = defaultdict(list)
    for r in engagement_rows:
        uid = r.get("user_id")
        mid = r.get("material_id")
        score = r.get("engagement_score")
        if uid is not None and mid is not None and score is not None:
            eng_by_user_mat[(uid, mid)].append(score)

    # --- Load quiz scores from SQLite -------------------------------------
    sys.path.insert(0, BACKEND_DIR)
    try:
        from database import SessionLocal, QuizSubmission, Assignment, User
    except ImportError:
        print("Could not import database models; skipping paired_engagement_quiz.csv")
        return

    db = SessionLocal()
    try:
        # Build mapping: material_id -> list of assignment_ids
        assignments = db.query(Assignment).filter(Assignment.material_id.isnot(None)).all()
        mat_to_assignments = defaultdict(list)
        for a in assignments:
            mat_to_assignments[a.material_id].append(a.id)

        # For each (user, material) pair, find quiz submissions
        paired_rows = []
        for (uid, mid), eng_scores in eng_by_user_mat.items():
            avg_eng = round(sum(eng_scores) / len(eng_scores), 2)
            assignment_ids = mat_to_assignments.get(mid, [])
            if not assignment_ids:
                continue  # No quiz linked to this material
            subs = (
                db.query(QuizSubmission)
                .filter(
                    QuizSubmission.user_id == uid,
                    QuizSubmission.assignment_id.in_(assignment_ids),
                )
                .all()
            )
            if not subs:
                continue  # Student hasn't taken the quiz
            avg_quiz = round(sum(s.score for s in subs) / len(subs), 2)
            user = db.query(User).filter(User.id == uid).first()
            paired_rows.append({
                "user_id": uid,
                "material_id": mid,
                "avg_engagement_score": avg_eng,
                "quiz_score": avg_quiz,
                "full_name": user.full_name if user else "",
                "engagement_sessions": len(eng_scores),
                "quiz_submissions": len(subs),
            })
    finally:
        db.close()

    if not paired_rows:
        print("No paired (engagement, quiz) data found; skipping paired_engagement_quiz.csv")
        return

    fieldnames = [
        "user_id", "material_id", "full_name",
        "avg_engagement_score", "quiz_score",
        "engagement_sessions", "quiz_submissions",
    ]
    with open(PAIRED_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(paired_rows)
    print(f"  paired_engagement_quiz.csv  — {len(paired_rows)} rows")

    # --- Quick Pearson r preview -----------------------------------------
    if len(paired_rows) >= 3:
        s_vals = [r["avg_engagement_score"] for r in paired_rows]
        q_vals = [r["quiz_score"] for r in paired_rows]
        n = len(s_vals)
        mean_s = sum(s_vals) / n
        mean_q = sum(q_vals) / n
        num = sum((s - mean_s) * (q - mean_q) for s, q in zip(s_vals, q_vals))
        den_s = math.sqrt(sum((s - mean_s) ** 2 for s in s_vals))
        den_q = math.sqrt(sum((q - mean_q) ** 2 for q in q_vals))
        r = num / (den_s * den_q) if (den_s * den_q) > 0 else 0
        print(f"    Pearson r = {r:.4f}  (N={n})")


# ---------------------------------------------------------------------------
# 5. Latency percentiles CSV  — Experiment C
# ---------------------------------------------------------------------------

def write_latency_percentiles_csv():
    """
    Compute p50 (median) and p95 latency per operation type from
    inference_metrics.jsonl for Experiment C benchmarking.
    """
    rows = load_jsonl(INFERENCE_JSONL)
    if not rows:
        print("No inference data; skipping latency_percentiles.csv")
        return

    # Group durations by operation
    by_op = defaultdict(list)
    for r in rows:
        op = r.get("operation")
        dur = r.get("duration_ms")
        if op and dur is not None:
            by_op[op].append(dur)

    out_rows = []
    for op in sorted(by_op.keys()):
        vals = sorted(by_op[op])
        n = len(vals)
        avg = sum(vals) / n
        out_rows.append({
            "operation": op,
            "count": n,
            "avg_ms": round(avg, 1),
            "p50_ms": round(percentile(vals, 50), 1),
            "p95_ms": round(percentile(vals, 95), 1),
            "min_ms": round(vals[0], 1),
            "max_ms": round(vals[-1], 1),
        })

    fieldnames = ["operation", "count", "avg_ms", "p50_ms", "p95_ms", "min_ms", "max_ms"]
    with open(LATENCY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f"  latency_percentiles.csv     — {len(out_rows)} operations")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    print("Exporting research data to CSV...")
    print()
    write_inference_csv()
    write_engagement_csv()
    write_summary_csv()
    write_paired_csv()
    write_latency_percentiles_csv()
    print()
    print(f"Done. All CSVs saved to {RESEARCH_DIR}")


if __name__ == "__main__":
    main()
