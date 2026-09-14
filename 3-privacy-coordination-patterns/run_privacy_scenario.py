import csv
import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent

# Simulator package used by this replication package
PROJECT_ROOT = ROOT if (ROOT / "sim").exists() else ROOT.parent

# Experiment configuration
CONFIGS_DIR = ROOT / "configs"

# Generated data
DATA_DIR = ROOT / "data"
RAW_LOGS_DIR = DATA_DIR / "raw-logs"

# Processed results and figures
RESULTS_DIR = ROOT / "results"
PLOTS_DIR = RESULTS_DIR / "plots"
FIGSIZE = (3.0, 2.0)

for d in [CONFIGS_DIR, RAW_LOGS_DIR, RESULTS_DIR, PLOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

ARCHITECTURES = {
    'Centralized': 'centralized-impprox',
    'Semi-Decentralized': 'semi-decentralized',
    'Decentralized': 'decentralized',
}

WORKLOAD_LEVELS = {
    'Low Load': 180,
    'Medium Load': 90,
    'High Load': 30,
}

PRIVACY_LEVELS = {
    'Low Privacy Overhead': {
        'privacy_comm_bonus': [0.0, 1.00, 2.00],
        'privacy_comp_bonus': [0.0, 0.05, 0.10],
    },
    'Medium Privacy Overhead': {
        'privacy_comm_bonus': [0.0, 5.00, 10.00],
        'privacy_comp_bonus': [0.0, 0.20, 0.50],
    },
    'High Privacy Overhead': {
        'privacy_comm_bonus': [0.0, 20.00, 40.00],
        'privacy_comp_bonus': [0.0, 0.50, 1.00],
    },
}

DEFAULT_REPETITIONS = 5
SENSITIVE_IMPORTANCES = [1, 2]

BASE_CONFIG = {
    'SIM_TIME': 3600,
    'TOPOLOGY_NAME': 'mesh25',
    'N_ROOMS': 25,
    'SOURCE': 0,
    'TARGETS': -1,
    'ITEM_SPAWNING_DISTR': 'exponential',
    'ITEM_SPAWNING_TRACE': '_',
    'IMPORTANCE_PROBABILITIES': [0.40, 0.35, 0.25],
    'EXPIRATION_TIME': [900, 600, 420],
    'EXPIRATION_DISTR': ['deterministic', 'deterministic', 'deterministic'],
    'N_ROBOTS': 12,
    'N_MALICIOUS': 0,
    'MALICIOUS_FAKE_FAILURES': True,
    'FIND_ROUTE_STRATEGY': 'breadth',
    'FAIL_PROB': 0.02,
    'COMM_FAIL_PROB': 0.003,
    'LOAD_TIME': 1.0,
    'LOAD_DISTR': 'exponential',
    'LOAD_TRACE': '_',
    'MOVEMENT_TIME': 5.0,
    'MOVEMENT_DISTR': 'exponential',
    'MOVEMENT_TRACE': '_',
    'DROP_TIME': 1.0,
    'DROP_DISTR': 'exponential',
    'DROP_TRACE': '_',
    'COMP_TIME': 0.05,
    'COMP_DISTR': 'exponential',
    'COMP_TRACE': '_',
    'COMM_TIME': 0.03,
    'COMM_DISTR': 'exponential',
    'COMM_TRACE': '_',
    'RECOVERY_TIME': 300.0,
    'RECOVERY_DISTR': 'exponential',
    'RECOVERY_TRACE': '_',
    'PRIVACY_COMM_TIME_BONUS': [0.0, 0.0, 0.0],
    'PRIVACY_COMP_TIME_BONUS': [0.0, 0.0, 0.0],
    'LOG_ITEM': True,
    'LOG_DELIVERY': True,
    'LOG_LOAD': False,
    'LOG_DROP': False,
    'LOG_EXPIRE': True,
    'LOG_MOVE': False,
    'LOG_FAIL': True,
    'LOG_RECOVERY': True,
    'LOG_HELP': False,
    'LOG_FAKE': False,
    'LOG_RESCUE': False,
}


@dataclass
class RunMetrics:
    created: int
    delivered: int
    expired: int
    failed: int
    recovered: int
    sensitive_created: int
    sensitive_delivered: int
    success_rate: float
    expiration_rate: float
    avg_latency_s: float
    p95_latency_s: float
    privacy_comm_burden_s: float


def percentile(values, q):
    if not values:
        return 0.0
    values = sorted(values)
    if len(values) == 1:
        return float(values[0])
    idx = (len(values) - 1) * q
    lower = math.floor(idx)
    upper = math.ceil(idx)
    if lower == upper:
        return float(values[lower])
    frac = idx - lower
    return float(values[lower] * (1 - frac) + values[upper] * frac)


def architecture_privacy_weight(arch_label: str) -> float:
    if arch_label == 'Decentralized':
        return 0.0
    if arch_label == 'Semi-Decentralized':
        return 0.75
    return 1.0


def build_config(arch_label: str, workload_label: str, privacy_label: str, repetition: int) -> tuple[dict, Path]:
    cfg = dict(BASE_CONFIG)
    cfg['ARCHITECTURE'] = ARCHITECTURES[arch_label]
    cfg['ITEM_SPAWNING_TIME'] = WORKLOAD_LEVELS[workload_label]
    cfg['PRIVACY_COMM_TIME_BONUS'] = PRIVACY_LEVELS[privacy_label]['privacy_comm_bonus']
    cfg['PRIVACY_COMP_TIME_BONUS'] = PRIVACY_LEVELS[privacy_label]['privacy_comp_bonus']

    scenario_slug = f"{arch_label.lower().replace(' ', '_').replace('-', '_')}__{workload_label.lower().replace(' ', '_')}__{privacy_label.lower().replace(' ', '_')}__r{repetition}"
    run_dir = RAW_LOGS_DIR / scenario_slug
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg['RESULTS_DIR'] = str(run_dir)
    cfg['LOGFILE'] = str(run_dir / 'simulation_log.csv')
    cfg['SIMTIME_LOGFILE'] = str(run_dir / 'sim_time.csv')

    cfg_path = CONFIGS_DIR / f'{scenario_slug}.json'
    with cfg_path.open('w') as f:
        json.dump(cfg, f, indent=2)
    return cfg, cfg_path


def analyze_log(csv_path: Path, arch_label: str, privacy_label: str) -> RunMetrics:
    create_times = {}
    create_importance = {}
    latencies = []
    sensitive_created = 0
    sensitive_delivered = 0
    counts = {
        'create': 0,
        'deliver': 0,
        'expire': 0,
        'fail': 0,
        'recover': 0,
    }

    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            event = row['event']
            item_id = int(float(row['itemId']))
            item_imp = int(float(row['itemImportance']))
            sim_time = float(row['simTime'])

            if event in counts:
                counts[event] += 1

            if event == 'create':
                create_times[item_id] = sim_time
                create_importance[item_id] = item_imp
                if item_imp in SENSITIVE_IMPORTANCES:
                    sensitive_created += 1
            elif event == 'deliver' and item_id in create_times:
                latencies.append(sim_time - create_times[item_id])
                if create_importance.get(item_id) in SENSITIVE_IMPORTANCES:
                    sensitive_delivered += 1

    created = counts['create']
    delivered = counts['deliver']
    expired = counts['expire']
    success_rate = delivered / created if created else 0.0
    expiration_rate = expired / created if created else 0.0

    privacy_weight = architecture_privacy_weight(arch_label)
    comm_bonus = PRIVACY_LEVELS[privacy_label]['privacy_comm_bonus']
    avg_sensitive_bonus = mean(comm_bonus[i] for i in SENSITIVE_IMPORTANCES)
    privacy_comm_burden = sensitive_delivered * avg_sensitive_bonus * privacy_weight

    return RunMetrics(
        created=created,
        delivered=delivered,
        expired=expired,
        failed=counts['fail'],
        recovered=counts['recover'],
        sensitive_created=sensitive_created,
        sensitive_delivered=sensitive_delivered,
        success_rate=success_rate,
        expiration_rate=expiration_rate,
        avg_latency_s=mean(latencies) if latencies else 0.0,
        p95_latency_s=percentile(latencies, 0.95),
        privacy_comm_burden_s=privacy_comm_burden,
    )


def run_all(repetitions=DEFAULT_REPETITIONS, generate_plots=True, generate_report=True):
    records = []
    total_runs = len(ARCHITECTURES) * len(WORKLOAD_LEVELS) * len(PRIVACY_LEVELS) * repetitions
    run_idx = 0

    for workload_label in WORKLOAD_LEVELS:
        for privacy_label in PRIVACY_LEVELS:
            for arch_label in ARCHITECTURES:
                for repetition in range(1, repetitions + 1):
                    run_idx += 1
                    cfg, cfg_path = build_config(arch_label, workload_label, privacy_label, repetition)
                    print(f'[{run_idx}/{total_runs}] {arch_label} | {workload_label} | {privacy_label} | rep {repetition}')
                    result = subprocess.run(
                        [sys.executable, '-m', 'sim.simulator', str(cfg_path)],
                        cwd=PROJECT_ROOT,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        raise RuntimeError(f'Simulation failed for {cfg_path}: {result.stderr}')
                    metrics = analyze_log(Path(cfg['LOGFILE']), arch_label, privacy_label)
                    record = {
                        'architecture_label': arch_label,
                        'architecture': cfg['ARCHITECTURE'],
                        'workload_label': workload_label,
                        'privacy_label': privacy_label,
                        'repetition': repetition,
                        **metrics.__dict__,
                    }
                    records.append(record)

    raw_df = pd.DataFrame(records)
    raw_df.to_csv(RESULTS_DIR / 'privacy_scenario_raw_runs.csv', index=False)

    summary = raw_df.groupby(['workload_label', 'privacy_label', 'architecture_label'], as_index=False).agg(
        avg_created=('created', 'mean'),
        avg_delivered=('delivered', 'mean'),
        avg_expired=('expired', 'mean'),
        avg_failed=('failed', 'mean'),
        avg_recovered=('recovered', 'mean'),
        avg_sensitive_created=('sensitive_created', 'mean'),
        avg_sensitive_delivered=('sensitive_delivered', 'mean'),
        avg_success_rate=('success_rate', 'mean'),
        avg_expiration_rate=('expiration_rate', 'mean'),
        avg_latency_s=('avg_latency_s', 'mean'),
        p95_latency_s=('p95_latency_s', 'mean'),
        avg_privacy_comm_burden_s=('privacy_comm_burden_s', 'mean'),
    )
    summary.to_csv(RESULTS_DIR / 'privacy_scenario_summary.csv', index=False)

    winners_latency = summary.loc[summary.groupby(['workload_label', 'privacy_label'])['avg_latency_s'].idxmin()].copy()
    winners_latency['winner_metric'] = 'lowest_avg_latency'
    winners_success = summary.loc[summary.groupby(['workload_label', 'privacy_label'])['avg_success_rate'].idxmax()].copy()
    winners_success['winner_metric'] = 'highest_success_rate'
    winners = pd.concat([winners_latency, winners_success], ignore_index=True)
    winners.to_csv(RESULTS_DIR / 'privacy_scenario_winners.csv', index=False)

    if generate_plots:
        build_plots(summary)
    if generate_report:
        build_report(summary, winners, repetitions)


def build_plots(summary: pd.DataFrame):
    privacy_order = list(PRIVACY_LEVELS.keys())
    workload_order = list(WORKLOAD_LEVELS.keys())
    arch_order = list(ARCHITECTURES.keys())
    arch_labels = {
        'Centralized': 'CE',
        'Semi-Decentralized': 'SD',
        'Decentralized': 'FD',
    }
    colors = {
        'Decentralized': '#666666',
        'Semi-Decentralized': '#999999',
        'Centralized': '#b3b3b3',
    }
    hatches = {
        'Decentralized': '',
        'Semi-Decentralized': '',
        'Centralized': '',
    }
    privacy_tick_labels = ['Low', 'Medium', 'High']

    plot_specs = [
        ('avg_latency_s', 'Average Delivery Latency (s)', 'latency_by_privacy.png'),
        ('avg_success_rate', 'Delivery Success Rate', 'success_rate_by_privacy.png'),
        ('avg_privacy_comm_burden_s', 'Estimated Privacy Communication Burden (s)', 'privacy_burden_by_privacy.png'),
        ('avg_expiration_rate', 'Item Expiration Rate', 'expiration_rate_by_privacy.png'),
    ]

    for plot_idx, (metric, ylabel, filename) in enumerate(plot_specs):
        fig, axes = plt.subplots(1, len(workload_order), figsize=(FIGSIZE[0] * len(workload_order), FIGSIZE[1]), sharey=False)
        if len(workload_order) == 1:
            axes = [axes]
        for ax, workload in zip(axes, workload_order):
            subset = summary[summary['workload_label'] == workload].copy()
            x = range(len(privacy_order))
            width = 0.23
            ax.set_axisbelow(True)
            ax.grid(axis='y', linestyle=':', linewidth=0.5)
            for idx, arch in enumerate(arch_order):
                vals = []
                for privacy in privacy_order:
                    row = subset[(subset['privacy_label'] == privacy) & (subset['architecture_label'] == arch)]
                    vals.append(float(row[metric].iloc[0]))
                ax.bar(
                    [i + (idx - 1) * width for i in x],
                    vals,
                    width=width,
                    label=arch_labels[arch],
                    color=colors[arch],
                    hatch=hatches[arch],
                    edgecolor='black',
                    linewidth=0.4,
                )
            ax.set_title(workload)
            ax.set_xticks(list(x))
            ax.set_xticklabels(privacy_tick_labels)
            ax.set_xlabel('Privacy Overhead')
            ax.tick_params(axis='both', labelsize=8)
            if metric == 'avg_success_rate':
                ax.set_ylim(0.90, 1.00)
        axes[0].set_ylabel(ylabel)
        if plot_idx == 0:
            handles, labels = axes[0].get_legend_handles_labels()
            fig.legend(
                handles,
                labels,
                title='Coordination',
                loc='lower center',
                bbox_to_anchor=(0.5, 1.02),
                ncol=len(arch_order),
                frameon=False,
            )
        fig.tight_layout()
        fig.savefig(PLOTS_DIR / filename, dpi=200, bbox_inches='tight')
        fig.savefig(PLOTS_DIR / filename.replace('.png', '.pdf'), bbox_inches='tight')
        plt.close(fig)


def build_report(summary: pd.DataFrame, winners: pd.DataFrame, repetitions: int):
    def make_table(metric_col: str, value_fmt: str):
        lines = []
        for workload in WORKLOAD_LEVELS:
            lines.append(f'### {workload}')
            lines.append('')
            lines.append('| Privacy Level | Centralized | Semi-Decentralized | Decentralized |')
            lines.append('|---|---:|---:|---:|')
            for privacy in PRIVACY_LEVELS:
                row = summary[(summary['workload_label'] == workload) & (summary['privacy_label'] == privacy)]
                vals = []
                for arch in ARCHITECTURES:
                    value = row[row['architecture_label'] == arch][metric_col].iloc[0]
                    vals.append(value_fmt.format(value))
                lines.append(f'| {privacy} | {vals[0]} | {vals[1]} | {vals[2]} |')
            lines.append('')
        return '\n'.join(lines)

    winner_lines = []
    for workload in WORKLOAD_LEVELS:
        winner_lines.append(f'### {workload}')
        winner_lines.append('')
        winner_lines.append('| Privacy Level | Lowest Avg Latency | Highest Success Rate |')
        winner_lines.append('|---|---|---|')
        for privacy in PRIVACY_LEVELS:
            lat = winners[(winners['workload_label'] == workload) & (winners['privacy_label'] == privacy) & (winners['winner_metric'] == 'lowest_avg_latency')]['architecture_label'].iloc[0]
            suc = winners[(winners['workload_label'] == workload) & (winners['privacy_label'] == privacy) & (winners['winner_metric'] == 'highest_success_rate')]['architecture_label'].iloc[0]
            winner_lines.append(f'| {privacy} | {lat} | {suc} |')
        winner_lines.append('')

    report_md = f'''# Privacy Scenario Results

## Scenario Summary

This folder contains a privacy-aware comparison of the three coordination mechanisms already supported by the simulator:

- Centralized
- Semi-Decentralized
- Decentralized

The privacy scenario uses **selective communication overhead only for privacy-sensitive items**:

- Low-priority items: no extra privacy overhead
- Medium-priority items: extra privacy overhead
- High-priority items: higher privacy overhead

The campaign varies two dimensions:

- **Workload**: Low, Medium, High
- **Privacy Overhead**: Low, Medium, High

Each combination is repeated **{repetitions}** times.

## Fixed Configuration

- Topology: `mesh25`
- Agents: `12`
- Simulation window: `3600 s`
- Item importance probabilities: `[0.40, 0.35, 0.25]`
- Expiration times: `[900, 600, 420]`
- Base communication time: `0.03 s`
- Base computation time: `0.05 s`

## Interpretation Notes

This comparison uses the simulator's existing architectural trade-offs:

- centralized coordination benefits from stronger global coordination,
- decentralized coordination avoids communication overhead during assignment,
- semi-decentralized coordination sits between the two.

The privacy-specific extension added for this scenario affects only medium- and high-priority items by increasing communication and, slightly, computation overhead.

## Average Delivery Latency

{make_table('avg_latency_s', '{:.2f}')}

## Average Success Rate

{make_table('avg_success_rate', '{:.3f}')}

## Estimated Privacy Communication Burden

{make_table('avg_privacy_comm_burden_s', '{:.2f}')}

## Winners by Condition

{chr(10).join(winner_lines)}

## Files Produced

- `results/privacy_scenario_raw_runs.csv`: one row per run
- `results/privacy_scenario_summary.csv`: averaged summary by condition
- `results/privacy_scenario_winners.csv`: winner per condition and metric
- `results/plots/*.png`: comparison plots
- `results/plots/*.pdf`: PDF versions of the comparison plots

## Bottom Line

This scenario is designed to make the privacy trade-off visible without changing the simulator's default behavior outside this folder. It shows how higher privacy overhead can erode the advantage of coordination mechanisms that rely more on communication, while lower-information mechanisms can retain privacy benefits at the cost of coordination quality.
'''

    report_path = RESULTS_DIR / 'privacy_scenario_report.md'
    report_path.write_text(report_md)


def parse_args():
    parser = argparse.ArgumentParser(description='Run the standalone privacy scenario replication package.')
    parser.add_argument('--repetitions', type=int, default=DEFAULT_REPETITIONS, help='Number of repetitions per condition.')
    parser.add_argument('--skip-plots', action='store_true', help='Skip plot generation.')
    parser.add_argument('--skip-report', action='store_true', help='Skip markdown report generation.')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    run_all(
        repetitions=args.repetitions,
        generate_plots=not args.skip_plots,
        generate_report=not args.skip_report,
    )
