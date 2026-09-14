# Simulation scripts

This directory contains the scripts for the CARLA simulator and screencasts.
Each script represents one test case:

- `fp_ep.py`: functional pass, ethical pass
- `fp_ef.py`: functional pass, ethical fail
- `ff_ep.py`: functional fail, ethical pass
- `ff_ef.py`: functional fail, ethical fail

The scripts require a running CARLA server and the CARLA Python API. They were developed for scenarios in CARLA Town05.

NOTE: The scripts and the CARLA simulator do not behave deterministically and may be influenced by the host machine. To replicate the study material, use the recorded videos of the scenarios.