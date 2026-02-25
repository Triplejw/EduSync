#!/usr/bin/env python3
"""
Analyze attention_log.csv for conference paper.

Run from the backend directory:
    python scripts/analyze_attention.py

Inputs (under backend/research_data/):
    attention_log.csv  — timestamp, timestamp_iso, student_id, yaw, pitch, roll, attention_state, assignment_id
    (legacy 7-column format without timestamp_iso also supported)

Outputs (under backend/research_data/):
    attention_summary.csv   — per-student or per-(student,assignment): mean yaw/pitch/roll, focused_ratio
    attention_vs_quiz.csv   — paired (focused_ratio, quiz_score) for Pearson r (if assignment_id present)

Statistical Analysis:
    - Pearson correlation coefficient (r)
    - Two-tailed p-value using t-distribution
    - 95% confidence interval using Fisher z-transformation
    - Effect size interpretation (Cohen, 1988)

Use attention_summary.csv to fill Table 2 in PROJECT_REPORT.md.
"""

import csv
import math
import os
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
RESEARCH_DIR = os.path.join(BACKEND_DIR, "research_data")
ATTENTION_LOG = os.path.join(RESEARCH_DIR, "attention_log.csv")
ATTENTION_SUMMARY = os.path.join(RESEARCH_DIR, "attention_summary.csv")
ATTENTION_VS_QUIZ = os.path.join(RESEARCH_DIR, "attention_vs_quiz.csv")


def load_attention_log():
    """Load attention_log.csv. Handles both 6-column (legacy) and 7-column (with assignment_id) formats."""
    try:
        import pandas as pd
    except ImportError:
        # Fallback to csv
        return _load_attention_log_csv()
    if not os.path.exists(ATTENTION_LOG):
        return []
    df = pd.read_csv(ATTENTION_LOG)
    if df.empty:
        return []
    rows = []
    for _, r in df.iterrows():
        try:
            ts = int(r.get("timestamp", 0))
            sid = str(r.get("student_id", ""))
            yaw = float(r.get("yaw", 0))
            pitch = float(r.get("pitch", 0))
            roll = float(r.get("roll", 0))
            astate = int(r.get("attention_state", 0))
            aid = r.get("assignment_id", "")
            if pd.isna(aid) or aid == "":
                assignment_id = None
            else:
                try:
                    assignment_id = int(float(aid))
                except (ValueError, TypeError):
                    assignment_id = None
            rows.append({
                "timestamp": ts,
                "student_id": sid,
                "yaw": yaw,
                "pitch": pitch,
                "roll": roll,
                "attention_state": astate,
                "assignment_id": assignment_id,
            })
        except (ValueError, KeyError, TypeError):
            continue
    return rows


