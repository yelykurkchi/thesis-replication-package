"""Metric aggregation and result comparison helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from .config import DEST_DISPLAY_NAMES, SimulationConfig


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def summarize_run(
    log_df: pd.DataFrame,
    config: SimulationConfig,
    experiment_id: str,
    timestamp: str,
    run_id: int,
    seed: int,
    previous_results: Optional[pd.DataFrame] = None,
) -> Dict[str, object]:
    events = log_df["simulated_event_type"] != "none"
    alerts = log_df["generated_alert"].astype(bool)

    true_positive = int((events & alerts).sum())
    true_negative = int((~events & ~alerts).sum())
    false_positive = int((~events & alerts).sum())
    false_negative = int((events & ~alerts).sum())
    total = len(log_df)

    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1_score = _ratio(2 * precision * recall, precision + recall)
    accuracy = _ratio(true_positive + true_negative, total)

    detected_events = log_df.loc[events & alerts]
    average_detection_time_ms = (
        float(detected_events["total_latency_ms"].mean()) if not detected_events.empty else 0.0
    )

    active_dest_ids = config.active_dest_ids()
    active_dest = [DEST_DISPLAY_NAMES.get(dest_id, dest_id) for dest_id in active_dest_ids]
    row: Dict[str, object] = {
        "experiment_id": experiment_id,
        "timestamp": timestamp,
        "execution_mode": config.execution_mode,
        "run_id": run_id,
        "seed": seed,
        "number_workers": config.number_workers,
        "simulation_duration": config.simulation_duration,
        "sampling_frequency": config.sampling_frequency,
        "total_timesteps": config.total_steps,
        "risk_score_threshold": config.risk_score_threshold,
        "sensor_noise_level": config.sensor_noise_level,
        "packet_loss_probability_configured": config.packet_loss_probability,
        "gateway_processing_capacity": config.gateway_processing_capacity,
        "active_dest_count": len(active_dest),
        "active_dest": "; ".join(active_dest),
        "covered_ethical_categories": "; ".join(config.covered_ethical_categories()),
        "total_generated_alerts": int(alerts.sum()),
        "correct_alerts": true_positive,
        "false_positives": false_positive,
        "false_negatives": false_negative,
        "true_negatives": true_negative,
        "risk_detection_accuracy": accuracy,
        "average_detection_time_ms": average_detection_time_ms,
        "break_recommendations": int((log_df["recommendation"] == "suggest_break").sum()),
        "undetected_critical_events": false_negative,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "average_communication_latency_ms": float(log_df["communication_latency_ms"].mean()),
        "average_processing_latency_ms": float(log_df["processing_latency_ms"].mean()),
        "average_total_latency_ms": float(log_df["total_latency_ms"].mean()),
        "number_transmitted_messages": int(total),
        "packet_loss_rate": float(log_df["packet_loss"].mean()),
        "total_energy_consumption_mj": float(log_df["energy_consumption_mj"].sum()),
        "average_energy_consumption_mj": float(log_df["energy_consumption_mj"].mean()),
        "simulated_computational_load_gateway": float(log_df["computational_load"].mean()),
        "percentage_data_processed_locally": float(log_df["local_processing_ratio"].mean() * 100.0),
        "percentage_data_transmitted_externally": float(log_df["external_transmission_ratio"].mean() * 100.0),
        "privacy_score": float(log_df["privacy_score"].mean()),
        "security_score": float(log_df["security_score"].mean()),
        "transparency_score": float(log_df["transparency_score"].mean()),
        "privacy_exposure_score": float(log_df["privacy_exposure_score"].mean()),
        "security_risk_score": float(log_df["security_risk_score"].mean()),
        "explainability_availability_flag": bool(log_df["explainability_available"].max()),
        "unauthorized_access_probability": float(log_df["unauthorized_access_probability"].mean()),
        "observed_unauthorized_access_rate": float(log_df["unauthorized_access"].mean()),
        "data_tampering_probability": float(log_df["data_tampering_probability"].mean()),
        "observed_data_tampering_rate": float(log_df["data_tampered"].mean()),
        "attack_propagation_risk": float(log_df["attack_propagation_risk"].mean()),
        "external_data_exposure_ratio": float(log_df["external_transmission_ratio"].mean()),
        "simulated_dete4cpes_overhead_ms": float(log_df["dete4cpes_overhead_ms"].mean()),
    }
    row.update(metric_variation(row, previous_results))
    return row


def metric_variation(row: Dict[str, object], previous_results: Optional[pd.DataFrame]) -> Dict[str, object]:
    variation = {
        "accuracy_delta_vs_previous_comparable": None,
        "latency_delta_vs_previous_comparable_ms": None,
        "privacy_score_delta_vs_previous_comparable": None,
        "security_score_delta_vs_previous_comparable": None,
        "transparency_delta_vs_previous_comparable": None,
    }
    if previous_results is None or previous_results.empty:
        return variation

    required = {
        "execution_mode",
        "number_workers",
        "simulation_duration",
        "sampling_frequency",
        "risk_detection_accuracy",
        "average_total_latency_ms",
        "privacy_score",
        "security_score",
        "transparency_score",
    }
    if not required.issubset(previous_results.columns):
        return variation

    comparable = previous_results[
        (previous_results["execution_mode"] == row["execution_mode"])
        & (previous_results["number_workers"] == row["number_workers"])
        & (previous_results["simulation_duration"] == row["simulation_duration"])
        & (previous_results["sampling_frequency"] == row["sampling_frequency"])
    ]
    if comparable.empty:
        return variation

    previous = comparable.iloc[-1]
    variation["accuracy_delta_vs_previous_comparable"] = float(
        row["risk_detection_accuracy"] - previous["risk_detection_accuracy"]
    )
    variation["latency_delta_vs_previous_comparable_ms"] = float(
        row["average_total_latency_ms"] - previous["average_total_latency_ms"]
    )
    variation["privacy_score_delta_vs_previous_comparable"] = float(
        row["privacy_score"] - previous["privacy_score"]
    )
    variation["security_score_delta_vs_previous_comparable"] = float(
        row["security_score"] - previous["security_score"]
    )
    variation["transparency_delta_vs_previous_comparable"] = float(
        row["transparency_score"] - previous["transparency_score"]
    )
    return variation


def load_previous_aggregate_results(aggregate_dir: Path) -> pd.DataFrame:
    frames = []
    if not aggregate_dir.exists():
        return pd.DataFrame()
    for path in sorted(aggregate_dir.glob("aggregate_*.csv")):
        try:
            frames.append(pd.read_csv(path))
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def compare_modes(results: pd.DataFrame, metrics: Iterable[str]) -> pd.DataFrame:
    if results.empty or "execution_mode" not in results.columns:
        return pd.DataFrame()
    available = [metric for metric in metrics if metric in results.columns]
    if not available:
        return pd.DataFrame()
    return results.groupby("execution_mode", as_index=False)[available].mean(numeric_only=True)
