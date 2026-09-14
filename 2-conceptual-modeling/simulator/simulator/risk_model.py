"""Interpretable fatigue and health-risk scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import SimulationConfig
from .sensors import SensorReading


def _scaled(value: float, low: float, high: float) -> float:
    return float(np.clip((value - low) / max(high - low, 1e-9), 0.0, 1.0))


@dataclass
class RiskDecision:
    risk_score: float
    generated_alert: bool
    recommendation: str
    effective_threshold: float


class RiskModel:
    """A compact white-box scoring function for repeatable experiments."""

    high_risk_areas = {"ICU", "Emergency", "Surgery"}

    def score(
        self,
        reading: SensorReading,
        context: Any,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> float:
        available = context.accessible_features

        hr_component = _scaled(reading.heart_rate, 85, 150) if "heart_rate" in available else 0.35
        temp_component = _scaled(reading.skin_temperature, 37.0, 39.6) if "skin_temperature" in available else 0.35
        spo2_component = _scaled(96.0 - reading.spo2, 0, 9) if "spo2" in available else 0.35
        accel_component = _scaled(reading.accelerometer_magnitude, 1.4, 4.2) if "accelerometer" in available else 0.20
        activity_component = reading.activity_level if "activity" in available else 0.45

        location_component = 0.0
        if "location" in available:
            area = reading.approximate_location.split("-R", maxsplit=1)[0].replace("-zone", "")
            location_component = 0.10 if area in self.high_risk_areas else 0.03

        risk = (
            0.24 * hr_component
            + 0.24 * temp_component
            + 0.22 * spo2_component
            + 0.18 * accel_component
            + 0.07 * activity_component
            + location_component
        )

        # Lower precision pulls scores toward the decision boundary and adds uncertainty.
        precision = float(np.clip(context.risk_precision * context.signal_quality, 0.35, 1.15))
        risk = 0.5 + (risk - 0.5) * precision
        if context.risk_score_noise_std > 0:
            risk += float(rng.normal(0, context.risk_score_noise_std))
        return float(np.clip(risk, 0.0, 1.0))

    def decide(
        self,
        reading: SensorReading,
        context: Any,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> RiskDecision:
        risk_score = self.score(reading, context, config, rng)
        effective_threshold = float(np.clip(config.risk_score_threshold + context.threshold_adjustment, 0.20, 0.95))
        generated_alert = risk_score >= effective_threshold

        if not generated_alert:
            recommendation = "none"
        elif reading.accelerometer_magnitude >= config.fall_accel_threshold:
            recommendation = "fall_detection_alert"
        elif reading.skin_temperature >= config.heat_temp_threshold:
            recommendation = "heat_stress_warning"
        elif risk_score >= config.supervisor_threshold:
            recommendation = "notify_supervisor"
        else:
            recommendation = "suggest_break"

        return RiskDecision(
            risk_score=risk_score,
            generated_alert=generated_alert,
            recommendation=recommendation,
            effective_threshold=effective_threshold,
        )
