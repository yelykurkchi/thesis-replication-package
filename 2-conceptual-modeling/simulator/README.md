# Patient Monitoring Simulator

This repository contains a lightweight Python prototype for a patient monitoring scenario. The simulator generates synthetic discrete-event traces for monitored patients, wearable sensor readings, emergency alerts, cloud-side processing, medical-staff decisions, and wearable actuator notifications.

The interface supports two execution modes:

- `Standard`: the scenario without DeTe4CPES design techniques.
- `DeTe4CPES`: the scenario with selected Design Techniques (DESTs).

The current prototype focuses on the privacy-related DESTs used in the paper evaluation: `Encryption` and `Data obfuscation`. The tool is intended as a repeatable experimental prototype, not as a clinical or production model.

## Project Structure

```text
.
  app.py
  run_paper_experiments.py
  simulator/
    config.py
    worker.py
    sensors.py
    risk_model.py
    communication.py
    dete4cpes.py
    metrics.py
    experiment_runner.py
  results/
  requirements.txt
  README.md
```

## Installation

Create and activate a Python environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the Web App

```bash
streamlit run app.py
```

If `streamlit` is not on your shell path, use:

```bash
.venv/bin/python -m streamlit run app.py
```

The app is served by default at:

```text
http://localhost:8501
```

## Simulation Parameters

The web interface exposes the main parameters used during interactive exploration:

- number of monitored patients;
- simulation duration in minutes;
- number of repetitions;
- emergency trigger threshold;
- execution mode: `Standard` or `DeTe4CPES`;
- selectable privacy DESTs: `Encryption` and `Data obfuscation`;
- DEST level: `Low`, `Medium`, or `High`;
- two editable numeric values for the selected Low, Medium, or High DEST profile: privacy exposure delta and security risk delta.

Other simulation parameters are defined in `simulator/config.py` to keep the interface compact.

When `DeTe4CPES` mode is selected, each enabled DEST keeps its own level selector. After choosing a level, the interface exposes only two editable values for that level: `Privacy exposure delta` and `Security risk delta`.

The selected level still controls the built-in technical behavior, such as encryption overhead or data-obfuscation strength. The editable deltas customize only how the selected level contributes to the ethical scores: negative values reduce exposure or risk and therefore increase the corresponding score.

## Implemented DESTs

### Encryption

`Encryption` transforms the transmitted sensor and actuator payloads before communication. In this prototype, the implementation uses Python standard-library JSON serialization and Base64 encoding to simulate encoded payloads with three levels: `enc-low`, `enc-medium`, and `enc-high`.

This is a simulation of the effect of encryption on transmitted data and overhead. It is not production-grade cryptography.

For each selected encryption level, the web interface lets the user customize the `Privacy exposure delta` and `Security risk delta` used by the ethical-score calculation.

### Data Obfuscation

`Data obfuscation` preserves the exact patient location, because the doctor needs it to reach the patient during the emergency. Instead, it protects personal and physiological information by:

- pseudonymizing the patient name with a SHA-256-based token;
- perturbing vital signs with controlled Gaussian noise;
- quantizing vital signs into broader value bands.

The obfuscated vital signs include:

- heart rate;
- skin temperature;
- SpO2;
- accelerometer magnitude;
- activity level.

The three levels control how aggressively the transmitted values are perturbed and quantized.

For each selected data-obfuscation level, the web interface lets the user customize the `Privacy exposure delta` and `Security risk delta` used by the ethical-score calculation.

## Generated CSV Files

Every experiment writes unique files, so previous results are not overwritten:

```text
results/<experiment_group>/aggregate/aggregate_EXP_<timestamp>_<suffix>.csv
results/<experiment_group>/logs/temporal_log_EXP_<timestamp>_<suffix>.csv
```

### Aggregate CSV

One row is produced per repetition. Main columns include:

- experiment metadata: `experiment_id`, `timestamp`, `execution_mode`, `run_id`, `seed`;
- configuration: `number_workers`, `simulation_duration`, `sampling_frequency`, thresholds, packet loss, processing capacity;
- DEST metadata: `active_dest_count`, `active_dest`, `covered_ethical_categories`;
- operational metrics: alerts, correct alerts, false positives, false negatives, accuracy, precision, recall, F1-score;
- CPS metrics: communication latency, processing latency, total latency, packet loss, energy, gateway load;
- ethical metrics: `privacy_score`, `security_score`, `transparency_score`.

All three ethical scores are in the interval `[0, 1]`, and higher values are better.

### Temporal Log CSV

One row is produced per patient per timestep. Main columns include:

- source data: `source_patient_name`, `source_heart_rate`, `source_skin_temperature`, `source_spo2`, `source_approximate_location`;
- transmitted or received data: `patient_name`, `heart_rate`, `skin_temperature`, `spo2`, `approximate_location`;
- payloads: `transmitted_sensor_payload`, `transmitted_actuator_payload`;
- DEST metadata: `encryption_level`, `data_obfuscation_level`, `sensor_payload_encrypted`;
- event and decision values: `simulated_event_type`, `risk_score`, `generated_alert`, `recommendation`;
- CPS values: latency, packet loss, energy, computational load;
- applied DeTe4CPES summary: `applied_dest_effects`, including the active privacy and security deltas.

## Replicating the Paper Experiments

The paper evaluation can be reproduced with:

```bash
.venv/bin/python run_paper_experiments.py \
  --repetitions 10 \
  --duration 60 \
  --seed 42 \
  --output-dir results/paper_experiments
```

This command runs:

- one `Standard` configuration;
- three `Encryption` configurations: Low, Medium, High;
- three `Data obfuscation` configurations: Low, Medium, High;
- nine combined configurations covering every `Encryption x Data obfuscation` level pair.

The summary is written to:

```text
results/paper_experiments/summary.csv
```

The command also creates the corresponding aggregate and temporal log CSV files under:

```text
results/paper_experiments/aggregate/
results/paper_experiments/logs/
```

## One-Month Simulation

To run the same evaluation over a one-month horizon, use `43,200` minutes:

```bash
.venv/bin/python run_paper_experiments.py \
  --repetitions 1 \
  --duration 43200 \
  --number-workers 5 \
  --seed 42 \
  --scenario-set standard-mm \
  --output-dir results/month_experiment
```

This runs a smaller one-month comparison between `Standard` and the Medium-Medium `Encryption + Data obfuscation` configuration. A full one-month matrix with all DEST combinations can produce very large temporal logs, so it is better to start with this targeted run and increase `--number-workers`, `--repetitions`, or `--scenario-set full` only if needed.

## Metric Meaning

- Critical event: any simulated event other than `none`, such as `high_fatigue`, `fall`, or `heat_stress`.
- Correct alerts: critical events that generated an alert, also reported as true positives.
- False positives: alerts generated when no critical event occurred.
- False negatives: critical events with no alert.
- True negatives: non-critical observations with no alert.
- Risk detection accuracy: `(true positives + true negatives) / all observations`.
- Precision: `true positives / all generated alerts`.
- Recall: `true positives / all critical events`.
- F1-score: harmonic mean of precision and recall.
- Privacy Score: mean timestep score computed as `1 - privacy_exposure_score`; higher is better. The editable `Privacy exposure delta` changes this score.
- Security Score: mean timestep score computed as `1 - security_risk_score`; higher is better. The editable `Security risk delta` changes this score.
- Transparency Score: mean timestep transparency score; higher is better.
