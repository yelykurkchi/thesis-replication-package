"""Experiment execution and CSV persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from uuid import uuid4

import pandas as pd

from .communication import (
    apply_tampering,
    build_actuator_payload,
    build_sensor_payload,
    pseudonymize_patient_name,
    reconstruct_sensor_reading,
    simulate_communication,
)
from .config import SimulationConfig
from .dete4cpes import apply_enabled_dest, base_context
from .metrics import load_previous_aggregate_results, summarize_run
from .risk_model import RiskDecision, RiskModel
from .sensors import CRITICAL_EVENTS, generate_event, generate_sensor_reading
from .worker import create_population

ProgressCallback = Callable[[int, int, str], None]


@dataclass
class ExperimentResult:
    experiment_id: str
    aggregate_df: pd.DataFrame
    temporal_log_df: pd.DataFrame
    aggregate_path: Path
    temporal_log_path: Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_results_dir(config: SimulationConfig) -> Path:
    results_dir = Path(config.results_dir)
    if not results_dir.is_absolute():
        results_dir = _project_root() / results_dir
    return results_dir


def _experiment_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"EXP_{stamp}_{uuid4().hex[:6]}"


def run_experiment(
    config: SimulationConfig,
    progress_callback: Optional[ProgressCallback] = None,
) -> ExperimentResult:
    """Run exactly the selected mode and persist unique aggregate/log CSV files."""
    config.validate()
    experiment_id = _experiment_id()
    timestamp = datetime.now().isoformat(timespec="seconds")
    results_dir = _resolve_results_dir(config)
    aggregate_dir = results_dir / "aggregate"
    log_dir = results_dir / "logs"
    aggregate_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    previous_results = load_previous_aggregate_results(aggregate_dir)
    aggregate_rows = []
    log_frames: List[pd.DataFrame] = []

    total_units = config.repetitions * config.total_steps
    completed_units = 0
    for repetition_index in range(config.repetitions):
        run_id = repetition_index + 1
        seed = config.random_seed + repetition_index
        if progress_callback:
            progress_callback(completed_units, total_units, f"Starting run {run_id}/{config.repetitions}")
        run_log, completed_units = _run_single(
            config=config,
            experiment_id=experiment_id,
            run_id=run_id,
            seed=seed,
            completed_units=completed_units,
            total_units=total_units,
            progress_callback=progress_callback,
        )
        log_frames.append(run_log)
        aggregate_rows.append(
            summarize_run(
                log_df=run_log,
                config=config,
                experiment_id=experiment_id,
                timestamp=timestamp,
                run_id=run_id,
                seed=seed,
                previous_results=previous_results,
            )
        )

    aggregate_df = pd.DataFrame(aggregate_rows)
    temporal_log_df = pd.concat(log_frames, ignore_index=True) if log_frames else pd.DataFrame()

    aggregate_path = aggregate_dir / f"aggregate_{experiment_id}.csv"
    temporal_log_path = log_dir / f"temporal_log_{experiment_id}.csv"
    aggregate_df.to_csv(aggregate_path, index=False)
    temporal_log_df.to_csv(temporal_log_path, index=False)

    if progress_callback:
        progress_callback(total_units, total_units, f"Saved {aggregate_path.name} and {temporal_log_path.name}")

    return ExperimentResult(
        experiment_id=experiment_id,
        aggregate_df=aggregate_df,
        temporal_log_df=temporal_log_df,
        aggregate_path=aggregate_path,
        temporal_log_path=temporal_log_path,
    )


def _run_single(
    config: SimulationConfig,
    experiment_id: str,
    run_id: int,
    seed: int,
    completed_units: int,
    total_units: int,
    progress_callback: Optional[ProgressCallback],
) -> Tuple[pd.DataFrame, int]:
    import numpy as np

    rng = np.random.default_rng(seed)
    workers = create_population(config.number_workers, rng)
    risk_model = RiskModel()
    rows = []

    for step in range(config.total_steps):
        for worker in workers:
            event_type = generate_event(worker, step, config.total_steps, config, rng)
            reading = generate_sensor_reading(worker, step, config.total_steps, event_type, config, rng)
            context = base_context(reading, config)
            context = apply_enabled_dest(context, config, rng)
            encryption_level = (
                config.dest_level("encryption")
                if config.is_dete4cpes_enabled and config.enabled_dest.get("encryption", False)
                else None
            )
            data_obfuscation_level = (
                config.dest_level("data_obfuscation")
                if config.is_dete4cpes_enabled and config.enabled_dest.get("data_obfuscation", False)
                else None
            )
            transmitted_patient_name = pseudonymize_patient_name(
                worker.patient_name,
                worker.worker_id,
                data_obfuscation_level,
            )
            sensor_payload_encrypted = encryption_level is not None
            transmitted_sensor_payload = build_sensor_payload(context, encryption_level=encryption_level)

            communication = simulate_communication(context, config, rng, len(workers))
            model_reading = reconstruct_sensor_reading(
                transmitted_sensor_payload,
                context,
            )
            if communication.data_tampered:
                model_reading = apply_tampering(model_reading, rng)

            if communication.packet_loss:
                decision = RiskDecision(
                    risk_score=0.0,
                    generated_alert=False,
                    recommendation="no_assessment_packet_loss",
                    effective_threshold=config.risk_score_threshold,
                )
            else:
                decision = risk_model.decide(model_reading, context, config, rng)
            actuator_payload_encrypted = sensor_payload_encrypted
            transmitted_actuator_payload = build_actuator_payload(
                decision.recommendation,
                decision.generated_alert,
                encryption_level=encryption_level,
            )

            total_latency = communication.communication_latency_ms + communication.processing_latency_ms
            is_critical = event_type in CRITICAL_EVENTS
            rows.append(
                {
                    "experiment_id": experiment_id,
                    "run_id": run_id,
                    "timestep": step,
                    "time_minutes": step / max(config.sampling_frequency, 1),
                    "worker_id": worker.worker_id,
                    "worker_role": worker.role,
                    "source_patient_name": worker.patient_name,
                    "patient_name": transmitted_patient_name,
                    "source_heart_rate": round(context.reading.heart_rate, 3),
                    "source_skin_temperature": round(context.reading.skin_temperature, 3),
                    "source_spo2": round(context.reading.spo2, 3),
                    "source_accelerometer_magnitude": round(context.reading.accelerometer_magnitude, 3),
                    "source_approximate_location": context.reading.approximate_location,
                    "source_activity_level": round(context.reading.activity_level, 3),
                    "heart_rate": round(model_reading.heart_rate, 3),
                    "skin_temperature": round(model_reading.skin_temperature, 3),
                    "spo2": round(model_reading.spo2, 3),
                    "accelerometer_magnitude": round(model_reading.accelerometer_magnitude, 3),
                    "approximate_location": model_reading.approximate_location,
                    "activity_level": round(model_reading.activity_level, 3),
                    "transmitted_sensor_payload": transmitted_sensor_payload,
                    "transmitted_actuator_payload": transmitted_actuator_payload,
                    "sensor_payload_encrypted": sensor_payload_encrypted,
                    "actuator_payload_encrypted": actuator_payload_encrypted,
                    "encryption_level": encryption_level or "none",
                    "data_obfuscation_level": data_obfuscation_level or "none",
                    "intercepted_sensor_payload": transmitted_sensor_payload if communication.unauthorized_access else "",
                    "intercepted_actuator_payload": transmitted_actuator_payload if communication.unauthorized_access else "",
                    "simulated_event_type": event_type,
                    "is_critical_event": is_critical,
                    "risk_score": round(decision.risk_score, 4),
                    "generated_alert": bool(decision.generated_alert),
                    "recommendation": decision.recommendation,
                    "effective_threshold": round(decision.effective_threshold, 4),
                    "communication_latency_ms": round(communication.communication_latency_ms, 3),
                    "processing_latency_ms": round(communication.processing_latency_ms, 3),
                    "total_latency_ms": round(total_latency, 3),
                    "packet_loss": bool(communication.packet_loss),
                    "energy_consumption_mj": round(communication.energy_consumption_mj, 5),
                    "computational_load": round(communication.computational_load, 5),
                    "local_processing_ratio": round(context.local_processing_ratio, 5),
                    "external_transmission_ratio": round(context.external_transmission_ratio, 5),
                    "privacy_score": round(1.0 - context.privacy_exposure_score, 5),
                    "security_score": round(1.0 - context.security_risk_score, 5),
                    "transparency_score": round(context.transparency_score, 5),
                    "privacy_exposure_score": round(context.privacy_exposure_score, 5),
                    "security_risk_score": round(context.security_risk_score, 5),
                    "explainability_available": bool(context.explainability_available),
                    "unauthorized_access_probability": round(context.unauthorized_access_probability, 5),
                    "unauthorized_access": bool(communication.unauthorized_access),
                    "data_tampering_probability": round(context.data_tampering_probability, 5),
                    "data_tampered": bool(communication.data_tampered),
                    "attack_propagation_risk": round(context.attack_propagation_risk, 5),
                    "dete4cpes_overhead_ms": round(context.dete4cpes_overhead_ms, 3),
                    "applied_dest_effects": "; ".join(context.applied_effects),
                }
            )

        completed_units += 1
        if progress_callback:
            progress_callback(
                completed_units,
                total_units,
                f"Run {run_id}/{config.repetitions}, timestep {step + 1}/{config.total_steps}",
            )

    return pd.DataFrame(rows), completed_units
