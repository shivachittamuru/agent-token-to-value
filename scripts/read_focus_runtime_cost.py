"""Read local FOCUS Cost and Usage CSV evidence and apply existing allocations."""

import argparse
from pathlib import Path
import sys

from foundry_prompt_agent.azure_runtime_cost import (
    build_azure_runtime_cost_config,
    load_azure_runtime_allocation_config,
    summarize_azure_runtime_cost,
)
from foundry_prompt_agent.cost_snapshot import (
    COST_SNAPSHOTS_DIR,
    build_cost_snapshot,
    save_cost_snapshot,
)
from foundry_prompt_agent.focus_cost import (
    load_focus_cost_data,
    month_period,
    normalize_focus_resource_costs,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "economics" / "azure_runtime_cost.yaml"
DEFAULT_INPUT = ROOT / "focus_samples" / "contoso-september-2026.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--month", required=True, help="Completed month, YYYY-MM")
    parser.add_argument(
        "--cost-metric",
        choices=("effective_cost", "billed_cost"),
        default="effective_cost",
    )
    parser.add_argument("--focus-version", default="1.2")
    parser.add_argument("--save-snapshot", action="store_true")
    args = parser.parse_args()

    try:
        start, end = month_period(args.month)
        allocation_config = load_azure_runtime_allocation_config(args.config)
        rows = load_focus_cost_data(args.input, cost_metric=args.cost_metric)
        evidence = normalize_focus_resource_costs(
            rows=rows,
            allocation_config=allocation_config,
            start=start,
            end=end,
            cost_metric=args.cost_metric,
            focus_version=args.focus_version,
        )
        print(f"FOCUS source: {args.input}")
        print(f"FOCUS version: {args.focus_version}")
        print(f"Cost metric: {args.cost_metric}")
        print(f"Period: {start.isoformat()} through {end.isoformat()} (USD)")
        for resource in evidence["resources"]:
            cost = resource["actual_cost_usd"]
            display = (
                f"{cost:.6f} USD"
                if cost is not None
                else "not_returned (not observed zero)"
            )
            status = resource["cost_evidence_status"]
            print(f"{resource['name']}: {display} [{status}]")

        combined = build_azure_runtime_cost_config(
            allocation_config=allocation_config,
            cost_evidence=evidence,
        )
        summary = summarize_azure_runtime_cost(combined)
        print(
            "Raw selected-resource cost: "
            f"{summary['actual_selected_resource_cost_usd']:.6f} USD"
        )
        print(
            "Allocated Azure runtime cost: "
            f"{summary['allocated_azure_runtime_cost_usd']:.6f} USD"
        )
        print(f"Allocation status: {summary['allocation_status']}")

        if args.save_snapshot:
            snapshot_id = f"{summary['workload_id']}-focus-{args.month}"
            snapshot = build_cost_snapshot(
                azure_runtime_cost=summary,
                snapshot_id=snapshot_id,
            )
            path = COST_SNAPSHOTS_DIR / f"{snapshot_id}.json"
            save_cost_snapshot(snapshot, path)
            print(f"Saved cost snapshot: {path}")
    except (OSError, ValueError) as error:
        print(f"FOCUS runtime cost read failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
