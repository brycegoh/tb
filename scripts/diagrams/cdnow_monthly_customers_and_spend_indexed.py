"""Index customer counts, monthly spend and revenue to April 1997 = 100%."""
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

BASE = Path(__file__).resolve().parents[2] / "assets" / "diagrams"
with (BASE / "cdnow_monthly_customers_and_spend.csv").open() as source:
    rows = [r for r in csv.DictReader(source) if r["month"] >= "1997-04"]
assert len(rows) == 15 and rows[0]["month"] == "1997-04"
customers = [Decimal(r["purchasing_customers"]) for r in rows]
# Use revenue and customer counts to avoid rounding the intermediate average.
revenue = [Decimal(r["revenue_usd"]) for r in rows]
spend = [r / n for r, n in zip(revenue, customers)]
indices = [[float(value / series[0] * 100) for value in series] for series in (customers, spend, revenue)]
assert all(series[0] == 100 for series in indices)
assert all(abs(r - c * s / 100) < 1e-9 for c, s, r in zip(*indices))
stem = Path(__file__).stem
with (BASE / (stem + ".csv")).open("w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["month", "purchasing_customers_index_apr1997_100", "monthly_spend_per_customer_index_apr1997_100", "monthly_revenue_index_apr1997_100"])
    for i, row in enumerate(rows):
        writer.writerow([row["month"], *[f"{series[i]:.4f}" for series in indices]])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.parse_math": False})
fig, ax = plt.subplots(figsize=(13.6, 7.4), facecolor="#FAFAF8")
ax.set_facecolor("#FAFAF8")
colors = ["#4D7EA8", "#D68B2E", "#367D67"]
labels = ["Purchasing customers", "Monthly spend per purchasing customer", "Monthly revenue"]
for j, (values, color, label) in enumerate(zip(indices, colors, labels)):
    ax.plot(range(len(rows)), values, color=color, linewidth=2.6, marker=("o", "o", "s")[j], markersize=(6, 6, 4)[j], linestyle=("-", "-", "--")[j], label=label)
    ax.annotate(f"{values[-1]:.1f}%", (len(rows)-1, values[-1]), xytext=(12, (11, 0, -11)[j]), textcoords="offset points", va="center", color=color, fontsize=12, weight="bold", arrowprops={"arrowstyle": "-", "color": color, "lw": .8})
ax.axhline(100, color="#8A8D89", linestyle=(0, (4, 4)), linewidth=1.2, zorder=0)
ax.annotate("April baseline: 100%", (0, 100), xytext=(10, -24), textcoords="offset points", fontsize=10, color="#57636D")
ticks = [datetime.strptime(r["month"], "%Y-%m") for r in rows]
ax.set_xticks(range(len(rows)), [d.strftime("%b\n%Y") if i == 0 or d.month == 1 else d.strftime("%b") for i, d in enumerate(ticks)])
ax.set_ylim(0, 125)
ax.set_yticks(range(0, 121, 20))
ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
ax.set_ylabel("Percentage of April 1997 level", labelpad=12)
ax.set_xlim(-.35, len(rows)-.05)
ax.grid(axis="y", color="#DDDDD8", linewidth=.7)
ax.set_axisbelow(True)
ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
ax.tick_params(axis="both", length=0, pad=9)
ax.legend(loc="lower left", frameon=False)
fig.text(.08, .94, "Revenue tracks falling customer numbers as spend holds steady", fontsize=20, weight="bold", color="#202D3A")
fig.text(.08, .89, "CDNOW cohort · April 1997 = 100% · April 1997–June 1998", fontsize=12, color="#57636D")
fig.text(.08, .045, f"April baseline: 2,822 purchasing customers; ${float(spend[0]):.2f} spend per customer; ${float(revenue[0]):,.2f} revenue.\nEach index = month's value ÷ April value × 100. Revenue = purchasing customers × monthly spend per customer.\nSource: raw_data/CDNOW_master.txt · All purchases in this period are repeat purchases from the Jan–Mar 1997 cohort.", fontsize=9.5, color="#57636D", linespacing=1.5)
fig.subplots_adjust(left=.08, right=.95, top=.83, bottom=.21)
for extension in ("png", "svg"):
    fig.savefig(BASE / (stem + "." + extension), dpi=180, facecolor=fig.get_facecolor())
print(f"June 1998: customers {indices[0][-1]:.2f}%; monthly spend/customer {indices[1][-1]:.2f}%; revenue {indices[2][-1]:.2f}%")
