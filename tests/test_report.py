import pytest

from budget_report import core
from budget_report.cli import main

BUDGET = [{"cost_center": "A", "category": "Util", "month": str(m), "amount": "100"} for m in range(1, 5)]


def act(date, amount, cat="Util", center="A"):
    return {"date": date, "cost_center": center, "category": cat, "amount": str(amount)}


def test_ytd_sums_only_requested_months():
    rows = core.build(BUDGET, [act("2026-01-05", 90), act("2026-03-05", 95)], 2026, 2)
    assert (rows[0].budget, rows[0].actual) == (200.0, 90.0)


def test_other_year_ignored():
    rows = core.build(BUDGET, [act("2025-01-05", 500), act("2026-01-05", 10)], 2026, 12)
    assert rows[0].actual == 10.0


def test_over_flag_and_percent():
    rows = core.build(BUDGET, [act("2026-01-05", 130)], 2026, 1)
    assert rows[0].flag == "OVER" and rows[0].variance_pct == 30.0 and rows[0].variance == 30.0


def test_within_threshold_not_flagged():
    assert core.build(BUDGET, [act("2026-01-05", 104)], 2026, 1)[0].flag == ""


def test_threshold_is_adjustable():
    assert core.build(BUDGET, [act("2026-01-05", 104)], 2026, 1, threshold_pct=2)[0].flag == "OVER"


def test_under_flag():
    assert core.build(BUDGET, [act("2026-01-05", 50)], 2026, 1)[0].flag == "UNDER"


def test_unbudgeted_spending():
    rows = core.build(BUDGET, [act("2026-01-05", 40, cat="Security")], 2026, 1)
    assert [r.flag for r in rows if r.category == "Security"] == ["UNBUDGETED"]
    assert [r for r in rows if r.category == "Security"][0].variance_pct is None


def test_roll_up_by_cost_center():
    budget = BUDGET + [{"cost_center": "A", "category": "Repairs", "month": "1", "amount": "50"}]
    rows = core.roll_up(core.build(budget, [act("2026-01-05", 80)], 2026, 1))
    assert len(rows) == 1 and rows[0].budget == 150.0 and rows[0].actual == 80.0


def test_invalid_month_threshold_and_input():
    with pytest.raises(ValueError, match="month"):
        core.build(BUDGET, [], 2026, 13)
    with pytest.raises(ValueError, match="threshold"):
        core.build(BUDGET, [], 2026, 1, threshold_pct=-1)
    with pytest.raises(ValueError, match="not a number"):
        core.build(BUDGET, [act("2026-01-05", "abc")], 2026, 1)
    with pytest.raises(ValueError, match="not a date"):
        core.build(BUDGET, [act("01/05/2026", 5)], 2026, 1)


def test_bad_budget_month():
    with pytest.raises(ValueError, match="between 1 and 12"):
        core.build([{"cost_center": "A", "category": "U", "month": "0", "amount": "1"}], [], 2026, 3)


def test_cli_report_and_csv(tmp_path, capsys):
    out = tmp_path / "o.csv"
    code = main(["--budget", "data/budget.csv", "--actuals", "data/actuals.csv", "--month", "4",
                 "--flagged", "--csv", str(out)])
    text = capsys.readouterr().out
    assert code == 0 and "OVER" in text and "TOTAL" in text
    assert out.read_text().startswith("cost_center,category")


def test_cli_missing_file(capsys):
    assert main(["--budget", "nope.csv", "--actuals", "nope.csv"]) == 1
