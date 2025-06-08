#!/usr/bin/env python3
import os, sys
import argparse
import multiprocessing

# figure out where "src" lives, relative to this file
ROOT = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)
from Simulator import Simulator

# figure out where "src" lives, relative to this file
ROOT = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


def worker(run_id: int, n_nodes: int, max_sim_time: int):
    """
    Creates its own log folder,
    instantiates Simulator with the given params,
    and runs it.
    """
    run_dir = os.path.join("logs", f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    # Option A: if Simulator writes logs to cwd by default:
    os.chdir(run_dir)
    sim = Simulator(
        n_nodes=n_nodes,
        max_simulation_time=max_sim_time
    )
    sim.run()  # or however you launch it
    # logs will drop into run_dir


def main():
    parser = argparse.ArgumentParser(
        description="Parallel runs of Simulator—one task per core."
    )
    parser.add_argument(
        "--n-nodes",
        type=int,
        nargs="+",
        required=True,
        help="List of node-counts, one per run/core."
    )
    parser.add_argument(
        "--max-simulation-time",
        type=int,
        nargs="+",
        required=True,
        help="List of sim times, one per run/core."
    )
    args = parser.parse_args()

    if len(args.n_nodes) != len(args.max_simulation_time):
        parser.error(
            "You must supply the same number of --n-nodes and --max-simulation-time values."
        )

    params = list(zip(
        range(1, len(args.n_nodes) + 1),
        args.n_nodes,
        args.max_simulation_time
    ))

    cpu_count = multiprocessing.cpu_count()
    print(f"Launching {len(params)} jobs on up to {cpu_count} cores…")

    # You can choose to limit processes to cpu_count if you have more params than cores:
    pool_size = min(cpu_count, len(params))
    with multiprocessing.Pool(pool_size) as pool:
        # Pool.starmap unpacks each tuple into worker()
        pool.starmap(worker, params)

    print("FINISHED - All simulations complete.")


if __name__ == "__main__":
    main()

# HOW TO RUN:
"""

./parallel_simulations.py \
  --n-nodes    50 100 75 120 60  80  90 110 \
  --max-simulation-time 200 300 250 400 180 220 260 340

  test run with barely any computation for testing:
  parallel_simulations.py \
  --n-nodes    5 10 15 20 25  30  35 40 \
  --max-simulation-time 10 20 25 30 35 40 45 50

Behind the scenes it will fan out up to 8 processes (one per core)
and drop each run’s logs in logs/run_1/…logs/run_8/.
"""

