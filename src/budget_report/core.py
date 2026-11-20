"""Budget versus actual variance by cost center and category."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BUDGET_COLS = ["cost_center", "category", "month", "amount"]
ACTUAL_COLS = ["date", "cost_center", "category", "amount"]


@dataclass
class Row:
    """Year-to-date figures for one cost center and category."""

    cost_center: str
    category: str
    budget: float
    actual: float
    flag: str = ""

    @property
    def variance(self) -> float:
        """Actual minus budget. Positive means overspent."""
        return round(self.actual - self.budget, 2)

    @property
    def variance_pct(self) -> float | None:
        """Variance as a percent of budget, or None when nothing was budgeted."""
        return None if self.budget == 0 else round(self.variance / self.budget * 100, 1)


def read_csv(path: str | Path, columns: list[str]) -> list[dict[str, str]]:
    """Read a CSV and check that the required columns exist."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in columns if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s) {', '.join(missing)}")
        return list(reader)


def _amount(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"'{value}' is not a number") from None


def build(budget: list[dict], actuals: list[dict], year: int, through_month: int,
          threshold_pct: float = 5.0) -> list[Row]:
    """Sum budget and actuals for months 1 to through_month of the year and flag overspending.

    A row is flagged OVER when actual exceeds budget by more than threshold_pct percent,
    UNBUDGETED when money was spent where no budget exists, and UNDER when spending is
    below budget by more than the threshold.
    """
    if not 1 <= through_month <= 12:
        raise ValueError("month must be between 1 and 12")
    if threshold_pct < 0:
        raise ValueError("threshold must not be negative")
    totals: dict[tuple[str, str], list[float]] = {}
    for b in budget:
        month = int(b["month"])
        if not 1 <= month <= 12:
            raise ValueError(f"budget month {month} is not between 1 and 12")
        if month <= through_month:
            totals.setdefault((b["cost_center"], b["category"]), [0.0, 0.0])[0] += _amount(b["amount"])
    for a in actuals:
        try:
            when = date.fromisoformat(a["date"])
        except ValueError:
            raise ValueError(f"'{a['date']}' is not a date (use YYYY-MM-DD)") from None
        if when.year == year and when.month <= through_month:
            totals.setdefault((a["cost_center"], a["category"]), [0.0, 0.0])[1] += _amount(a["amount"])
    rows = []
    for (center, category), (planned, spent) in sorted(totals.items()):
        row = Row(center, category, round(planned, 2), round(spent, 2))
        if planned == 0 and spent > 0:
            row.flag = "UNBUDGETED"
        elif row.variance_pct is not None and row.variance_pct > threshold_pct:
            row.flag = "OVER"
        elif row.variance_pct is not None and row.variance_pct < -threshold_pct:
            row.flag = "UNDER"
        rows.append(row)
    return rows


def roll_up(rows: list[Row]) -> list[Row]:
    """Combine categories so there is one row per cost center."""
    combined: dict[str, Row] = {}
    for r in rows:
        c = combined.setdefault(r.cost_center, Row(r.cost_center, "ALL", 0.0, 0.0))
        c.budget = round(c.budget + r.budget, 2)
        c.actual = round(c.actual + r.actual, 2)
    return [combined[k] for k in sorted(combined)]
