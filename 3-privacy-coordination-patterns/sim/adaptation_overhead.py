"""
Adaptation Overhead Tracking Module

Provides utilities to measure and report the computational overhead
of dynamic adaptation in the COORDINATE 2.0 simulator.
"""

import csv
import os
from typing import List, Dict


def log_overhead_statistics(
    adaptation_check_count: int,
    adaptation_switch_count: int,
    adaptation_overhead_total: float,
    adaptation_overhead_samples: List[Dict],
    wall_time: float,
    logfile: str
):
    """
    Log and save adaptation overhead statistics.
    
    Args:
        adaptation_check_count: Number of adaptation checks performed
        adaptation_switch_count: Number of architecture switches
        adaptation_overhead_total: Total wall-clock time spent on adaptation (seconds)
        adaptation_overhead_samples: List of individual overhead measurements
        wall_time: Total simulation wall time (seconds)
        logfile: Path to the main simulation log file
    """
    if adaptation_check_count == 0:
        return
    
    avg_overhead_ms = (adaptation_overhead_total / adaptation_check_count) * 1000
    overhead_percentage = (adaptation_overhead_total / wall_time) * 100
    
    print("\n" + "="*70)
    print("DYNAMIC ADAPTATION OVERHEAD STATISTICS")
    print("="*70)
    print(f"Total adaptation checks:     {adaptation_check_count}")
    print(f"Architecture switches:       {adaptation_switch_count}")
    print(f"Total overhead time:         {adaptation_overhead_total:.3f}s ({adaptation_overhead_total*1000:.2f}ms)")
    print(f"Average overhead per check:  {avg_overhead_ms:.2f}ms")
    print(f"Overhead as % of wall time:  {overhead_percentage:.3f}%")
    print(f"Total wall time:             {wall_time:.3f}s")
    print("="*70 + "\n")
    
    # Save detailed overhead data to CSV
    overhead_csv = logfile.replace('.csv', '_overhead.csv')
    try:
        with open(overhead_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'sim_time', 'total_overhead_ms', 'rtlola_query_ms',
                'scoring_ms', 'switched', 'latency'
            ])
            writer.writeheader()
            writer.writerows(adaptation_overhead_samples)
        print(f"[OVERHEAD] Detailed overhead data saved to: {os.path.basename(overhead_csv)}")
    except Exception as e:
        print(f"[WARNING] Could not save overhead CSV: {e}")


def calculate_overhead_metrics(adaptation_overhead_samples: List[Dict]) -> Dict:
    """
    Calculate statistical metrics from overhead samples.
    
    Args:
        adaptation_overhead_samples: List of overhead measurements
        
    Returns:
        Dictionary with min, max, mean, median overhead values
    """
    if not adaptation_overhead_samples:
        return {}
    
    total_overheads = [s['total_overhead_ms'] for s in adaptation_overhead_samples]
    rtlola_overheads = [s['rtlola_query_ms'] for s in adaptation_overhead_samples]
    scoring_overheads = [s['scoring_ms'] for s in adaptation_overhead_samples]
    
    return {
        'total_min_ms': min(total_overheads),
        'total_max_ms': max(total_overheads),
        'total_mean_ms': sum(total_overheads) / len(total_overheads),
        'rtlola_mean_ms': sum(rtlola_overheads) / len(rtlola_overheads),
        'scoring_mean_ms': sum(scoring_overheads) / len(scoring_overheads),
        'num_switches': sum(1 for s in adaptation_overhead_samples if s['switched'])
    }
