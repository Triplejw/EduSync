#!/usr/bin/env python3
"""
Comprehensive Statistical Analysis for EduSync Research

Run from the backend directory:
    python scripts/run_statistical_analysis.py

Purpose:
    Apply rigorous statistical methods to validate engagement-quiz correlations.
    Addresses common reviewer concerns about statistical methodology.

Statistical Tests:
    1. Shapiro-Wilk normality test (both variables)
    2. Pearson r (parametric) with p-value and 95% CI
    3. Spearman rho (non-parametric alternative)
    4. Cohen's d effect size for group comparison
    5. Bonferroni correction for multiple comparisons
    6. Bootstrapped 95% CI (distribution-free)

Output:
    backend/research_data/statistical_analysis.csv
"""

import csv
import json
import math
import os
import random
import sys
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
RESEARCH_DIR = os.path.join(BACKEND_DIR, "research_data")
sys.path.insert(0, BACKEND_DIR)

ENGAGEMENT_JSONL = os.path.join(RESEARCH_DIR, "engagement_metrics.jsonl")
ATTENTION_VS_QUIZ = os.path.join(RESEARCH_DIR, "attention_vs_quiz.csv")
PAIRED_CSV = os.path.join(RESEARCH_DIR, "paired_engagement_quiz.csv")
OUTPUT_CSV = os.path.join(RESEARCH_DIR, "statistical_analysis.csv")


# ---------------------------------------------------------------------------
# Math helpers (pure Python fallbacks when scipy unavailable)
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    """Standard normal CDF via error function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _pearson_r(x, y):
    """Pearson correlation coefficient, t-stat, and two-tailed p-value."""
    n = len(x)
    if n < 3:
        return 0.0, 0.0, 1.0
    mx, my = sum(x) / n, sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    r = num / (dx * dy) if dx * dy > 0 else 0.0
    if abs(r) < 1:
        t = r * math.sqrt(n - 2) / math.sqrt(1 - r ** 2)
    else:
        t = float("inf") if r > 0 else float("-inf")
    try:
        from scipy.stats import t as t_dist
        p = 2 * (1 - t_dist.cdf(abs(t), df=n - 2))
    except ImportError:
        p = 2 * (1 - _norm_cdf(abs(t)))
    return r, t, p


def _fisher_ci(r, n, alpha=0.05):
    """95% CI for Pearson r via Fisher z-transformation."""
    if n <= 3 or abs(r) >= 1:
        return -1.0, 1.0
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    z_crit = 1.96 if alpha == 0.05 else 2.576  # 95% or 99%
    lo = math.tanh(z - z_crit * se)
    hi = math.tanh(z + z_crit * se)
    return lo, hi


def _spearman_rho(x, y):
    """Spearman rank correlation coefficient and p-value."""
    try:
        from scipy.stats import spearmanr
        rho, p = spearmanr(x, y)
        return rho, p
    except ImportError:
        pass
    # Manual rank calculation
    n = len(x)
    if n < 3:
        return 0.0, 1.0

    def _rank(vals):
        indexed = sorted(enumerate(vals), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)
    rho, _, p = _pearson_r(rx, ry)
    return rho, p


def _shapiro_wilk(values):
    """Shapiro-Wilk normality test. Returns (W, p_value)."""
    try:
        from scipy.stats import shapiro
        w, p = shapiro(values)
        return w, p
    except ImportError:
        # Cannot compute without scipy; return None to indicate unavailability
        return None, None


def _cohens_d(group1, group2):
    """Cohen's d effect size between two groups."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1, m2 = sum(group1) / n1, sum(group2) / n2
    var1 = sum((x - m1) ** 2 for x in group1) / (n1 - 1)
    var2 = sum((x - m2) ** 2 for x in group2) / (n2 - 1)
    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return (m1 - m2) / pooled_std


def _cohens_d_interpretation(d):
    """Interpret Cohen's d magnitude."""
    d = abs(d)
    if d < 0.2:
        return "negligible"
    elif d < 0.5:
        return "small"
    elif d < 0.8:
        return "medium"
    else:
        return "large"


