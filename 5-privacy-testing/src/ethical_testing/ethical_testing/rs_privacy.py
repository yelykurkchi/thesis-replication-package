import os
from typing import Optional

from ethical_testing.ga_privacy import GAConfig, PrivacyGAProblemAdjacent, GATraceLogger


def make_rs_trace_dir(cfg: GAConfig) -> str:
    ws_root = os.path.expanduser("~/yelyzaveta/hunav_and_omni_base_ws")
    trace_dir = os.path.join(
        ws_root,
        "ethical_output",
        "algorithm_trace",
        f"RS_{cfg.route}",
    )
    os.makedirs(trace_dir, exist_ok=True)
    return trace_dir


def random_search(
    cfg: GAConfig,
    sample_size: int = 100,
    max_retries: int = 1,
    trace_dir: Optional[str] = None,
):
    if trace_dir is None:
        trace_dir = make_rs_trace_dir(cfg)

    trace_logger = GATraceLogger(trace_dir, prefix="rs")

    problem = PrivacyGAProblemAdjacent(
        cfg,
        max_attempts=max_retries,
        trace_logger=trace_logger,
    )

    best_sol = None
    best_duration = float("-inf")

    print(
        f"[RS] starting random search: samples={sample_size}, "
        f"max_attempts={max_retries}"
    )
    print(f"[RS] trace logs will be saved to: {trace_dir}")

    for i in range(sample_size):
        problem.set_current_generation(0)

        sol = problem.create_solution()
        sol.attributes["source"] = "random"

        sol = problem.evaluate(sol)
        duration = -sol.objectives[0]

        if best_sol is None or duration > best_duration:
            best_sol = sol
            best_duration = duration

        print(
            f"[RS] sample {i + 1}/{sample_size}: "
            f"duration={duration:.3f} s, "
            f"best={best_duration:.3f} s"
        )

    assert best_sol is not None

    print(f"[RS] finished: best privacy_violation_duration = {best_duration:.3f} s")
    print(f"[RS] best variables = {best_sol.variables}")
    print(f"[RS] total evaluations = {problem.eval_counter}")

    return best_sol


if __name__ == "__main__":
    cfg = GAConfig()
    best = random_search(cfg, sample_size=100, max_retries=1)
    best_duration = -best.objectives[0]
    print(f"[RS] Best privacy_violation_duration = {best_duration:.3f} s")
    print(f"[RS] Best variables = {best.variables}")