def _load_attention_log_csv():
    """Fallback CSV reader if pandas not available."""
    if not os.path.exists(ATTENTION_LOG):
        return []
    rows = []
    with open(ATTENTION_LOG, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                ts = int(r.get("timestamp", 0))
                sid = str(r.get("student_id", ""))
                yaw = float(r.get("yaw", 0))
                pitch = float(r.get("pitch", 0))
                roll = float(r.get("roll", 0))
                astate = int(r.get("attention_state", 0))
                aid_raw = r.get("assignment_id", r.get("Unnamed: 6", ""))
                aid = str(aid_raw).strip() if aid_raw is not None and aid_raw != "" else ""
                assignment_id = int(aid) if aid and aid.replace("-", "").isdigit() else None
                rows.append({
                    "timestamp": ts,
                    "student_id": sid,
                    "yaw": yaw,
                    "pitch": pitch,
                    "roll": roll,
                    "attention_state": astate,
                    "assignment_id": assignment_id,
                })
            except (ValueError, KeyError):
                continue
    return rows


def compute_summary(rows):
    """Group by (student_id, assignment_id) or (student_id,) and compute stats."""
    # key: (student_id,) or (student_id, assignment_id)
    groups = defaultdict(lambda: {"yaw": [], "pitch": [], "roll": [], "attention_state": []})
    for r in rows:
        if r["assignment_id"] is not None:
            key = (r["student_id"], r["assignment_id"])
        else:
            key = (r["student_id"],)
        g = groups[key]
        g["yaw"].append(r["yaw"])
        g["pitch"].append(r["pitch"])
        g["roll"].append(r["roll"])
        g["attention_state"].append(r["attention_state"])

    summary_rows = []
    for key, g in groups.items():
        n = len(g["attention_state"])
        focused = sum(g["attention_state"])
        focused_ratio = round(focused / n, 4) if n > 0 else 0
        mean_yaw = round(sum(g["yaw"]) / n, 2) if n > 0 else 0
        mean_pitch = round(sum(g["pitch"]) / n, 2) if n > 0 else 0
        mean_roll = round(sum(g["roll"]) / n, 2) if n > 0 else 0
        row = {
            "student_id": key[0],
            "sample_count": n,
            "mean_yaw": mean_yaw,
            "mean_pitch": mean_pitch,
            "mean_roll": mean_roll,
            "focused_ratio": focused_ratio,
        }
        if len(key) == 2:
            row["assignment_id"] = key[1]
        else:
            row["assignment_id"] = ""
        summary_rows.append(row)
    return summary_rows


def compute_correlation_stats(x: list, y: list) -> dict:
    """
    Compute Pearson correlation with p-value and 95% CI.

    Uses:
    - Pearson r formula
    - Two-tailed p-value from t-distribution (scipy if available, else approximation)
    - 95% CI via Fisher z-transformation

    Returns dict with: r, p_value, ci_lower, ci_upper, n, t_stat, effect_size
    """
    n = len(x)
    if n < 3:
        return {"r": 0, "p_value": 1.0, "ci_lower": -1, "ci_upper": 1, "n": n,
                "t_stat": 0, "effect_size": "insufficient data"}

    # Pearson r
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
    r = num / (den_x * den_y) if (den_x * den_y) > 0 else 0

    # t-statistic for significance test
    if abs(r) < 1:
        t_stat = r * math.sqrt(n - 2) / math.sqrt(1 - r ** 2)
    else:
        t_stat = float('inf') if r > 0 else float('-inf')

    # p-value from t-distribution
    try:
        from scipy import stats as scipy_stats
        p_value = 2 * (1 - scipy_stats.t.cdf(abs(t_stat), df=n - 2))
    except ImportError:
        # Approximation using normal distribution for large n
        if n > 30:
            # Normal approximation
            p_value = 2 * (1 - _norm_cdf(abs(t_stat)))
        else:
            # Very rough approximation for small n
            p_value = 2 * (1 - _norm_cdf(abs(t_stat) * math.sqrt((n - 2) / n)))

    # 95% Confidence Interval via Fisher z-transformation
    if abs(r) < 1:
        z = 0.5 * math.log((1 + r) / (1 - r))  # Fisher z
        se_z = 1 / math.sqrt(n - 3) if n > 3 else 1
        z_crit = 1.96  # 95% CI
        z_lower = z - z_crit * se_z
        z_upper = z + z_crit * se_z
        # Transform back
        ci_lower = (math.exp(2 * z_lower) - 1) / (math.exp(2 * z_lower) + 1)
        ci_upper = (math.exp(2 * z_upper) - 1) / (math.exp(2 * z_upper) + 1)
    else:
        ci_lower = ci_upper = r

    # Effect size interpretation (Cohen, 1988)
    abs_r = abs(r)
    if abs_r < 0.1:
        effect_size = "negligible"
    elif abs_r < 0.3:
        effect_size = "small"
    elif abs_r < 0.5:
        effect_size = "medium"
    else:
        effect_size = "large"

    return {
        "r": round(r, 4),
        "p_value": round(p_value, 6),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "n": n,
        "t_stat": round(t_stat, 4),
        "effect_size": effect_size,
    }


def _norm_cdf(x: float) -> float:
    """Approximate standard normal CDF using error function approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def print_correlation_report(label: str, stats: dict):
    """Print formatted correlation statistics for research paper."""
    print(f"\n    === Correlation Analysis: {label} ===")
    print(f"    Sample size (N):           {stats['n']}")
    print(f"    Pearson r:                 {stats['r']:.4f}")
    print(f"    t-statistic:               {stats['t_stat']:.4f}")
    print(f"    p-value (two-tailed):      {stats['p_value']:.6f}")
    print(f"    95% CI:                    [{stats['ci_lower']:.4f}, {stats['ci_upper']:.4f}]")
    print(f"    Effect size (Cohen):       {stats['effect_size']}")

    # Significance interpretation
    if stats['p_value'] < 0.001:
        sig = "*** (p < 0.001)"
    elif stats['p_value'] < 0.01:
        sig = "** (p < 0.01)"
    elif stats['p_value'] < 0.05:
        sig = "* (p < 0.05)"
    else:
        sig = "not significant (p >= 0.05)"
    print(f"    Significance:              {sig}")

    # CI interpretation
    if stats['ci_lower'] > 0:
        print(f"    CI interpretation:         Positive correlation (CI excludes 0)")
    elif stats['ci_upper'] < 0:
        print(f"    CI interpretation:         Negative correlation (CI excludes 0)")
    else:
        print(f"    CI interpretation:         CI includes 0 - correlation may be spurious")


def write_attention_vs_quiz(summary_rows):
    """Join attention summary (with assignment_id) to quiz scores. Write attention_vs_quiz.csv."""
    # Only rows with assignment_id
    with_aid = [r for r in summary_rows if r.get("assignment_id") != ""]
    if not with_aid:
        return

    sys.path.insert(0, BACKEND_DIR)
    try:
        from database import SessionLocal, QuizSubmission, User
    except ImportError:
        print("Could not import database; skipping attention_vs_quiz.csv")
        return

    db = SessionLocal()
    paired = []
    try:
        for r in with_aid:
            sid = int(r["student_id"]) if r["student_id"].isdigit() else None
            aid = r["assignment_id"]
            if sid is None:
                continue
            sub = (
                db.query(QuizSubmission)
                .filter(
                    QuizSubmission.user_id == sid,
                    QuizSubmission.assignment_id == aid,
                )
                .first()
            )
            if sub is None:
                continue
            user = db.query(User).filter(User.id == sid).first()
            paired.append({
                "student_id": sid,
                "assignment_id": aid,
                "full_name": user.full_name if user else "",
                "focused_ratio": r["focused_ratio"],
                "quiz_score": round(sub.score, 2),
                "sample_count": r["sample_count"],
            })
    finally:
        db.close()

    if not paired:
        print("No paired (attention, quiz) data; skipping attention_vs_quiz.csv")
        return

    fieldnames = ["student_id", "assignment_id", "full_name", "focused_ratio", "quiz_score", "sample_count"]
    with open(ATTENTION_VS_QUIZ, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(paired)
    print(f"  attention_vs_quiz.csv       — {len(paired)} rows")

    if len(paired) >= 2:
        fr = [p["focused_ratio"] for p in paired]
        qs = [p["quiz_score"] for p in paired]
        stats = compute_correlation_stats(fr, qs)
        print_correlation_report("focused_ratio vs quiz_score", stats)


def main():
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    print("Analyzing attention_log.csv...")
    rows = load_attention_log()
    if not rows:
        print("attention_log.csv missing or empty. Run quizzes to collect data.")
        return

    summary_rows = compute_summary(rows)
    fieldnames = ["student_id", "assignment_id", "sample_count", "mean_yaw", "mean_pitch", "mean_roll", "focused_ratio"]
    with open(ATTENTION_SUMMARY, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(summary_rows)
    print(f"  attention_summary.csv       — {len(summary_rows)} rows")

    write_attention_vs_quiz(summary_rows)

    # Overall stats for Table 2
    all_yaw = [r["yaw"] for r in rows]
    all_pitch = [r["pitch"] for r in rows]
    all_roll = [r["roll"] for r in rows]
    all_state = [r["attention_state"] for r in rows]
    n = len(rows)
    focused_ratio = sum(all_state) / n if n > 0 else 0
    print()
    print("Overall stats (for Table 2 in PROJECT_REPORT):")
    print(f"  Yaw (deg):    mean={sum(all_yaw)/n:.2f}, std={(sum((x - sum(all_yaw)/n)**2 for x in all_yaw)/n)**0.5:.2f}, min={min(all_yaw):.2f}, max={max(all_yaw):.2f}")
    print(f"  Pitch (deg):  mean={sum(all_pitch)/n:.2f}, std={(sum((x - sum(all_pitch)/n)**2 for x in all_pitch)/n)**0.5:.2f}, min={min(all_pitch):.2f}, max={max(all_pitch):.2f}")
    print(f"  Roll (deg):   mean={sum(all_roll)/n:.2f}, std={(sum((x - sum(all_roll)/n)**2 for x in all_roll)/n)**0.5:.2f}, min={min(all_roll):.2f}, max={max(all_roll):.2f}")
    print(f"  Focused ratio: {focused_ratio:.4f}")
    print()
    print(f"Done. Outputs in {RESEARCH_DIR}")


if __name__ == "__main__":
    main()
