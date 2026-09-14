import csv
import os
import subprocess
import time
import signal

# Algorithm selection via environment variable:
# ETHICAL_NAV_ALGO:
#   - "CATER" (preferred name for our approach)
#   - "GA" (legacy name, equivalent to CATER)
#   - "RS" (Random Search baseline)
raw_algo = os.environ.get("ETHICAL_NAV_ALGO", "GA").upper()

if raw_algo in ["GA", "CATER"]:
    ALGORITHM = "GA"
    ALGO_LABEL = "CATER"
elif raw_algo == "RS":
    ALGORITHM = "RS"
    ALGO_LABEL = "RS"
else:
    raise ValueError(f"Unknown algorithm '{raw_algo}'. Use CATER, GA, or RS.")

# classes for the genetic algorithm evaluation
from ethical_testing.ga_privacy import GAConfig, PrivacyGAProblemAdjacent, TraceableGeneticAlgorithm
from jmetal.algorithm.singleobjective.genetic_algorithm import GeneticAlgorithm
from jmetal.operator.crossover import SBXCrossover
from jmetal.operator.mutation import PolynomialMutation
from jmetal.operator.selection import BinaryTournamentSelection
from jmetal.util.termination_criterion import StoppingByEvaluations

def run_command(command):
    return subprocess.run(command, shell=True, capture_output=True, text=True)

def popen_command(command):
    return subprocess.Popen(command, shell=True, preexec_fn=os.setsid)

WS_ROOT = os.path.expanduser(
    "~/yelyzaveta/hunav_and_omni_base_ws"
)

# route definitions used by multiple modules
route_start_end = {
    "route_1": {
        "start": {"x": -0.1, "y": -0.35, "yaw": 0.0},
        "end": {"x": 1.75, "y": -8.6, "yaw": 4.5},
        "timeout": 25,
    },
    "route_2": {
        "start": {"x": -4.4, "y": -8.6, "yaw": 1.2},
        "end": {"x": 1.75, "y": -2.15, "yaw": 0.0},
        "timeout": 25,
    },
    "route_3": {
        "start": {"x": 5.8, "y": 2.1, "yaw": 3.15},
        "end": {"x": -0.1, "y": 6.8, "yaw": 2.5},
        "timeout": 25,
    },
    "route_4": {
        "start": {"x": -4.4, "y": 5.85, "yaw": -1.0},
        "end": {"x": -0.9, "y": -4.85, "yaw": -0.75},
        "timeout": 28,
    },
    "route_5": {
        "start": {"x": -3.8, "y": -6.75, "yaw": 1.5},
        "end": {"x": 1.75, "y": 1.3, "yaw": 1.5},
        "timeout": 35,
    },
}
def ensure_folder(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def save_search_summary(output_root, algorithm, route, num_evaluations, total_runtime_sec, best_duration, best_variables):
    ensure_folder(output_root)

    csv_path = os.path.join(output_root, "search_summary.csv")

    file_exists = os.path.exists(csv_path)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header once
        if not file_exists:
            writer.writerow([
                "algorithm",
                "route",
                "num_evaluations",
                "total_runtime_sec",
                "best_privacy_violation_duration",
                "best_variables"
            ])

        writer.writerow([
            ALGO_LABEL,
            route,
            num_evaluations,
            total_runtime_sec,
            best_duration,
            ";".join(map(str, best_variables))
        ])

    print(f"[ethical_hunav] summary appended to: {csv_path}")

def stop_process_tree(proc, timeout=5):
    if proc is None:
        return

    try:
        pgid = os.getpgid(proc.pid)
    except ProcessLookupError:
        return

    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=timeout)
        except Exception:
            pass

def gazebo_leftovers_exist():
    cmd = "pgrep -f 'gzserver|gzclient|gz sim|^gz$|rviz2|controller_manager' >/dev/null 2>&1"
    return subprocess.run(cmd, shell=True).returncode == 0

def cleanup_simulation(test_hunav_launch, ethical_process, max_rounds=3):
    stop_process_tree(ethical_process)
    stop_process_tree(test_hunav_launch)

    time.sleep(2)

    for _ in range(max_rounds):
        if not gazebo_leftovers_exist():
            break

        subprocess.run("pkill -TERM -f 'rviz2' || true", shell=True)
        subprocess.run("pkill -TERM -f 'gzclient' || true", shell=True)
        subprocess.run("pkill -TERM -f 'gzserver' || true", shell=True)
        subprocess.run("pkill -TERM -f 'gz sim' || true", shell=True)
        subprocess.run("pkill -TERM -f '^gz$' || true", shell=True)
        subprocess.run("pkill -TERM -f 'controller_manager' || true", shell=True)

        time.sleep(2)

        if not gazebo_leftovers_exist():
            break

        subprocess.run("pkill -KILL -f 'rviz2' || true", shell=True)
        subprocess.run("pkill -KILL -f 'gzclient' || true", shell=True)
        subprocess.run("pkill -KILL -f 'gzserver' || true", shell=True)
        subprocess.run("pkill -KILL -f 'gz sim' || true", shell=True)
        subprocess.run("pkill -KILL -f '^gz$' || true", shell=True)
        subprocess.run("pkill -KILL -f 'controller_manager' || true", shell=True)

        time.sleep(1)

