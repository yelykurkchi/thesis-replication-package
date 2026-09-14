"""Run reproducible experiments for the patient-monitoring paper evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from simulator.config import (
    BASELINE_MODE,
    DETE4CPES_MODE,
    SimulationConfig,
    default_dest_levels,
    default_dest_switches,
)
from simulator.experiment_runner import run_experiment

LEVELS = ("low", "medium", "high")


def _switches(*enabled: str) -> dict[str, bool]:
    switches = default_dest_switches(False)
    for dest in enabled:
        switches[dest] = True
    return switches


def _levels(**levels: str) -> dict[str, str]:
    dest_levels = default_dest_levels("medium")
    dest_levels.update(levels)
    return dest_levels


def _scenario_config(
    mode: str,
    repetitions: int,
    duration: int,
    number_workers: int,
    seed: int,
    results_dir: Path,
    enabled_dest: dict[str, bool],
    dest_levels: dict[str, str],
) -> SimulationConfig:
    return SimulationConfig(
        execution_mode=mode,
        number_workers=number_workers,
        repetitions=repetitions,
        simulation_duration=duration,
        random_seed=seed,
        results_dir=results_dir,
        enabled_dest=enabled_dest,
        dest_levels=dest_levels,
    )


def build_scenarios(
    repetitions: int,
    duration: int,
    number_workers: int,
    seed: int,
    results_dir: Path,
    scenario_set: str,
):
    scenarios = [
        (
            "standard",
            "none",
            "none",
            _scenario_config(
                BASELINE_MODE,
                repetitions,
                duration,
                number_workers,
                seed,
                results_dir,
                _switches(),
                _levels(),
            ),
        )
    ]
    if scenario_set == "standard-mm":
        scenarios.append(
            (
                "combined_medium_medium",
                "medium",
                "medium",
                _scenario_config(
                    DETE4CPES_MODE,
                    repetitions,
                    duration,
                    number_workers,
                    seed,
                    results_dir,
                    _switches("encryption", "data_obfuscation"),
                    _levels(encryption="medium", data_obfuscation="medium"),
                ),
            )
        )
        return scenarios

    for level in LEVELS:
        scenarios.append(
            (
                f"encryption_{level}",
                level,
                "none",
                _scenario_config(
                    DETE4CPES_MODE,
                    repetitions,
                    duration,
                    number_workers,
                    seed,
                    results_dir,
                    _switches("encryption"),
                    _levels(encryption=level),
                ),
            )
        )

    for level in LEVELS:
        scenarios.append(
            (
                f"data_obfuscation_{level}",
                "none",
                level,
                _scenario_config(
                    DETE4CPES_MODE,
                    repetitions,
                    duration,
                    number_workers,
                    seed,
                    results_dir,
                    _switches("data_obfuscation"),
                    _levels(data_obfuscation=level),
                ),
            )
        )

    for encryption_level in LEVELS:
        for obfuscation_level in LEVELS:
            scenarios.append(
                (
                    f"combined_{encryption_level}_{obfuscation_level}",
                    encryption_level,
                    obfuscation_level,
                    _scenario_config(
                        DETE4CPES_MODE,
                        repetitions,
                        duration,
                        number_workers,
                        seed,
                        results_dir,
                        _switches("encryption", "data_obfuscation"),
                        _levels(encryption=encryption_level, data_obfuscation=obfuscation_level),
                    ),
                )
            )
    return scenarios


def run_suite(
    repetitions: int,
    duration: int,
    number_workers: int,
    seed: int,
    output_dir: Path,
    scenario_set: str,
) -> pd.DataFrame:
    rows = []
    for scenario, encryption_level, data_obfuscation_level, config in build_scenarios(
        repetitions,
        duration,
        number_workers,
        seed,
        output_dir,
        scenario_set,
    ):
        result = run_experiment(config)
        aggregate = result.aggregate_df
        log = result.temporal_log_df
        rows.append(
            {
                "scenario": scenario,
                "encryption_level": encryption_level,
                "data_obfuscation_level": data_obfuscation_level,
                "runs": repetitions,
                "duration_minutes": duration,
                "privacy_score_mean": aggregate["privacy_score"].mean(),
                "security_score_mean": aggregate["security_score"].mean(),
                "transparency_score_mean": aggregate["transparency_score"].mean(),
                "risk_detection_accuracy_mean": aggregate["risk_detection_accuracy"].mean(),
                "precision_mean": aggregate["precision"].mean(),
                "recall_mean": aggregate["recall"].mean(),
                "f1_score_mean": aggregate["f1_score"].mean(),
                "latency_mean_ms": aggregate["average_total_latency_ms"].mean(),
                "energy_total_mean_mj": aggregate["total_energy_consumption_mj"].mean(),
                "encrypted_payload_rate": log["sensor_payload_encrypted"].mean(),
                "name_pseudonymized_rate": (log["source_patient_name"] != log["patient_name"]).mean(),
                "location_changed_rate": (
                    log["source_approximate_location"] != log["approximate_location"]
                ).mean(),
                "vitals_changed_rate": (log["source_heart_rate"] != log["heart_rate"]).mean(),
                "aggregate_csv": str(result.aggregate_path),
                "temporal_log_csv": str(result.temporal_log_path),
            }
        )

    summary = pd.DataFrame(rows)
    standard = summary.loc[summary["scenario"] == "standard", "privacy_score_mean"].iloc[0]
    summary["privacy_score_delta_vs_standard"] = summary["privacy_score_mean"] - standard
    summary["privacy_score_gain_pct"] = (
        (summary["privacy_score_mean"] - standard) / standard * 100.0
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "summary.csv", index=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--duration", type=int, default=60, help="Simulation duration in minutes.")
    parser.add_argument("--number-workers", type=int, default=20, help="Number of monitored patients.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("results/paper_experiments"))
    parser.add_argument(
        "--scenario-set",
        choices=("full", "standard-mm"),
        default="full",
        help="Use 'standard-mm' for a smaller Standard vs Medium-Medium comparison.",
    )
    args = parser.parse_args()

    summary = run_suite(
        args.repetitions,
        args.duration,
        args.number_workers,
        args.seed,
        args.output_dir,
        args.scenario_set,
    )
    columns = [
        "scenario",
        "encryption_level",
        "data_obfuscation_level",
        "privacy_score_mean",
        "privacy_score_delta_vs_standard",
        "latency_mean_ms",
        "energy_total_mean_mj",
    ]
    print(summary[columns].to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"\nSaved summary to {args.output_dir / 'summary.csv'}")


if __name__ == "__main__":
    main()
