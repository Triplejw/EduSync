"""
Performance Metrics Logger for EduSync Research Paper

This module collects performance metrics for the BTech ECE research paper:
"Edge AI-Powered Learning Analytics: A DSP Approach for Student Engagement Detection"

Metrics collected:
1. Inference time for each AI operation (OCR, Summary, Flashcards, Quiz)
2. Input/output sizes for throughput analysis
3. System resource utilization
4. Signal processing metrics from engagement detection

Data is saved to JSONL format for easy analysis with pandas/matplotlib.
"""

import time
import json
import os
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any

# Metrics file path
METRICS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research_data")
os.makedirs(METRICS_DIR, exist_ok=True)

INFERENCE_METRICS_FILE = os.path.join(METRICS_DIR, "inference_metrics.jsonl")
ENGAGEMENT_METRICS_FILE = os.path.join(METRICS_DIR, "engagement_metrics.jsonl")
SYSTEM_METRICS_FILE = os.path.join(METRICS_DIR, "system_metrics.jsonl")


class Timer:
    """
    Context manager for precise timing of operations.
    
    Usage:
        with Timer("summary") as t:
            result = generate_summary(text)
        print(f"Duration: {t.duration_ms} ms")
    """
    def __init__(self, operation_name: str):
        self.operation = operation_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        return False  # Don't suppress exceptions


