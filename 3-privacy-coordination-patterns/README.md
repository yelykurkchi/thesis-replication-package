# Privacy Coordination Patterns

This directory contains the replication materials for **Chapter 4 — Modeling Ethical Concerns when Designing Cyber-Physical Systems**, specifically the section **From Privacy Requirements to Design Strategies for Coordination**.

The section investigates how the operationalization of privacy requirements can influence the design and performance of coordination mechanisms in Cyber-Physical Systems (CPS). The study considers three alternative coordination strategies:

* **Centralized**;
* **Semi-Decentralized**;
* **Fully Decentralized**.

The experimental evaluation analyzes how privacy-related communication and computation overhead affects these coordination strategies under different workload conditions. The considered outcomes include delivery latency, success rate, expiration rate, and privacy-related communication overhead.

The study presented in this section is based on the work:

*Designing Cyber-Physical Systems by Privacy-based Coordination Patterns*

**Authors:** Yelyzaveta Kurkchi, Ivan Compagnucci, and Catia Trubiani

## Repository Structure

```text
3-privacy-coordination-patterns/
├── analysis/
│   └── privacy-plots.ipynb
├── configs/
├── data/
│   ├── literature/
│   │   └── privacy-software-architectures.xlsx
│   └── raw-logs/
├── results/
│   ├── plots/
│   ├── privacy_scenario_raw_runs.csv
│   ├── privacy_scenario_summary.csv
│   ├── privacy_scenario_winners.csv
│   └── privacy_scenario_report.md
├── sim/
├── run_privacy_scenario.py
├── run_privacy_scenario.sh
├── requirements.txt
└── README.md
```

## Experimental Scenario

The replication package contains a privacy-aware experimental campaign based on an indoor delivery scenario.

The experiments compare three coordination mechanisms:

* **Centralized (CE)**;
* **Semi-Decentralized (SD)**;
* **Fully Decentralized (FD)**.

Medium- and high-priority items are treated as privacy-sensitive. Processing these items introduces additional communication and computation overhead intended to represent the cost associated with privacy-preserving mechanisms.

The experiments vary two main factors:

* **Workload**: Low, Medium, and High;
* **Privacy overhead**: Low, Medium, and High.

Each combination is evaluated across the three coordination mechanisms.

## Experimental Configuration

The main fixed configuration of the experimental scenario is:

* topology: `mesh25`;
* number of agents: `12`;
* simulation time: `3600 s`;
* item importance probabilities: `[0.40, 0.35, 0.25]`;
* expiration times: `[900, 600, 420]`;
* base communication time: `0.03 s`;
* base computation time: `0.05 s`;
* repetitions per experimental condition: `5` by default.

The workload levels are defined through different item-spawning intervals:

* **Low Load**: `180 s`;
* **Medium Load**: `90 s`;
* **High Load**: `30 s`.

The privacy levels introduce increasing communication and computation overhead for privacy-sensitive items.

### Privacy Communication Overhead

* **Low**: `[0.0, 1.0, 2.0]`;
* **Medium**: `[0.0, 5.0, 10.0]`;
* **High**: `[0.0, 20.0, 40.0]`.

### Privacy Computation Overhead

* **Low**: `[0.0, 0.05, 0.10]`;
* **Medium**: `[0.0, 0.20, 0.50]`;
* **High**: `[0.0, 0.50, 1.00]`.

The first value corresponds to low-priority items, which are not treated as privacy-sensitive. Additional privacy overhead is applied to medium- and high-priority items.

## Experiment Runner

### `run_privacy_scenario.py`

This script is the main entry point for reproducing the experimental campaign.

It:

1. generates the configuration for each experimental condition;
2. executes the simulator for each coordination mechanism, workload level, privacy level, and repetition;
3. analyzes the generated simulation logs;
4. computes the experimental metrics;
5. aggregates the results;
6. identifies the best-performing coordination mechanism for selected metrics;
7. generates plots and a summary report.

### `run_privacy_scenario.sh`

This file provides a shell wrapper for executing the experiment runner.

