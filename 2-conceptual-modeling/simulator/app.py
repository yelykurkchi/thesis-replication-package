"""Streamlit dashboard for the wearable DeTe4CPES simulator."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from simulator.config import (
    BASELINE_MODE,
    DETE4CPES_MODE,
    DEST_CATALOG,
    DEST_DESCRIPTIONS,
    DEST_DISPLAY_NAMES,
    DEST_LEVEL_DISPLAY,
    DEST_LEVELS,
    SimulationConfig,
    default_dest_levels,
    default_dest_switches,
)
from simulator.dete4cpes import DATA_OBFUSCATION_PROFILES, ENCRYPTION_PROFILES
from simulator.experiment_runner import ExperimentResult, run_experiment

PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"
AGGREGATE_DIR = RESULTS_DIR / "aggregate"

SCORE_DETAILS = {
    "privacy_score": {
        "label": "Privacy Score",
        "base": 0.22,
        "goal": "Lower is better",
        "adjustments": {
            "data_obfuscation": {"low": 0.07, "medium": 0.14, "high": 0.21},
            "noise_injection": 0.11,
            "encryption": {"low": 0.07, "medium": 0.13, "high": 0.19},
            "differential_privacy": 0.16,
            "object_service_restrictions": 0.15,
        },
    },
    "security_score": {
        "label": "Security Score",
        "base": 0.42,
        "goal": "Higher is better",
        "adjustments": {
            "encryption": {"low": 0.05, "medium": 0.10, "high": 0.15},
            "transport_layer_security": 0.13,
            "identity_management": 0.11,
            "private_intranet": 0.14,
            "secure_local_network": 0.08,
            "decentralized_segmentation": 0.10,
        },
    },
    "transparency_score": {
        "label": "Transparency Score",
        "base": 0.18,
        "goal": "Higher is better",
        "adjustments": {
            "virtual_objects": 0.16,
            "partial_dependence_plot": 0.20,
            "offline_preprocessor": 0.09,
            "online_white_box_optimizer": 0.18,
        },
    },
}

CUSTOMIZABLE_DEST_PROFILES = {
    "encryption": ENCRYPTION_PROFILES,
    "data_obfuscation": DATA_OBFUSCATION_PROFILES,
}
CUSTOMIZABLE_PROFILE_FIELDS = ("privacy_delta", "security_delta")

PROFILE_FIELD_LABELS = {
    "privacy_delta": "Privacy exposure delta",
    "security_delta": "Security risk delta",
}

PROFILE_FIELD_HELP = {
    "privacy_delta": "Negative values reduce privacy exposure and increase the Privacy Score.",
    "security_delta": "Negative values reduce security risk and increase the Security Score.",
}


def _numeric_profile_values(profile: Dict[str, object]) -> Dict[str, float]:
    return {
        key: float(profile.get(key, 0.0))
        for key in CUSTOMIZABLE_PROFILE_FIELDS
    }


def _default_dest_profile_overrides() -> Dict[str, Dict[str, Dict[str, float]]]:
    return {
        dest_id: {
            level: _numeric_profile_values(profile)
            for level, profile in profiles.items()
        }
        for dest_id, profiles in CUSTOMIZABLE_DEST_PROFILES.items()
    }


def _normalize_dest_profile_overrides(
    overrides: Dict[str, Dict[str, Dict[str, float]]],
) -> Dict[str, Dict[str, Dict[str, float]]]:
    normalized = _default_dest_profile_overrides()
    for dest_id, levels in overrides.items():
        if dest_id not in normalized:
            continue
        for level, values in levels.items():
            if level not in normalized[dest_id]:
                continue
            for key, value in values.items():
                if key in normalized[dest_id][level]:
                    normalized[dest_id][level][key] = float(value)
    return normalized


def _customized_profile(dest_id: str, level: str) -> Dict[str, float]:
    profiles = CUSTOMIZABLE_DEST_PROFILES.get(dest_id)
    if profiles is None or level not in profiles:
        return {}
    profile = _numeric_profile_values(profiles[level])
    overrides = st.session_state.get("dest_profile_overrides", {})
    profile.update(overrides.get(dest_id, {}).get(level, {}))
    return profile


def _score_adjustment(metric_key: str, dest_id: str, level: str, fallback: float) -> float:
    profile = _customized_profile(dest_id, level)
    if metric_key == "privacy_score" and "privacy_delta" in profile:
        return -float(profile["privacy_delta"])
    if metric_key == "security_score" and "security_delta" in profile:
        return -float(profile["security_delta"])
    return fallback


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _build_config(
    enabled_dest: Dict[str, bool],
    dest_levels: Dict[str, str],
    dest_profile_overrides: Dict[str, Dict[str, Dict[str, float]]],
) -> SimulationConfig:
    mode = st.session_state["execution_mode"]
    with st.sidebar:
        st.header("Simulation Parameters")
        number_workers = st.number_input("Monitored patients", min_value=1, max_value=500, value=20, step=1)
        simulation_duration = st.number_input("Simulation duration (minutes)", min_value=1, max_value=1440, value=60, step=5)
        repetitions = st.number_input("Repetitions", min_value=1, max_value=100, value=1, step=1)
        st.header("Emergency Rule")
        risk_score_threshold = st.slider("Emergency trigger threshold", 0.10, 0.95, 0.65, 0.01)

    return SimulationConfig(
        execution_mode=mode,
        number_workers=int(number_workers),
        simulation_duration=int(simulation_duration),
        repetitions=int(repetitions),
        risk_score_threshold=float(risk_score_threshold),
        enabled_dest=enabled_dest,
        dest_levels=dest_levels,
        dest_profile_overrides=dest_profile_overrides,
        results_dir=RESULTS_DIR,
    )


def _render_profile_customization(
    dest_id: str,
    level: str,
    dest_profile_overrides: Dict[str, Dict[str, Dict[str, float]]],
) -> None:
    profile = dest_profile_overrides[dest_id][level]
    level_label = DEST_LEVEL_DISPLAY[level]
    dest_label = DEST_DISPLAY_NAMES[dest_id]
    with st.expander(f"Customize {dest_label} {level_label} numbers", expanded=True):
        cols = st.columns(2)
        for index, (field_name, current_value) in enumerate(profile.items()):
            with cols[index % 2]:
                profile[field_name] = st.number_input(
                    PROFILE_FIELD_LABELS.get(field_name, field_name.replace("_", " ").title()),
                    value=float(current_value),
                    step=0.01,
                    format="%.3f",
                    key=f"dest_profile_{dest_id}_{level}_{field_name}",
                    help=PROFILE_FIELD_HELP.get(field_name),
                )


def _dest_panel() -> tuple[Dict[str, bool], Dict[str, str], Dict[str, Dict[str, Dict[str, float]]]]:
    st.subheader("DeTe4CPES")
    if "dest_switches" not in st.session_state:
        st.session_state["dest_switches"] = default_dest_switches(True)
    if "dest_levels" not in st.session_state:
        st.session_state["dest_levels"] = default_dest_levels("medium")
    if "dest_profile_overrides" not in st.session_state:
        st.session_state["dest_profile_overrides"] = _default_dest_profile_overrides()

    enabled_dest = dict(st.session_state["dest_switches"])
    dest_levels = dict(st.session_state["dest_levels"])
    dest_profile_overrides = _normalize_dest_profile_overrides(st.session_state["dest_profile_overrides"])

    cols = st.columns(3)
    for idx, (category, dest_ids) in enumerate(DEST_CATALOG.items()):
        with cols[idx]:
            st.markdown(f"**{category}**")
            ordered_dest_ids = list(dest_ids)
            if category == "Privacy":
                ordered_dest_ids = ["encryption", "data_obfuscation"] + [
                    dest_id for dest_id in dest_ids if dest_id not in {"encryption", "data_obfuscation"}
                ]

            for dest_id in ordered_dest_ids:
                is_editable = dest_id in {"encryption", "data_obfuscation"}
                if not is_editable:
                    enabled_dest[dest_id] = False
                enabled_dest[dest_id] = st.toggle(
                    DEST_DISPLAY_NAMES[dest_id],
                    value=enabled_dest.get(dest_id, False),
                    key=f"dest_{dest_id}",
                    help=DEST_DESCRIPTIONS[dest_id],
                    disabled=not is_editable,
                )
                if is_editable and enabled_dest[dest_id]:
                    current_level = dest_levels.get(dest_id, "medium")
                    dest_levels[dest_id] = st.selectbox(
                        f"{DEST_DISPLAY_NAMES[dest_id]} level",
                        DEST_LEVELS,
                        index=DEST_LEVELS.index(current_level) if current_level in DEST_LEVELS else 1,
                        key=f"dest_level_{dest_id}",
                        format_func=lambda level: DEST_LEVEL_DISPLAY[level],
                    )
                    _render_profile_customization(dest_id, dest_levels[dest_id], dest_profile_overrides)
    st.session_state["dest_switches"] = enabled_dest
    st.session_state["dest_levels"] = dest_levels
    st.session_state["dest_profile_overrides"] = dest_profile_overrides
    return enabled_dest, dest_levels, dest_profile_overrides


def _show_configuration(config: SimulationConfig) -> None:
    active = config.active_dest_display_names()
    data = {
        "Parameter": [
            "Execution mode",
            "Patients",
            "Duration",
            "Repetitions",
            "Emergency threshold",
            "Active DEST",
        ],
        "Value": [
            config.execution_mode,
            config.number_workers,
            config.simulation_duration,
            config.repetitions,
            config.risk_score_threshold,
            ", ".join(active) if active else "None",
        ],
    }
    st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)


def _format_report_location(location: str, patient_id: int, timestep: int) -> str:
    area = location.split("-R", maxsplit=1)[0].replace("-zone", "")
    x_coord = 10 + (patient_id * 7 + timestep * 3) % 90
    y_coord = 5 + (patient_id * 11 + timestep * 5) % 95
    return f"{area} coordinate ({x_coord}, {y_coord})"


def _compute_alert_level(risk_score: float, threshold: float, generated_alert: bool) -> str:
    if not generated_alert:
        return "Low"
    if risk_score >= min(0.95, threshold + 0.15):
        return "High"
    return "Medium"


def _build_fake_patient_reports(result: ExperimentResult, config: SimulationConfig) -> list[Dict[str, str]]:
    logs = result.temporal_log_df
    if logs.empty:
        return []

    alerted = logs.loc[logs["generated_alert"] == True].copy()
    source = alerted.sort_values(["timestep", "worker_id"]).reset_index(drop=True) if not alerted.empty else logs.sort_values(
        ["risk_score", "total_latency_ms"], ascending=[False, True]
    ).head(1)

    reports: list[Dict[str, str]] = []
    for report_number, (_, selected) in enumerate(source.iterrows(), start=1):
        risk_score = float(selected["risk_score"])
        generated_alert = bool(selected["generated_alert"])
        assistance_needed = bool(selected["is_critical_event"] or risk_score >= max(0.75, config.risk_score_threshold))
        medical_decision = "Assistance needed" if assistance_needed else "False positive"
        patient_notification = "Wearable notified: help is on the way" if assistance_needed else "Wearable notification not required"
        alert_level = _compute_alert_level(risk_score, config.risk_score_threshold, generated_alert)

        reports.append(
            {
                "report_number": f"{report_number}",
                "patient_id": f"P-{int(selected['worker_id']):03d}",
                "patient_name": str(selected.get("patient_name", f"P-{int(selected['worker_id']):03d}")),
                "timestamp": f"Timestep {int(selected['timestep'])} ({float(selected['time_minutes']):.1f} min)",
                "location": (
                    _format_report_location(
                        str(selected["approximate_location"]),
                        int(selected["worker_id"]),
                        int(selected["timestep"]),
                    )
                    if assistance_needed
                    else "-,-"
                ),
                "heart_rate": f"{float(selected['heart_rate']):.0f} bpm",
                "temperature": f"{float(selected['skin_temperature']):.1f} C",
                "spo2": f"{float(selected['spo2']):.0f}%",
                "risk_score": f"{risk_score:.2f}",
                "alert_status": "Generated" if generated_alert else "Not generated",
                "alert_level": alert_level,
                "medical_decision": medical_decision,
                "patient_notification": patient_notification,
                "doctor_note": (
                    "The doctor receives location and vital signs in advance and can plan the intervention before arrival."
                    if assistance_needed
                    else "The staff reviews the alert and closes the case without sending assistance."
                ),
            }
        )
    return reports


def _render_patient_report(report: Dict[str, str]) -> None:
    st.markdown(
        """
        <style>
        .report-shell {
            background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
            border: 1px solid #d6dde8;
            border-radius: 22px;
            padding: 24px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.10);
            margin-bottom: 18px;
        }
        .report-head {
            display: flex;
            justify-content: space-between;
            gap: 18px;
            align-items: flex-start;
            border-bottom: 1px solid #d6dde8;
            padding-bottom: 14px;
            margin-bottom: 16px;
        }
        .report-kicker {
            color: #b42318;
            font-size: 0.78rem;
            letter-spacing: 0.12em;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 0;
            line-height: 1.1;
        }
        .report-title {
            color: #101828;
            font-size: 1.55rem;
            font-weight: 700;
            line-height: 1.05;
            margin: 0 0 2px 0;
        }
        .report-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
            margin-bottom: 18px;
        }
        .report-panel {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid #dde3ea;
            border-radius: 16px;
            padding: 16px;
        }
        .report-label {
            color: #667085;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
            font-weight: 600;
        }
        .report-value {
            color: #101828;
            font-size: 1.05rem;
            font-weight: 650;
        }
        .report-vitals {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-bottom: 18px;
        }
        .report-vital {
            background: #ffffff;
            border: 1px solid #dde3ea;
            border-radius: 18px;
            padding: 18px 16px;
        }
        .report-vital-value {
            color: #0f172a;
            font-size: 1.35rem;
            font-weight: 700;
            margin-top: 4px;
        }
        .report-note {
            background: #fff;
            border-left: 5px solid #2563eb;
            border-radius: 14px;
            padding: 14px 16px;
            color: #334155;
        }
        @media (max-width: 900px) {
            .report-grid, .report-vitals {
                grid-template-columns: 1fr;
            }
            .report-head {
                flex-direction: column;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    report_html = f"""
    <section class="report-shell">
      <div class="report-head">
        <div>
          <div class="report-kicker">Facility Emergency Monitoring</div>
          <h3 class="report-title">Patient Emergency Report</h3>
        </div>
      </div>

      <div class="report-grid">
        <div class="report-panel">
          <div class="report-label">Patient Name</div>
          <div class="report-value">{report["patient_name"]}</div>
        </div>
        <div class="report-panel">
          <div class="report-label">Patient Coordinates</div>
          <div class="report-value">{report["location"]}</div>
        </div>
      </div>

      <div class="report-grid">
        <div class="report-panel">
          <div class="report-label">Medical Staff Decision</div>
          <div class="report-value">{report["medical_decision"]}</div>
        </div>
        <div class="report-panel">
          <div class="report-label">Patient ID</div>
          <div class="report-value">{report["patient_id"]}</div>
        </div>
      </div>

      <div class="report-vitals">
        <div class="report-vital">
          <div class="report-label">Heart Rate</div>
          <div class="report-vital-value">{report["heart_rate"]}</div>
        </div>
        <div class="report-vital">
          <div class="report-label">Skin Temperature</div>
          <div class="report-vital-value">{report["temperature"]}</div>
        </div>
        <div class="report-vital">
          <div class="report-label">SpO2</div>
          <div class="report-vital-value">{report["spo2"]}</div>
        </div>
      </div>

      <div class="report-grid">
        <div class="report-panel">
          <div class="report-label">Alert Status</div>
          <div class="report-value">{report["alert_status"]}</div>
        </div>
        <div class="report-panel">
          <div class="report-label">Risk Score</div>
          <div class="report-value">{report["risk_score"]}</div>
        </div>
      </div>

      <div class="report-note">
        <strong>Patient Notification:</strong> {report["patient_notification"]}<br/>
        <strong>Doctor Note:</strong> {report["doctor_note"]}
      </div>
    </section>
    """
    st.markdown(report_html, unsafe_allow_html=True)


def _goto_previous_report() -> None:
    current = int(st.session_state.get("report_index", 0))
    st.session_state["report_index"] = max(0, current - 1)


def _goto_next_report() -> None:
    current = int(st.session_state.get("report_index", 0))
    max_index = int(st.session_state.get("report_max_index", 0))
    st.session_state["report_index"] = min(max_index, current + 1)


def _show_fake_patient_reports(result: ExperimentResult, config: SimulationConfig) -> None:
    reports = _build_fake_patient_reports(result, config)
    if not reports:
        return

    report_ids = [f"{report['patient_id']}|{report['timestamp']}|{report['risk_score']}" for report in reports]
    if st.session_state.get("report_ids") != report_ids:
        st.session_state["report_ids"] = report_ids
        st.session_state["report_index"] = 0

    if "report_index" not in st.session_state:
        st.session_state["report_index"] = 0
    st.session_state["report_index"] = max(0, min(st.session_state["report_index"], len(reports) - 1))
    total_reports = len(reports)
    st.session_state["report_max_index"] = total_reports - 1

    st.subheader("Patient Emergency Reports")
    if total_reports > 1:
        nav_prev, nav_mid, nav_next = st.columns([1, 2, 1])
        with nav_prev:
            st.button(
                "Previous report",
                key="previous_report_button",
                disabled=st.session_state["report_index"] <= 0,
                use_container_width=True,
                on_click=_goto_previous_report,
            )
        with nav_next:
            st.button(
                "Next report",
                key="next_report_button",
                disabled=st.session_state["report_index"] >= total_reports - 1,
                use_container_width=True,
                on_click=_goto_next_report,
            )
        with nav_mid:
            current_report_number = st.session_state["report_index"] + 1
            st.markdown(
                f"<div style='text-align:center; color:#b42318; font-weight:700; padding-top:0.45rem;'>"
                f"Report {current_report_number} / {total_reports}</div>",
                unsafe_allow_html=True,
            )

    st.session_state["report_index"] = max(0, min(st.session_state["report_index"], total_reports - 1))
    _render_patient_report(reports[st.session_state["report_index"]])


def _score_breakdown(enabled_dest: Dict[str, bool]) -> pd.DataFrame:
    rows = []
    for metric_key, details in SCORE_DETAILS.items():
        total = details["base"]
        active_adjustments = []
        active_terms = []
        for dest_id, raw_delta in details["adjustments"].items():
            if enabled_dest.get(dest_id, False):
                if isinstance(raw_delta, dict):
                    level = st.session_state.get("dest_levels", {}).get(dest_id, "medium")
                    delta = _score_adjustment(metric_key, dest_id, level, raw_delta.get(level, raw_delta["medium"]))
                    label = f"{DEST_DISPLAY_NAMES[dest_id]} {DEST_LEVEL_DISPLAY[level]} ({delta:+.2f})"
                else:
                    delta = raw_delta
                    label = f"{DEST_DISPLAY_NAMES[dest_id]} ({delta:+.2f})"
                total += delta
                active_adjustments.append(label)
                active_terms.append(f"{delta:+.2f}")

        rows.append(
            {
                "Score": details["label"],
                "Base score": f"{details['base']:.2f}",
                "Active DEST contributions": ", ".join(active_adjustments) if active_adjustments else "None",
                "Formula": f"clamp({details['base']:.2f} {' '.join(active_terms) if active_terms else '+0.00'}, 0, 1)",
                "Preview": f"{_clamp(total):.2f}",
                "Interpretation": details["goal"],
            }
        )
    return pd.DataFrame(rows)


def _score_rules() -> pd.DataFrame:
    rows = []
    for metric_key, details in SCORE_DETAILS.items():
        rows.append(
            {
                "Score": details["label"],
                "DEST": "Baseline",
                "Effect": f"Starts from {details['base']:.2f}",
            }
        )
        for dest_id, delta in details["adjustments"].items():
            if isinstance(delta, dict):
                for level, level_delta in delta.items():
                    adjusted_delta = _score_adjustment(metric_key, dest_id, level, level_delta)
                    rows.append(
                        {
                            "Score": details["label"],
                            "DEST": f"{DEST_DISPLAY_NAMES[dest_id]} ({DEST_LEVEL_DISPLAY[level]})",
                            "Effect": f"{adjusted_delta:+.2f}",
                        }
                    )
            else:
                rows.append(
                    {
                        "Score": details["label"],
                        "DEST": DEST_DISPLAY_NAMES[dest_id],
                        "Effect": f"{delta:+.2f}",
                    }
                )
    return pd.DataFrame(rows)


def _show_score_method(enabled_dest: Dict[str, bool]) -> None:
    st.write(
        "Each timestep starts from a baseline score, applies the active DeTe4CPES adjustments, "
        "and then clamps the result to the `[0, 1]` range. The aggregate CSV stores the mean of those timestep scores."
    )
    st.code(
        "\n".join(
            [
                "privacy_score = clamp(0.22 + privacy_DEST_adjustments, 0, 1)",
                "security_score = clamp(0.42 + security_DEST_adjustments, 0, 1)",
                "transparency_score = clamp(0.18 + transparency_DEST_adjustments, 0, 1)",
            ]
        ),
        language="text",
    )
    st.dataframe(_score_breakdown(enabled_dest), hide_index=True, use_container_width=True)
    with st.expander("Detailed score contributions"):
        st.dataframe(_score_rules(), hide_index=True, use_container_width=True)


@st.dialog("How ethical scores are calculated", width="large")
def _show_scores_dialog(enabled_dest: Dict[str, bool]) -> None:
    _show_score_method(enabled_dest)


def _show_dashboard(result: ExperimentResult, config: SimulationConfig) -> None:
    aggregate = result.aggregate_df

    _show_fake_patient_reports(result, config)

    st.subheader("Aggregate Metrics")
    important = [
        "execution_mode",
        "run_id",
        "active_dest_count",
        "total_generated_alerts",
        "correct_alerts",
        "false_positives",
        "false_negatives",
        "risk_detection_accuracy",
        "precision",
        "recall",
        "f1_score",
        "average_total_latency_ms",
        "total_energy_consumption_mj",
        "privacy_score",
        "security_score",
        "transparency_score",
    ]
    st.dataframe(aggregate[[col for col in important if col in aggregate.columns]], use_container_width=True)
    st.caption(
        "The three ethical scores shown above are aggregate means computed from the timestep-level values generated during the simulation. Higher values are better."
    )


def main() -> None:
    st.set_page_config(page_title="Patient Emergency Monitoring Simulator", layout="wide")
    st.title("Patient Emergency Monitoring Simulator")

    st.radio(
        "",
        [BASELINE_MODE, DETE4CPES_MODE],
        key="execution_mode",
        horizontal=True,
        help="The app runs only the selected mode when you press the execution button.",
        label_visibility="collapsed",
    )

    enabled_dest = dict(st.session_state.get("dest_switches", default_dest_switches(True)))
    dest_levels = dict(st.session_state.get("dest_levels", default_dest_levels("medium")))
    dest_profile_overrides = _normalize_dest_profile_overrides(
        st.session_state.get("dest_profile_overrides", _default_dest_profile_overrides())
    )
    if st.session_state["execution_mode"] == DETE4CPES_MODE:
        enabled_dest, dest_levels, dest_profile_overrides = _dest_panel()
    config = _build_config(enabled_dest, dest_levels, dest_profile_overrides)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Current Configuration")
        _show_configuration(config)
    with right:
        st.subheader("Run Status")
        status_box = st.empty()
        progress = st.progress(0.0)
        run_col, download_col = st.columns([1, 1])
        with run_col:
            run_button = st.button("Run Selected Simulation", type="primary", use_container_width=True)
        with download_col:
            result_for_download = st.session_state.get("last_result")
            if result_for_download is not None:
                st.download_button(
                    "Download simulation CSV",
                    data=result_for_download.aggregate_path.read_bytes(),
                    file_name=result_for_download.aggregate_path.name,
                    mime="text/csv",
                    use_container_width=True,
                )

    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None

    if run_button:
        def progress_callback(done: int, total: int, message: str) -> None:
            progress.progress(done / max(total, 1))
            status_box.info(message)

        with st.spinner(f"Running {config.execution_mode}"):
            result = run_experiment(config, progress_callback=progress_callback)
        st.session_state["last_result"] = result
        st.session_state["report_index"] = 0
        status_box.success(f"Completed experiment {result.experiment_id}")

    result = st.session_state.get("last_result")
    if result is not None:
        _show_dashboard(result, config)

    footer_left, footer_right = st.columns([1, 1])
    with footer_left:
        open_scores = st.button("How ethical scores are calculated", use_container_width=True)
    if open_scores:
        _show_scores_dialog(enabled_dest)

if __name__ == "__main__":
    main()
