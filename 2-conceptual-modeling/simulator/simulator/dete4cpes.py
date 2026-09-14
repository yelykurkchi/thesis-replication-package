"""Modular DeTe4CPES design technique effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set

import numpy as np

from .config import DEST_CATALOG, DEST_DISPLAY_NAMES, SimulationConfig
from .sensors import SensorReading


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return float(np.clip(value, low, high))


DATA_OBFUSCATION_PROFILES = {
    "low": {
        "privacy_delta": -0.07,
        "security_delta": 0.0,
        "risk_precision_delta": -0.02,
        "noise_scale": 0.35,
        "heart_rate_step": 5.0,
        "temperature_step": 0.1,
        "spo2_step": 1.0,
        "accelerometer_step": 0.25,
        "activity_step": 0.05,
        "summary": "vital signs rounded with minimal perturbation",
    },
    "medium": {
        "privacy_delta": -0.14,
        "security_delta": 0.0,
        "risk_precision_delta": -0.04,
        "noise_scale": 0.70,
        "heart_rate_step": 10.0,
        "temperature_step": 0.2,
        "spo2_step": 2.0,
        "accelerometer_step": 0.5,
        "activity_step": 0.10,
        "summary": "vital signs perturbed and rounded to clinical bands",
    },
    "high": {
        "privacy_delta": -0.21,
        "security_delta": 0.0,
        "risk_precision_delta": -0.07,
        "noise_scale": 1.05,
        "heart_rate_step": 15.0,
        "temperature_step": 0.4,
        "spo2_step": 3.0,
        "accelerometer_step": 0.75,
        "activity_step": 0.20,
        "summary": "vital signs strongly perturbed and coarsened",
    },
}

ENCRYPTION_PROFILES = {
    "low": {
        "privacy_delta": -0.07,
        "security_delta": -0.05,
        "latency_ms": 4.0,
        "energy_mj": 0.025,
    },
    "medium": {
        "privacy_delta": -0.13,
        "security_delta": -0.10,
        "latency_ms": 8.0,
        "energy_mj": 0.045,
    },
    "high": {
        "privacy_delta": -0.19,
        "security_delta": -0.15,
        "latency_ms": 12.0,
        "energy_mj": 0.070,
    },
}

CUSTOMIZABLE_PROFILE_FIELDS = {"privacy_delta", "security_delta"}


def _profile_with_overrides(
    dest_id: str,
    level: str,
    profiles: Dict[str, Dict[str, object]],
    config: SimulationConfig,
) -> Dict[str, object]:
    profile = dict(profiles[level])
    overrides = config.dest_profile_overrides.get(dest_id, {}).get(level, {})
    for key, value in overrides.items():
        if key in CUSTOMIZABLE_PROFILE_FIELDS and key in profile and isinstance(profile[key], (int, float)):
            profile[key] = float(value)
    return profile


def _quantize(value: float, step: float) -> float:
    return float(round(value / step) * step)


def _perturb_and_quantize(
    value: float,
    rng: np.random.Generator,
    noise_std: float,
    step: float,
    low: float,
    high: float,
) -> float:
    perturbed = value + float(rng.normal(0, noise_std))
    return float(np.clip(_quantize(perturbed, step), low, high))


@dataclass
class SimulationContext:
    reading: SensorReading
    transmitted_reading: SensorReading
    transmitted_fields: Set[str]
    accessible_features: Set[str]
    privacy_exposure_score: float
    security_risk_score: float
    transparency_score: float
    explainability_available: bool
    unauthorized_access_probability: float
    data_tampering_probability: float
    attack_propagation_risk: float
    packet_loss_probability: float
    local_processing_ratio: float
    external_transmission_ratio: float
    latency_variability: float = 1.0
    communication_latency_overhead_ms: float = 0.0
    processing_latency_overhead_ms: float = 0.0
    energy_overhead_mj: float = 0.0
    computational_load_overhead: float = 0.0
    risk_precision: float = 1.0
    signal_quality: float = 1.0
    risk_score_noise_std: float = 0.0
    threshold_adjustment: float = 0.0
    dete4cpes_overhead_ms: float = 0.0
    applied_effects: List[str] = field(default_factory=list)

    def add_effect(self, dest_id: str, summary: str) -> None:
        display = DEST_DISPLAY_NAMES.get(dest_id, dest_id)
        self.applied_effects.append(f"{display}: {summary}")

    def normalize(self) -> None:
        self.privacy_exposure_score = clamp(self.privacy_exposure_score)
        self.security_risk_score = clamp(self.security_risk_score)
        self.transparency_score = clamp(self.transparency_score)
        self.unauthorized_access_probability = clamp(self.unauthorized_access_probability)
        self.data_tampering_probability = clamp(self.data_tampering_probability)
        self.attack_propagation_risk = clamp(self.attack_propagation_risk)
        self.packet_loss_probability = clamp(self.packet_loss_probability)
        self.local_processing_ratio = clamp(self.local_processing_ratio)
        self.external_transmission_ratio = clamp(self.external_transmission_ratio)
        self.risk_precision = clamp(self.risk_precision, 0.45, 1.10)
        self.signal_quality = clamp(self.signal_quality, 0.45, 1.15)


def base_context(reading: SensorReading, config: SimulationConfig) -> SimulationContext:
    fields = {
        "heart_rate",
        "skin_temperature",
        "spo2",
        "accelerometer",
        "location",
        "activity",
    }
    return SimulationContext(
        reading=reading,
        transmitted_reading=reading.clone(),
        transmitted_fields=set(fields),
        accessible_features=set(fields),
        privacy_exposure_score=0.78,
        security_risk_score=0.58,
        transparency_score=0.18,
        explainability_available=False,
        unauthorized_access_probability=0.075,
        data_tampering_probability=0.055,
        attack_propagation_risk=0.52,
        packet_loss_probability=config.packet_loss_probability,
        local_processing_ratio=0.35,
        external_transmission_ratio=0.65,
    )


class DesignTechnique:
    dest_id: str = ""
    category: str = ""

    def apply(
        self,
        context: SimulationContext,
        config: SimulationConfig,
        rng: np.random.Generator,
    ) -> None:
        raise NotImplementedError


class DataObfuscation(DesignTechnique):
    dest_id = "data_obfuscation"
    category = "Privacy"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        level = config.dest_level(self.dest_id)
        profile = _profile_with_overrides(self.dest_id, level, DATA_OBFUSCATION_PROFILES, config)
        reading = context.transmitted_reading
        scale = profile["noise_scale"]
        reading.heart_rate = _perturb_and_quantize(
            reading.heart_rate,
            rng,
            noise_std=2.5 * scale,
            step=profile["heart_rate_step"],
            low=45,
            high=190,
        )
        reading.skin_temperature = _perturb_and_quantize(
            reading.skin_temperature,
            rng,
            noise_std=0.08 * scale,
            step=profile["temperature_step"],
            low=34.5,
            high=41.5,
        )
        reading.spo2 = _perturb_and_quantize(
            reading.spo2,
            rng,
            noise_std=0.45 * scale,
            step=profile["spo2_step"],
            low=82,
            high=100,
        )
        reading.accelerometer_magnitude = _perturb_and_quantize(
            reading.accelerometer_magnitude,
            rng,
            noise_std=0.18 * scale,
            step=profile["accelerometer_step"],
            low=0,
            high=6.0,
        )
        reading.activity_level = _perturb_and_quantize(
            reading.activity_level,
            rng,
            noise_std=0.04 * scale,
            step=profile["activity_step"],
            low=0.0,
            high=1.0,
        )
        context.privacy_exposure_score += profile["privacy_delta"]
        context.security_risk_score += profile["security_delta"]
        context.risk_precision += profile["risk_precision_delta"]
        context.add_effect(
            self.dest_id,
            (
                f"{level} obfuscation; {profile['summary']}; exact location preserved; "
                f"privacy exposure {profile['privacy_delta']:+.2f}; security risk {profile['security_delta']:+.2f}"
            ),
        )


class NoiseInjection(DesignTechnique):
    dest_id = "noise_injection"
    category = "Privacy"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        level = max(config.sensor_noise_level, 0.04)
        context.reading.heart_rate += float(rng.normal(0, 5.5 * level))
        context.reading.skin_temperature += float(rng.normal(0, 0.30 * level))
        context.reading.spo2 += float(rng.normal(0, 1.5 * level))
        context.reading.accelerometer_magnitude += float(rng.normal(0, 0.25 * level))
        context.privacy_exposure_score -= 0.11
        context.signal_quality -= min(0.12, 0.22 * level)
        context.risk_precision -= min(0.09, 0.18 * level)
        context.add_effect(self.dest_id, "added controlled signal noise; privacy exposure -0.11")


class Encryption(DesignTechnique):
    dest_id = "encryption"
    category = "Privacy"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        level = config.dest_level(self.dest_id)
        profile = _profile_with_overrides(self.dest_id, level, ENCRYPTION_PROFILES, config)
        context.privacy_exposure_score += profile["privacy_delta"]
        context.security_risk_score += profile["security_delta"]
        context.communication_latency_overhead_ms += profile["latency_ms"]
        context.energy_overhead_mj += profile["energy_mj"]
        context.dete4cpes_overhead_ms += profile["latency_ms"]
        context.add_effect(
            self.dest_id,
            (
                f"{level} encrypted payloads; latency +{profile['latency_ms']:.0f} ms; "
                f"energy +{profile['energy_mj']:.3f} mJ; privacy exposure {profile['privacy_delta']:+.2f}; "
                f"security risk {profile['security_delta']:+.2f}"
            ),
        )


class DifferentialPrivacy(DesignTechnique):
    dest_id = "differential_privacy"
    category = "Privacy"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.risk_score_noise_std += 0.025 + 0.02 * config.sensor_noise_level
        context.privacy_exposure_score -= 0.16
        context.risk_precision -= 0.05
        context.add_effect(self.dest_id, "added risk-score privacy noise; privacy exposure -0.16")


class ObjectServiceRestrictions(DesignTechnique):
    dest_id = "object_service_restrictions"
    category = "Privacy"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.transmitted_fields.discard("location")
        context.accessible_features.discard("location")
        context.external_transmission_ratio *= 0.62
        context.local_processing_ratio += 0.12
        context.privacy_exposure_score -= 0.15
        context.processing_latency_overhead_ms += 3.5
        context.dete4cpes_overhead_ms += 3.5
        context.risk_precision -= 0.035
        context.add_effect(self.dest_id, "restricted location stream; external data ratio reduced")


class TransportLayerSecurity(DesignTechnique):
    dest_id = "transport_layer_security"
    category = "Security"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.security_risk_score -= 0.13
        context.data_tampering_probability *= 0.25
        context.communication_latency_overhead_ms += 6.0
        context.energy_overhead_mj += 0.030
        context.dete4cpes_overhead_ms += 6.0
        context.add_effect(self.dest_id, "reduced tampering probability; latency +6 ms")


class IdentityManagement(DesignTechnique):
    dest_id = "identity_management"
    category = "Security"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.unauthorized_access_probability *= 0.35
        context.security_risk_score -= 0.11
        context.processing_latency_overhead_ms += 2.0
        context.dete4cpes_overhead_ms += 2.0
        context.add_effect(self.dest_id, "reduced unauthorized access probability; processing +2 ms")


class PrivateIntranet(DesignTechnique):
    dest_id = "private_intranet"
    category = "Security"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.local_processing_ratio += 0.28
        context.external_transmission_ratio *= 0.55
        context.security_risk_score -= 0.14
        context.packet_loss_probability *= 0.72
        context.computational_load_overhead += 0.10
        context.add_effect(self.dest_id, "shifted processing locally; external data and packet loss reduced")


class SecureLocalNetwork(DesignTechnique):
    dest_id = "secure_local_network"
    category = "Security"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.packet_loss_probability *= 0.60
        context.latency_variability *= 0.65
        context.security_risk_score -= 0.08
        context.local_processing_ratio += 0.05
        context.add_effect(self.dest_id, "lowered packet loss and latency variability")


class DecentralizedSegmentation(DesignTechnique):
    dest_id = "decentralized_segmentation"
    category = "Security"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.attack_propagation_risk *= 0.45
        context.security_risk_score -= 0.10
        context.processing_latency_overhead_ms += 4.0
        context.computational_load_overhead += 0.06
        context.dete4cpes_overhead_ms += 4.0
        context.add_effect(self.dest_id, "segmented communication zones; propagation risk reduced")


class VirtualObjects(DesignTechnique):
    dest_id = "virtual_objects"
    category = "Transparency"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.transparency_score += 0.16
        context.explainability_available = True
        context.processing_latency_overhead_ms += 1.5
        context.dete4cpes_overhead_ms += 1.5
        context.add_effect(self.dest_id, "sensor and actuator abstractions enabled")


class PartialDependencePlot(DesignTechnique):
    dest_id = "partial_dependence_plot"
    category = "Transparency"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.transparency_score += 0.20
        context.explainability_available = True
        context.processing_latency_overhead_ms += 4.5
        context.computational_load_overhead += 0.04
        context.dete4cpes_overhead_ms += 4.5
        context.add_effect(self.dest_id, "feature sensitivity explanation available")


class OfflinePreprocessor(DesignTechnique):
    dest_id = "offline_preprocessor"
    category = "Transparency"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        context.reading.heart_rate = float(np.clip(context.reading.heart_rate, 45, 185))
        context.reading.skin_temperature = float(np.clip(context.reading.skin_temperature, 35.0, 41.0))
        context.reading.spo2 = float(np.clip(context.reading.spo2, 84, 100))
        context.signal_quality += 0.10
        context.risk_precision += 0.045
        context.transparency_score += 0.09
        context.processing_latency_overhead_ms += 6.0
        context.dete4cpes_overhead_ms += 6.0
        context.add_effect(self.dest_id, "preprocessed signals; quality +0.10; latency +6 ms")


class OnlineWhiteBoxOptimizer(DesignTechnique):
    dest_id = "online_white_box_optimizer"
    category = "Transparency"

    def apply(self, context: SimulationContext, config: SimulationConfig, rng: np.random.Generator) -> None:
        high_risk_signal = (
            context.reading.skin_temperature >= config.heat_temp_threshold - 0.25
            or context.reading.accelerometer_magnitude >= config.fall_accel_threshold - 0.35
            or context.reading.spo2 <= 92.5
        )
        activity_artifact = (
            context.reading.activity_level > 0.78
            and context.reading.heart_rate > 110
            and context.reading.skin_temperature < config.heat_temp_threshold - 0.45
        )
        if high_risk_signal:
            context.threshold_adjustment -= 0.035
            summary = "lowered alert threshold for interpretable high-risk signal"
        elif activity_artifact:
            context.threshold_adjustment += 0.025
            summary = "raised alert threshold for activity artifact"
        else:
            summary = "kept threshold stable"
        context.transparency_score += 0.18
        context.explainability_available = True
        context.processing_latency_overhead_ms += 3.0
        context.dete4cpes_overhead_ms += 3.0
        context.add_effect(self.dest_id, summary)


DEST_REGISTRY: Dict[str, DesignTechnique] = {
    cls.dest_id: cls()
    for cls in [
        DataObfuscation,
        NoiseInjection,
        Encryption,
        DifferentialPrivacy,
        ObjectServiceRestrictions,
        TransportLayerSecurity,
        IdentityManagement,
        PrivateIntranet,
        SecureLocalNetwork,
        DecentralizedSegmentation,
        VirtualObjects,
        PartialDependencePlot,
        OfflinePreprocessor,
        OnlineWhiteBoxOptimizer,
    ]
}


def ordered_dest_ids(active_dest_ids: Iterable[str]) -> List[str]:
    active = set(active_dest_ids)
    ordered: List[str] = []
    for dests in DEST_CATALOG.values():
        ordered.extend([dest for dest in dests if dest in active])
    return ordered


def apply_enabled_dest(
    context: SimulationContext,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> SimulationContext:
    if not config.is_dete4cpes_enabled:
        return context
    for dest_id in ordered_dest_ids(config.active_dest_ids()):
        technique = DEST_REGISTRY.get(dest_id)
        if technique is not None:
            technique.apply(context, config, rng)
            context.normalize()
    return context
