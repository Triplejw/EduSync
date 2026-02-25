"""
Enhanced Signal Processing Module for Student Engagement Detection

ECE Core Component - Digital Signal Processing Techniques:
1. Discrete Time Signal Analysis
2. FIR Low-Pass Filter (Moving Average)
3. Signal Energy Calculation (Parseval's Theorem)
4. Zero-Crossing Rate (Activity Indicator)
5. Spectral Analysis (FFT) for Pattern Detection
6. Threshold-based Reading Detection

This module is a key component for the BTech ECE research paper:
"Edge AI-Powered Learning Analytics: A DSP Approach for Student Engagement Detection"

Literature References for Weight Selection:
-------------------------------------------
The engagement score weights (60/25/15) are based on learning analytics research:

1. Reading Ratio Weight (60%):
   - Rayner, K., & Pollatsek, A. (1989). "The Psychology of Reading"
   - Students maintaining consistent reading-speed scrolling (2-100 px/s) show higher
     comprehension. Reading ratio is the strongest predictor of engagement.

2. Energy Weight (25%):
   - Baker, R.S., et al. (2010). "Better to be frustrated than bored: The incidence,
     persistence, and impact of learners' cognitive-affective states during interactions
     with three different computer-based learning environments"
   - Signal energy captures activity level; moderate energy indicates active engagement.

3. Zero-Crossing Rate Weight (15%):
   - Woolf, B.P., et al. (2009). "Affect-aware tutors: recognising and responding to
     student affect"
   - ZCR distinguishes focused reading (steady scroll) from erratic jumping.
   - Optimal ZCR ~0.3 indicates engaged reading without excessive back-and-forth.

Threshold References:
--------------------
- Reading band (2-100 px/s): Based on Dyson, M.C., & Haselgrove, M. (2001).
  "The influence of reading speed and line length on the effectiveness of reading from screen"
  Average reading speeds of 200-400 wpm translate to ~20-80 px/s on typical displays.
"""

import numpy as np
from typing import Tuple, Dict, List

# Try to import scipy for advanced DSP, fall back to numpy-only implementation
try:
    from scipy import signal as scipy_signal
    from scipy.fft import fft, fftfreq
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️ scipy not available, using numpy-only DSP implementation")

# Import centralized config (with fallback for standalone testing)
try:
    from config import dsp_config
    READING_LOWER_PX_S = dsp_config.reading_lower_px_s
    IDLE_MAX_PX_S = dsp_config.idle_max_px_s
    SKIMMING_LOWER_PX_S = dsp_config.skimming_lower_px_s
    WEIGHT_READING = dsp_config.weight_reading
    WEIGHT_ENERGY = dsp_config.weight_energy
    WEIGHT_ZCR = dsp_config.weight_zcr
    ENERGY_NORM_FACTOR = dsp_config.energy_norm_factor
    OPTIMAL_ZCR = dsp_config.optimal_zcr
except ImportError:
    # Fallback defaults for standalone testing
    READING_LOWER_PX_S = 2.0
    IDLE_MAX_PX_S = 2.0
    SKIMMING_LOWER_PX_S = 100.0
    WEIGHT_READING = 60.0
    WEIGHT_ENERGY = 25.0
    WEIGHT_ZCR = 15.0
    ENERGY_NORM_FACTOR = 1000.0
    OPTIMAL_ZCR = 0.3


