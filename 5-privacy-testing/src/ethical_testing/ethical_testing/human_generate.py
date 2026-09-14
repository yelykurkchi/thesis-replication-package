import os
import math
import argparse
import yaml
from ethical_testing.config.waypoints import waypoints

WS_ROOT = os.path.expanduser("~/hunav_and_omni_base_ws/")


def _goals_from_waypoint_keys(path_wp, route_name: str, worker_name: str):
    missing = [w for w in path_wp if w not in waypoints]
    if missing:
        raise RuntimeError(
            f"[humans_generate] Missing waypoints for {worker_name} ({route_name}): {missing}. "
            f"Check ethical_testing.config.waypoints."
        )

    goals = [waypoints[w] for w in path_wp]

    for w, g in zip(path_wp, goals):
        if not isinstance(g, dict):
            raise RuntimeError(f"[humans_generate] Waypoint {w} is not a dict: {g!r}")
        if "x" not in g or "y" not in g:
            raise RuntimeError(f"[humans_generate] Waypoint {w} missing x/y fields: {g}")

    return goals


def _assert_distinct_start(worker1_goals, worker2_goals, tol: float = 1e-6):
    x1, y1 = float(worker1_goals[0]["x"]), float(worker1_goals[0]["y"])
    x2, y2 = float(worker2_goals[0]["x"]), float(worker2_goals[0]["y"])

    if math.isfinite(x1) and math.isfinite(y1) and math.isfinite(x2) and math.isfinite(y2):
        if abs(x1 - x2) < tol and abs(y1 - y2) < tol:
            raise RuntimeError(
                "[humans_generate] worker1 and worker2 initial poses are identical "
                f"({x1}, {y1}). This will spawn them at the same point. "
                "Fix the first waypoint of each route (e.g., G11 vs F11) in waypoints."
            )
    else:
        raise RuntimeError(
            f"[humans_generate] Non-finite init pose values detected: "
            f"worker1=({x1}, {y1}), worker2=({x2}, {y2})"
        )


def make_worker1_goals(route: str):
    if route == "route_1":
        path_wp = ["G11", "G12", "G13", "G14", "D14", "G14", "G15", "G16"]
    elif route == "route_4":
        path_wp = ["G12", "G13", "G14", "G15", "G16", "G17", "G18"]
    else:
        path_wp = ["E10", "E11", "E12", "E13", "E14", "E15", "E16", "E17", "E18"]

    return _goals_from_waypoint_keys(path_wp, route, "worker1")


def make_worker2_goals(route: str):
    if route == "route_1":
        path_wp = ["F11", "F12", "F13", "F14", "F15", "F16"]
    elif route == "route_4":
        path_wp = ["F12", "F13", "F14", "F15", "F16", "F17"]
    else:
        path_wp = ["F18", "F17", "F16", "F15", "F14", "F13", "F12", "F11", "F10"]

    return _goals_from_waypoint_keys(path_wp, route, "worker2")


def generate_hunav_yaml(route: str, yaml_rel_path: str = "src/hunav_sim/hunav_agent_manager/config/test.yaml"):
    worker1_goals = make_worker1_goals(route)
    worker2_goals = make_worker2_goals(route)

    if not worker1_goals or not worker2_goals:
        raise RuntimeError("[humans_generate] No goals generated for workers. Check your waypoint names.")

    # Ensure we do not accidentally spawn both workers at the same place
    _assert_distinct_start(worker1_goals, worker2_goals)

    # Debug: print initial poses that will be written
    print(
        f"[humans_generate] route={route} "
        f"worker1_init=({worker1_goals[0]['x']}, {worker1_goals[0]['y']}) "
        f"worker2_init=({worker2_goals[0]['x']}, {worker2_goals[0]['y']})"
    )

    yaml_data = {
        "hunav_loader": {
            "ros__parameters": {
                "map": "map",
                "publish_people": True,
                "agents": ["worker1"],
                "worker1": {
                    "id": 1,
                    "skin": 0,
                    "group_id": -1,
                    "max_vel": 1.5,
                    "radius": 0.4,
                    "behavior": {
                        "type": 1,
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
                    "init_pose": {
                        "x": worker1_goals[0]["x"],
                        "y": worker1_goals[0]["y"],
                        "z": 1.250000,
                        "h": 0.0,
                    },
                    "goal_radius": 0.3,
                    "cyclic_goals": True,
                    "goals": [f"g{i}" for i in range(len(worker1_goals))]
                }
            }
        }
    }

    for i, g in enumerate(worker1_goals):
        yaml_data["hunav_loader"]["ros__parameters"]["worker1"][f"g{i}"] = {
            "x": g["x"],
            "y": g["y"],
            "h": 1.250000
        }

    yaml_data["hunav_loader"]["ros__parameters"]["agents"].append("worker2")

    worker2_data = {
        "id": 2,
        "skin": 4,
        "group_id": -1,
        "max_vel": 1.5,
        "radius": 0.4,
        "behavior": {
            "type": 1,
            "configuration": 2,
            "duration": 40.0,
            "once": True,
            "vel": 0.6,
            "dist": 0.0,
            "goal_force_factor": 2.0,
            "obstacle_force_factor": 10.0,
            "social_force_factor": 5.0,
            "other_force_factor": 20.0,
        },
        "init_pose": {
            "x": worker2_goals[0]["x"],
            "y": worker2_goals[0]["y"],
            "z": 1.250000,
            "h": 0.0,
        },
        "goal_radius": 0.3,
        "cyclic_goals": True,
        "goals": [f"g{i}" for i in range(len(worker2_goals))]
    }

    yaml_data["hunav_loader"]["ros__parameters"]["worker2"] = worker2_data

    for i, g in enumerate(worker2_goals):
        yaml_data["hunav_loader"]["ros__parameters"]["worker2"][f"g{i}"] = {
            "x": g["x"],
            "y": g["y"],
            "h": 1.250000
        }

    class HunavDumper(yaml.SafeDumper):
        def represent_bool(self, data):
            return self.represent_scalar("tag:yaml.org,2002:bool", "true" if data else "false")

    HunavDumper.add_representer(bool, HunavDumper.represent_bool)

    yaml_path = os.path.join(WS_ROOT, yaml_rel_path)
    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, sort_keys=False, Dumper=HunavDumper)

    print(f"[humans_generate] Written HuNav config to: {yaml_path}")
    return yaml_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", type=str, default="route_1", help="Route name (e.g., route_1, route_4)")
    parser.add_argument(
        "--output",
        type=str,
        default="src/hunav_sim/hunav_agent_manager/config/test.yaml",
        help="Path relative to WS_ROOT where test.yaml should be written",
    )
    args = parser.parse_args()

    generate_hunav_yaml(args.route, yaml_rel_path=args.output)


if __name__ == "__main__":
    main()