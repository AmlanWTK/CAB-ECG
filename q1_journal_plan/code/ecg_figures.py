"""Figures for the ECG study (WP10), from the E3 runs and E5 tables of the three seeds.

    F1  unsafe rate per transfer, by policy (seed 0; seeds 1-2 as the spread of the mean)
    F2  CAB: share of runs switched on, per transfer and label budget
    F3  labels needed against prevalence, with the 42-positive floor
    F4  whole-cohort judge (primary) vs the unlabelled ECGs only, per transfer and budget
    F5  WP7 comparators: unsafe rate per transfer, by policy (wp7_comparators.py)
    F6  WP8 monitoring: false alarms while safe, and drifts detected by audits after the change
        (wp8_monitor.py, 16,000-audit horizon)

Run from the repository root after ecg_e3_cab.py, ecg_e5_labels.py, wp7_comparators.py and
wp8_monitor.py --t-post 16000 --tag W8long:
    python q1_journal_plan/code/ecg_figures.py
Writes outputs/ecg/figures/<name>.pdf and .png, in the chapter's figure style.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sepsis_figures import FULL_W, GRID, INK, INK2, MM, MUTED, style  # noqa: E402
import ecg_e3_cab as E  # noqa: E402

FIG = E.OUT / "figures"
SEEDS = {0: "E3", 1: "E3seed1", 2: "E3seed2"}
POLICIES = ["AS-IS", "RECALIBRATE", "NAIVE-VAL", "NAIVE-500", "CRC", "CAB"]
COLOR = {"CAB": "#2a78d6", "AS-IS": "#eb6834", "NAIVE-VAL": "#1baf7a", "RECALIBRATE": "#eda100",
         "NAIVE-500": "#e87ba4", "CRC": "#7a5cc7"}
MARK = {"CAB": "o", "AS-IS": "s", "NAIVE-VAL": "^", "RECALIBRATE": "D", "NAIVE-500": "v", "CRC": "P"}
LABEL = {"CAB": "CAB (certified)", "AS-IS": "As supplied", "RECALIBRATE": "Recalibrate",
         "NAIVE-VAL": "Local validation", "NAIVE-500": "Validation, first 500",
         "CRC": "Conformal risk control"}
SITE = {"georgia": "Georgia (USA)", "cpsc_2018": "CPSC 2018 (China)",
        "cpsc_2018_extra": "CPSC-Extra (China)", "chapman_shaoxing": "Chapman (China)",
        "ningbo": "Ningbo (China)", "code15": "CODE-15% (Brazil)"}
OUTCOME = {"switched on": ("#2a78d6", "o"), "too few labels": ("#eb6834", "s"),
           "no safe remedy": (MUTED, "X")}


def runs(tag):
    r = pd.concat([pd.read_csv(E.OUT / f"{tag}_runs_{t}.csv") for t in E.TARGETS])
    return r[(r.s_star == E.PRIMARY[0]) & (r.margin == E.PRIMARY[1]) & (r.finding != "AF_from_AFL")]


def per_transfer(r, col="unsafe_cohort"):  # primary judge: the whole cohort
    return r.groupby(["policy", "target", "finding"])[col].mean().rename("unsafe").reset_index()


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote figures/{name}.pdf and .png")


def f1_unsafe(all_runs):
    t0 = per_transfer(all_runs[0])
    means = {s: per_transfer(r).groupby("policy").unsafe.mean() for s, r in all_runs.items()}
    fig, ax = plt.subplots(figsize=(FULL_W, 62 * MM))
    rng = np.random.default_rng(1)
    for i, pol in enumerate(POLICIES):
        u = t0[t0.policy == pol].unsafe.to_numpy()
        ax.scatter(u, i + rng.uniform(-0.18, 0.18, len(u)), s=14, marker=MARK[pol],
                   facecolor=COLOR[pol], edgecolor="white", linewidth=0.5, zorder=3)
        m = [means[s][pol] for s in means]
        ax.plot([min(m), max(m)], [i, i], color=INK, lw=1, zorder=4)
        ax.plot([means[0][pol]] * 2, [i - 0.3, i + 0.3], color=INK, lw=1.6, zorder=4)
        over = int((u > E.ALPHA).sum())
        ax.text(1.03, i, f"mean {means[0][pol]:.1%}  ·  {over} of {len(u)} over 5%",
                va="center", fontsize=7, color=INK2, transform=ax.get_yaxis_transform())
    ax.axvline(E.ALPHA, color=INK2, lw=0.8, ls=(0, (3, 2)), zorder=2)
    ax.text(E.ALPHA + 0.008, len(POLICIES) - 0.45, "α = 5%", fontsize=7, color=INK2)
    ax.set_yticks(range(len(POLICIES)), [LABEL[p] for p in POLICIES])
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.6, len(POLICIES) - 0.3)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Share of runs that switched on an unsafe finding (whole cohort; per transfer, all budgets)")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[Line2D([], [], color=INK, lw=1.6, marker="|", markersize=9, linestyle="-",
                              label="mean (seed 0); line: range over three seeds")],
              loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=6.8)
    ax.set_title("Unsafe activation across 31 imported ECG findings", pad=16)
    save(fig, "F1_unsafe_by_policy")


def f2_decisions(r0):
    cab = r0[r0.policy == "CAB"]
    on = cab.pivot_table(index=["target", "finding"], columns="n_labelled", values="activated", aggfunc="mean")
    order = [(t, f) for t in E.TARGETS for f in E.PANEL if (t, f) in on.index]
    on = on.loc[order]
    budgets = list(on.columns)
    fig, ax = plt.subplots(figsize=(FULL_W * 0.62, 118 * MM))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("blue", ["#f3f7fc", "#2a78d6", "#0d366b"])
    arr = np.ma.masked_invalid(on.to_numpy(dtype=float))
    cmap.set_bad("white")
    im = ax.pcolormesh(np.arange(arr.shape[1] + 1) - 0.5, np.arange(arr.shape[0] + 1) - 0.5, arr,
                       cmap=cmap, vmin=0, vmax=1, edgecolors="white", linewidth=1.5)
    ax.invert_yaxis()
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            v = on.iloc[i, j]
            if v == v and v >= 0.05:
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=5.6,
                        color="white" if v > 0.55 else INK)
            elif v != v:
                ax.text(j, i, "–", ha="center", va="center", fontsize=6, color=MUTED)
    ax.set_xticks(range(len(budgets)), [f"{b // 1000}k" if b >= 1000 else str(b) for b in budgets])
    ax.set_yticks(range(len(order)), [f for _, f in order], fontsize=6.5)
    ax.grid(visible=False)
    y = 0
    for t in E.TARGETS:
        n = sum(1 for tt, _ in order if tt == t)
        if n == 0:
            continue
        ax.text(-0.27, (y + y + n - 1) / 2, SITE[t], transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=6.8, color=INK)
        if y:
            ax.plot([-0.5, len(budgets) - 0.5], [y - 0.5] * 2, color=INK2, lw=0.8, zorder=5)
        y += n
    ax.set_xlabel("Labelled ECGs at the site (– : more than half the cohort)")
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, format=matplotlib.ticker.PercentFormatter(1.0, 0))
    cb.set_label("Runs in which CAB switched the finding on")
    cb.outline.set_visible(False)
    ax.set_title("CAB switches findings on as labels accumulate", loc="left")
    save(fig, "F2_cab_decisions")


def f3_labels(e5):
    e5 = e5[~e5.secondary].copy()
    floor = int(round((e5.floor_labels_calibrate * e5.prevalence).median()))
    fig, ax = plt.subplots(figsize=(FULL_W * 0.62, 80 * MM))
    x = np.geomspace(0.005, 0.5, 100)
    ax.plot(x, floor / x, color=INK2, lw=1, zorder=2)
    ax.plot(x, 2 * floor / x, color=INK2, lw=1, ls=(0, (3, 2)), zorder=2)
    ax.text(0.11, floor / 0.11 * 0.62, f"{floor} positives (calibrate)", fontsize=6.5, color=INK2,
            ha="left", va="top", rotation=-33, rotation_mode="anchor")
    ax.text(0.0058, 2 * floor / 0.0058 * 0.8, f"{2 * floor} positives (adapt)", fontsize=6.5, color=INK2,
            ha="left", va="top", rotation=-33, rotation_mode="anchor")

    def outcome(r):
        if r.budget_half_on == r.budget_half_on:
            return "switched on"
        return "too few labels" if r.safe_remedy_exists else "no safe remedy"
    e5["outcome"] = e5.apply(outcome, axis=1)
    e5["y"] = np.where(e5.outcome == "switched on", e5.budget_half_on, e5.largest_budget)
    for name, (c, mk) in OUTCOME.items():
        g = e5[e5.outcome == name]
        ax.scatter(g.prevalence, g.y, s=26, marker=mk, facecolor=c, edgecolor="white", linewidth=0.6,
                   zorder=3, label=f"{name} ({len(g)})")
    short = {"georgia": "Georgia", "chapman_shaoxing": "Chapman", "ningbo": "Ningbo"}
    nudge = {("chapman_shaoxing", "SB"): (-7, 5, "right", "Chapman and Ningbo SB"),
             ("ningbo", "SB"): None, ("ningbo", "IAVB"): (-6, 3, "right", None)}
    for r in e5[e5.outcome == "switched on"].itertuples():
        nd = nudge.get((r.target, r.finding), (5, 3, "left", None))
        if nd is None:
            continue
        dx, dy, ha, text = nd
        ax.annotate(text or f"{short.get(r.target, r.target)} {r.finding}", (r.prevalence, r.y), xytext=(dx, dy),
                    textcoords="offset points", fontsize=5.8, color=INK2, ha=ha)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.005, 0.5)
    ax.set_ylim(100, 40000)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlabel("Prevalence of the finding at the site")
    ax.set_ylabel("Labelled ECGs")
    ax.legend(title="CAB outcome (y: first budget with half of\nruns on, else largest budget tried)",
              title_fontsize=6.5, fontsize=6.5, frameon=False, loc="lower left")
    ax.set_title("Labels needed rise with rarity", loc="left")
    save(fig, "F3_labels_needed")


def f4_judges(r0):
    fig, axes = plt.subplots(1, 3, figsize=(FULL_W, 60 * MM), sharex=True, sharey=True)
    for ax, pol in zip(axes, ["CAB", "CRC", "NAIVE-VAL"]):
        g = r0[r0.policy == pol].groupby(["target", "finding", "n_labelled"])[["unsafe", "unsafe_cohort"]].mean()
        # x: the unlabelled ECGs only (sensitivity analysis); y: the whole cohort (primary)
        ax.plot([0, 1], [0, 1], color=GRID, lw=1, zorder=1)
        ax.axvline(E.ALPHA, color=INK2, lw=0.7, ls=(0, (3, 2)))
        ax.axhline(E.ALPHA, color=INK2, lw=0.7, ls=(0, (3, 2)))
        ax.scatter(g.unsafe, g.unsafe_cohort, s=12, marker=MARK[pol], facecolor=COLOR[pol],
                   edgecolor="white", linewidth=0.4, zorder=3)
        n_r, n_c = int((g.unsafe > E.ALPHA).sum()), int((g.unsafe_cohort > E.ALPHA).sum())
        ax.set_title(LABEL[pol], loc="left")
        ax.text(0.03, 0.97, f"cells over 5% (of {len(g)}):\n{n_r} on unlabelled ECGs\n{n_c} on whole cohort",
                transform=ax.transAxes, ha="left", va="top", fontsize=6.3, color=INK2, zorder=6,
                bbox=dict(boxstyle="square,pad=0.25", facecolor="white", edgecolor="none"))
        ax.set_xscale("symlog", linthresh=0.05)
        ax.set_yscale("symlog", linthresh=0.05)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        for a in (ax.xaxis, ax.yaxis):
            a.set_major_locator(matplotlib.ticker.FixedLocator([0, 0.05, 0.2, 1]))
            a.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
            a.set_minor_locator(matplotlib.ticker.NullLocator())
    axes[0].set_ylabel("Unsafe, judged on the whole cohort (primary)")
    axes[1].set_xlabel("Unsafe, judged on the unlabelled ECGs only")
    fig.suptitle("Judging on the unlabelled ECGs adds chance failures near the 5% line", x=0.01, ha="left",
                 fontsize=8.5, weight="bold", color=INK, y=1.03)
    save(fig, "F4_judges")


W7_POLICIES = ["CORAL", "CORAL-VAL", "BAYES-HOME", "RILEY-SIZE", "BAYES-FLAT", "BAYES-MATCHED", "CAB"]
W7_COLOR = {"CAB": "#2a78d6", "CORAL": "#eb6834", "CORAL-VAL": "#1baf7a", "BAYES-HOME": "#eda100",
            "RILEY-SIZE": "#e87ba4", "BAYES-FLAT": "#008300", "BAYES-MATCHED": "#6250d6"}
W7_MARK = {"CAB": "o", "CORAL": "s", "CORAL-VAL": "D", "BAYES-HOME": "^", "RILEY-SIZE": "v",
           "BAYES-FLAT": "P", "BAYES-MATCHED": "X"}
W7_LABEL = {"CAB": "CAB (certified)", "CORAL": "Domain adaptation, no labels",
            "CORAL-VAL": "Domain adaptation, recalibrated", "BAYES-HOME": "Bayesian, vendor's validation as prior",
            "RILEY-SIZE": "Sample-size rule, then estimates", "BAYES-FLAT": "Bayesian, flat prior (95%)",
            "BAYES-MATCHED": "Bayesian, flat prior (CAB's strictness)"}
W8_MON = {"MONITOR": ("Betting monitor (Ville)", "#2a78d6", "-"),
          "CUSUM-20k": ("CUSUM detector (ARL 20,000)", "#eb6834", "-"),
          "CHECK-TEST": ("Repeated tests, uncorrected", "#1baf7a", (0, (4, 2))),
          "CHECK-POINT": ("Point-estimate checks", "#eda100", (0, (1, 1.5)))}


def f5_comparators():
    w7 = pd.concat([pd.read_csv(E.OUT / f"W7_runs_{t}.csv") for t in E.TARGETS])
    cab = runs("E3")
    cab = cab[cab.policy == "CAB"][["policy", "target", "finding", "unsafe_cohort"]]
    r = pd.concat([w7[["policy", "target", "finding", "unsafe_cohort"]], cab])
    r["unsafe_cohort"] = r.unsafe_cohort.astype(float)
    t0 = per_transfer(r)
    fig, ax = plt.subplots(figsize=(FULL_W, 66 * MM))
    rng = np.random.default_rng(1)
    for i, pol in enumerate(W7_POLICIES):
        u = t0[t0.policy == pol].unsafe.to_numpy()
        ax.scatter(u, i + rng.uniform(-0.18, 0.18, len(u)), s=14, marker=W7_MARK[pol],
                   facecolor=W7_COLOR[pol], edgecolor="white", linewidth=0.5, zorder=3)
        ax.plot([u.mean()] * 2, [i - 0.3, i + 0.3], color=INK, lw=1.6, zorder=4)
        ax.text(1.03, i, f"mean {u.mean():.1%}  ·  {int((u > E.ALPHA).sum())} of {len(u)} over 5%",
                va="center", fontsize=7, color=INK2, transform=ax.get_yaxis_transform())
    ax.axvline(E.ALPHA, color=INK2, lw=0.8, ls=(0, (3, 2)), zorder=2)
    ax.text(E.ALPHA + 0.008, len(W7_POLICIES) - 0.45, "α = 5%", fontsize=7, color=INK2)
    ax.set_yticks(range(len(W7_POLICIES)), [W7_LABEL[p] for p in W7_POLICIES])
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.6, len(W7_POLICIES) - 0.3)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Share of runs that switched on an unsafe finding (whole cohort; per transfer, all budgets)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Stronger comparators across the same 31 transfers (tick: mean)", pad=8)
    save(fig, "F5_comparators")


def f6_monitoring():
    r = pd.read_csv(E.OUT / "W8long_runs.csv")
    r = r[(r.remedy != "BLOCK")]
    r = r[~r.unsafe_a.astype(bool)]
    t_pre = 2000
    safe = r[~r.unsafe_b.astype(bool)]
    drift = r[(r.site_b != r.site_a) & r.unsafe_b.astype(bool)]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(FULL_W, 62 * MM), gridspec_kw={"width_ratios": [1, 1.5]})
    mons = list(W8_MON)
    fa = [(safe[m] >= 0).mean() for m in mons]
    y = np.arange(len(mons))[::-1]
    a1.barh(y, fa, height=0.55, color=[W8_MON[m][1] for m in mons], zorder=3)
    for yy, v in zip(y, fa):
        a1.text(min(v, 0.78) + 0.02, yy, f"{v:.1%}", va="center", fontsize=7, color=INK)
    a1.set_yticks(y, [W8_MON[m][0] for m in mons], fontsize=7)
    a1.set_xlim(0, 1)
    a1.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    a1.set_xlabel("Safe deployments with any alarm\n(18,000 audits)")
    a1.grid(axis="y", visible=False)
    a1.set_title("False alarms", loc="left")
    d = np.arange(0, 16001, 50)
    for m in ["MONITOR", "CUSUM-20k", "CHECK-TEST", "CHECK-POINT"]:
        delay = (drift[m] - t_pre + 1).where(drift[m] >= t_pre).to_numpy()
        curve = [(delay <= x).mean() for x in d]
        a2.plot(d, curve, color=W8_MON[m][1], ls=W8_MON[m][2], lw=2, label=W8_MON[m][0])
    a2.set_xlim(0, 16000)
    a2.set_ylim(0, 1)
    a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    a2.set_xticks([0, 4000, 8000, 12000, 16000], ["0", "4k", "8k", "12k", "16k"])
    a2.set_xlabel("Audits after the population changed")
    a2.set_ylabel("Drifts to an unsafe population detected")
    a2.set_title(f"Detection ({len(drift):,} runs, {drift.drop_duplicates(['site_a', 'finding', 'site_b']).shape[0]} scenarios)",
                 loc="left")
    a2.legend(frameon=False, fontsize=6.8, loc="lower right", bbox_to_anchor=(1, 0.12))
    fig.tight_layout(w_pad=2.5)
    save(fig, "F6_monitoring")


def main():
    style()
    all_runs = {s: runs(tag) for s, tag in SEEDS.items()}
    e5 = pd.read_csv(E.OUT / "E3_E5_labels.csv")
    f1_unsafe(all_runs)
    f2_decisions(all_runs[0])
    f3_labels(e5)
    f4_judges(all_runs[0])
    f5_comparators()
    f6_monitoring()


if __name__ == "__main__":
    main()
