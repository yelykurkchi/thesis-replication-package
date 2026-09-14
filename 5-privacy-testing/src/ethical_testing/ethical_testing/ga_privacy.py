#!/usr/bin/env python3
import csv
import hashlib
import os
import signal
import subprocess
import time
import random
import shutil
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import yaml


from ethical_testing.config.waypoints import waypoints     

# jMetalPy
from jmetal.core.problem import Problem
from jmetal.core.solution import FloatSolution
from jmetal.algorithm.singleobjective.genetic_algorithm import GeneticAlgorithm
from jmetal.operator.crossover import SBXCrossover
from jmetal.operator.mutation import PolynomialMutation
from jmetal.operator.selection import BinaryTournamentSelection
from jmetal.util.termination_criterion import StoppingByEvaluations


WS_ROOT = os.path.expanduser("~/yelyzaveta/hunav_and_omni_base_ws")
HUNAV_TEST_REL = "src/hunav_sim/hunav_agent_manager/config/test.yaml"
OUTPUT_ROOT = os.path.join(WS_ROOT, "ethical_output")

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def vars_to_str(vars_: List[float]) -> str:
    return ";".join(f"{float(v):.6f}" for v in vars_)


class GATraceLogger:
    def __init__(self, trace_dir: str, prefix: str = "ga"):
        self.trace_dir = trace_dir
        self.prefix = prefix
        ensure_dir(trace_dir)

        self.evaluations_csv = os.path.join(trace_dir, f"{self.prefix}_evaluations.csv")
        self.selection_csv = os.path.join(trace_dir, f"{self.prefix}_selection.csv")
        self.generations_csv = os.path.join(trace_dir, f"{self.prefix}_generations.csv")

        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.evaluations_csv):
            with open(self.evaluations_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "eval_id",
                    "generation",
                    "source", # initial / offspring / cache
                    "solution_id",
                    "variables_hash",
                    "fitness",
                    "status",
                    "output_dir_exists",
                    "log_csv_exists",
                    "attempts_used",
                    "variables",
                    "decoded_start1",
                    "decoded_start2",
                    "decoded_steps1",
                    "decoded_steps2",
                    "goal_radius1",
                    "radius1",
                    "max_vel1",
                    "behavior_type1",
                    "goals1",
                    "goal_radius2",
                    "radius2",
                    "max_vel2",
                    "behavior_type2",
                    "goals2",
                ])

        if not os.path.exists(self.selection_csv):
            with open(self.selection_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "generation",
                    "selection_index",
                    "selected_solution_id",
                    "selected_fitness",
                    "selected_variables_hash",
                ])

        if not os.path.exists(self.generations_csv):
            with open(self.generations_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "generation",
                    "stage",                # population / survivors
                    "rank_in_population",
                    "solution_id",
                    "fitness",
                    "variables_hash",
                    "variables",
                ])

    def log_evaluation(
        self,
        eval_id: int,
        generation: int,
        source: str,
        solution_id: str,
        variables_hash: str,
        fitness: float,
        status: str,
        output_dir_exists: bool,
        log_csv_exists: bool,
        attempts_used: int,
        variables: List[float],
        decoded: Dict[str, object],
    ) -> None:
        with open(self.evaluations_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                eval_id,
                generation,
                source,
                solution_id,
                variables_hash,
                fitness,
                status,
                output_dir_exists,
                log_csv_exists,
                attempts_used,
                vars_to_str(variables),
                decoded["start1"],
                decoded["start2"],
                ";".join(map(str, decoded["steps1"])),
                ";".join(map(str, decoded["steps2"])),
                decoded["goal_radius1"],
                decoded["radius1"],
                decoded["max_vel1"],
                decoded["behavior_type1"],
                ";".join(decoded["goals1"]),
                decoded["goal_radius2"],
                decoded["radius2"],
                decoded["max_vel2"],
                decoded["behavior_type2"],
                ";".join(decoded["goals2"]),
            ])

    def log_selection(self, generation: int, mating_population: List[FloatSolution]) -> None:
        with open(self.selection_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for i, sol in enumerate(mating_population):
                duration = ""
                if sol.objectives:
                    duration = -sol.objectives[0]
                writer.writerow([
                    generation,
                    i,
                    sol.attributes.get("solution_id", ""),
                    duration,
                    sol.attributes.get("variables_hash", ""),
                ])

    def log_population(self, generation: int, stage: str, population: List[FloatSolution]) -> None:
        with open(self.generations_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for i, sol in enumerate(population):
                duration = ""
                if sol.objectives:
                    duration = -sol.objectives[0]
                writer.writerow([
                    generation,
                    stage,
                    i,
                    sol.attributes.get("solution_id", ""),
                    duration,
                    sol.attributes.get("variables_hash", ""),
                    vars_to_str(sol.variables),
                ])

class TraceableGeneticAlgorithm(GeneticAlgorithm):
    def __init__(
        self,
        *args,
        trace_logger: Optional[GATraceLogger] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.trace_logger = trace_logger
        self.current_generation = 0

    def stopping_condition_is_met(self):
        # use configured termination criterion from parent (e.g., StoppingByEvaluations)
        return super().stopping_condition_is_met()

    def init_progress(self) -> None:
        super().init_progress()
        self.current_generation = 0

        if hasattr(self.problem, "set_current_generation"):
            self.problem.set_current_generation(self.current_generation)

        if self.trace_logger is not None:
            self.trace_logger.log_population(
                generation=self.current_generation,
                stage="population",
                population=self.solutions,
            )

    def selection(self, population: List[FloatSolution]) -> List[FloatSolution]:
        if hasattr(self.problem, "set_current_generation"):
            self.problem.set_current_generation(self.current_generation)

        mating_population = super().selection(population)

        if self.trace_logger is not None:
            self.trace_logger.log_selection(
                generation=self.current_generation,
                mating_population=mating_population,
            )
        return mating_population

    def reproduction(self, mating_population: List[FloatSolution]) -> List[FloatSolution]:
        offspring_population = super().reproduction(mating_population)
        for sol in offspring_population:
            sol.attributes["source"] = "offspring"
            if hasattr(self.problem, "_next_solution_id"):
                sol.attributes["solution_id"] = self.problem._next_solution_id()
        return offspring_population

    def replacement(
        self,
        population: List[FloatSolution],
        offspring_population: List[FloatSolution]
    ) -> List[FloatSolution]:
        new_population = super().replacement(population, offspring_population)
        self.current_generation += 1

        if hasattr(self.problem, "set_current_generation"):
            self.problem.set_current_generation(self.current_generation)

        if self.trace_logger is not None:
            self.trace_logger.log_population(
                generation=self.current_generation,
                stage="survivors",
                population=new_population,
            )

        return new_population

def popen_cmd(cmd: str) -> subprocess.Popen:
    """Run a command in its own process group (so we can SIGTERM the whole group)."""
    return subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)


def kill_process_group(proc: subprocess.Popen, timeout: float = 10.0) -> None:
    if proc is None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=timeout)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass


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


def cleanup_simulation(sim_proc: subprocess.Popen, nav_proc: subprocess.Popen, max_rounds=3):
    # stop the processes similarly to ethical_hunav.py
    stop_process_tree(nav_proc)
    stop_process_tree(sim_proc)
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

def safe_float(x: float, lo: float, hi: float) -> float:
    return float(min(max(float(x), lo), hi))


def safe_int(x: float, lo: int, hi: int) -> int:
    v = int(round(float(x)))
    return max(lo, min(hi, v))


def euclid(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return (dx * dx + dy * dy) ** 0.5


@dataclass(frozen=True)
class GAConfig:
    route: str = "route_2"
    scenario_number: int = 0
    goals_per_human: int = 10

    # Bounds
    goal_radius_min: float = 0.1
    goal_radius_max: float = 1.0
    radius_min: float = 0.2
    radius_max: float = 0.6
    max_vel_min: float = 0.2
    max_vel_max: float = 1.5

    behavior_type_min: int = 1
    behavior_type_max: int = 6

    # Adjacency encoding
    max_neighbors: int = 8
    neighbor_threshold_factor: float = 1.25

    # Evaluation control (40s typical run; leave buffer)
    startup_wait_sec: float = 15.0    # mirrors ethical_hunav.py :contentReference[oaicite:6]{index=6}
    hard_timeout_sec: float = 120.0   # kill if send_goal_and_log hangs


class WaypointAdjacency:
    def __init__(self, cfg: GAConfig):
        self.cfg = cfg
        self.wp_keys: List[str] = sorted(list(waypoints.keys()))
        self.xy: List[Tuple[float, float]] = [
            (float(waypoints[k]["x"]), float(waypoints[k]["y"])) for k in self.wp_keys
        ]
        self.n = len(self.wp_keys)
        self.threshold = self._compute_threshold()
        self.neighbors: List[List[int]] = self._compute_neighbors()

    def _compute_threshold(self) -> float:
        # nearest neighbor distance for each waypoint
        nnd: List[float] = []
        for i in range(self.n):
            best = None
            for j in range(self.n):
                if i == j:
                    continue
                d = euclid(self.xy[i], self.xy[j])
                if best is None or d < best:
                    best = d
            if best is not None:
                nnd.append(best)
        nnd.sort()
        if not nnd:
            return 0.0
        mid = len(nnd) // 2
        median = nnd[mid] if len(nnd) % 2 == 1 else 0.5 * (nnd[mid - 1] + nnd[mid])
        return self.cfg.neighbor_threshold_factor * median

    def _compute_neighbors(self) -> List[List[int]]:
        neighbors: List[List[int]] = []
        for i in range(self.n):
            dist_list: List[Tuple[float, int]] = []
            for j in range(self.n):
                if i == j:
                    continue
                d = euclid(self.xy[i], self.xy[j])
                if d <= self.threshold:
                    dist_list.append((d, j))

            dist_list.sort(key=lambda x: x[0])
            # cap
            neigh = [j for _, j in dist_list[: self.cfg.max_neighbors]]

            # safety: ensure at least one neighbor (fallback to closest overall)
            if not neigh:
                closest = sorted(
                    [(euclid(self.xy[i], self.xy[j]), j) for j in range(self.n) if j != i],
                    key=lambda x: x[0],
                )
                neigh = [closest[0][1]] if closest else []

            neighbors.append(neigh)
        return neighbors

    def idx_to_xy(self, idx: int) -> Tuple[float, float]:
        return self.xy[idx]

    def idx_to_key(self, idx: int) -> str:
        return self.wp_keys[idx]


class HunavYamlWriter:
    def __init__(self, cfg: GAConfig, adj: WaypointAdjacency):
        self.cfg = cfg
        self.adj = adj

    def _walk_goals(self, start_idx: int, step_choices: List[int]) -> List[int]:
        goals = [start_idx]
        cur = start_idx
        for choice in step_choices:
            neigh = self.adj.neighbors[cur]
            nxt = neigh[int(choice) % len(neigh)]
            goals.append(nxt)
            cur = nxt
        return goals

    def build_two_humans_goals(
        self,
        start1: int,
        steps1: List[int],
        start2: int,
        steps2: List[int],
    ) -> Tuple[List[int], List[int]]:
        # First-goal constraint: must differ
        if start1 == start2:
            start2 = (start2 + 1) % self.adj.n

        g1 = self._walk_goals(start1, steps1)
        g2 = self._walk_goals(start2, steps2)

        # Small repair: avoid consecutive duplicates (can happen if neighbor list degenerates)
        def repair(seq: List[int]) -> List[int]:
            out = list(seq)
            for i in range(1, len(out)):
                if out[i] == out[i - 1]:
                    out[i] = self.adj.neighbors[out[i - 1]][0]
            return out

        return repair(g1), repair(g2)

    def write(
        self,
        goals1_idx: List[int],
        goals2_idx: List[int],
        goal_radius1: float,
        goal_radius2: float,
        radius1: float,
        radius2: float,
        max_vel1: float,
        max_vel2: float,
        behavior_type1: int,
        behavior_type2: int,
        yaml_rel_path: str = HUNAV_TEST_REL,
    ) -> str:
        K = self.cfg.goals_per_human
        assert len(goals1_idx) == K and len(goals2_idx) == K

        def mk_goal_dict(idx: int) -> Dict[str, float]:
            x, y = self.adj.idx_to_xy(idx)
            return {"x": float(x), "y": float(y)}

        w1_goals = [mk_goal_dict(i) for i in goals1_idx]
        w2_goals = [mk_goal_dict(i) for i in goals2_idx]

        yaml_data = {
            "hunav_loader": {
                "ros__parameters": {
                    "map": "map",
                    "publish_people": True,
                    "agents": ["worker1", "worker2"],
                    "worker1": {
                        "id": 1,
                        "skin": 0,
                        "group_id": -1,
                        "max_vel": float(max_vel1),
                        "radius": float(radius1),
                        "behavior": {
                            "type": int(behavior_type1),
                            "configuration": 0,
                            "duration": 40.0,
                            "once": True,
                            "vel": 0.6,
                            "dist": 0.0,
                            "goal_force_factor": 2.0,
                            "obstacle_force_factor": 10.0,
                            "social_force_factor": 5.0,
                            "other_force_factor": 20.0,
                        },
                        "init_pose": {"x": w1_goals[0]["x"], "y": w1_goals[0]["y"], "z": 1.25, "h": 0.0},
                        "goal_radius": float(goal_radius1),
                        "cyclic_goals": True,
                        "goals": [f"g{i}" for i in range(K)],
                    },
                    "worker2": {
                        "id": 2,
                        "skin": 4,
                        "group_id": -1,
                        "max_vel": float(max_vel2),
                        "radius": float(radius2),
                        "behavior": {
                            "type": int(behavior_type2),
                            "configuration": 0,
                            "duration": 40.0,
                            "once": True,
                            "vel": 0.6,
                            "dist": 0.0,
                            "goal_force_factor": 2.0,
                            "obstacle_force_factor": 10.0,
                            "social_force_factor": 5.0,
                            "other_force_factor": 20.0,
                        },
                        "init_pose": {"x": w2_goals[0]["x"], "y": w2_goals[0]["y"], "z": 1.25, "h": 0.0},
                        "goal_radius": float(goal_radius2),
                        "cyclic_goals": True,
                        "goals": [f"g{i}" for i in range(K)],
                    },
                }
            }
        }

        for i, g in enumerate(w1_goals):
            yaml_data["hunav_loader"]["ros__parameters"]["worker1"][f"g{i}"] = {"x": g["x"], "y": g["y"], "h": 1.25}
        for i, g in enumerate(w2_goals):
            yaml_data["hunav_loader"]["ros__parameters"]["worker2"][f"g{i}"] = {"x": g["x"], "y": g["y"], "h": 1.25}

        class HunavDumper(yaml.SafeDumper):
            def represent_bool(self, data):
                return self.represent_scalar("tag:yaml.org,2002:bool", "true" if data else "false")

        HunavDumper.add_representer(bool, HunavDumper.represent_bool)

        yaml_path = os.path.join(WS_ROOT, yaml_rel_path)
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, sort_keys=False, Dumper=HunavDumper)

        return yaml_path


class PrivacySimulationEvaluator:
    """
    Launches sim similar to ethical_hunav.py :contentReference[oaicite:10]{index=10}
    then runs send_goal_and_log, and parses privacy_violation_duration from log.csv :contentReference[oaicite:11]{index=11}
    """
    def __init__(self, cfg: GAConfig):
        self.cfg = cfg

    def _launch_simulation(self, episode: int) -> subprocess.Popen:
        # route_start_end defined in ethical_hunav; import lazily to avoid circular
        from ethical_testing.ethical_hunav import route_start_end
        start = route_start_end[self.cfg.route]["start"]
        cmd = (
            "ros2 launch test_hunav test_hunav.launch.py "
            "is_public_sim:=True navigation:=True "
            "world_name:=no_roof_small_warehouse "
            f"x:={start['x']} y:={start['y']} yaw:={start['yaw']} "
            f"number:={self.cfg.scenario_number} episode:={episode}"
        )
        return popen_cmd(cmd)

    def _run_privacy_test(self, episode: int) -> subprocess.Popen:
        cmd = (
            "ros2 run ethical_testing ethical_navigation "
            f"--ros-args -p route:={self.cfg.route} -p episode:={episode} -p number:={self.cfg.scenario_number}"
        )
        proc = popen_cmd(cmd)
        try:
            proc.wait(timeout=self.cfg.hard_timeout_sec)
        except subprocess.TimeoutExpired:
            kill_process_group(proc)
            raise TimeoutError("send_goal_and_log timed out")
        return proc

    def _read_privacy_violation_duration(self, episode: int) -> Dict[str, object]:
        metrics_dir = os.path.join(OUTPUT_ROOT, "privacy", self.cfg.route, str(episode))
        metrics_csv = os.path.join(metrics_dir, "log.csv")

        output_dir_exists = os.path.isdir(metrics_dir)
        log_csv_exists = os.path.isfile(metrics_csv)

        if not output_dir_exists:
            return {"duration": 0.0, "status": "folder_missing", "output_dir_exists": False, "log_csv_exists": False}

        if not log_csv_exists:
            return {"duration": 0.0, "status": "csv_missing", "output_dir_exists": True, "csv_exists": False}

        with open(metrics_csv, "r", newline="") as f:
            rows = list(csv.reader(f))

        if len(rows) < 2:
            return {"duration": 0.0, "status": "csv_missing", "output_dir_exists": True, "csv_exists": True}

        header = rows[0]
        last = rows[-1]

        if "privacy_violation_duration" not in header:
            return {"duration": 0.0, "status": "csv_missing", "output_dir_exists": True, "csv_exists": True}

        idx = header.index("privacy_violation_duration")
        try:
            duration = float(last[idx])
        except Exception:
            return {"duration": 0.0, "status": "csv_missing", "output_dir_exists": True, "csv_exists": True}

        return {"duration": duration, "status": "valid", "output_dir_exists": True, "csv_exists": True}

    def _cleanup_previous_output(self, episode: int) -> None:
        metrics_dir = os.path.join(OUTPUT_ROOT, "privacy", self.cfg.route, str(episode))
        if os.path.exists(metrics_dir):
            shutil.rmtree(metrics_dir, ignore_errors=True)


    def evaluate(self, episode: int) -> Dict[str, object]:
        sim_proc = None
        nav_proc = None
        try:
            self._cleanup_previous_output(episode)
            sim_proc = self._launch_simulation(episode)
            time.sleep(self.cfg.startup_wait_sec)
            nav_proc = self._run_privacy_test(episode)
            return self._read_privacy_violation_duration(episode)
        except TimeoutError as e:
            print(f"[PrivacySimulationEvaluator] evaluation error: {e}")
            return {
                "duration": 0.0,
                "status": "timeout",
                "output_dir_exists": False,
                "log_csv_exists": False,
            }
        except Exception as e:
            print(f"[PrivacySimulationEvaluator] evaluation error: {e}")
            return {
                "duration": 0.0,
                "status": "startup_failure",
                "output_dir_exists": False,
                "log_csv_exists": False,
            }

        finally:
            cleanup_simulation(sim_proc, nav_proc)

class PrivacyGAProblemAdjacent(Problem[FloatSolution]):
    def __init__(
        self,
        cfg: GAConfig,
        max_attempts: int = 1,
        trace_dir: Optional[str] = None,
        trace_logger: Optional[GATraceLogger] = None,
    ):
        super().__init__()
        self.cfg = cfg
        self.adj = WaypointAdjacency(cfg)
        self.writer = HunavYamlWriter(cfg, self.adj)
        self.evaluator = PrivacySimulationEvaluator(cfg)
        # how many times to retry a configuration on failure
        self.max_attempts = max_attempts

        self.trace_dir = trace_dir
        self.trace_logger = trace_logger if trace_logger is not None else (
            GATraceLogger(trace_dir) if trace_dir else None
        )
        self.current_generation = 0
        self._solution_counter = 0

        K = cfg.goals_per_human

        # Required by jMetalPy
        self._number_of_constraints = 0
        self._number_of_objectives = 1
        self._number_of_variables = 2 * (1 + (K - 1) + 4)

        lower: List[float] = []
        upper: List[float] = []

        # start indices (2 humans)
        lower += [0.0, 0.0]
        upper += [float(self.adj.n - 1), float(self.adj.n - 1)]

        # neighbor choices: 2*(K-1) values in [0..max_neighbors-1]
        for _ in range(2 * (K - 1)):
            lower.append(0.0)
            upper.append(float(cfg.max_neighbors - 1))

        # per human: goal_radius, radius, max_vel, behavior_type
        for _ in range(2):
            lower += [cfg.goal_radius_min, cfg.radius_min, cfg.max_vel_min, float(cfg.behavior_type_min)]
            upper += [cfg.goal_radius_max, cfg.radius_max, cfg.max_vel_max, float(cfg.behavior_type_max)]

        self.lower_bound = lower
        self.upper_bound = upper

        self._cache: Dict[str, float] = {}
        self.eval_counter = 0

    @property
    def number_of_variables(self) -> int:
        return self._number_of_variables

    @property
    def number_of_objectives(self) -> int:
        return self._number_of_objectives

    @property
    def number_of_constraints(self) -> int:
        return self._number_of_constraints

    def create_solution(self) -> FloatSolution:
        solution = FloatSolution(
            lower_bound=self.lower_bound,
            upper_bound=self.upper_bound,
            number_of_objectives=self.number_of_objectives,
            number_of_constraints=self.number_of_constraints,
        )
        solution.variables = [
            random.uniform(lb, ub) for lb, ub in zip(self.lower_bound, self.upper_bound)
        ]

        solution.attributes["solution_id"] = self._next_solution_id()
        solution.attributes["source"] = "initial"
        return solution

    def name(self) -> str:
        return "PrivacyGAProblemAdjacent"

    def _hash_vars(self, vars_: List[float]) -> str:
        b = ",".join(f"{v:.6f}" for v in vars_).encode("utf-8")
        return hashlib.sha256(b).hexdigest()
    
    def set_current_generation(self, generation: int) -> None:
        self.current_generation = generation

    def _next_solution_id(self) -> str:
        self._solution_counter += 1
        return f"S{self._solution_counter:06d}"

    def _decode_variables(self, vars_: List[float]) -> Dict[str, object]:
        K = self.cfg.goals_per_human

        start1 = safe_int(vars_[0], 0, self.adj.n - 1)
        start2 = safe_int(vars_[1], 0, self.adj.n - 1)

        steps_raw = [
            safe_int(v, 0, self.cfg.max_neighbors - 1)
            for v in vars_[2 : 2 + 2 * (K - 1)]
        ]
        steps1 = steps_raw[: (K - 1)]
        steps2 = steps_raw[(K - 1) :]

        base = 2 + 2 * (K - 1)

        goal_radius1 = safe_float(vars_[base + 0], self.cfg.goal_radius_min, self.cfg.goal_radius_max)
        radius1      = safe_float(vars_[base + 1], self.cfg.radius_min, self.cfg.radius_max)
        max_vel1     = safe_float(vars_[base + 2], self.cfg.max_vel_min, self.cfg.max_vel_max)
        btype1       = safe_int(vars_[base + 3], self.cfg.behavior_type_min, self.cfg.behavior_type_max)

        base2 = base + 4
        goal_radius2 = safe_float(vars_[base2 + 0], self.cfg.goal_radius_min, self.cfg.goal_radius_max)
        radius2      = safe_float(vars_[base2 + 1], self.cfg.radius_min, self.cfg.radius_max)
        max_vel2     = safe_float(vars_[base2 + 2], self.cfg.max_vel_min, self.cfg.max_vel_max)
        btype2       = safe_int(vars_[base2 + 3], self.cfg.behavior_type_min, self.cfg.behavior_type_max)

        goals1_idx, goals2_idx = self.writer.build_two_humans_goals(start1, steps1, start2, steps2)
        goals1 = [self.adj.idx_to_key(i) for i in goals1_idx]
        goals2 = [self.adj.idx_to_key(i) for i in goals2_idx]

        return {
            "start1": start1,
            "start2": start2,
            "steps1": steps1,
            "steps2": steps2,
            "goal_radius1": goal_radius1,
            "radius1": radius1,
            "max_vel1": max_vel1,
            "behavior_type1": btype1,
            "goals1": goals1,
            "goal_radius2": goal_radius2,
            "radius2": radius2,
            "max_vel2": max_vel2,
            "behavior_type2": btype2,
            "goals2": goals2,
        }

    def evaluate(self, solution: FloatSolution) -> FloatSolution:
        self.eval_counter += 1
        vars_ = solution.variables
        key = self._hash_vars(vars_)

        if "solution_id" not in solution.attributes:
            solution.attributes["solution_id"] = self._next_solution_id()

        decoded = self._decode_variables(vars_)
        solution.attributes["variables_hash"] = key

        if key in self._cache:
            duration = self._cache[key]
            result = {
                "duration": duration,
                "status": "valid_cache",
                "output_dir_exists": True,
                "csv_exists": True,
            }
            attempts_used = 0
            source = "cache"
        else:
            start1 = decoded["start1"]
            start2 = decoded["start2"]
            steps1 = decoded["steps1"]
            steps2 = decoded["steps2"]

            goals1_idx, goals2_idx = self.writer.build_two_humans_goals(start1, steps1, start2, steps2)

            self.writer.write(
                goals1_idx=goals1_idx,
                goals2_idx=goals2_idx,
                goal_radius1=decoded["goal_radius1"],
                goal_radius2=decoded["goal_radius2"],
                radius1=decoded["radius1"],
                radius2=decoded["radius2"],
                max_vel1=decoded["max_vel1"],
                max_vel2=decoded["max_vel2"],
                behavior_type1=decoded["behavior_type1"],
                behavior_type2=decoded["behavior_type2"],
            )

            result = {"duration": 0.0, "status": "startup_failure", "output_dir_exists": False, "log_csv_exists": False}
            attempts_used = 0
            source = solution.attributes.get("source", "offspring")

            for attempt in range(1, self.max_attempts + 1):
                attempts_used = attempt
                try:
                    result = self.evaluator.evaluate(episode=self.eval_counter)
                except Exception:
                    result = {
                        "duration": 0.0,
                        "status": "startup_failure",
                        "output_dir_exists": False,
                        "log_csv_exists": False,
                    }

                if result["status"] in ("valid", "valid_cache"):
                    break

                if attempt < self.max_attempts:
                    time.sleep(1.0)

            duration = float(result["duration"])
            if result["status"] == "valid":
                self._cache[key] = duration

        fitness = duration
        solution.objectives[0] = -1.0 * fitness

        if self.trace_logger is not None:
            self.trace_logger.log_evaluation(
                eval_id=self.eval_counter,
                generation=self.current_generation,
                source=source,
                solution_id=solution.attributes["solution_id"],
                variables_hash=key,
                fitness=fitness,
                status=result["status"],
                output_dir_exists=bool(result.get("output_dir_exists", False)),
                log_csv_exists=bool(result.get("log_csv_exists", False)),
                attempts_used=attempts_used,
                variables=vars_,
                decoded=decoded,
            )

        return solution

def main():
    cfg = GAConfig()

    population_size = 10
    generations = 10
    max_evals = population_size * generations

    problem = PrivacyGAProblemAdjacent(cfg)

    algorithm = GeneticAlgorithm(
        problem=problem,
        population_size=population_size,
        offspring_population_size=population_size,
        selection=BinaryTournamentSelection(),
        crossover=SBXCrossover(probability=0.9, distribution_index=20),
        mutation=PolynomialMutation(probability=0.2, distribution_index=20),
        termination_criterion=StoppingByEvaluations(max_evaluations=max_evals),
    )

    algorithm.run()
    best = algorithm.result()
    best_duration = -best.objectives[0]

    print(f"[GA] Best privacy_violation_duration = {best_duration:.3f} s")
    print(f"[GA] Best variables = {best.variables}")
    print(f"[GA] Neighbor threshold used = {problem.adj.threshold:.4f} (max_neighbors={cfg.max_neighbors})")


if __name__ == "__main__":
    main()