def make_run_trace_dir(output_root, algorithm, route):
    trace_dir = os.path.join(output_root, "algorithm_trace", f"{algorithm}_{route}")
    ensure_folder(trace_dir)
    return trace_dir

def main():
    algo = ALGORITHM

    requirement = "privacy"
    route = "route_5"                                         # one of route_1..route_5
    population_size = 10                                      # must be even for SBXCrossover!!! GA only
    generations = 50                                          # GA only
    max_retries = 3                                           # both
    rs_samples = population_size * generations                # RS only

    output_root = os.path.join(WS_ROOT, "ethical_output")
    os.makedirs(output_root, exist_ok=True)

    cfg = GAConfig(route=route)

    if algo == "GA":
        trace_dir = make_run_trace_dir(output_root, "GA", route)

        problem = PrivacyGAProblemAdjacent(
            cfg,
            max_attempts=max_retries,
            trace_dir=trace_dir
        )

        algorithm = TraceableGeneticAlgorithm(
            problem=problem,
            population_size=population_size,
            offspring_population_size=population_size,
            selection=BinaryTournamentSelection(),
            crossover=SBXCrossover(probability=0.9, distribution_index=20),
            mutation=PolynomialMutation(
                probability=1.0 / problem.number_of_variables,
                distribution_index=20
            ),
            trace_logger=problem.trace_logger,
            termination_criterion=StoppingByEvaluations(max_evaluations=population_size * generations),
        )

        print(
            f"[ethical_hunav] starting {ALGO_LABEL} with fixed generation budget (no stagnation early stop): "
            f"target {generations} generations, pop={population_size}, max_attempts={max_retries}"
        )
        print(f"[ethical_hunav] trace logs will be saved to: {trace_dir}")

        start_time = time.time()
        algorithm.run()
        end_time = time.time()
        total_runtime = end_time - start_time

        best = algorithm.result()
        best_duration = -best.objectives[0]

        executed_generations = getattr(algorithm, "current_generation", None)
        num_evaluations = problem.eval_counter

        print(f"[ethical_hunav] {ALGO_LABEL} finished: best privacy_violation_duration = {best_duration:.3f} s")
        print(f"[ethical_hunav] best variables = {best.variables}")
        if executed_generations is not None:
            print(f"[ethical_hunav] generations executed: {executed_generations}")
        print(f"[ethical_hunav] total evaluations: {num_evaluations}")
        print(f"[ethical_hunav] total {ALGO_LABEL} runtime: {total_runtime:.2f} seconds")

        save_search_summary(
            output_root=output_root,
            algorithm="GA",
            route=route,
            num_evaluations=num_evaluations,
            total_runtime_sec=total_runtime,
            best_duration=best_duration,
            best_variables=best.variables,
        )

    elif algo == "RS":
        from ethical_testing.rs_privacy import random_search

        trace_dir = make_run_trace_dir(output_root, "RS", route)

        print(f"[ethical_hunav] starting random search: samples={rs_samples}, max_attempts={max_retries}")
        print(f"[ethical_hunav] trace logs will be saved to: {trace_dir}")

        start_time = time.time()

        best = random_search(
            cfg,
            sample_size=rs_samples,
            max_retries=max_retries,
            trace_dir=trace_dir
        )

        end_time = time.time()
        total_runtime = end_time - start_time

        best_duration = -best.objectives[0]

        print(f"[ethical_hunav] {ALGO_LABEL} finished: best privacy_violation_duration = {best_duration:.3f} s")
        print(f"[ethical_hunav] best variables = {best.variables}")
        print(f"[ethical_hunav] total evaluations: {rs_samples}")
        print(f"[ethical_hunav] total {ALGO_LABEL} runtime: {total_runtime:.2f} seconds")

        save_search_summary(
            output_root=output_root,
            algorithm="RS",
            route=route,
            num_evaluations=rs_samples,
            total_runtime_sec=total_runtime,
            best_duration=best_duration,
            best_variables=best.variables,
        )

    else:
        raise ValueError(f"unknown algorithm '{algo}', set ALGORITHM to 'GA' or 'RS'")

    return

if __name__ == "__main__":
    main()