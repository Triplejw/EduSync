#!/usr/bin/env python3
"""
Export research metrics from JSONL to CSV for thesis/report tables.

Run from backend directory:
    python scripts/export_research_csv.py

Outputs:
    backend/research_data/inference_metrics.csv
    backend/research_data/engagement_metrics.csv
    backend/research_data/metrics_summary.csv (aggregated)
"""

import json
import os
import sys
import csv

# Paths: script is in backend/scripts/, data is in backend/research_data/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
RESEARCH_DIR = os.path.join(BACKEND_DIR, "research_data")
INFERENCE_JSONL = os.path.join(RESEARCH_DIR, "inference_metrics.jsonl")
ENGAGEMENT_JSONL = os.path.join(RESEARCH_DIR, "engagement_metrics.jsonl")
INFERENCE_CSV = os.path.join(RESEARCH_DIR, "inference_metrics.csv")
ENGAGEMENT_CSV = os.path.join(RESEARCH_DIR, "engagement_metrics.csv")
SUMMARY_CSV = os.path.join(RESEARCH_DIR, "metrics_summary.csv")


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


def write_inference_csv():
    """Export inference_metrics.jsonl to inference_metrics.csv."""
    rows = load_jsonl(INFERENCE_JSONL)
    if not rows:
        print("No inference metrics found; skipping inference_metrics.csv")
        return
    # Use first row to get keys; ensure consistent column order
    fieldnames = [
        "timestamp", "operation", "duration_ms", "duration_s",
        "input_chars", "output_chars", "chars_per_second",
        "model", "gpu_layers", "platform"
    ]
    # Add any extra keys from data
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with open(INFERENCE_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {INFERENCE_CSV}")


def write_engagement_csv():
    """Export engagement_metrics.jsonl to engagement_metrics.csv."""
    rows = load_jsonl(ENGAGEMENT_JSONL)
    if not rows:
        print("No engagement metrics found; skipping engagement_metrics.csv")
        return
    # Build fieldnames: fixed first, then DSP keys
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
    print(f"Wrote {len(rows)} rows to {ENGAGEMENT_CSV}")


def write_summary_csv():
    """Compute summary stats and write metrics_summary.csv (e.g. avg inference per operation)."""
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
            "avg_ms": None,
            "std_ms": None,
            "min_ms": None,
            "max_ms": None,
        })
    if not rows:
        print("No summary data; skipping metrics_summary.csv")
        return
    fieldnames = ["metric_type", "operation", "count", "avg_ms", "std_ms", "min_ms", "max_ms"]
    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote summary to {SUMMARY_CSV}")


def main():
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    write_inference_csv()
    write_engagement_csv()
    write_summary_csv()
    print("Done. CSVs are in", RESEARCH_DIR)


if __name__ == "__main__":
    main()