## Running the Experiments

Install the required dependencies from the `3-privacy-coordination-patterns/` directory:

```bash
pip install -r requirements.txt
```

Run the complete experimental campaign with:

```bash
python3 run_privacy_scenario.py
```

or, equivalently:

```bash
./run_privacy_scenario.sh
```

The default experiment executes five repetitions for each combination of coordination mechanism, workload level, and privacy level.

The number of repetitions can be changed with:

```bash
python3 run_privacy_scenario.py --repetitions 3
```

Plot generation can be disabled with:

```bash
python3 run_privacy_scenario.py --skip-plots
```

and generation of the Markdown report can be disabled with:

```bash
python3 run_privacy_scenario.py --skip-report
```

## Configurations

The `configs/` directory contains the configuration files generated for individual experimental runs.

Each configuration specifies the coordination mechanism, workload, privacy overhead, simulator parameters, logging configuration, and output locations used for a particular run.

## Simulation Implementation

The `sim/` directory contains the simulator modules required to execute the experimental scenario.

The experiment runner invokes the simulator using the configurations generated for each experimental condition.

## Data

### `data/literature/`

This directory contains supporting material related to the analysis of privacy-aware software architectures and coordination strategies.

#### `literature-search-results.xlsx`

This workbook contains the literature material associated with the investigation of privacy-aware design strategies.

### `data/raw-logs/`

This directory contains the raw simulation logs generated for individual experimental runs.

Each run is stored separately according to its coordination mechanism, workload level, privacy level, and repetition.

These logs provide the raw data from which the experimental metrics are calculated.

## Results

The `results/` directory contains the aggregated results produced by the experimental campaign.

### `privacy_scenario_raw_runs.csv`

Contains one row for each individual experimental run, including the configuration and the calculated metrics.

### `privacy_scenario_summary.csv`

Contains the results aggregated by:

* workload level;
* privacy level;
* coordination mechanism.

The file reports average values for the experimental metrics across repetitions.

### `privacy_scenario_winners.csv`

Reports the best-performing coordination mechanism for each workload and privacy condition according to selected metrics, including:

* lowest average latency;
* highest success rate.

### `privacy_scenario_report.md`

Provides an automatically generated summary of the experimental campaign and its results.

### `results/plots/`

Contains the visualizations generated from the experimental results in PNG and PDF formats.

The plots include comparisons of:

* average delivery latency;
* delivery success rate;
* privacy-related communication overhead;
* item expiration rate.

## Analysis

### `analysis/privacy-plots.ipynb`

This Jupyter Notebook supports inspection and visualization of the aggregated experimental results.

It reads the generated summary files from `results/` and produces tables and plots comparing the three coordination mechanisms across workload and privacy-overhead levels.

The notebook uses the same experimental definitions and ordering as `run_privacy_scenario.py`.

## Metrics

The experimental campaign records and derives metrics including:

* number of created items;
* number of delivered items;
* number of expired items;
* number of failures and recoveries;
* number of privacy-sensitive items created and delivered;
* delivery success rate;
* expiration rate;
* average delivery latency;
* 95th-percentile delivery latency;
* estimated privacy-related communication burden.

These metrics are used to analyze the effects of privacy-related overhead on alternative coordination strategies.

## Main Replication Artifacts

The package provides four main types of artifacts:

* **Supporting literature data**, documenting the investigation of privacy-aware software architectures and coordination strategies;
* **Simulation implementation and configurations**, supporting the execution of the experimental scenario;
* **Raw and aggregated experimental data**, providing the results of individual runs and their summaries;
* **Analysis and visualizations**, supporting comparison of the Centralized, Semi-Decentralized, and Decentralized coordination mechanisms.

Together, these artifacts support the reproduction and inspection of the experimental evaluation of privacy-based coordination strategies.

## Related Publication

The work presented in this section is based on:

*Designing Cyber-Physical Systems by Privacy-based Coordination Patterns*

Yelyzaveta Kurkchi, Ivan Compagnucci, and Catia Trubiani.