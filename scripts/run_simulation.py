"""Synthetic workload simulation entrypoint.

Run from the repository root, for example:

    uv run scripts/run_simulation.py --seed 42 --outcome-seed 4201 --count 20

Generates reproducible synthetic customer inquiries (no LLM), then sends them
through the REAL Contoso agent and REAL Foundry evaluation. On top of that real
technical execution it layers a SYNTHETIC business experiment: randomized
treatment/control assignment and synthetic customer outcomes (Simulator 1B),
and propagates that synthetic experiment evidence through Value-to-Action while
keeping it strictly labeled as simulated (Simulator 1C).

All business, pilot, and causal evidence produced here is synthetic. It is NOT
production traffic, and synthetic evidence never satisfies a production-evidence
claim: real business outcomes, production incrementality, and complete customer
cost remain Unknown, so the selected portfolio action stays PROVE.
"""

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

# Reuse the regression orchestration helpers from the sibling script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_evaluation import (  # noqa: E402
    RESULTS_PATH,
    build_run_id,
    process_completed_run,
    run_agent_over_cases,
)

from foundry_prompt_agent.agent import project_client  # noqa: E402
from foundry_prompt_agent.foundry_eval import run_cloud_evaluation  # noqa: E402
from foundry_prompt_agent.synthetic_inquiries import (  # noqa: E402
    GENERATOR_VERSION,
    generate_inquiries,
    load_menu,
)
from foundry_prompt_agent.synthetic_outcomes import (  # noqa: E402
    build_simulation_metadata,
    simulate_pilot_outcomes,
)

MENU_PATH = Path("data/contoso.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a synthetic workload simulation.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--outcome-seed", type=int, default=4201)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--menu", type=Path, default=MENU_PATH)
    return parser.parse_args()


def print_synthetic_header(seed: int, cases: list[dict]) -> None:
    print("\n=== Synthetic Workload ===")
    print("Mode: SIMULATION")
    print(f"Seed: {seed}")
    print(f"Generated inquiries: {len(cases)}")
    print(f"Generator version: {GENERATOR_VERSION}")

    print("\nCategory mix:")
    mix = Counter(case["category"] for case in cases)
    for category in sorted(mix):
        print(f"  {category}: {mix[category]}")


def main() -> None:
    args = parse_args()
    judge_model = os.environ["FOUNDRY_JUDGE_MODEL"]

    run_id = build_run_id()

    # 1. Generate reproducible synthetic inquiries (deterministic, no LLM).
    menu = load_menu(args.menu)
    cases = generate_inquiries(seed=args.seed, count=args.count, menu=menu)
    print_synthetic_header(args.seed, cases)

    # 2. Real agent execution over the synthetic workload.
    efficiency, execution_records = run_agent_over_cases(cases, run_id)

    # 3. Real Foundry evaluation.
    run = run_cloud_evaluation(
        project_client,
        results_path=RESULTS_PATH,
        run_id=run_id,
        judge_model=judge_model,
    )

    print(f"Final status: {run.status}")
    print(f"Foundry report: {run.report_url}")

    # 4. Shared evidence pipeline, tagged as a simulation run. Synthetic pilot
    # assignment and outcomes are generated from acceptance-joined records.
    simulation_metadata = build_simulation_metadata(
        inquiry_seed=args.seed,
        outcome_seed=args.outcome_seed,
        count=args.count,
        generator_version=GENERATOR_VERSION,
    )

    def pilot_simulator(execution_records: list[dict]):
        return simulate_pilot_outcomes(
            interaction_records=execution_records,
            seed=args.outcome_seed,
            config=None,
        )

    print(f"\nOutcome seed: {args.outcome_seed}")

    process_completed_run(
        run_id=run_id,
        cases=cases,
        efficiency=efficiency,
        execution_records=execution_records,
        run=run,
        run_mode="simulation",
        simulation_metadata=simulation_metadata,
        pilot_simulator=pilot_simulator,
    )


if __name__ == "__main__":
    main()
