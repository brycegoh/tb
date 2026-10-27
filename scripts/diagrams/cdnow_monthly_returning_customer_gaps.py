"""Monthly repeat customers by calendar-month purchase continuity.
Run: uv run --with matplotlib scripts/diagrams/cdnow_monthly_returning_customer_gaps.py
"""
from collections import defaultdict
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BASE = Path(__file__).resolve().parents[2] / "assets" / "diagrams"
rows = []
for index, line in enumerate((BASE.parents[1] / "raw_data/CDNOW_master.txt").read_text().splitlines()):
    customer, date, cds, value = line.split()
    rows.append((customer, date, index, Decimal(value)))
first = {}
active = defaultdict(set)
for customer, date, index, value in rows:
    first[customer] = min(first.get(customer, (date, index)), (date, index))
    active[date[:6]].add(customer)
months = sorted(active)
repeat = defaultdict(lambda: defaultdict(lambda: [0, Decimal(0)]))
for customer, date, index, value in rows:
    if (date, index) != first[customer]:
        repeat[date[:6]][customer][0] += 1
        repeat[date[:6]][customer][1] += value

groups = ("previous_month", "gap", "first_month_repeat")
metrics = {}
for i, month in enumerate(months):
    metrics[month] = {group: [0, 0, Decimal(0)] for group in groups}
    previous = active[months[i - 1]] if i else set()
    for customer, (transactions, revenue) in repeat[month].items():
        if customer in previous:
            group = "previous_month"
        elif first[customer][0][:6] == month:
            group = "first_month_repeat"
        else:
            group = "gap"
        metrics[month][group][0] += 1
        metrics[month][group][1] += transactions
        metrics[month][group][2] += revenue
    assert sum(m[0] for m in metrics[month].values()) == len(repeat[month])
    assert sum(m[2] for m in metrics[month].values()) == sum(v[1] for v in repeat[month].values())
assert len(rows) == 69659 and len(first) == 23570 and len(months) == 18
assert sum(m[1] for by_group in metrics.values() for m in by_group.values()) == len(rows) - len(first)
assert all(metrics[m]["first_month_repeat"][0] == 0 for m in months[3:])

with (BASE / (Path(__file__).stem + ".csv")).open("w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["month", "group", "repeat_customers", "repeat_transactions", "repeat_revenue_usd", "share_of_monthly_repeat_customers"])
    for month in months:
        for group in groups:
            customers, transactions, revenue = metrics[month][group]
            writer.writerow([month[:4] + "-" + month[4:], group, customers, transactions, revenue, f"{customers / len(repeat[month]):.6f}"])
        n = len(repeat[month])
        print(f"{month}: repeat customers={n:,}; previous month={metrics[month]['previous_month'][0]:,}; gap={metrics[month]['gap'][0]:,} ({metrics[month]['gap'][0]/n:.1%}); first-month repeat={metrics[month]['first_month_repeat'][0]:,}")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
fig, ax = plt.subplots(figsize=(13.6, 8), facecolor="#FAFAF8")
ax.set_facecolor("#FAFAF8")
bottom = [0] * len(months)
for group, label, color in zip(groups, ("Also bought last month", "Returned after ≥1 skipped month", "Repeat within first month"), ("#4D7EA8", "#E6A04B", "#ADB6BF")):
    values = [metrics[m][group][0] for m in months]
    ax.bar(range(18), values, bottom=bottom, label=label, color=color, width=.73)
    bottom = [b + v for b, v in zip(bottom, values)]
for i, month in enumerate(months):
    n = len(repeat[month])
    ax.text(i, n + 45, f"{n:,}", ha="center", fontsize=9, color="#57636D")
    if i >= 3:
        count = metrics[month]["gap"][0]
        ax.text(i, metrics[month]["previous_month"][0] + count / 2, f"{count/n:.0%}", ha="center", va="center", fontsize=10, color="#463018", weight="bold")
ax.set_xticks(range(18), [datetime.strptime(m, "%Y%m").strftime("%b\n%Y") if m.endswith("01") else datetime.strptime(m, "%Y%m").strftime("%b") for m in months])
ax.set_ylabel("Unique customers making repeat purchases", labelpad=12)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.set_ylim(0, max(bottom) * 1.21)
ax.set_xlim(-.7, 17.7)
ax.set_axisbelow(True)
ax.grid(axis="y", color="#DDDDD8", linewidth=.7)
ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
ax.tick_params(axis="both", length=0, pad=9)
ax.axvline(2.5, color="#AAA99F", linestyle=(0, (3, 4)), linewidth=1)
fig.text(.08, .95, "Do returning customers buy in consecutive months?", fontsize=22, weight="bold", color="#202D3A")
fig.text(.08, .907, "CDNOW · Q1 1997 acquisition cohort · One skipped calendar month counts as a gap", fontsize=12, color="#57636D")
handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(.073, .88), frameon=False, ncol=3, fontsize=10.5)
fig.text(.08, .042, "Each returning customer is counted once per month. Percentages in orange = share returning after a gap (Apr 1997 onward).\nRepeat within first month is shown separately: these customers have no earlier calendar month to compare.\nRepeat excludes the first transaction; same-day ties use file order. Source: raw_data/CDNOW_master.txt.", fontsize=9.3, color="#57636D", linespacing=1.6)
fig.subplots_adjust(left=.08, right=.975, top=.79, bottom=.19)
for extension in ("png", "svg"):
    fig.savefig(BASE / (Path(__file__).stem + "." + extension), dpi=180, facecolor=fig.get_facecolor())