def log_inference_metrics(
    operation: str,
    duration_ms: float,
    input_size: int,
    output_size: int,
    model_name: str = "llama-3-8b-q4",
    gpu_layers: int = -1,
    extra_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log AI inference metrics for research analysis.
    
    Args:
        operation: Type of operation ("ocr", "summary", "flashcards", "quiz")
        duration_ms: Time taken in milliseconds
        input_size: Input size in characters
        output_size: Output size in characters
        model_name: Name/version of the model used
        gpu_layers: Number of GPU layers (-1 = all)
        extra_data: Additional metrics to include
        
    Returns:
        The logged metric dictionary
    """
    # Calculate derived metrics
    chars_per_second = (output_size / (duration_ms / 1000)) if duration_ms > 0 else 0
    
    metric = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "duration_s": round(duration_ms / 1000, 3),
        "input_chars": input_size,
        "output_chars": output_size,
        "chars_per_second": round(chars_per_second, 2),
        "model": model_name,
        "gpu_layers": gpu_layers,
        "platform": "edge",  # Can be "edge" or "cloud" for comparison
    }
    
    if extra_data:
        metric.update(extra_data)
    
    # Append to JSONL file
    try:
        with open(INFERENCE_METRICS_FILE, "a") as f:
            f.write(json.dumps(metric) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to log inference metrics: {e}")
    
    return metric


def log_engagement_metrics(
    user_id: int,
    material_id: int,
    engagement_score: float,
    dsp_metrics: Dict[str, Any],
    session_duration_s: Optional[float] = None
) -> Dict[str, Any]:
    """
    Log engagement detection metrics from signal processing.
    
    Args:
        user_id: ID of the user
        material_id: ID of the material being studied
        engagement_score: Calculated engagement score (0-100)
        dsp_metrics: DSP analysis metrics from signal_processor
        session_duration_s: Optional session duration in seconds
        
    Returns:
        The logged metric dictionary
    """
    metric = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "material_id": material_id,
        "engagement_score": round(engagement_score, 2),
        "session_duration_s": session_duration_s,
        **dsp_metrics  # Include all DSP metrics
    }
    
    try:
        with open(ENGAGEMENT_METRICS_FILE, "a") as f:
            f.write(json.dumps(metric) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to log engagement metrics: {e}")
    
    return metric


def log_system_metrics(
    event: str,
    model_load_time_ms: Optional[float] = None,
    gpu_memory_mb: Optional[float] = None,
    cpu_percent: Optional[float] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log system resource utilization metrics.
    
    Args:
        event: Type of event ("startup", "model_load", "inference", etc.)
        model_load_time_ms: Time to load the model
        gpu_memory_mb: GPU memory usage in MB
        cpu_percent: CPU utilization percentage
        extra_data: Additional system metrics
        
    Returns:
        The logged metric dictionary
    """
    metric = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "model_load_time_ms": model_load_time_ms,
        "gpu_memory_mb": gpu_memory_mb,
        "cpu_percent": cpu_percent,
    }
    
    if extra_data:
        metric.update(extra_data)
    
    # Remove None values for cleaner output
    metric = {k: v for k, v in metric.items() if v is not None}
    
    try:
        with open(SYSTEM_METRICS_FILE, "a") as f:
            f.write(json.dumps(metric) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to log system metrics: {e}")
    
    return metric


def get_metrics_summary() -> Dict[str, Any]:
    """
    Generate a summary of collected metrics for the research paper.
    
    Returns:
        Dictionary with aggregated statistics
    """
    summary = {
        "inference_metrics": {"count": 0, "operations": {}},
        "engagement_metrics": {"count": 0},
        "system_metrics": {"count": 0},
    }
    
    # Analyze inference metrics
    try:
        if os.path.exists(INFERENCE_METRICS_FILE):
            operations = {}
            with open(INFERENCE_METRICS_FILE, "r") as f:
                for line in f:
                    try:
                        metric = json.loads(line.strip())
                        op = metric.get("operation", "unknown")
                        if op not in operations:
                            operations[op] = {"count": 0, "total_ms": 0, "durations": []}
                        operations[op]["count"] += 1
                        operations[op]["total_ms"] += metric.get("duration_ms", 0)
                        operations[op]["durations"].append(metric.get("duration_ms", 0))
                        summary["inference_metrics"]["count"] += 1
                    except json.JSONDecodeError:
                        continue
            
            # Calculate averages
            for op, data in operations.items():
                if data["count"] > 0:
                    durations = np.array(data["durations"])
                    operations[op] = {
                        "count": data["count"],
                        "avg_ms": round(np.mean(durations), 2),
                        "std_ms": round(np.std(durations), 2),
                        "min_ms": round(np.min(durations), 2),
                        "max_ms": round(np.max(durations), 2),
                    }
            summary["inference_metrics"]["operations"] = operations
    except Exception as e:
        summary["inference_metrics"]["error"] = str(e)
    
    # Count engagement metrics
    try:
        if os.path.exists(ENGAGEMENT_METRICS_FILE):
            with open(ENGAGEMENT_METRICS_FILE, "r") as f:
                summary["engagement_metrics"]["count"] = sum(1 for _ in f)
    except Exception as e:
        summary["engagement_metrics"]["error"] = str(e)
    
    # Count system metrics
    try:
        if os.path.exists(SYSTEM_METRICS_FILE):
            with open(SYSTEM_METRICS_FILE, "r") as f:
                summary["system_metrics"]["count"] = sum(1 for _ in f)
    except Exception as e:
        summary["system_metrics"]["error"] = str(e)
    
    return summary


# Export paths for external access
def get_metrics_file_paths() -> Dict[str, str]:
    """Return paths to all metrics files."""
    return {
        "inference": INFERENCE_METRICS_FILE,
        "engagement": ENGAGEMENT_METRICS_FILE,
        "system": SYSTEM_METRICS_FILE,
        "directory": METRICS_DIR,
    }


if __name__ == "__main__":
    # Test the metrics logger
    print("Testing Metrics Logger...")
    
    # Test inference metrics
    with Timer("test_operation") as t:
        time.sleep(0.1)  # Simulate work
    
    metric = log_inference_metrics(
        operation="test",
        duration_ms=t.duration_ms,
        input_size=1000,
        output_size=500,
    )
    print(f"Logged inference metric: {metric}")
    
    # Test engagement metrics
    metric = log_engagement_metrics(
        user_id=1,
        material_id=1,
        engagement_score=75.5,
        dsp_metrics={"zcr": 0.3, "energy": 150.0},
    )
    print(f"Logged engagement metric: {metric}")
    
    # Test system metrics
    metric = log_system_metrics(
        event="test_startup",
        model_load_time_ms=5000,
    )
    print(f"Logged system metric: {metric}")
    
    # Get summary
    summary = get_metrics_summary()
    print(f"\nMetrics Summary: {json.dumps(summary, indent=2)}")
    
    print(f"\nMetrics files saved to: {METRICS_DIR}")
