# Behavior Assessment

This directory contains the replication materials for **Chapter 5 — Assessing Human Perceptions of Cyber-Physical Systems Behavior** of the thesis.

The chapter investigates how people assess the ethical acceptability of Cyber-Physical System behavior through an empirical study involving self-driving car scenarios. The study examines participants' judgments of simulated driving behavior and analyzes the relationship between perceived safety and ethical acceptability.

The replication package includes the anonymized study data, analysis notebooks, survey material, CARLA simulation scripts, and recorded scenario videos used in the study.

The chapter is based on the following work:

*Human Perception of Ethics in Self-Driving Cars: An Empirical Study*

Yelyzaveta Kurkchi, Christian Birchler, Sebastiano Panichella, and Catia Trubiani. Submitted to *ACM Transactions on Software Engineering and Methodology*, August 2026.

## Repository Structure

```text
4-behavior-assessment/
├── analysis/
│   ├── analysis.ipynb
│   ├── preprocessing.ipynb
├── data/
│   ├── processed/
│   │   └── final_processed_data.csv
│   └── raw/
│   │   └── README.md
│   └── README.md
├── simulation/
│   ├── scripts/
│   ├── screencasts/
│   └── README.md
├── survey/
│   └── survey.pdf
└── README.md
```

## Study Data

The `data/` directory contains the data associated with the empirical study.

### `data/processed/`

This directory contains the processed and anonymized dataset used to reproduce the quantitative analyses reported in the study.

#### `final_processed_data.csv`

This file is the main dataset for reproducing the reported results.

It contains the processed and anonymized participant responses used by the analysis notebook.

### `data/raw/`

The raw participant data are not distributed in the replication package for privacy reasons.

The `README.md` in this directory documents the status of the unavailable raw data and explains the relationship between the raw responses and the processed anonymized dataset.

## Analysis

The `analysis/` directory contains the notebooks and dependencies used to process and analyze the study data.

### `analysis.ipynb`

This notebook reproduces the main quantitative analyses reported in the study using:

```text
../data/processed/final_processed_data.csv
```

It should be used as the primary entry point for reproducing the reported empirical results.

### `preprocessing.ipynb`

This notebook documents the preprocessing steps applied to the original participant responses before analysis.

The raw participant data required to execute the preprocessing notebook are not included in the replication package. The notebook is therefore provided for transparency rather than direct execution.

## Survey Material

The `survey/` directory contains the survey instrument used in the empirical study.

### `survey.pdf`

This file provides the questionnaire presented to participants, including the study questions associated with the evaluated self-driving car scenarios.

## Simulation Material

The `simulation/` directory contains the CARLA material used to construct the scenarios evaluated by participants.

### `scripts/`

This directory contains the scripts used to configure and execute the CARLA scenarios.

### `screencasts/`

This directory contains the recorded scenario videos presented to participants during the study.

Because CARLA executions can vary across environments and runs, these recordings should be treated as the **reference scenarios** for reproducing the participant-facing study material.

Additional details about the simulation setup are provided in:

```text
simulation/README.md
```

## Reproducing the Analysis

To reproduce the main empirical results, navigate to the `analysis/` directory:

```bash
cd 4-behavior-assessment/analysis
```

Then start Jupyter:

```bash
jupyter notebook
```

and open:

```text
analysis.ipynb
```

Run the notebook cells sequentially.

The notebook uses the anonymized dataset stored at:

```text
../data/processed/final_processed_data.csv
```

The raw participant data are not required to reproduce the reported analysis.

## Main Replication Artifacts

The package provides four main types of artifacts:

* **Anonymized study data**, supporting reproduction of the reported empirical analyses;
* **Analysis notebooks**, documenting preprocessing and reproducing the quantitative results;
* **Survey material**, providing the questionnaire administered to participants;
* **Simulation material**, including CARLA scripts and the recorded scenarios shown during the study.

Together, these artifacts support the reproduction and inspection of the study design, participant-facing material, and reported analyses while preserving participant privacy.

## Related Publication

Yelyzaveta Kurkchi, Christian Birchler, Sebastiano Panichella, and Catia Trubiani. *Human Perception of Ethics in Self-Driving Cars: An Empirical Study*. Submitted to *ACM Transactions on Software Engineering and Methodology*, August 2026.