def _bootstrap_ci(x, y, n_boot=5000, alpha=0.05, seed=42):
    """Bootstrap 95% CI for Pearson r (distribution-free)."""
    rng = random.Random(seed)
    n = len(x)
    if n < 3:
        return -1.0, 1.0
    boot_rs = []
    for _ in range(n_boot):
        indices = [rng.randint(0, n - 1) for _ in range(n)]
        bx = [x[i] for i in indices]
        by = [y[i] for i in indices]
        r, _, _ = _pearson_r(bx, by)
        boot_rs.append(r)
    boot_rs.sort()
    lo_idx = int(n_boot * alpha / 2)
    hi_idx = int(n_boot * (1 - alpha / 2))
    return boot_rs[lo_idx], boot_rs[hi_idx]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_paired_engagement_quiz():
    """Load paired (engagement_score, quiz_score) from CSV."""
    if not os.path.exists(PAIRED_CSV):
        return [], []
    eng, quiz = [], []
    with open(PAIRED_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                eng.append(float(row["avg_engagement_score"]))
                quiz.append(float(row["quiz_score"]))
            except (KeyError, ValueError):
                continue
    return eng, quiz


def load_attention_vs_quiz():
    """Load paired (focused_ratio, quiz_score) from CSV."""
    if not os.path.exists(ATTENTION_VS_QUIZ):
        return [], []
    fr, quiz = [], []
    with open(ATTENTION_VS_QUIZ, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                fr.append(float(row["focused_ratio"]))
                quiz.append(float(row["quiz_score"]))
            except (KeyError, ValueError):
                continue
    return fr, quiz


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_pair(label, x, y, alpha=0.05):
    """Run full statistical battery on one (x, y) pair."""
    n = len(x)
    result = {"analysis": label, "n": n}

    if n < 3:
        result["error"] = "insufficient data (n < 3)"
        return result

    # 1. Normality tests
    w_x, p_x = _shapiro_wilk(x)
    w_y, p_y = _shapiro_wilk(y)
    result["shapiro_w_x"] = round(w_x, 4) if w_x is not None else "N/A (scipy required)"
    result["shapiro_p_x"] = round(p_x, 6) if p_x is not None else "N/A"
    result["shapiro_w_y"] = round(w_y, 4) if w_y is not None else "N/A"
    result["shapiro_p_y"] = round(p_y, 6) if p_y is not None else "N/A"

    normal_x = p_x is not None and p_x > alpha
    normal_y = p_y is not None and p_y > alpha
    result["x_normal"] = "yes" if normal_x else ("no" if p_x is not None else "unknown")
    result["y_normal"] = "yes" if normal_y else ("no" if p_y is not None else "unknown")

    # 2. Pearson r (parametric)
    r, t_stat, p_pearson = _pearson_r(x, y)
    ci_lo, ci_hi = _fisher_ci(r, n, alpha)
    result["pearson_r"] = round(r, 4)
    result["pearson_t"] = round(t_stat, 4)
    result["pearson_p"] = round(p_pearson, 6)
    result["pearson_ci_lower"] = round(ci_lo, 4)
    result["pearson_ci_upper"] = round(ci_hi, 4)

    # 3. Spearman rho (non-parametric)
    rho, p_spearman = _spearman_rho(x, y)
    result["spearman_rho"] = round(rho, 4)
    result["spearman_p"] = round(p_spearman, 6)

    # 4. Recommended method
    if normal_x and normal_y:
        result["recommended_method"] = "Pearson (both distributions normal)"
    else:
        result["recommended_method"] = "Spearman (normality assumption violated or unknown)"

    # 5. Bootstrap CI (distribution-free)
    boot_lo, boot_hi = _bootstrap_ci(x, y)
    result["bootstrap_ci_lower"] = round(boot_lo, 4)
    result["bootstrap_ci_upper"] = round(boot_hi, 4)

    # 6. Cohen's d (median split)
    median_x = sorted(x)[n // 2]
    high_group = [y[i] for i in range(n) if x[i] >= median_x]
    low_group = [y[i] for i in range(n) if x[i] < median_x]
    d = _cohens_d(high_group, low_group)
    result["cohens_d"] = round(d, 4)
    result["cohens_d_interpretation"] = _cohens_d_interpretation(d)
    result["high_group_mean_y"] = round(sum(high_group) / len(high_group), 2) if high_group else "N/A"
    result["low_group_mean_y"] = round(sum(low_group) / len(low_group), 2) if low_group else "N/A"

    # 7. Effect size interpretation
    abs_r = abs(r)
    if abs_r < 0.1:
        result["r_effect_size"] = "negligible"
    elif abs_r < 0.3:
        result["r_effect_size"] = "small"
    elif abs_r < 0.5:
        result["r_effect_size"] = "medium"
    else:
        result["r_effect_size"] = "large"

    return result


def run_statistical_analysis():
    """Run comprehensive statistical analysis on all correlation pairs."""
    print("=" * 70)
    print("EduSync Comprehensive Statistical Analysis")
    print("=" * 70)
    os.makedirs(RESEARCH_DIR, exist_ok=True)

    analyses = []
    p_values_for_bonferroni = []

    # --- Analysis 1: Engagement vs Quiz Score ---
    eng, quiz_eng = load_paired_engagement_quiz()
    if len(eng) >= 3:
        result = analyze_pair("Engagement Score vs Quiz Score", eng, quiz_eng)
        analyses.append(result)
        if "pearson_p" in result:
            p_values_for_bonferroni.append(("Engagement vs Quiz (Pearson)", result["pearson_p"]))
        if "spearman_p" in result:
            p_values_for_bonferroni.append(("Engagement vs Quiz (Spearman)", result["spearman_p"]))
    else:
        print(f"  Engagement vs Quiz: skipped (only {len(eng)} paired observations)")

    # --- Analysis 2: Attention (focused_ratio) vs Quiz Score ---
    fr, quiz_att = load_attention_vs_quiz()
    if len(fr) >= 3:
        result = analyze_pair("Focused Ratio vs Quiz Score", fr, quiz_att)
        analyses.append(result)
        if "pearson_p" in result:
            p_values_for_bonferroni.append(("Attention vs Quiz (Pearson)", result["pearson_p"]))
        if "spearman_p" in result:
            p_values_for_bonferroni.append(("Attention vs Quiz (Spearman)", result["spearman_p"]))
    else:
        print(f"  Attention vs Quiz: skipped (only {len(fr)} paired observations)")

    if not analyses:
        print("\nNo data available for statistical analysis.")
        print("Run export_research_csv.py and analyze_attention.py first.")
        return

    # --- Bonferroni correction ---
    num_tests = len(p_values_for_bonferroni)
    bonferroni_alpha = 0.05 / num_tests if num_tests > 0 else 0.05

    print(f"\n  Bonferroni correction: {num_tests} tests, adjusted alpha = {bonferroni_alpha:.4f}")
    print()

    bonferroni_results = []
    for label, p in p_values_for_bonferroni:
        adjusted_p = min(p * num_tests, 1.0)
        significant = adjusted_p < 0.05
        bonferroni_results.append({
            "test": label,
            "raw_p": round(p, 6),
            "adjusted_p": round(adjusted_p, 6),
            "significant_after_correction": "yes" if significant else "no",
        })

    # --- Write results ---
    # Main analysis CSV
    if analyses:
        fieldnames = list(analyses[0].keys())
        for a in analyses[1:]:
            for k in a:
                if k not in fieldnames:
                    fieldnames.append(k)

        with open(OUTPUT_CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(analyses)
        print(f"  statistical_analysis.csv    -- {len(analyses)} analyses")

    # Bonferroni CSV
    bonferroni_csv = os.path.join(RESEARCH_DIR, "bonferroni_correction.csv")
    if bonferroni_results:
        with open(bonferroni_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["test", "raw_p", "adjusted_p", "significant_after_correction"])
            w.writeheader()
            w.writerows(bonferroni_results)
        print(f"  bonferroni_correction.csv   -- {len(bonferroni_results)} tests")

    # --- Print detailed report ---
    for result in analyses:
        print()
        print(f"  {'=' * 60}")
        print(f"  {result['analysis']}  (N = {result['n']})")
        print(f"  {'=' * 60}")

        if "error" in result:
            print(f"    Error: {result['error']}")
            continue

        # Normality
        print(f"    Shapiro-Wilk (X):  W = {result['shapiro_w_x']}, p = {result['shapiro_p_x']}")
        print(f"    Shapiro-Wilk (Y):  W = {result['shapiro_w_y']}, p = {result['shapiro_p_y']}")
        print(f"    X normal (alpha=0.05): {result['x_normal']}")
        print(f"    Y normal (alpha=0.05): {result['y_normal']}")

        # Pearson
        sig_p = "***" if result["pearson_p"] < 0.001 else "**" if result["pearson_p"] < 0.01 else "*" if result["pearson_p"] < 0.05 else "ns"
        print(f"\n    Pearson r  = {result['pearson_r']:.4f}  {sig_p}")
        print(f"    t-stat     = {result['pearson_t']:.4f}")
        print(f"    p-value    = {result['pearson_p']:.6f}")
        print(f"    95% CI     = [{result['pearson_ci_lower']:.4f}, {result['pearson_ci_upper']:.4f}]")

        # Spearman
        sig_s = "***" if result["spearman_p"] < 0.001 else "**" if result["spearman_p"] < 0.01 else "*" if result["spearman_p"] < 0.05 else "ns"
        print(f"\n    Spearman rho = {result['spearman_rho']:.4f}  {sig_s}")
        print(f"    p-value      = {result['spearman_p']:.6f}")

        # Bootstrap
        print(f"\n    Bootstrap 95% CI = [{result['bootstrap_ci_lower']:.4f}, {result['bootstrap_ci_upper']:.4f}]")

        # Cohen's d
        print(f"\n    Cohen's d (median split) = {result['cohens_d']:.4f}  ({result['cohens_d_interpretation']})")
        print(f"    High-engagement group mean quiz = {result['high_group_mean_y']}")
        print(f"    Low-engagement group mean quiz  = {result['low_group_mean_y']}")

        print(f"\n    Recommended method: {result['recommended_method']}")
        print(f"    Effect size (|r|):  {result['r_effect_size']}")

    # Bonferroni summary
    if bonferroni_results:
        print(f"\n  {'=' * 60}")
        print(f"  Bonferroni Multiple Comparison Correction")
        print(f"  {'=' * 60}")
        print(f"    Number of tests: {num_tests}")
        print(f"    Adjusted alpha:  {bonferroni_alpha:.4f}")
        print()
        for br in bonferroni_results:
            print(f"    {br['test']}:")
            print(f"      Raw p = {br['raw_p']:.6f}, Adjusted p = {br['adjusted_p']:.6f}, "
                  f"Significant: {br['significant_after_correction']}")

    print(f"\n  Done. Results saved to {RESEARCH_DIR}")


if __name__ == "__main__":
    run_statistical_analysis()
