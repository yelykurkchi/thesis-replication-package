"""Communication, packet loss, latency, and gateway load models."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from .config import SimulationConfig
from .dete4cpes import SimulationContext
from .sensors import SensorReading


@dataclass
class CommunicationOutcome:
    communication_latency_ms: float
    processing_latency_ms: float
    packet_loss: bool
    energy_consumption_mj: float
    computational_load: float
    unauthorized_access: bool
    data_tampered: bool


def _serialize_payload(payload: Dict[str, object], encryption_level: Optional[str]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if encryption_level is None:
        return raw
    if encryption_level == "low":
        protected = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
    elif encryption_level == "high":
        first_pass = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
        protected = base64.urlsafe_b64encode(first_pass[::-1].encode("utf-8")).decode("ascii")
    else:
        protected = base64.urlsafe_b64encode(raw[::-1].encode("utf-8")).decode("ascii")
    return f"enc-{encryption_level}:{protected}"


def _deserialize_payload(payload_text: str) -> Dict[str, object]:
    raw = payload_text
    if payload_text.startswith("enc-low:"):
        raw = base64.urlsafe_b64decode(payload_text.removeprefix("enc-low:").encode("ascii")).decode("utf-8")
    elif payload_text.startswith("enc-medium:"):
        decoded = base64.urlsafe_b64decode(payload_text.removeprefix("enc-medium:").encode("ascii")).decode("utf-8")
        raw = decoded[::-1]
    elif payload_text.startswith("enc-high:"):
        decoded = base64.urlsafe_b64decode(payload_text.removeprefix("enc-high:").encode("ascii")).decode("utf-8")
        first_pass = decoded[::-1]
        raw = base64.urlsafe_b64decode(first_pass.encode("ascii")).decode("utf-8")
    loaded = json.loads(raw)
    return loaded if isinstance(loaded, dict) else {}


def build_sensor_payload(context: SimulationContext, encryption_level: Optional[str]) -> str:
    payload: Dict[str, object] = {}
    reading = context.transmitted_reading
    if "heart_rate" in context.transmitted_fields:
        payload["heart_rate"] = round(reading.heart_rate, 3)
    if "skin_temperature" in context.transmitted_fields:
        payload["skin_temperature"] = round(reading.skin_temperature, 3)
    if "spo2" in context.transmitted_fields:
        payload["spo2"] = round(reading.spo2, 3)
    if "accelerometer" in context.transmitted_fields:
        payload["accelerometer_magnitude"] = round(reading.accelerometer_magnitude, 3)
    if "location" in context.transmitted_fields:
        payload["approximate_location"] = reading.approximate_location
    if "activity" in context.transmitted_fields:
        payload["activity_level"] = round(reading.activity_level, 3)
    return _serialize_payload(payload, encryption_level)


def pseudonymize_patient_name(patient_name: str, patient_id: int, level: Optional[str]) -> str:
    if level is None:
        return patient_name
    digest_length = {"low": 4, "medium": 6, "high": 8}.get(level, 6)
    digest = hashlib.sha256(f"{patient_id}:{patient_name}".encode("utf-8")).hexdigest()[:digest_length].upper()
    return f"PAT-{digest}"


def reconstruct_sensor_reading(
    payload_text: str,
    context: SimulationContext,
) -> SensorReading:
    payload = _deserialize_payload(payload_text)
    reconstructed = context.transmitted_reading.clone()
    if "heart_rate" in payload:
        reconstructed.heart_rate = float(payload["heart_rate"])
    if "skin_temperature" in payload:
        reconstructed.skin_temperature = float(payload["skin_temperature"])
    if "spo2" in payload:
        reconstructed.spo2 = float(payload["spo2"])
    if "accelerometer_magnitude" in payload:
        reconstructed.accelerometer_magnitude = float(payload["accelerometer_magnitude"])
    if "approximate_location" in payload:
        reconstructed.approximate_location = str(payload["approximate_location"])
    if "activity_level" in payload:
        reconstructed.activity_level = float(payload["activity_level"])
    return reconstructed


def build_actuator_payload(
    recommendation: str,
    generated_alert: bool,
    encryption_level: Optional[str],
) -> str:
    payload = {
        "device_command": "notify_help_on_the_way" if generated_alert else "no_notification",
        "message": "Help is on the way" if generated_alert else "No action required",
        "recommendation": recommendation,
    }
    return _serialize_payload(payload, encryption_level)


def apply_tampering(reading: SensorReading, rng: np.random.Generator) -> SensorReading:
    tampered = reading.clone()
    tampered.heart_rate = float(np.clip(tampered.heart_rate + rng.normal(0, 12), 45, 190))
    tampered.skin_temperature = float(np.clip(tampered.skin_temperature + rng.normal(0, 0.8), 34.5, 41.5))
    tampered.spo2 = float(np.clip(tampered.spo2 + rng.normal(0, 3.5), 82, 100))
    tampered.accelerometer_magnitude = float(np.clip(tampered.accelerometer_magnitude + rng.normal(0, 0.8), 0, 6.0))
    return tampered


def simulate_communication(
    context: SimulationContext,
    config: SimulationConfig,
    rng: np.random.Generator,
    messages_in_timestep: int,
) -> CommunicationOutcome:
    variability = max(context.latency_variability, 0.05)
    base_latency = float(np.clip(rng.normal(36.0, 8.0 * variability), 4.0, 120.0))
    external_penalty = 18.0 * context.external_transmission_ratio
    communication_latency_ms = base_latency + external_penalty + context.communication_latency_overhead_ms

    packet_loss = bool(rng.random() < context.packet_loss_probability)
    unauthorized_access = bool(rng.random() < context.unauthorized_access_probability)
    data_tampered = bool(rng.random() < context.data_tampering_probability)

    field_factor = len(context.transmitted_fields) / 6.0
    energy_consumption_mj = (
        0.110
        + 0.060 * field_factor
        + 0.015 * context.external_transmission_ratio
        + context.energy_overhead_mj
    )

    capacity = max(config.gateway_processing_capacity, 1)
    queue_pressure = max(0.0, messages_in_timestep / capacity - 1.0)
    computational_load = min(
        1.5,
        (messages_in_timestep / capacity) * (1.0 + context.computational_load_overhead),
    )

    if packet_loss:
        processing_latency_ms = 0.0
    else:
        processing_latency_ms = (
            float(np.clip(rng.normal(12.0, 2.0), 3.0, 40.0))
            + queue_pressure * 28.0
            + 8.0 * context.local_processing_ratio
            + context.processing_latency_overhead_ms
        )

    return CommunicationOutcome(
        communication_latency_ms=float(max(0.0, communication_latency_ms)),
        processing_latency_ms=float(max(0.0, processing_latency_ms)),
        packet_loss=packet_loss,
        energy_consumption_mj=float(max(0.0, energy_consumption_mj)),
        computational_load=float(computational_load),
        unauthorized_access=unauthorized_access,
        data_tampered=data_tampered and not packet_loss,
    )
