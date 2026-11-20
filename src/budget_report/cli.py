"""Command line interface for the budget variance report."""
from __future__ import annotations

import argparse
import csv
import sys

from . import core


def _pct(row: core.Row) -> str:
    return "n/a" if row.variance_pct is None else f"{row.variance_pct:+.1f}%"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="budget_report", description="Budget versus actual by cost center.")
    parser.add_argument("--budget", required=True, help="budget CSV (cost_center, category, month, amount)")
    parser.add_argument("--actuals", required=True, help="actuals CSV (date, cost_center, category, amount)")
    parser.add_argument("--year", type=int, default=2026, help="fiscal year to report (default 2026)")
    parser.add_argument("--month", type=int, default=12, help="report year to date through this month (default 12)")
    parser.add_argument("--threshold", type=float, default=5.0, help="flag variances above this percent (default 5)")
    parser.add_argument("--by-cost-center", action="store_true", help="one row per cost center")
    parser.add_argument("--flagged", action="store_true", help="show only flagged rows")
    parser.add_argument("--csv", metavar="FILE", help="also write the rows to a CSV file")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the report. Returns the exit code."""
    args = build_parser().parse_args(argv)
    try:
        rows = core.build(core.read_csv(args.budget, core.BUDGET_COLS), core.read_csv(args.actuals, core.ACTUAL_COLS),
                          args.year, args.month, args.threshold)
        if args.by_cost_center:
            rows = core.roll_up(rows)
            for r in rows:
                r.flag = "OVER" if (r.variance_pct or 0) > args.threshold else ""
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    shown = [r for r in rows if r.flag] if args.flagged else rows
    print(f"Year {args.year}, January to month {args.month}")
    print(f"{'Cost center':<14} {'Category':<12} {'Budget':>10} {'Actual':>10} {'Variance':>10} {'Var %':>8}  Flag")
    for r in shown:
        print(f"{r.cost_center:<14} {r.category:<12} {r.budget:>10,.2f} {r.actual:>10,.2f} "
              f"{r.variance:>+10,.2f} {_pct(r):>8}  {r.flag}".rstrip())
    total_b, total_a = sum(r.budget for r in rows), sum(r.actual for r in rows)
    print(f"{'TOTAL':<27} {total_b:>10,.2f} {total_a:>10,.2f} {total_a - total_b:>+10,.2f}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["cost_center", "category", "budget", "actual", "variance", "variance_pct", "flag"])
            writer.writerows([r.cost_center, r.category, r.budget, r.actual, r.variance, r.variance_pct, r.flag]
                             for r in rows)
    return 0
