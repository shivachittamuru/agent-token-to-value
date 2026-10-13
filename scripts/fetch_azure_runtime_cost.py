"""Fetch completed-month billing evidence and optionally save a local snapshot."""

import argparse
from pathlib import Path
import sys

from azure.core.exceptions import AzureError

from foundry_prompt_agent.azure_cost_management import (
    calendar_month,
    fetch_azure_resource_costs,
)
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

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "economics" / "azure_runtime_cost.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True, help="Completed calendar month, YYYY-MM")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--save-snapshot", action="store_true")
    parser.add_argument("--snapshot-path", type=Path, help="Save to this path instead of the default")
    args = parser.parse_args()
    try:
        start, end = calendar_month(args.month)
        config = load_azure_runtime_allocation_config(args.config)
        evidence = fetch_azure_resource_costs(
            allocation_config=config, start=start, end=end
        )
        for resource in evidence["resources"]:
            cost = resource["actual_cost_usd"]
            display = f"{cost:.6f} USD" if cost is not None else "not_returned (not observed zero)"
            if resource["cost_evidence_status"] == "no_direct_charge_returned":
                display += " [no_direct_charge_returned; charges may be billed elsewhere]"
            print(f"{resource['name']}: {display}")
        combined = build_azure_runtime_cost_config(
            allocation_config=config, cost_evidence=evidence
        )
        summary = summarize_azure_runtime_cost(combined)
        print(f"Raw selected-resource total: {summary['actual_selected_resource_cost_usd']:.6f} USD")
        print(f"Allocated Azure runtime cost: {summary['allocated_azure_runtime_cost_usd']:.6f} USD")
        print(f"Allocation status: {summary['allocation_status']}")
        if args.save_snapshot or args.snapshot_path is not None:
            snapshot = build_cost_snapshot(azure_runtime_cost=summary)
            path = (
                args.snapshot_path if args.snapshot_path is not None
                else COST_SNAPSHOTS_DIR / f"{snapshot['snapshot_id']}.json"
            )
            save_cost_snapshot(snapshot, path)
            print(f"Saved cost snapshot: {path}")
    except (AzureError, ValueError, OSError) as error:
        print(f"Azure runtime cost fetch failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
