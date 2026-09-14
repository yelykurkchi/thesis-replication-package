"""Synthetic sensor and event generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .config import SimulationConfig
from .worker import HOSPITAL_AREAS, HospitalWorker

EventType = Literal["none", "high_fatigue", "fall", "heat_stress"]
CRITICAL_EVENTS = {"high_fatigue", "fall", "heat_stress"}


@dataclass
class SensorReading:
    heart_rate: float
    skin_temperature: float
    spo2: float
    accelerometer_magnitude: float
    approximate_location: str
    activity_level: float

    def clone(self) -> "SensorReading":
        return SensorReading(
            heart_rate=self.heart_rate,
            skin_temperature=self.skin_temperature,
            spo2=self.spo2,
            accelerometer_magnitude=self.accelerometer_magnitude,
            approximate_location=self.approximate_location,
            activity_level=self.activity_level,
        )


def generate_event(
    worker: HospitalWorker,
    step: int,
    total_steps: int,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> EventType:
    fatigue = worker.fatigue_level(step, total_steps)
    activity_pressure = 0.7 + 0.6 * worker.base_activity

    fall_probability = config.fall_probability * activity_pressure * (0.7 + fatigue)
    heat_probability = config.heat_stress_probability * (0.75 + fatigue)
    fatigue_probability = config.high_fatigue_probability * (0.5 + fatigue)

    draw = rng.random()
    if draw < fall_probability:
        return "fall"
    if draw < fall_probability + heat_probability:
        return "heat_stress"
    if draw < fall_probability + heat_probability + fatigue_probability:
        return "high_fatigue"
    return "none"


def generate_sensor_reading(
    worker: HospitalWorker,
    step: int,
    total_steps: int,
    event_type: EventType,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> SensorReading:
    fatigue = worker.fatigue_level(step, total_steps)
    activity = float(np.clip(worker.base_activity + rng.normal(0, 0.12), 0.05, 1.0))

    if event_type == "fall":
        activity = float(np.clip(activity + rng.normal(0.20, 0.10), 0.05, 1.0))
    elif event_type == "high_fatigue":
        activity = float(np.clip(activity - rng.normal(0.12, 0.05), 0.02, 1.0))

    heart_rate = worker.base_heart_rate + 26 * activity + 22 * fatigue
    skin_temp = worker.base_skin_temp + 0.35 * activity + 0.65 * fatigue
    spo2 = worker.base_spo2 - 2.1 * fatigue - 0.5 * activity
    accel = abs(rng.normal(0.6 + 1.4 * activity, 0.35))

    if event_type == "fall":
        heart_rate += rng.normal(18, 5)
        accel = float(rng.uniform(3.0, 5.2))
        spo2 -= rng.uniform(0.5, 2.0)
    elif event_type == "heat_stress":
        heart_rate += rng.normal(16, 5)
        skin_temp += rng.uniform(1.0, 1.8)
        spo2 -= rng.uniform(0.2, 1.0)
    elif event_type == "high_fatigue":
        heart_rate += rng.normal(10, 4)
        skin_temp += rng.uniform(0.2, 0.7)
        spo2 -= rng.uniform(1.0, 2.8)

    noise = config.sensor_noise_level
    heart_rate += rng.normal(0, 8.0 * noise)
    skin_temp += rng.normal(0, 0.45 * noise)
    spo2 += rng.normal(0, 2.5 * noise)
    accel += rng.normal(0, 0.50 * noise)

    area = worker.home_area if rng.random() > 0.12 else str(rng.choice(HOSPITAL_AREAS))
    room = int(rng.integers(1, 16))
    location = f"{area}-R{room:02d}"

    return SensorReading(
        heart_rate=float(np.clip(heart_rate, 45, 190)),
        skin_temperature=float(np.clip(skin_temp, 34.5, 41.5)),
        spo2=float(np.clip(spo2, 82, 100)),
        accelerometer_magnitude=float(np.clip(accel, 0, 6.0)),
        approximate_location=location,
        activity_level=float(np.clip(activity, 0.0, 1.0)),
    )
