"""Configuration models and DeTe4CPES design technique catalog."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

BASELINE_MODE = "Standard"
DETE4CPES_MODE = "DeTe4CPES"
DEST_LEVELS: List[str] = ["low", "medium", "high"]
DEST_LEVEL_DISPLAY: Dict[str, str] = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}

DEST_CATALOG: Dict[str, List[str]] = {
    "Privacy": [
        "data_obfuscation",
        "noise_injection",
        "encryption",
        "differential_privacy",
        "object_service_restrictions",
    ],
    "Security": [
        "transport_layer_security",
        "identity_management",
        "private_intranet",
        "secure_local_network",
        "decentralized_segmentation",
    ],
    "Transparency": [
        "virtual_objects",
        "partial_dependence_plot",
        "offline_preprocessor",
        "online_white_box_optimizer",
    ],
}

DEST_DISPLAY_NAMES: Dict[str, str] = {
    "data_obfuscation": "Data obfuscation",
    "noise_injection": "Noise injection",
    "encryption": "Encryption",
    "differential_privacy": "Differential privacy",
    "object_service_restrictions": "Object-related service restrictions",
    "transport_layer_security": "Transport Layer Security",
    "identity_management": "Identity management framework",
    "private_intranet": "Private intranet",
    "secure_local_network": "Secure local network connection",
    "decentralized_segmentation": "Decentralized segmentation",
    "virtual_objects": "Virtual objects",
    "partial_dependence_plot": "Partial dependence plot",
    "offline_preprocessor": "Offline pre-processor",
    "online_white_box_optimizer": "Online white-box optimizer",
}

DEST_DESCRIPTIONS: Dict[str, str] = {
    "data_obfuscation": "Reduces the precision of transmitted vital signs while preserving exact patient location.",
    "noise_injection": "Adds controlled physiological noise to reduce sensitive signal precision.",
    "encryption": "Protects transmitted data with extra latency and wearable energy cost.",
    "differential_privacy": "Adds privacy-preserving noise to transmitted values and risk precision.",
    "object_service_restrictions": "Limits which streams are externally available to reduce exposure.",
    "transport_layer_security": "Reduces tampering risk with communication overhead.",
    "identity_management": "Reduces unauthorized access probability with small processing overhead.",
    "private_intranet": "Moves more processing inside the hospital network and reduces external traffic.",
    "secure_local_network": "Stabilizes local communication and lowers packet loss.",
    "decentralized_segmentation": "Limits attack propagation across hospital areas.",
    "virtual_objects": "Adds explicit digital abstractions for monitored entities.",
    "partial_dependence_plot": "Adds simple feature sensitivity explanations for the risk score.",
    "offline_preprocessor": "Improves signal quality before risk scoring at the cost of latency.",
    "online_white_box_optimizer": "Adjusts risk thresholds with interpretable rules.",
}


def default_dest_switches(enabled: bool = True) -> Dict[str, bool]:
    """Return a switch map for every available DEST."""
    return {dest: enabled for dests in DEST_CATALOG.values() for dest in dests}


def default_dest_levels(level: str = "medium") -> Dict[str, str]:
    """Return a default level map for every available DEST."""
    return {dest: level for dests in DEST_CATALOG.values() for dest in dests}


def dest_category(dest_id: str) -> str:
    for category, dests in DEST_CATALOG.items():
        if dest_id in dests:
            return category
    return "Unknown"


@dataclass
class SimulationConfig:
    """All parameters needed to execute one experiment."""

    execution_mode: str = BASELINE_MODE
    number_workers: int = 20
    simulation_duration: int = 60
    sampling_frequency: int = 1
    repetitions: int = 1
    random_seed: int = 42

    risk_score_threshold: float = 0.65
    supervisor_threshold: float = 0.82
    fall_accel_threshold: float = 2.6
    heat_temp_threshold: float = 38.0

    sensor_noise_level: float = 0.05
    fall_probability: float = 0.006
    heat_stress_probability: float = 0.010
    high_fatigue_probability: float = 0.025
    packet_loss_probability: float = 0.04
    gateway_processing_capacity: int = 30

    enabled_dest: Dict[str, bool] = field(default_factory=default_dest_switches)
    dest_levels: Dict[str, str] = field(default_factory=default_dest_levels)
    dest_profile_overrides: Dict[str, Dict[str, Dict[str, float]]] = field(default_factory=dict)
    results_dir: Path = Path("results")

    @property
    def total_steps(self) -> int:
        return max(1, int(self.simulation_duration) * max(1, int(self.sampling_frequency)))

    @property
    def is_dete4cpes_enabled(self) -> bool:
        return self.execution_mode == DETE4CPES_MODE

    def active_dest_ids(self) -> List[str]:
        if not self.is_dete4cpes_enabled:
            return []
        return [dest for dest, enabled in self.enabled_dest.items() if enabled]

    def active_dest_display_names(self) -> List[str]:
        names = []
        for dest in self.active_dest_ids():
            name = DEST_DISPLAY_NAMES.get(dest, dest)
            if dest in {"encryption", "data_obfuscation"}:
                name = f"{name} ({DEST_LEVEL_DISPLAY[self.dest_level(dest)]})"
            names.append(name)
        return names

    def dest_level(self, dest_id: str) -> str:
        level = self.dest_levels.get(dest_id, "medium")
        return level if level in DEST_LEVELS else "medium"

    def covered_ethical_categories(self) -> List[str]:
        active = set(self.active_dest_ids())
        return [category for category, dests in DEST_CATALOG.items() if active.intersection(dests)]

    def validate(self) -> None:
        if self.execution_mode not in {BASELINE_MODE, DETE4CPES_MODE}:
            raise ValueError(f"Unknown execution mode: {self.execution_mode}")
        if self.number_workers < 1:
            raise ValueError("number_workers must be at least 1")
        if self.simulation_duration < 1:
            raise ValueError("simulation_duration must be at least 1")
        if self.sampling_frequency < 1:
            raise ValueError("sampling_frequency must be at least 1")
        if self.repetitions < 1:
            raise ValueError("repetitions must be at least 1")
        if self.gateway_processing_capacity < 1:
            raise ValueError("gateway_processing_capacity must be at least 1")
        for name in (
            "risk_score_threshold",
            "supervisor_threshold",
            "sensor_noise_level",
            "fall_probability",
            "heat_stress_probability",
            "high_fatigue_probability",
            "packet_loss_probability",
        ):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.risk_score_threshold > self.supervisor_threshold:
            raise ValueError("risk_score_threshold should not exceed supervisor_threshold")
        for dest_id, level in self.dest_levels.items():
            if level not in DEST_LEVELS:
                raise ValueError(f"Invalid DEST level for {dest_id}: {level}")
        for dest_id, levels in self.dest_profile_overrides.items():
            for level, values in levels.items():
                if level not in DEST_LEVELS:
                    raise ValueError(f"Invalid DEST customization level for {dest_id}: {level}")
                for name, value in values.items():
                    if name not in {"privacy_delta", "security_delta"}:
                        raise ValueError(f"Unknown DEST customization value for {dest_id}.{level}: {name}")
                    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                        raise ValueError(f"Invalid DEST customization value for {dest_id}.{level}.{name}: {value}")
