"""Analyze calendar-month activity by customer age and observed revenue concentration.

Run: uv run --with matplotlib assets/diagrams/cdnow_activity_by_month_since_first_purchase.py
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
end = 1998 * 12 + 5
first = {c: min(m for m, value in transactions) for c, transactions in customers.items()}
active_ages = {c: {m - first[c] for m, value in transactions} for c, transactions in customers.items()}
activity = []
for age in range(1, 18):
    eligible = [c for c in customers if first[c] + age <= end]
    active = sum(age in active_ages[c] for c in eligible)
    activity.append((age, len(eligible), active, active / len(eligible) * 100))
assert all(row[1] == 23570 for row in activity[:15])
with (BASE / "cdnow_activity_by_month_since_first_purchase.csv").open("w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["months_since_first_purchase_month", "eligible_customers", "purchasing_customers", "purchasing_percent"])
    writer.writerows(activity)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.parse_math": False})
def style(ax):
    ax.set_facecolor("#FAFAF8")
    ax.grid(axis="y", color="#DDDDD8", linewidth=.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.tick_params(axis="both", length=0, pad=9)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))

fig, ax = plt.subplots(figsize=(13.6, 7.4), facecolor="#FAFAF8")
style(ax)
ax.plot([a[0] for a in activity], [a[3] for a in activity], color="#4D7EA8", marker="o", linewidth=2.6)
ax.axvspan(15.5, 17.4, color="#ECE6DB", zorder=0)
ax.text(16.45, 27, "Fewer cohorts\nobserved", ha="center", color="#786D59", fontsize=10)
ax.set_xlim(.6, 17.4)
ax.set_ylim(0, 30)
ax.set_xticks(range(1, 18))
ax.set_xlabel("Months since first-purchase month", labelpad=13)
ax.set_ylabel("Customers purchasing in that month", labelpad=12)
for age, eligible, active, share in activity:
    if age in (1, 3, 6, 9, 12, 15, 16, 17):
        ax.annotate(f"{share:.1f}%", (age, share), xytext=(0, 11), textcoords="offset points", ha="center", color="#345D7F", fontsize=10)
fig.text(.08, .94, "Purchasing activity by time since first purchase", fontsize=22, weight="bold", color="#202D3A")
fig.text(.08, .89, "CDNOW · Customers aligned to their first-purchase month · Repeat purchases only", fontsize=12, color="#57636D")
fig.text(.08, .04, "Month 1 = the next calendar month, not a fixed 30-day window. Each customer counts once per month.\nRate = customers purchasing ÷ customers whose corresponding month is fully observed; customers can skip months and return.\nMonths 1–15: all 23,570 customers; month 16: Jan–Feb entrants; month 17: Jan entrants only. First-purchase month excluded.\nSource: raw_data/CDNOW_master.txt · Observation ends 30 June 1998.", fontsize=9.5, color="#57636D", linespacing=1.5)
fig.subplots_adjust(left=.08, right=.965, top=.83, bottom=.25)
for ext in ("png", "svg"):
    fig.savefig(BASE / ("cdnow_activity_by_month_since_first_purchase." + ext), dpi=180, facecolor=fig.get_facecolor())
plt.close(fig)


print("Activity (age, eligible, purchasing, percent):")
for row in activity:
    print(row)
