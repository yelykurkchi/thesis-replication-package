"""Synthetic hospital worker population."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

HOSPITAL_AREAS = [
    "ICU",
    "Emergency",
    "Surgery",
    "Ward-A",
    "Ward-B",
    "Radiology",
    "Pharmacy",
    "Laboratory",
]

ROLES = ["nurse", "physician", "technician", "porter", "cleaning_staff"]
PATIENT_FIRST_NAMES = [
    "Mary",
    "John",
    "Anne",
    "William",
    "Susan",
    "Charles",
    "Linda",
    "Robert",
    "Patricia",
    "James",
]
PATIENT_LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Miller",
    "Davis",
    "Wilson",
    "Anderson",
    "Taylor",
]


@dataclass
class HospitalWorker:
    worker_id: int
    patient_name: str
    role: str
    home_area: str
    base_heart_rate: float
    base_skin_temp: float
    base_spo2: float
    base_activity: float
    fatigue_sensitivity: float
    shift_phase: float

    def fatigue_level(self, step: int, total_steps: int) -> float:
        progress = step / max(total_steps - 1, 1)
        shift_curve = 0.25 + 0.75 * progress
        wave = 0.08 * np.sin(2 * np.pi * (progress + self.shift_phase))
        return float(np.clip((shift_curve + wave) * self.fatigue_sensitivity, 0.0, 1.0))


def create_population(number_workers: int, rng: np.random.Generator) -> List[HospitalWorker]:
    workers: List[HospitalWorker] = []
    for worker_id in range(1, number_workers + 1):
        role = str(rng.choice(ROLES))
        area = str(rng.choice(HOSPITAL_AREAS))
        patient_name = f"{PATIENT_FIRST_NAMES[(worker_id - 1) % len(PATIENT_FIRST_NAMES)]} {PATIENT_LAST_NAMES[(worker_id - 1) % len(PATIENT_LAST_NAMES)]}"
        workers.append(
            HospitalWorker(
                worker_id=worker_id,
                patient_name=patient_name,
                role=role,
                home_area=area,
                base_heart_rate=float(rng.normal(74, 7)),
                base_skin_temp=float(rng.normal(36.6, 0.25)),
                base_spo2=float(rng.normal(97.0, 1.0)),
                base_activity=float(np.clip(rng.normal(0.55, 0.18), 0.15, 0.95)),
                fatigue_sensitivity=float(np.clip(rng.normal(1.0, 0.20), 0.65, 1.45)),
                shift_phase=float(rng.random()),
            )
        )
    return workers
