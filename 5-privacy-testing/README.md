# Privacy Testing

This directory contains the replication materials for **Chapter 6 — Verifying Ethical Concerns when Testing Cyber-Physical Systems** of the thesis.

The chapter investigates how privacy requirements can be operationalized and systematically assessed through simulation-based testing of robotic systems. In particular, it presents **CATER**, a search-based testing approach based on Genetic Algorithms (GAs), for generating test cases that expose privacy violations.

CATER is evaluated against **Random Search (RS)** as a baseline in a robotic simulation environment involving robot navigation, human agents, and restricted areas.

The chapter is based on the following publication:

Yelyzaveta Kurkchi, Hassan Sartaj, Catia Trubiani, and Shaukat Ali. *Search-Based Testing of Privacy Requirements: A Case Study in Robotic Systems*. In *Proceedings of the International Conference on Testing Software and Systems (ICTSS)*, Lecture Notes in Computer Science. Springer, 2026.

## Overview

This replication package provides the implementation and experimental setup used for simulation-based testing of privacy requirements in robotic navigation.

The proposed approach, **CATER**, uses a Genetic Algorithm to search for simulation configurations that are likely to expose privacy violations. It is compared with **Random Search (RS)** under the same simulation conditions.

The implementation extends the RVSG framework with:

* CATER, a GA-based search strategy for privacy-violation test generation;
* Random Search as a baseline;
* a fitness function measuring privacy-violation duration;
* scenario configurations for privacy-aware robotic navigation;
* generation of restricted areas;
* experimental logging and analysis support.

## Repository Structure

The main implementation is located under the original ROS 2 workspace structure, including the `src/ethical_testing/` package and the simulation resources required by the framework.

## Base Framework

This implementation extends the open-source **RVSG** framework:

[RVSG — Simula-COMPLEX](https://github.com/Simula-COMPLEX/RVSG)

The simulation environment also relies on:

* [TIAGo OMNI Base ROS 2 Simulation](https://github.com/pal-robotics/omni_base_simulation)
* [HuNavSim — Human Navigation Simulator](https://github.com/robotics-upo/hunav_sim)

The replication package adds the privacy-testing functionality required for the experiments reported in the thesis and related publication.

## Requirements

The experiments were developed using:

* Ubuntu 22.04;
* ROS 2 Humble;
* Gazebo;
* Python 3.10.

The main Python dependencies include:

```text
jmetalpy
numpy
pandas
matplotlib
scipy
notebook
```

## Setup

The project follows the setup procedure of the RVSG framework.

### 1. Set up RVSG and dependencies

Follow the official RVSG installation instructions:

https://github.com/Simula-COMPLEX/RVSG

Ensure that the required ROS 2, Gazebo, TIAGo OMNI, and HuNavSim dependencies are available.

### 2. Create the Python environment

Create the Conda environment with:

```bash
conda env create -f environment.yaml
```

### 3. Configure the maps

Copy the generated map resources to the PAL Robotics map directory:

```bash
cp -r generatedWorld /opt/ros/humble/share/pal_maps/maps
```

## Building the Workspace

Before running the experiments, execute:

```bash
export PATH=/usr/bin:$PATH

source /usr/share/gazebo/setup.sh

colcon build --symlink-install

source install/setup.bash
```

## Generating Restricted Areas

Restricted areas are used to operationalize privacy requirements within the robotic environment.

Generate the restricted-area configuration with:

```bash
python3 src/ethical_testing/ethical_testing/generate_restricted_yaml.py
```

## Running the Experiments

### CATER

Run the simulation using CATER with:

```bash
ETHICAL_NAV_ALGO=CATER ros2 run ethical_testing ethical_hunav
```

If `ETHICAL_NAV_ALGO` is not specified, CATER is used as the default testing approach.

Internally, some implementation or data files may still use the label `GA` for backward compatibility.

### Random Search

Run the same simulation using Random Search with:

```bash
ETHICAL_NAV_ALGO=RS ros2 run ethical_testing ethical_hunav
```

## Experimental Setup

The empirical evaluation compares CATER and Random Search in privacy-aware robotic navigation scenarios.

The experiments use:

* a single robot;
* human agents simulated through HuNavSim;
* predefined robot routes;
* restricted areas representing privacy-sensitive regions;
* scenario configurations that vary the conditions under which privacy violations may occur.

The main experimental comparison investigates:

* the effectiveness of CATER relative to Random Search in exposing privacy violations;
* the influence of scenario characteristics on testing effectiveness.

## Analysis

The analysis notebook is located at:

```text
src/ethical_testing/ethical_testing/analysis.ipynb
```

To reproduce the analysis, run:

```bash
jupyter notebook src/ethical_testing/ethical_testing/analysis.ipynb
```

The notebook processes the experimental outputs and supports reproduction of the analyses, tables, and figures reported in the study.

## Reproducibility Notes

The experiments use fixed random seeds where applicable.

However, the evaluation relies on robotic simulation and interactions with dynamic human agents. Therefore, small numerical differences may occur across machines or executions due to simulation nondeterminism.

The overall experimental trends are expected to remain consistent with the reported results.

## Main Replication Artifacts

The package provides:

* **Testing implementation**, including CATER and the Random Search baseline;
* **Privacy-aware simulation configurations**, including restricted-area generation;
* **Experimental outputs**, generated during the simulation runs;
* **Analysis material**, supporting reproduction of the reported empirical results.

Together, these artifacts support the reproduction and inspection of the privacy-aware search-based testing approach presented in Chapter 6.

## Related Publication

Yelyzaveta Kurkchi, Hassan Sartaj, Catia Trubiani, and Shaukat Ali. *Search-Based Testing of Privacy Requirements: A Case Study in Robotic Systems*. In *Proceedings of the International Conference on Testing Software and Systems (ICTSS)*, Lecture Notes in Computer Science. Springer, 2026.