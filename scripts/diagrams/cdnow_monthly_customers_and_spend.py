"""Monthly customer counts and spend. Run with: uv run --with matplotlib <this file>."""
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
for customer, date, index, value in rows:
    first[customer] = min(first.get(customer, (date, index)), (date, index))
all_spend = defaultdict(lambda: defaultdict(Decimal))
repeat_spend = defaultdict(lambda: defaultdict(Decimal))
orders = defaultdict(lambda: [0, 0])
for customer, date, index, value in rows:
    month = date[:6]
    all_spend[month][customer] += value
    orders[month][0] += 1
    if (date, index) != first[customer]:
        repeat_spend[month][customer] += value
        orders[month][1] += 1
months = sorted(all_spend)
assert len(rows) == 69659 and len(first) == 23570 and len(months) == 18
assert sum(sum(s.values()) for s in all_spend.values()) == sum(r[3] for r in rows)
assert sum(o[1] for o in orders.values()) == len(rows) - len(first)
for month in months[3:]:
    assert all_spend[month] == repeat_spend[month]

counts = [[len(series[m]) for m in months] for series in (all_spend, repeat_spend)]
averages = [[float(sum(series[m].values()) / len(series[m])) for m in months] for series in (all_spend, repeat_spend)]
with (BASE / (Path(__file__).stem + ".csv")).open("w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["month", "purchasing_customers", "repeat_purchasing_customers", "revenue_usd", "repeat_revenue_usd", "monthly_spend_per_customer_usd", "repeat_monthly_spend_per_repeat_customer_usd", "average_order_value_usd", "repeat_average_order_value_usd"])
    for i, month in enumerate(months):
        total = sum(all_spend[month].values())
        repeat = sum(repeat_spend[month].values())
        writer.writerow([month[:4] + "-" + month[4:], counts[0][i], counts[1][i], total, repeat, f"{averages[0][i]:.2f}", f"{averages[1][i]:.2f}", f"{total / orders[month][0]:.2f}", f"{repeat / orders[month][1]:.2f}"])
        print(f"{month}: customers={counts[0][i]:,}; repeat customers={counts[1][i]:,}; spend/customer=${averages[0][i]:.2f}; repeat spend/customer=${averages[1][i]:.2f}")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
fig, axes = plt.subplots(2, 1, figsize=(13.6, 10.4), sharex=True, facecolor="#FAFAF8")
labels = [datetime.strptime(m, "%Y%m").strftime("%b\n%Y") if m.endswith("01") else datetime.strptime(m, "%Y%m").strftime("%b") for m in months]
for ax, values, title, ylabel in zip(axes, (counts, averages), ("1. How many customers purchased each month?", "2. How much did each purchasing customer spend that month?"), ("Unique purchasing customers", "Average monthly spend (USD)")):
    ax.set_facecolor("#FAFAF8")
    ax.plot(range(18), values[0], color="#4D7EA8", marker="o", linewidth=2.6, markersize=6, label="All purchases")
    ax.plot(range(18), values[1], color="#D68B2E", marker="o", linewidth=2.3, markersize=4, linestyle="--", label="Repeat purchases only")
    ax.set_title(title, loc="left", fontsize=15, pad=16, weight="bold", color="#202D3A")
    ax.set_ylabel(ylabel, labelpad=12)
    ax.set_ylim(0, max(max(v) for v in values) * 1.19)
    ax.grid(axis="y", color="#DDDDD8", linewidth=.7)
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.tick_params(axis="both", length=0, pad=9)
    ax.axvline(2.5, color="#AAA99F", linestyle=(0, (3, 4)), linewidth=1)
    ax.set_xlim(-.5, 17.5)
axes[0].legend(frameon=False, loc="upper right", ncol=2)
axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
axes[1].set_xticks(range(18), labels)
for i in (0, 2, 3, 17):
    axes[0].annotate(f"{counts[1][i]:,}", (i, counts[1][i]), xytext=(0, 12), textcoords="offset points", ha="center", fontsize=10, color="#985F1B")
    axes[1].annotate(f"${averages[1][i]:.2f}", (i, averages[1][i]), xytext=(0, 12), textcoords="offset points", ha="center", fontsize=10, color="#985F1B")
fig.text(.085, .965, "Returning revenue: customer numbers and spending", fontsize=22, weight="bold", color="#202D3A")
fig.text(.085, .93, "CDNOW · 23,570 customers acquired Jan–Mar 1997 · All purchases and repeat purchases coincide from April 1997", fontsize=11, color="#57636D")
fig.text(.085, .035, "Spend per customer = monthly revenue ÷ unique customers purchasing that month; includes multiple orders per customer.\nRepeat excludes each customer's first transaction (same-day ties use file order). Source: raw_data/CDNOW_master.txt.", fontsize=9.5, color="#57636D", linespacing=1.6)
fig.subplots_adjust(left=.085, right=.97, top=.86, bottom=.13, hspace=.35)
for extension in ("png", "svg"):
    fig.savefig(BASE / (Path(__file__).stem + "." + extension), dpi=180, facecolor=fig.get_facecolor())
