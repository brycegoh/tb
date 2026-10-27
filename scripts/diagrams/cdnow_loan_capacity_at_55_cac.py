"""Compare historical scenario loan capacity with a $55 CAC acquisition budget."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BASE = Path(__file__).resolve().parents[2] / "assets" / "diagrams"
with (BASE / "cdnow_cohort_loan_capacity.csv").open() as source:
    rows = list(csv.DictReader(source))
loan = 23570 * 55
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "text.parse_math": False})
fig, ax = plt.subplots(figsize=(13.6, 7.4), facecolor="#FAFAF8")
ax.set_facecolor("#FAFAF8")
for scenario, color, label in (("normal", "#4D7EA8", "Base case"), ("worse", "#D68B2E", "Worse case")):
    values = [float(r[scenario + "_max_upfront_loan_usd"]) for r in rows]
    ax.plot(range(1, 19), values, color=color, marker="o", markersize=5, linewidth=2.6, label=label)
    ax.annotate(f"${values[-1]:,.0f}", (18, values[-1]), xytext=(10, 0), textcoords="offset points", va="center", color=color, weight="bold", fontsize=11)
ax.axhline(loan, color="#9C5053", linewidth=1.7, linestyle="--", label="$55 CAC acquisition loan: $1,296,350")
ax.text(1.2, loan + 24000, "$1,296,350 needed upfront", color="#9C5053", fontsize=11)
ax.set_xlim(.7, 20)
ax.set_ylim(0, 1450000)
ax.set_xticks(range(1, 19))
ax.set_xlabel("Months from start of cohort acquisition quarter", labelpad=12)
ax.set_ylabel("Maximum loan reaching full 1.2× repayment (USD)", labelpad=12)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v/1000000:.1f}m"))
ax.grid(axis="y", color="#DDDDD8", linewidth=.7)
ax.set_axisbelow(True)
ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
ax.tick_params(axis="both", length=0, pad=9)
ax.legend(loc="lower right", frameon=False)
fig.text(.085, .94, "At $55 CAC, neither case supports full repayment within 18 months", fontsize=19, weight="bold", color="#202D3A")
fig.text(.085, .89, "23,570 target customers × $55 CAC = $1,296,350 upfront loan · 1.2× repayment target: $1,555,620", fontsize=11, color="#57636D")
fig.text(.085, .04, "Loan capacity = cumulative cohort revenue × 50% ÷ 1.2. Both cases use the same fixed upfront loan.\nBase replays observed behaviour. Worse acquires 20% fewer customers with a 5% top-spender mix; within-type behaviour unchanged.\nMonth 1 replays Jan 1997; month 18 replays Jun 1998. Results beyond month 18 are not estimated.\nSource: raw_data/CDNOW_master.txt. $55 CAC is a scenario assumption, not a measured cost for this cohort.", fontsize=9.5, color="#57636D", linespacing=1.5)
fig.subplots_adjust(left=.085, right=.97, top=.83, bottom=.24)
for ext in ("png", "svg"):
    fig.savefig(BASE / (Path(__file__).stem + "." + ext), dpi=180, facecolor=fig.get_facecolor())
