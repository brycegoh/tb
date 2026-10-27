"""Analyze calendar-month activity by customer age and observed revenue concentration.

Run: uv run --with matplotlib assets/diagrams/cdnow_customer_revenue_concentration.py
"""
from collections import defaultdict
import csv
from decimal import Decimal
from math import ceil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

BASE = Path(__file__).resolve().parent
customers = defaultdict(list)
for line in (BASE.parents[1] / "raw_data/CDNOW_master.txt").read_text().splitlines():
    customer, date, cds, amount = line.split()
    month = int(date[:4]) * 12 + int(date[4:6]) - 1
    customers[customer].append((month, Decimal(amount)))
assert len(customers) == 23570
assert sum(map(len, customers.values())) == 69659
ranked = sorted((sum(value for month, value in transactions) for transactions in customers.values()), reverse=True)
total = sum(ranked)
concentration = []
for percent in (1, 5, 10, 15, 20):
    count = ceil(len(ranked) * percent / 100)
    revenue = sum(ranked[:count])
    concentration.append((percent, count, count / len(ranked) * 100, revenue, float(revenue / total * 100)))
with (BASE / "cdnow_customer_revenue_concentration.csv").open("w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["top_customer_percent", "customer_count", "actual_customer_percent", "revenue_usd", "share_of_total_revenue_percent"])
    writer.writerows(concentration)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.parse_math": False})
def style(ax):
    ax.set_facecolor("#FAFAF8")
    ax.grid(axis="y", color="#DDDDD8", linewidth=.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.tick_params(axis="both", length=0, pad=9)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))

fig, ax = plt.subplots(figsize=(11.6, 7.4), facecolor="#FAFAF8")
style(ax)
ax.bar(range(5), [r[4] for r in concentration], width=.6, color="#367D67")
ax.set_xticks(range(5), [f"Top {r[0]}%\n({r[1]:,} customers)" for r in concentration])
ax.set_ylim(0, 100)
ax.set_ylabel("Share of total cohort revenue", labelpad=12)
for i, row in enumerate(concentration):
    ax.text(i, row[4] + 2, f"{row[4]:.1f}%", ha="center", color="#285C4D", fontsize=14, weight="bold")
fig.text(.09, .94, "How concentrated is customer revenue?", fontsize=22, weight="bold", color="#202D3A")
fig.text(.09, .89, f"23,570 customers · ${total:,.2f} total revenue · Jan 1997–Jun 1998", fontsize=12, color="#57636D")
fig.text(.09, .045, "Customers ranked by total observed spending, including initial and repeat purchases. Groups are cumulative.\nCustomer counts round up to whole people. Observation length varies with first-purchase date; these are not lifetime totals.\nSource: raw_data/CDNOW_master.txt.", fontsize=9.5, color="#57636D", linespacing=1.5)
fig.subplots_adjust(left=.09, right=.97, top=.83, bottom=.23)
for ext in ("png", "svg"):
    fig.savefig(BASE / ("cdnow_customer_revenue_concentration." + ext), dpi=180, facecolor=fig.get_facecolor())
print(f"Total revenue: ${total:,.2f}")
print("Concentration (top percent, count, actual percent, revenue, revenue share):")
for row in concentration:
    print(row)
