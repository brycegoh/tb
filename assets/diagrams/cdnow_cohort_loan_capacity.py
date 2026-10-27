"""Historical replay and customer-mix stress; loan ceiling = cumulative revenue / 2.4.

Run: uv run --with matplotlib assets/diagrams/cdnow_cohort_loan_capacity.py
"""
from collections import defaultdict
import csv
from decimal import Decimal
from math import ceil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BASE = Path(__file__).resolve().parent
rows = []
total_by_customer = defaultdict(Decimal)
for line in (BASE.parents[1] / "raw_data/CDNOW_master.txt").read_text().splitlines():
    customer, date, cds, value = line.split()
    value = Decimal(value)
    rows.append((customer, date[:6], value))
    total_by_customer[customer] += value
assert len(rows) == 69659 and len(total_by_customer) == 23570
ranked = sorted(total_by_customer, key=lambda c: (-total_by_customer[c], c))
top = set(ranked[:ceil(len(ranked) / 10)])
assert len(top) == 2357
# New cohort size = 80% of observed; mix = 5% top-type, 95% other-type.
# Original mix = 10% top-type, 90% other-type. Keep each type's monthly
# revenue/customer unchanged. Weights apply to every historical transaction.
top_weight = Decimal("0.8") * Decimal("0.05") / Decimal("0.10")
other_weight = Decimal("0.8") * Decimal("0.95") / Decimal("0.90")
assert abs(len(top) * top_weight + (len(ranked)-len(top)) * other_weight - Decimal(len(ranked)) * Decimal("0.8")) < Decimal("1e-20")
monthly = defaultdict(lambda: [Decimal(0), Decimal(0)])
for customer, month, value in rows:
    monthly[month][0] += value
    monthly[month][1] += value * (top_weight if customer in top else other_weight)
months = sorted(monthly)
assert len(months) == 18
cumulative = [Decimal(0), Decimal(0)]
results = []
for i, month in enumerate(months, 1):
    cumulative = [cumulative[j] + monthly[month][j] for j in range(2)]
    ceilings = [v * Decimal("0.5") / Decimal("1.2") for v in cumulative]
    results.append((i, month[:4] + "-" + month[4:], *monthly[month], *cumulative, *(v * Decimal("0.5") for v in cumulative), *ceilings))
    assert all(abs(ceilings[j] * Decimal("1.2") - cumulative[j] * Decimal("0.5")) < Decimal("1e-20") for j in range(2))
assert cumulative[0] == sum(total_by_customer.values())
with (BASE / (Path(__file__).stem + ".csv")).open("w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["replay_month", "historical_reference_month", "normal_monthly_revenue_usd", "worse_monthly_revenue_usd", "normal_cumulative_revenue_usd", "worse_cumulative_revenue_usd", "normal_available_repayment_usd", "worse_available_repayment_usd", "normal_max_upfront_loan_usd", "worse_max_upfront_loan_usd"])
    for row in results:
        writer.writerow([*row[:2], *[f"{v:.2f}" for v in row[2:]]])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.parse_math": False})
fig, ax = plt.subplots(figsize=(13.6, 7.8), facecolor="#FAFAF8")
ax.set_facecolor("#FAFAF8")
for j, (color, label) in enumerate((("#4D7EA8", "Normal: historical replay"), ("#D68B2E", "Worse: fewer customers and fewer top spenders"))):
    values = [float(r[8+j]) for r in results]
    ax.plot(range(1, 19), values, marker="o", markersize=5, linewidth=2.6, color=color, label=label)
    ax.annotate(f"${values[-1]/1000:,.0f}k", (18, values[-1]), xytext=(12, 0), textcoords="offset points", va="center", color=color, weight="bold", fontsize=12)
ax.set_xlim(.7, 19.2)
ax.set_ylim(0, 1150000)
ax.set_xticks(range(1, 19))
ax.set_xlabel("Months from start of cohort acquisition quarter", labelpad=12)
ax.set_ylabel("Maximum upfront loan supported (USD)", labelpad=12)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
ax.grid(axis="y", color="#DDDDD8", linewidth=.7)
ax.set_axisbelow(True)
ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
ax.tick_params(axis="both", length=0, pad=9)
ax.legend(loc="upper left", frameon=False)
fig.text(.085, .94, "Upfront loan supported by repayment deadline", fontsize=22, weight="bold", color="#202D3A")
fig.text(.085, .89, "50% of cumulative cohort revenue repaid · Repayment cap: 1.2× initial capital", fontsize=12, color="#57636D")
fig.text(.085, .035, "Maximum loan = cumulative revenue × 50% ÷ 1.2. Month 1 replays Jan 1997; month 18 replays Jun 1998.\nNormal: 23,570 customers, 10% top-spender mix. Worse: 18,856 customers, 5% top-spender mix; spending within each type unchanged.\nTop spenders ranked by total observed revenue. Includes initial and repeat purchases; monthly timing follows historical data.\nScenario ceilings assume the revenue share is paid in full by each month-end; no extrapolation beyond the observed 18 months.\nSource: raw_data/CDNOW_master.txt.", fontsize=9.2, color="#57636D", linespacing=1.5)
fig.subplots_adjust(left=.085, right=.96, top=.83, bottom=.28)
for ext in ("png", "svg"):
    fig.savefig(BASE / (Path(__file__).stem + "." + ext), dpi=180, facecolor=fig.get_facecolor())
for r in results:
    print(f"{r[0]:2} {r[1]} | cumulative normal ${r[4]:,.2f}, worse ${r[5]:,.2f} | loan normal ${r[8]:,.2f}, worse ${r[9]:,.2f}")
print(f"Worse/normal final revenue: {cumulative[1]/cumulative[0]:.4%}")