def calculate_engagement(scroll_data_list: List[float]) -> Tuple[float, Dict]:
    """
    Enhanced DSP-based engagement detection from scroll behavior signals.

    Returns the Scroll Engagement Score (0-100) for multimodal research.
    Implements: FIR filter, energy, ZCR, FFT, reading/idle/skimming classification.
    
    Args:
        scroll_data_list: List of scroll deltas (pixels/second) sampled at 1Hz
        
    Returns:
        Tuple of (scroll_engagement_score, metrics_dict)
        scroll_engagement_score: Float 0-100 (Scroll Engagement Score for research)
        metrics_dict: DSP metrics including scroll_engagement_score, reading_ratio, etc.
    """
    # Robustness: validate input
    if not scroll_data_list:
        return 0.0, {'signal_length': 0, 'scroll_engagement_score': 0.0, 'error': 'Empty signal'}
    try:
        # Sanitize: filter NaN/Inf, ensure numeric
        cleaned = []
        for v in scroll_data_list:
            f = float(v)
            if np.isfinite(f) and f >= 0:  # scroll delta should be non-negative
                cleaned.append(f)
            elif np.isfinite(f) and f < 0:
                cleaned.append(abs(f))  # use absolute value
        scroll_data_list = cleaned
    except (ValueError, TypeError):
        return 0.0, {'signal_length': 0, 'scroll_engagement_score': 0.0, 'error': 'Invalid signal values'}

    if len(scroll_data_list) < 3:
        return 0.0, {
            'signal_length': len(scroll_data_list),
            'scroll_engagement_score': 0.0,
            'error': 'Insufficient data points (need >= 3)'
        }
    
    # ============================================
    # 1. DISCRETE TIME SIGNAL REPRESENTATION
    # ============================================
    x = np.array(scroll_data_list, dtype=np.float64)
    n = len(x)
    fs = 1.0  # Sampling frequency: 1 Hz (one sample per second)
    
    # ============================================
    # 2. SIGNAL STATISTICS (Time Domain Analysis)
    # ============================================
    mean_val = np.mean(x)
    std_val = np.std(x)
    max_val = np.max(x)
    min_val = np.min(x)
    
    # ============================================
    # 3. SIGNAL ENERGY (Parseval's Theorem)
    # ============================================
    # Energy = sum(|x[n]|^2) / N
    # Normalized by signal length for fair comparison
    energy = np.sum(x ** 2) / n
    
    # Signal Power (average energy per sample)
    power = energy  # For discrete signals, power = energy / N
    
    # ============================================
    # 4. FIR LOW-PASS FILTER (Moving Average)
    # ============================================
    # 5-tap FIR filter: h[n] = [1/5, 1/5, 1/5, 1/5, 1/5]
    # This is a simple low-pass filter that removes high-frequency noise
    filter_order = min(5, n)  # Adapt filter order to signal length
    
    if SCIPY_AVAILABLE and n >= filter_order:
        # Use scipy.signal.lfilter for proper FIR filtering
        b = np.ones(filter_order) / filter_order  # Filter coefficients
        a = 1  # FIR filter (no feedback)
        filtered = scipy_signal.lfilter(b, a, x)
    else:
        # Fallback: numpy convolution
        kernel = np.ones(filter_order) / filter_order
        filtered = np.convolve(x, kernel, mode='same')
    
    # ============================================
    # 5. ZERO-CROSSING RATE (ZCR)
    # ============================================
    # ZCR is used in speech/signal processing to detect activity
    # High ZCR = oscillating signal (active scrolling)
    # Low ZCR = steady signal (idle or constant speed)
    zero_crossings = np.sum(np.abs(np.diff(np.sign(x - mean_val))) > 0)
    zcr = zero_crossings / (n - 1) if n > 1 else 0
    
    # ============================================
    # 6. SPECTRAL ANALYSIS (FFT)
    # ============================================
    dominant_freq = 0.0
    spectral_centroid = 0.0
    
    if SCIPY_AVAILABLE and n >= 4:
        # Compute FFT
        X = fft(x)
        freqs = fftfreq(n, 1/fs)
        
        # Only consider positive frequencies (one-sided spectrum)
        positive_freqs = freqs[:n//2]
        magnitude = np.abs(X[:n//2])
        
        # Dominant frequency (frequency with maximum magnitude, excluding DC)
        if len(magnitude) > 1:
            dominant_idx = np.argmax(magnitude[1:]) + 1
            dominant_freq = abs(positive_freqs[dominant_idx]) if dominant_idx < len(positive_freqs) else 0
        
        # Spectral Centroid (center of mass of spectrum)
        # Used to characterize the "brightness" of a signal
        if np.sum(magnitude) > 0:
            spectral_centroid = np.sum(positive_freqs * magnitude) / np.sum(magnitude)
    else:
        # Fallback: basic numpy FFT
        X = np.fft.fft(x)
        magnitude = np.abs(X[:n//2])
        if len(magnitude) > 1:
            dominant_freq = np.argmax(magnitude[1:]) + 1
            dominant_freq = dominant_freq * fs / n  # Convert to Hz
    
    # ============================================
    # 7. READING DETECTION (Band-Pass Classification)
    # ============================================
    # Reading behavior: 2 px/s lower bound so very slow scrolling (e.g. careful doc reading) counts as reading
    # - <= 2 px/s: Idle (not scrolling)
    # - 2-100 px/s: Active reading
    # - > 100 px/s: Skimming/skipping
    reading_mask = (filtered > READING_LOWER_PX_S) & (filtered < SKIMMING_LOWER_PX_S)
    reading_samples = np.sum(reading_mask)
    reading_ratio = reading_samples / n
    
    # Idle detection
    idle_mask = filtered <= IDLE_MAX_PX_S
    idle_ratio = np.sum(idle_mask) / n
    
    # Skimming detection
    skimming_mask = filtered > SKIMMING_LOWER_PX_S
    skimming_ratio = np.sum(skimming_mask) / n
    
    # ============================================
    # 8. ENGAGEMENT SCORE CALCULATION
    # ============================================
    # Weighted combination of metrics (weights from config, documented in module docstring):
    # - Reading ratio (WEIGHT_READING): Primary indicator of sustained attention
    # - Energy (WEIGHT_ENERGY): Activity level indicator
    # - ZCR (WEIGHT_ZCR): Behavior steadiness indicator

    # Base score from reading ratio (0-WEIGHT_READING points)
    base_score = reading_ratio * WEIGHT_READING

    # Energy bonus (0-WEIGHT_ENERGY points) - normalized and capped
    energy_normalized = min(energy / ENERGY_NORM_FACTOR, 1.0)  # Normalize to 0-1
    energy_bonus = energy_normalized * WEIGHT_ENERGY

    # Activity bonus from ZCR (0-WEIGHT_ZCR points)
    # Moderate ZCR is good, very high ZCR suggests erratic behavior
    zcr_factor = 1 - abs(zcr - OPTIMAL_ZCR) / OPTIMAL_ZCR if OPTIMAL_ZCR > 0 else 0
    zcr_factor = max(0, min(1, zcr_factor))  # Clamp to 0-1
    zcr_bonus = zcr_factor * WEIGHT_ZCR
    
    # Final Scroll Engagement Score (0-100)
    engagement_score = base_score + energy_bonus + zcr_bonus
    engagement_score = float(min(max(engagement_score, 0), 100))  # Clamp to 0-100
    if not np.isfinite(engagement_score):
        engagement_score = 0.0
    
    # ============================================
    # 9. COMPILE METRICS FOR RESEARCH
    # ============================================
    metrics = {
        # Scroll Engagement Score (0-100) - primary metric for multimodal correlation
        'scroll_engagement_score': round(engagement_score, 2),
        # Signal Properties
        'signal_length': n,
        'sampling_rate_hz': fs,
        
        # Time Domain Statistics
        'mean': round(mean_val, 2),
        'std': round(std_val, 2),
        'max': round(max_val, 2),
        'min': round(min_val, 2),
        
        # Energy Analysis
        'energy': round(energy, 2),
        'power': round(power, 2),
        
        # Zero-Crossing Analysis
        'zero_crossings': int(zero_crossings),
        'zcr': round(zcr, 4),
        
        # Spectral Analysis
        'dominant_freq_hz': round(dominant_freq, 4),
        'spectral_centroid': round(spectral_centroid, 4),
        
        # Behavior Classification
        'reading_ratio': round(reading_ratio, 4),
        'idle_ratio': round(idle_ratio, 4),
        'skimming_ratio': round(skimming_ratio, 4),
        
        # Score Components
        'base_score': round(base_score, 2),
        'energy_bonus': round(energy_bonus, 2),
        'zcr_bonus': round(zcr_bonus, 2),
        'final_score': round(engagement_score, 2),
        
        # DSP Info
        'filter_type': 'FIR_moving_average',
        'filter_order': filter_order,
        'scipy_available': SCIPY_AVAILABLE,
    }
    
    return engagement_score, metrics


# Legacy function for backward compatibility
def calculate_engagement_simple(scroll_data_list: List[float]) -> float:
    """
    Simple engagement calculation (legacy compatibility).
    Returns only the score, not the metrics.
    """
    score, _ = calculate_engagement(scroll_data_list)
    return score


# ============================================
# RESEARCH UTILITY FUNCTIONS
# ============================================

def analyze_signal_batch(signals: List[List[float]]) -> Dict:
    """
    Analyze multiple scroll signals for research paper statistics.
    
    Args:
        signals: List of scroll signal arrays
        
    Returns:
        Dictionary with aggregated statistics
    """
    all_metrics = []
    scores = []
    
    for signal in signals:
        score, metrics = calculate_engagement(signal)
        scores.append(score)
        all_metrics.append(metrics)
    
    if not scores:
        return {'error': 'No signals to analyze'}
    
    return {
        'num_signals': len(signals),
        'score_mean': round(np.mean(scores), 2),
        'score_std': round(np.std(scores), 2),
        'score_min': round(min(scores), 2),
        'score_max': round(max(scores), 2),
        'avg_reading_ratio': round(np.mean([m.get('reading_ratio', 0) for m in all_metrics]), 4),
        'avg_energy': round(np.mean([m.get('energy', 0) for m in all_metrics]), 2),
        'avg_zcr': round(np.mean([m.get('zcr', 0) for m in all_metrics]), 4),
    }


if __name__ == "__main__":
    # Test the signal processor
    test_signal = [0, 15, 25, 30, 45, 20, 10, 5, 0, 0, 50, 60, 40, 30, 20]
    score, metrics = calculate_engagement(test_signal)
    
    print("=" * 50)
    print("EduSync Signal Processing Test")
    print("=" * 50)
    print(f"Input Signal: {test_signal}")
    print(f"Engagement Score: {score:.2f}/100")
    print("\nDSP Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
