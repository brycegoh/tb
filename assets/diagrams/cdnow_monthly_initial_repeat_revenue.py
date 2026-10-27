"""Plot monthly revenue for the CDNOW acquisition cohort. Run: uv run --with matplotlib <this file>."""
from collections import defaultdict
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BASE = Path(__file__).resolve().parent
SOURCE = BASE.parents[1] / "raw_data" / "CDNOW_master.txt"
rows = []
for index, line in enumerate(SOURCE.read_text().splitlines()):
    customer, date, cds, value = line.split()
    rows.append((customer, date, index, Decimal(value)))

first = {}
for customer, date, index, value in rows:
    first[customer] = min(first.get(customer, (date, index)), (date, index))
monthly = defaultdict(lambda: [Decimal(0), Decimal(0), 0, 0])
for customer, date, index, value in rows:
    kind = 0 if first[customer] == (date, index) else 1
    monthly[date[:6]][kind] += value
    monthly[date[:6]][kind + 2] += 1

assert len(rows) == 69659 and len(first) == 23570
assert sum(v[2] for v in monthly.values()) == len(first)
assert sum(v[0] + v[1] for v in monthly.values()) == sum(r[3] for r in rows)
assert all(date <= "19970331" for date, index in first.values())
months = sorted(monthly)
assert len(months) == 18 and months[0] == "199701" and months[-1] == "199806"

with BASE.joinpath(Path(__file__).stem + ".csv").open("w", newline="") as output:
    writer = csv.writer(output)
    writer.writerow(["month", "initial_revenue_usd", "repeat_revenue_usd", "total_revenue_usd", "repeat_revenue_share", "initial_transactions", "repeat_transactions"])
    for month in months:
        initial, repeat, ni, nr = monthly[month]
        writer.writerow([month[:4] + "-" + month[4:], initial, repeat, initial + repeat, f"{repeat / (initial + repeat):.6f}", ni, nr])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(13.6, 7.4), facecolor="#FAFAF8")
ax.set_facecolor("#FAFAF8")
x = list(range(len(months)))
initial = [float(monthly[m][0]) for m in months]
repeat = [float(monthly[m][1]) for m in months]
ax.bar(x, initial, color="#4D7EA8", width=.73, label="Initial purchase")
ax.bar(x, repeat, bottom=initial, color="#E6A04B", width=.73, label="Repeat purchases")
ax.set_xticks(x, [datetime.strptime(m, "%Y%m").strftime("%b\n%Y") if m.endswith("01") or i == 0 else datetime.strptime(m, "%Y%m").strftime("%b") for i, m in enumerate(months)])
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
ax.set_ylabel("Monthly revenue (USD)", labelpad=12)
ax.set_axisbelow(True)
ax.grid(axis="y", color="#DDDDD8", linewidth=.7)
ax.spines[["left", "bottom"]].set_visible(False)
ax.tick_params(axis="both", length=0, pad=9)
ax.set_xlim(-.7, len(months) - .3)
ax.set_ylim(0, max(a + b for a, b in zip(initial, repeat)) * 1.16)
ax.axvline(2.5, color="#AAA99F", linestyle=(0, (3, 4)), linewidth=1)
ax.legend(loc="upper right", frameon=False, ncol=2)
fig.text(.075, .94, "Monthly revenue from initial and repeat purchases", fontsize=21, weight="bold", color="#202D3A")
fig.text(.075, .895, "CDNOW · 23,570 customers acquired Jan–Mar 1997 · Jan 1997–Jun 1998", fontsize=12, color="#57636D")
fig.text(.075, .055, "Initial = each customer's first transaction; repeat = every subsequent transaction. Same-day ties use file order.\nThis cohort only: no new customers enter after March 1997. Source: raw_data/CDNOW_master.txt.", fontsize=9.5, color="#57636D", linespacing=1.6)
fig.subplots_adjust(left=.075, right=.975, top=.84, bottom=.17)
for extension in ("png", "svg"):
    fig.savefig(BASE / (Path(__file__).stem + "." + extension), dpi=180, facecolor=fig.get_facecolor())

print(f"Validated {len(rows):,} transactions and {len(first):,} customers.")
for month in months:
    a, b, ni, nr = monthly[month]
    print(f"{month}: initial=${a:,.2f}; repeat=${b:,.2f}; repeat share={b/(a+b):.1%}")
