#!/usr/bin/env python3
"""
Visualize exported research CSVs for reports and calibration.

Run from the backend directory:
    python scripts/visualize_research_data.py

Inputs (under backend/research_data/):
    paired_engagement_quiz.csv   — engagement vs quiz for scatter and Pearson r
    engagement_metrics.csv      — optional: distribution of engagement_score, reading_ratio, session_duration_s
    latency_percentiles.csv     — optional: bar chart of latency by operation
    inference_metrics.csv       — alternative for latency (aggregate by operation)

Outputs (under backend/research_data/figures/):
    engagement_vs_quiz_scatter.png   — primary: scatter + regression + Pearson r
    engagement_distribution.png      — optional: histogram of engagement_score
    latency_by_operation.png        — optional: bar chart of avg/p50 latency per operation
    attention_timeseries.png        — yaw/pitch vs time for a sample session
    attention_distribution.png      — histogram of yaw/pitch and focused ratio
    attention_vs_quiz_scatter.png   — focused_ratio vs quiz_score (if attention_vs_quiz.csv exists)

Dependencies: matplotlib, pandas (see backend/requirements.txt).
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
RESEARCH_DIR = os.path.join(BACKEND_DIR, "research_data")
FIGURES_DIR = os.path.join(RESEARCH_DIR, "figures")

PAIRED_CSV = os.path.join(RESEARCH_DIR, "paired_engagement_quiz.csv")
ENGAGEMENT_CSV = os.path.join(RESEARCH_DIR, "engagement_metrics.csv")
LATENCY_CSV = os.path.join(RESEARCH_DIR, "latency_percentiles.csv")
INFERENCE_CSV = os.path.join(RESEARCH_DIR, "inference_metrics.csv")
ATTENTION_LOG = os.path.join(RESEARCH_DIR, "attention_log.csv")
ATTENTION_SUMMARY = os.path.join(RESEARCH_DIR, "attention_summary.csv")
ATTENTION_VS_QUIZ = os.path.join(RESEARCH_DIR, "attention_vs_quiz.csv")


def _ensure_figures_dir():
    os.makedirs(FIGURES_DIR, exist_ok=True)


def plot_engagement_vs_quiz():
    """Scatter: avg_engagement_score (x) vs quiz_score (y), labels, regression, Pearson r."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        from scipy import stats
    except ImportError as e:
        print("Missing dependency for scatter plot:", e)
        return

    if not os.path.exists(PAIRED_CSV):
        print("paired_engagement_quiz.csv missing or not run; skipping engagement vs quiz scatter.")
        return
    df = pd.read_csv(PAIRED_CSV)
    if df.empty or "avg_engagement_score" not in df.columns or "quiz_score" not in df.columns:
        print("paired_engagement_quiz.csv empty or missing required columns; skipping scatter.")
        return

    x = df["avg_engagement_score"]
    y = df["quiz_score"]
    n = len(df)
    label_col = "full_name" if "full_name" in df.columns and df["full_name"].notna().any() else "user_id"
    labels = df[label_col].astype(str).tolist() if label_col in df.columns else [str(i) for i in range(n)]

    fig, ax = plt.subplots()
    ax.scatter(x, y, s=80, alpha=0.8)
    if n <= 20:
        for i, (xi, yi) in enumerate(zip(x, y)):
            ax.annotate(labels[i], (xi, yi), xytext=(5, 5), textcoords="offset points", fontsize=8)

    if n >= 2:
        r, p = stats.pearsonr(x, y)
        slope, intercept, r_lin, _, _ = stats.linregress(x, y)
        xline = x.copy()
        xline_sorted = xline.sort_values()
        yline = slope * xline_sorted + intercept
        ax.plot(xline_sorted, yline, "r--", alpha=0.8, label="Linear fit")
        ax.legend()
        text = f"Pearson r = {r:.3f}"
        if p < 0.001:
            text += ", p < 0.001"
        else:
            text += f", p = {p:.3f}"
        ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=10, verticalalignment="top")

    ax.set_xlabel("Avg engagement score")
    ax.set_ylabel("Quiz score")
    ax.set_title("Engagement vs quiz score")
    fig.tight_layout()
    _ensure_figures_dir()
    out = os.path.join(FIGURES_DIR, "engagement_vs_quiz_scatter.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def plot_engagement_distribution():
    """Histogram of engagement_score from engagement_metrics.csv."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError as e:
        print("Missing dependency for engagement distribution:", e)
        return

    if not os.path.exists(ENGAGEMENT_CSV):
        print("engagement_metrics.csv missing; skipping engagement distribution.")
        return
    df = pd.read_csv(ENGAGEMENT_CSV)
    if df.empty or "engagement_score" not in df.columns:
        print("engagement_metrics.csv empty or missing engagement_score; skipping distribution.")
        return

    fig, ax = plt.subplots()
    ax.hist(df["engagement_score"], bins=min(30, max(10, len(df) // 5)), edgecolor="black", alpha=0.7)
    ax.set_xlabel("Engagement score")
    ax.set_ylabel("Count")
    ax.set_title("Distribution of engagement scores (sessions)")
    fig.tight_layout()
    _ensure_figures_dir()
    out = os.path.join(FIGURES_DIR, "engagement_distribution.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def plot_latency_by_operation():
    """Bar chart of latency per operation from latency_percentiles.csv or inference_metrics.csv."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError as e:
        print("Missing dependency for latency plot:", e)
        return

    df = None
    if os.path.exists(LATENCY_CSV):
        df = pd.read_csv(LATENCY_CSV)
        if not df.empty and "operation" in df.columns:
            # Prefer avg_ms or p50_ms for bar height
            bar_col = "avg_ms" if "avg_ms" in df.columns else "p50_ms"
            if bar_col not in df.columns:
                df = None
    if df is None or df.empty:
        if os.path.exists(INFERENCE_CSV):
            inf = pd.read_csv(INFERENCE_CSV)
            if not inf.empty and "operation" in inf.columns and "duration_ms" in inf.columns:
                df = inf.groupby("operation")["duration_ms"].agg(["mean", "count"]).reset_index()
                df = df.rename(columns={"mean": "avg_ms"})
        if df is None or df.empty:
            print("latency_percentiles.csv and inference_metrics.csv missing or empty; skipping latency plot.")
            return

    bar_col = "avg_ms" if "avg_ms" in df.columns else "p50_ms"
    ops = df["operation"].tolist()
    vals = df[bar_col].tolist()

    fig, ax = plt.subplots()
    ax.bar(range(len(ops)), vals, tick_label=ops, edgecolor="black", alpha=0.7)
    ax.set_ylabel("Latency (ms)")
    ax.set_xlabel("Operation")
    ax.set_title("Latency by operation")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    _ensure_figures_dir()
    out = os.path.join(FIGURES_DIR, "latency_by_operation.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def plot_attention_timeseries():
    """Plot yaw and pitch vs time for a sample session. Color/marker for attention_state."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError as e:
        print("Missing dependency for attention timeseries:", e)
        return

    if not os.path.exists(ATTENTION_LOG):
        print("attention_log.csv missing; skipping attention timeseries.")
        return
    df = pd.read_csv(ATTENTION_LOG)
    if df.empty or "timestamp" not in df.columns or "yaw" not in df.columns or "pitch" not in df.columns:
        print("attention_log.csv empty or missing columns; skipping attention timeseries.")
        return

    # Use first session with at least 10 samples (by student_id, or first 50 rows)
    if "student_id" in df.columns:
        for sid in df["student_id"].unique():
            sub = df[df["student_id"] == sid].head(50)
            if len(sub) >= 5:
                df_plot = sub.copy()
                break
        else:
            df_plot = df.head(50)
    else:
        df_plot = df.head(50)

    df_plot = df_plot.sort_values("timestamp").reset_index(drop=True)
    t0 = df_plot["timestamp"].iloc[0]
    t_rel = (df_plot["timestamp"] - t0) / 1000.0  # seconds from start

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
    has_state = "attention_state" in df_plot.columns

    ax1.plot(t_rel, df_plot["yaw"], "o-", markersize=4, alpha=0.8, c="C0")
    ax1.axhline(20, color="gray", linestyle="--", alpha=0.5)
    ax1.axhline(-20, color="gray", linestyle="--", alpha=0.5)
    ax1.set_ylabel("Yaw (deg)")
    ax1.set_title("Head pose vs time (sample session)")
    ax1.grid(alpha=0.3)

    ax2.plot(t_rel, df_plot["pitch"], "o-", markersize=4, alpha=0.8, c="C1")
    ax2.axhline(15, color="gray", linestyle="--", alpha=0.5)
    ax2.axhline(-15, color="gray", linestyle="--", alpha=0.5)
    ax2.set_ylabel("Pitch (deg)")
    ax2.set_xlabel("Time from session start (s)")
    ax2.grid(alpha=0.3)

    if has_state:
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor="green", alpha=0.7, label="Focused (|yaw|<20, |pitch|<15)"),
            Patch(facecolor="red", alpha=0.7, label="Distracted"),
        ]
        ax1.legend(handles=legend_elements, loc="upper right", fontsize=7)

    fig.tight_layout()
    _ensure_figures_dir()
    out = os.path.join(FIGURES_DIR, "attention_timeseries.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def plot_attention_distribution():
    """Histogram of yaw, pitch, and focused ratio distribution."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError as e:
        print("Missing dependency for attention distribution:", e)
        return

    if not os.path.exists(ATTENTION_LOG):
        print("attention_log.csv missing; skipping attention distribution.")
        return
    df = pd.read_csv(ATTENTION_LOG)
    if df.empty:
        print("attention_log.csv empty; skipping attention distribution.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))

    if "yaw" in df.columns:
        axes[0, 0].hist(df["yaw"], bins=min(40, max(15, len(df) // 3)), edgecolor="black", alpha=0.7)
        axes[0, 0].set_xlabel("Yaw (deg)")
        axes[0, 0].set_ylabel("Count")
        axes[0, 0].set_title("Distribution of yaw")
    if "pitch" in df.columns:
        axes[0, 1].hist(df["pitch"], bins=min(40, max(15, len(df) // 3)), edgecolor="black", alpha=0.7)
        axes[0, 1].set_xlabel("Pitch (deg)")
        axes[0, 1].set_ylabel("Count")
        axes[0, 1].set_title("Distribution of pitch")

    if "attention_state" in df.columns and "student_id" in df.columns:
        focused_ratio_per_student = df.groupby("student_id")["attention_state"].mean()
        axes[1, 0].hist(focused_ratio_per_student, bins=min(20, max(5, len(focused_ratio_per_student))), edgecolor="black", alpha=0.7)
        axes[1, 0].set_xlabel("Focused ratio (per student)")
        axes[1, 0].set_ylabel("Count")
        axes[1, 0].set_title("Focused ratio distribution (students)")
    else:
        axes[1, 0].axis("off")

    if "attention_state" in df.columns:
        state_counts = df["attention_state"].value_counts().sort_index()
        axes[1, 1].bar(["Distracted (0)", "Focused (1)"], [state_counts.get(0, 0), state_counts.get(1, 0)], edgecolor="black", alpha=0.7)
        axes[1, 1].set_ylabel("Count")
        axes[1, 1].set_title("Attention state distribution")

    fig.tight_layout()
    _ensure_figures_dir()
    out = os.path.join(FIGURES_DIR, "attention_distribution.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def plot_attention_vs_quiz_scatter():
    """Scatter: focused_ratio (x) vs quiz_score (y) with Pearson r."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        from scipy import stats
    except ImportError as e:
        print("Missing dependency for attention vs quiz scatter:", e)
        return

    if not os.path.exists(ATTENTION_VS_QUIZ):
        print("attention_vs_quiz.csv missing; run scripts/analyze_attention.py first. Skipping attention vs quiz scatter.")
        return
    df = pd.read_csv(ATTENTION_VS_QUIZ)
    if df.empty or "focused_ratio" not in df.columns or "quiz_score" not in df.columns:
        print("attention_vs_quiz.csv empty or missing columns; skipping scatter.")
        return

    x = df["focused_ratio"]
    y = df["quiz_score"]
    n = len(df)
    label_col = "full_name" if "full_name" in df.columns and df["full_name"].notna().any() else "student_id"
    labels = df[label_col].astype(str).tolist() if label_col in df.columns else [str(i) for i in range(n)]

    fig, ax = plt.subplots()
    ax.scatter(x, y, s=80, alpha=0.8)
    if n <= 20:
        for i, (xi, yi) in enumerate(zip(x, y)):
            ax.annotate(labels[i], (xi, yi), xytext=(5, 5), textcoords="offset points", fontsize=8)

    if n >= 2:
        r, p = stats.pearsonr(x, y)
        slope, intercept, _, _, _ = stats.linregress(x, y)
        x_sorted = x.sort_values()
        yline = slope * x_sorted + intercept
        ax.plot(x_sorted, yline, "r--", alpha=0.8, label="Linear fit")
        ax.legend()
        text = f"Pearson r = {r:.3f}"
        if p < 0.001:
            text += ", p < 0.001"
        else:
            text += f", p = {p:.3f}"
        ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=10, verticalalignment="top")

    ax.set_xlabel("Focused ratio (attention)")
    ax.set_ylabel("Quiz score")
    ax.set_title("Attention (focused ratio) vs quiz score")
    fig.tight_layout()
    _ensure_figures_dir()
    out = os.path.join(FIGURES_DIR, "attention_vs_quiz_scatter.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def main():
    sys.path.insert(0, BACKEND_DIR)
    print("Generating research figures...")
    plot_engagement_vs_quiz()
    plot_engagement_distribution()
    plot_latency_by_operation()
    plot_attention_timeseries()
    plot_attention_distribution()
    plot_attention_vs_quiz_scatter()
    print("Done.")


if __name__ == "__main__":
    main()
