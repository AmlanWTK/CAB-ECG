"""Chapter figures and tables for the sepsis CAB study (reads the CSVs written by E1-E12).

  fig_workflow         the CAB procedure as a flow chart (no data needed)
  fig1_transfer        imported vs local model at each hospital, with 95% bootstrap CIs (E2)
  fig2_cab_decisions   what CAB switched on, by label budget, in each setting (E3mac100, primary criterion)
  fig3_unsafe          share of runs that switched on an unsafe configuration, by policy and budget
  fig4_overall         unsafe and silent-failure rates per policy over ALL settings, criteria, budgets
  fig5_baselines       CAB against practical alternatives: unsafe and correct decisions (E10)
  fig6_labels          septic patients needed to certify, by the model's margin over the target (E5)
  fig7_validity        measured unsafe rate of every setting against the nominal alpha (E12)
  fig8_tolerance       approval at home by the hospital's false-alert tolerance (E11)
  fig_labels_tolerance fig6_labels and fig8_tolerance side by side (the chapter's version)
  chapter_tables.md    cohort, E1/E2 performance, E2 CIs, E3mac100 primary results

Each figure is written as PDF (vector, for the publisher) and PNG (300 dpi, for drafts).
Sized for Springer full text width (174 mm); grayscale-safe via markers, ramps and hatching.

Run from the repository root:
    python code\\sepsis_figures.py
Writes outputs/sepsis/figures/.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Patch  # noqa: E402

from cabsepsis.data import REPO  # noqa: E402

SEP = REPO / "outputs" / "sepsis"
FIG = SEP / "figures"
MM = 1 / 25.4
FULL_W = 174 * MM
PRIMARY = (0.80, 0.05)
SOURCE = "E3mac100"   # the final 100-repeat run, all on one machine

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#ffffff"
POLICY_ORDER = ["CAB", "AS-IS", "LABEL-FREE", "RECALIBRATE", "FINE-TUNE", "RETRAIN", "CLOSED-TEST"]
POLICY_COLOR = {"CAB": "#2a78d6", "AS-IS": "#eb6834", "LABEL-FREE": "#1baf7a",
                "RECALIBRATE": "#eda100", "FINE-TUNE": "#e87ba4", "RETRAIN": "#008300",
                "CLOSED-TEST": "#7a5cc7"}
POLICY_MARK = {"CAB": "o", "AS-IS": "s", "LABEL-FREE": "^", "RECALIBRATE": "D",
               "FINE-TUNE": "v", "RETRAIN": "P", "CLOSED-TEST": "X"}
POLICY_LABEL = {"CAB": "CAB (certified)", "AS-IS": "As-is", "LABEL-FREE": "Label-free reset",
                "RECALIBRATE": "Recalibrate", "FINE-TUNE": "Fine-tune", "RETRAIN": "Retrain locally",
                "CLOSED-TEST": "Classical updating (closed test)"}
POLICY_SHORT = {"CAB": "CAB", "AS-IS": "As-is", "LABEL-FREE": "Label-free", "RECALIBRATE": "Recalibrate",
                "FINE-TUNE": "Fine-tune", "RETRAIN": "Retrain", "CLOSED-TEST": "Closed test"}
BASELINE_ORDER = ["CAB", "LTT-DIRECT", "NAIVE-500", "NAIVE-VAL", "LABEL-SHIFT"]
BASELINE_LABEL = {"CAB": "CAB (certified)", "LTT-DIRECT": "Learn-then-Test, no order",
                  "NAIVE-500": "Local validation, 500 patients", "NAIVE-VAL": "Point-estimate validation",
                  "LABEL-SHIFT": "Prevalence correction"}
GROUP_COLOR = {"cross-hospital": "#2a78d6", "home": "#eb6834", "ICU unit": "#1baf7a"}
REMEDY_ORDER = ["KEEP", "CALIBRATE", "ADAPT", "BLOCK"]
REMEDY_COLOR = {"KEEP": "#86b6ef", "CALIBRATE": "#2a78d6", "ADAPT": "#104281", "BLOCK": "#dddcd7"}
REMEDY_LABEL = {"KEEP": "Keep", "CALIBRATE": "Calibrate", "ADAPT": "Adapt", "BLOCK": "Block"}
SITE = {"A": "Beth Israel", "B": "Emory"}
DIRECTIONS = ["A->B", "B->A", "A->A", "B->B"]
LOCAL_C, IMPORTED_C = "#2a78d6", "#eb6834"


def direction_title(d):
    s, t = d.split("->")
    if s == t:
        return f"{SITE[s]} \u2192 {SITE[t]} (control)"
    return f"{SITE[s]} model → {SITE[t]}"


def style():
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "axes.edgecolor": MUTED,
        "axes.linewidth": 0.6, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.axisbelow": True, "axes.titleweight": "bold", "axes.titlecolor": INK,
        "axes.titlelocation": "left", "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote figures/{name}.pdf and .png")


def fmt_n(n):
    return f"{n // 1000}k" if n >= 1000 else str(n)


def minus(s):
    return s.replace("-", "\u2212")


def md(df):
    """DataFrame -> GitHub markdown table (no extra packages)."""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(" --- " for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in row) + " |")
    return "\n".join(lines)


def parse_ci(s):
    lo, hi = s.strip("[]").split(",")
    return float(lo), float(hi)


def fig_workflow():
    fig, ax = plt.subplots(figsize=(FULL_W, 104 * MM))
    ax.set_xlim(0, 174); ax.set_ylim(0, 104); ax.axis("off")

    def box(x, y, w, h, title, body, face, edge=MUTED, tc=INK, bc=INK2):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6",
                                    fc=face, ec=edge, lw=0.8))
        ax.text(x + 2.5, y + h - 2.5, title, fontsize=7.4, weight="bold", color=tc, va="top")
        if body:
            ax.text(x + 2.5, y + h - 7.0, body, fontsize=6.5, color=bc, va="top", linespacing=1.4)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.8,
                                                             shrinkA=0, shrinkB=0, mutation_scale=7))

    def note(x, y, s, ha="left"):
        ax.text(x, y, s, fontsize=6.3, color=INK2, ha=ha, va="center", style="italic",
                bbox=dict(fc=SURFACE, ec="none", pad=0.4), zorder=5)

    soft = "#f4f3ef"
    box(2, 76, 58, 26, "Fixed before any local label",
        "Imported model, vendor threshold $\\tau_{home}$\n"
        "Sensitivity target $s^*$\n"
        "False-alert limit $f^* = F_{home} + m$\n"
        "Error level $\\alpha$; each test at $\\alpha/4$", soft)
    box(66, 76, 48, 26, "Label n patients at random",
        "Split within septic / non-septic:\n"
        "fit half (to adapt the model) and\n"
        "certification half (to test it).\n"
        "Stage 1 uses all n labels.", soft)
    arrow(60, 89, 66, 89)
    box(2, 41, 112, 29, "Stage 1: the imported model, all n labels",
        "1. Certify a threshold $\\tau$: the highest one whose sensitivity $\\geq s^*$\n"
        "    passes an exact binomial test (fixed-sequence from the sensitive end)\n"
        "2. Exact test of the false-alert rate $\\leq f^*$ at $\\tau$\n"
        "3. If both pass and $\\tau_{home} \\leq \\tau$: also test false alerts at $\\tau_{home}$",
        "#eef4fc", edge="#86b6ef")
    arrow(90, 76, 90, 70)
    box(2, 6, 112, 29, "Stage 2: an adapted model (only if Stage 1 fails)",
        "1. Fit on the fit half: extra boosting rounds, leaf refit, or both\n"
        "    (chosen by AUROC on an early-stopping part of the fit half)\n"
        "2. On the certification half: certify a threshold $\\tau_A$ and\n"
        "    test the false-alert rate at $\\tau_A$, as in Stage 1",
        "#e7eef8", edge="#2a78d6")
    arrow(58, 41, 58, 35)
    note(60, 38, "a test at $\\tau$ fails")
    out = [("KEEP", 84, "model and vendor threshold"), ("CALIBRATE", 60, "model, new threshold $\\tau$"),
           ("ADAPT", 30, "adapted model, threshold $\\tau_A$"), ("BLOCK", 6, "nothing switched on;\nusual care")]
    for rem, y, txt in out:
        face = REMEDY_COLOR[rem]
        tc = SURFACE if rem in ("CALIBRATE", "ADAPT") else INK
        box(130, y, 42, 14, rem.title(), txt, face, edge=face, tc=tc, bc=tc)
    arrow(114, 64, 130, 91); note(121, 82, "all three\npass", ha="center")
    arrow(114, 56, 130, 67); note(121, 57.5, "tests at $\\tau$\npass", ha="center")
    arrow(114, 26, 130, 37); note(121, 27.5, "both\npass", ha="center")
    arrow(114, 13, 130, 13); note(121, 16.5, "either\nfails", ha="center")
    ax.text(2, 0.5, "Guarantee: P(switching on a deployment with sensitivity $< s^*$ or false-alert rate $> f^*$) "
                    "$\\leq 4 \\times \\alpha/4 = \\alpha$, for any shift and any n.",
            fontsize=6.6, color=INK, va="bottom")
    save(fig, "fig_workflow")


# ----------------------------------------------------------------------------------------------
def fig1_transfer(ci):
    metrics = [("AUROC_hourly", "AUROC (hourly)"), ("utility", "Normalised utility"),
               ("sensitivity_patient", "Sensitivity (patients)"),
               ("false_alert_patients", "Non-septic patients alerted")]
    targets = [("B", "A"), ("A", "B")]
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 52 * MM), sharey=True)
    for ax, (tgt, src) in zip(axes, targets):
        d = ci[(ci.target == tgt)].set_index("metric")
        ys = np.arange(len(metrics))[::-1]
        for y, (m, _) in zip(ys, metrics):
            r = d.loc[m]
            (llo, lhi), (ilo, ihi) = parse_ci(r.local_CI), parse_ci(r.imported_CI)
            ax.errorbar(r.local, y + 0.12, xerr=[[r.local - llo], [lhi - r.local]], fmt="o", ms=5,
                        color=LOCAL_C, mec=SURFACE, mew=0.8, elinewidth=1, capsize=0, zorder=3)
            ax.errorbar(r.imported, y - 0.12, xerr=[[r.imported - ilo], [ihi - r.imported]], fmt="s",
                        ms=5, color=IMPORTED_C, mec=SURFACE, mew=0.8, elinewidth=1, capsize=0, zorder=3)
            dlo, dhi = parse_ci(r.difference_CI)
            ax.text(1.02, y, f"Δ {r.difference:+.2f}\n[{dlo:+.2f}, {dhi:+.2f}]",
                    transform=ax.get_yaxis_transform(), va="center", ha="left", fontsize=6.8, color=INK2)
        ax.set_yticks(ys, [lab for _, lab in metrics])
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.6, len(metrics) - 0.4)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Value (0–1)")
        ax.set_title(f"At {SITE[tgt]}: own model vs {SITE[src]} model", pad=6)
    handles = [Line2D([], [], marker="o", ls="", color=LOCAL_C, ms=5, label="Local model (trained at this hospital)"),
               Line2D([], [], marker="s", ls="", color=IMPORTED_C, ms=5, label="Imported model, unchanged")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.2))
    fig.subplots_adjust(wspace=0.55)
    save(fig, "fig1_transfer")


def fig2_cab_decisions(runs, oracle):
    cab = runs[(runs.policy == "CAB") & (runs.s_star == PRIMARY[0]) & (runs.margin == PRIMARY[1])]
    mix = cab.groupby(["direction", "n_labelled"])["remedy"].value_counts(normalize=True).unstack(fill_value=0)
    fig, axes = plt.subplots(2, 2, figsize=(FULL_W, 110 * MM), sharey=True)
    for ax, d in zip(axes.flat, DIRECTIONS):
        if d not in mix.index.get_level_values(0):
            ax.set_visible(False)
            continue
        m = mix.loc[d].reindex(columns=REMEDY_ORDER, fill_value=0)
        x = np.arange(len(m))
        bottom = np.zeros(len(m))
        for rem in REMEDY_ORDER:
            v = 100 * m[rem].to_numpy()
            ax.bar(x, v, bottom=bottom, width=0.72, color=REMEDY_COLOR[rem], edgecolor=SURFACE,
                   linewidth=1.0, hatch="////" if rem == "BLOCK" else None, label=REMEDY_LABEL[rem])
            bottom += v
        ax.set_xticks(x, [fmt_n(n) for n in m.index])
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.grid(axis="x", visible=False)
        o = oracle[(oracle.direction == d) & (oracle.s_star == PRIMARY[0]) & (oracle.margin == PRIMARY[1])]
        right = o.oracle_remedy.iloc[0].replace("|", " or ").title() if len(o) else "?"
        ax.set_title(direction_title(d), pad=14)
        ax.text(0, 1.015, f"Correct remedy (full data): {right}", transform=ax.transAxes,
                fontsize=7, color=INK2, va="bottom")
    for ax in axes[:, 0]:
        ax.set_ylabel("Share of runs (%)")
    for ax in axes[1, :]:
        ax.set_xlabel("Labelled patients at the target hospital")
    plt.rcParams["hatch.color"] = "#b8b7b0"
    handles = [Patch(facecolor=REMEDY_COLOR[r], edgecolor=SURFACE, hatch="////" if r == "BLOCK" else None,
                     label=REMEDY_LABEL[r]) for r in REMEDY_ORDER]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.07),
               title="What CAB switched on:", title_fontsize=7.5, alignment="left")
    fig.subplots_adjust(hspace=0.62, wspace=0.12)
    save(fig, "fig2_cab_decisions")


def fig3_unsafe(summ):
    p = summ[(summ.s_star == PRIMARY[0]) & (summ.margin == PRIMARY[1])]
    fig, axes = plt.subplots(2, 2, figsize=(FULL_W, 110 * MM), sharey=True)
    for ax, d in zip(axes.flat, DIRECTIONS):
        q = p[p.direction == d]
        if q.empty:
            ax.set_visible(False)
            continue
        budgets = sorted(q.n_labelled.unique())
        x = np.arange(len(budgets))
        series = {pol: tuple(np.round(100 * q[q.policy == pol].set_index("n_labelled")
                                      .reindex(budgets).unsafe_rate.to_numpy(), 1)) for pol in POLICY_ORDER}
        groups = {}
        for pol, s in series.items():
            groups.setdefault(s, []).append(POLICY_SHORT[pol])
        same = [g for g in groups.values() if len(g) > 1]
        note = "; ".join(", ".join(g) for g in same)
        ax.text(0, 1.015, f"Overlapping lines: {note}" if note else "", transform=ax.transAxes,
                fontsize=6.8, color=INK2, va="bottom")
        for pol in POLICY_ORDER[::-1]:
            r = q[q.policy == pol].set_index("n_labelled").reindex(budgets)
            lw, z = (2.2, 5) if pol == "CAB" else (1.2, 3)
            ax.plot(x, 100 * r.unsafe_rate, color=POLICY_COLOR[pol], marker=POLICY_MARK[pol], ms=4.5,
                    lw=lw, mec=SURFACE, mew=0.6, zorder=z, label=POLICY_LABEL[pol])
        ax.axhline(5, color=INK2, lw=0.8, ls=(0, (4, 3)), zorder=2)
        ax.set_xticks(x, [fmt_n(n) for n in budgets])
        ax.set_xlim(-0.3, len(budgets) - 0.7)
        ax.set_ylim(-3, 103)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_title(direction_title(d), pad=14)
    for ax in axes[:, 0]:
        ax.set_ylabel("Runs that switched on an\nunsafe configuration (%)")
    for ax in axes[1, :]:
        ax.set_xlabel("Labelled patients at the target hospital")
    handles = [Line2D([], [], color=POLICY_COLOR[p], marker=POLICY_MARK[p], ms=4.5,
                      lw=2.2 if p == "CAB" else 1.2, label=POLICY_LABEL[p]) for p in POLICY_ORDER]
    handles.append(Line2D([], [], color=INK2, lw=0.8, ls=(0, (4, 3)), label="5% bound guaranteed for CAB"))
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.12))
    fig.subplots_adjust(hspace=0.55, wspace=0.12)
    save(fig, "fig3_unsafe")


def fig4_overall(summ):
    g = summ.groupby("policy").agg(unsafe=("unsafe_rate", "mean"),
                                   silent=("silent_failure_rate", "mean")).reindex(POLICY_ORDER)
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 56 * MM), sharey=True)
    y = np.arange(len(POLICY_ORDER))[::-1]
    for ax, col, title in [(axes[0], "unsafe", "Switched on an unsafe configuration"),
                           (axes[1], "silent", "Silent failure: looked safe on its own data")]:
        for yi, pol in zip(y, POLICY_ORDER):
            v = 100 * g.loc[pol, col]
            if pol == "LABEL-FREE" and col == "silent":
                ax.text(1, yi, "n/a (no labels used)", va="center", fontsize=6.8, color=MUTED)
                continue
            ax.barh(yi, v, height=0.62, color=POLICY_COLOR[pol], edgecolor=SURFACE, linewidth=1.0)
            ax.text(v + 1.5, yi, f"{v:.1f}%", va="center", fontsize=7, color=INK)
        ax.set_xlim(0, 108)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.grid(axis="y", visible=False)
        ax.set_title(title, pad=6)
        ax.set_xlabel("Mean share of runs (%)")
    axes[0].set_yticks(y, [POLICY_LABEL[p] for p in POLICY_ORDER])
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig4_overall")


def fig5_baselines(summ):
    s = summ[summ.policy.isin(BASELINE_ORDER)].copy()
    s["group"] = np.where(s.direction.str[0] == s.direction.str[3], "home", "cross-hospital")
    g = s.groupby(["policy", "group"]).agg(unsafe=("unsafe_rate", "mean"), correct=("correct_rate", "mean"))
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 58 * MM), sharey=True)
    y = np.arange(len(BASELINE_ORDER))[::-1]
    h = 0.36
    for ax, col, title in [(axes[0], "unsafe", "Switched on an unsafe configuration"),
                           (axes[1], "correct", "Chose the correct remedy")]:
        for k, (grp, off) in enumerate([("cross-hospital", h / 2), ("home", -h / 2)]):
            for yi, pol in zip(y, BASELINE_ORDER):
                v = g[col].get((pol, grp), np.nan)
                if np.isnan(v):
                    if k == 0:
                        ax.text(1, yi, "n/a (no remedy chosen)", va="center", fontsize=6.8, color=MUTED)
                    continue
                v *= 100
                ax.barh(yi + off, v, height=h, color=GROUP_COLOR[grp], edgecolor=SURFACE, linewidth=0.8,
                        hatch="////" if grp == "home" else None)
                ax.text(v + 1.5, yi + off, f"{v:.1f}%", va="center", fontsize=6.5, color=INK)
        ax.set_xlim(0, 112)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.grid(axis="y", visible=False)
        ax.set_title(title, pad=6)
        ax.set_xlabel("Mean share of runs, all criteria and budgets (%)")
    axes[0].set_yticks(y, [BASELINE_LABEL[p] for p in BASELINE_ORDER])
    plt.rcParams["hatch.color"] = SURFACE
    handles = [Patch(facecolor=GROUP_COLOR["cross-hospital"], label="Imported from the other hospital"),
               Patch(facecolor=GROUP_COLOR["home"], hatch="////", edgecolor=SURFACE,
                     label="Same hospital (control)")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.2))
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig5_baselines")


def fig6_labels(an):
    a = an[an.table == "septic"]
    fig, ax = plt.subplots(figsize=(FULL_W * 0.55, 62 * MM))
    colors = {0.75: "#86b6ef", 0.80: "#2a78d6", 0.85: "#104281"}
    marks = {0.75: "^", 0.80: "o", 0.85: "s"}
    for s, q in a.groupby("target"):
        q = q.sort_values("gap")
        ax.plot(100 * q.gap, q.needed, marker=marks[s], color=colors[s], ms=4.5, lw=1.4, mec=SURFACE,
                mew=0.6, label=f"target sensitivity {s:.2f}")
    ax.set_yscale("log")
    ticks = [100, 200, 500, 1000, 2000, 5000]
    ax.set_yticks(ticks, [f"{v:,}" for v in ticks])
    ax.minorticks_off()
    ax.set_xlabel("True sensitivity above the target (percentage points)")
    ax.set_ylabel("Labelled septic patients needed")
    ax.set_xticks(sorted(100 * a.gap.unique()))
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("Labels needed to certify sensitivity", pad=6)
    save(fig, "fig6_labels")


def fig7_validity(val):
    v = val[(val.policy == "CAB") & val.tag.isin(["E3mac100", "E6units", "E12alpha01", "E12alpha10"])]
    alphas = sorted(v.alpha.unique())
    groups = ["cross-hospital", "home", "ICU unit"]
    fig, ax = plt.subplots(figsize=(FULL_W, 62 * MM))
    rng = np.random.default_rng(0)
    w = 0.26
    for i, a in enumerate(alphas):
        for j, grp in enumerate(groups):
            q = v[np.isclose(v.alpha, a) & (v.group == grp)]
            if q.empty:
                continue
            x0 = i + (j - 1) * w
            ax.scatter(x0 + rng.uniform(-w / 3, w / 3, len(q)), 100 * q.rate, s=7, color=GROUP_COLOR[grp],
                       alpha=0.55, linewidths=0, zorder=3)
            ax.plot([x0 - w / 2.4, x0 + w / 2.4], [100 * q.rate.mean()] * 2, color=INK, lw=1.6, zorder=4)
        ax.plot([i - 0.45, i + 0.45], [100 * a] * 2, color=INK2, lw=0.9, ls=(0, (4, 3)), zorder=2)
    ax.set_xticks(range(len(alphas)), [f"α = {a:g}" for a in alphas])
    ax.set_xlim(-0.55, len(alphas) - 0.45)
    ax.set_ylabel("Runs that switched on an\nunsafe configuration (%)")
    ax.grid(axis="x", visible=False)
    ax.set_title("Measured unsafe rate of every setting (100 runs each) against the nominal level", pad=6)
    handles = [Line2D([], [], marker="o", ls="", color=GROUP_COLOR[g], ms=4, label=
                      {"cross-hospital": "Other hospital", "home": "Same hospital", "ICU unit": "One ICU type"}[g])
               for g in groups]
    handles += [Line2D([], [], color=INK, lw=1.6, label="Mean"),
                Line2D([], [], color=INK2, lw=0.9, ls=(0, (4, 3)), label="Nominal α")]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.1))
    save(fig, "fig7_validity")


def fig8_tolerance(sim):
    q = sim[np.isclose(sim.s_star, PRIMARY[0]) & np.isclose(sim.headroom, 0)].copy()
    q["approved"] = q.P_KEEP + q.P_CALIBRATE
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 58 * MM), sharey=True)
    colors = {0.0: "#86b6ef", 0.05: "#2a78d6", 0.10: "#104281"}
    marks = {0.0: "^", 0.05: "o", 0.10: "s"}
    for ax, d in zip(axes, ["A->A", "B->B"]):
        r = q[q.direction == d]
        budgets = sorted(r.n_labelled.unique())
        x = np.arange(len(budgets))
        for m in sorted(r.margin.unique()):
            s = r[np.isclose(r.margin, m)].set_index("n_labelled").reindex(budgets)
            ax.plot(x, 100 * s.approved, marker=marks[round(m, 2)], color=colors[round(m, 2)], ms=4.5, lw=1.4,
                    mec=SURFACE, mew=0.6, label=f"+{100 * m:.0f} points")
        ax.set_xticks(x, [fmt_n(int(n)) for n in budgets])
        ax.set_ylim(-3, 103)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_title(direction_title(d), pad=6)
        ax.set_xlabel("Labelled patients")
    axes[0].set_ylabel("Runs in which CAB approved\nthe model (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.3),
               title="False alerts tolerated above the home rate:", title_fontsize=7.5)
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig8_tolerance")


def fig_labels_tolerance(an, sim):
    """(a) the label calculator; (b, c) approval at home by false-alert tolerance (E5 + E11)."""
    fig = plt.figure(figsize=(FULL_W, 60 * MM))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1, 1], wspace=0.32)
    ax = fig.add_subplot(gs[0])
    a = an[an.table == "septic"]
    colors = {0.75: "#86b6ef", 0.80: "#2a78d6", 0.85: "#104281"}
    marks = {0.75: "^", 0.80: "o", 0.85: "s"}
    for s, q in a.groupby("target"):
        q = q.sort_values("gap")
        ax.plot(100 * q.gap, q.needed, marker=marks[s], color=colors[s], ms=4, lw=1.3, mec=SURFACE,
                mew=0.6, label=f"s* = {s:.2f}")
    ax.set_yscale("log")
    ticks = [100, 200, 500, 1000, 2000, 5000]
    ax.set_yticks(ticks, [f"{v:,}" for v in ticks])
    ax.minorticks_off()
    ax.set_xticks(sorted(100 * a.gap.unique()))
    ax.set_xlabel("True sensitivity above target (points)")
    ax.set_ylabel("Septic patients needed")
    ax.legend(frameon=False, loc="upper right", fontsize=6.8)
    ax.set_title("(a) Labels to certify sensitivity", pad=6)
    q = sim[np.isclose(sim.s_star, PRIMARY[0]) & np.isclose(sim.headroom, 0)].copy()
    q["approved"] = q.P_KEEP + q.P_CALIBRATE
    tol_c = {0.0: "#86b6ef", 0.05: "#2a78d6", 0.10: "#104281"}
    tol_m = {0.0: "^", 0.05: "o", 0.10: "s"}
    for k, d in enumerate(["A->A", "B->B"]):
        ax = fig.add_subplot(gs[k + 1], sharey=None)
        r = q[q.direction == d]
        budgets = sorted(r.n_labelled.unique())
        x = np.arange(len(budgets))
        for m in sorted(r.margin.unique()):
            s = r[np.isclose(r.margin, m)].set_index("n_labelled").reindex(budgets)
            ax.plot(x, 100 * s.approved, marker=tol_m[round(m, 2)], color=tol_c[round(m, 2)], ms=4, lw=1.3,
                    mec=SURFACE, mew=0.6, label=f"+{100 * m:.0f} points")
        ax.set_xticks(x, [fmt_n(int(n)) for n in budgets])
        ax.set_ylim(-3, 103)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xlabel("Labelled patients")
        ax.set_title(f"({'bc'[k]}) {SITE[d[0]]}, home", pad=6)
        if k == 0:
            ax.set_ylabel("Runs approved (%)")
        else:
            ax.set_yticklabels([])
            ax.legend(frameon=False, loc="lower right", fontsize=6.8, title="Tolerance", title_fontsize=6.8)
    save(fig, "fig_labels_tolerance")


# ----------------------------------------------------------------------------------------------
def tables(e1, ci, summ, oracle):
    out = ["# Chapter tables (sepsis CAB study)", ""]
    try:
        from cabsepsis.data import load_all, patient_table
        pt = patient_table(load_all())
        rows = []
        for s, d in pt.groupby("site"):
            rows.append({"Hospital": SITE[s], "Patients": f"{len(d):,}",
                         "Septic, n (%)": f"{int(d.septic.sum()):,} ({100 * d.septic.mean():.1f})",
                         "Age, median (IQR)": f"{d.age.median():.0f} ({d.age.quantile(.25):.0f}–{d.age.quantile(.75):.0f})",
                         "Male (%)": f"{100 * d.male.mean():.1f}",
                         "ICU hours, median (IQR)": f"{d.n_hours.median():.0f} ({d.n_hours.quantile(.25):.0f}–{d.n_hours.quantile(.75):.0f})",
                         "Patient-hours": f"{int(d.n_hours.sum()):,}"})
        out += ["## Table 1. Cohorts", "", md(pd.DataFrame(rows)), ""]
    except Exception as exc:  # data not on this machine
        out += [f"(Table 1 skipped: {exc})", ""]

    if e1 is not None:
        keep = e1[(e1.method == "LightGBM") | (e1.threshold_rule.str.startswith("standard"))].copy()
        keep["Model"] = keep.method.str.replace("_mod", " (modified)")
        keep["Trained at"] = keep.trained_at.map(SITE).fillna("–")
        keep["Evaluated at"] = keep.evaluated_at.map(SITE)
        cols = {"AUROC_hourly": "AUROC", "AUPRC_hourly": "AUPRC", "utility": "Utility",
                "sensitivity_patient": "Sensitivity", "alarms_per_patient_day": "Alarms/patient-day",
                "alert_hours_pct": "Alert-hours (%)"}
        t = keep[["Model", "Trained at", "Evaluated at", "threshold_rule"] + list(cols)].rename(columns=cols)
        t = t.rename(columns={"threshold_rule": "Threshold"})
        out += ["## Table 2. Test-set performance: local and imported LightGBM, bedside scores",
                "", md(t.round(3)), ""]

    c = ci.copy()
    c["At"] = c.target.map(SITE)
    c["Imported from"] = c.imported_from.map(SITE)
    c["Local"] = c.local.round(3).astype(str) + " " + c.local_CI
    c["Imported"] = c.imported.round(3).astype(str) + " " + c.imported_CI
    c["Difference"] = c.difference.round(3).astype(str) + " " + c.difference_CI
    out += ["## Table 3. Imported vs local model at each hospital (95% patient-bootstrap CI)", "",
            md(c[["At", "Imported from", "metric", "Local", "Imported", "Difference"]]), ""]

    p = summ[(summ.s_star == PRIMARY[0]) & (summ.margin == PRIMARY[1])].copy()
    p["Setting"] = p.direction.map(direction_title)
    p["Unsafe (%)"] = (100 * p.unsafe_rate).round(1)
    p["Silent failure (%)"] = (100 * p.silent_failure_rate).round(1)
    p["Switched on (%)"] = (100 * p.activated_rate).round(1)
    p["Correct remedy (%)"] = (100 * p.correct_rate).round(1)
    p["Utility"] = p.utility_mean.round(3)
    t = p[["Setting", "n_labelled", "policy", "Switched on (%)", "Unsafe (%)", "Silent failure (%)",
           "Correct remedy (%)", "Utility"]].rename(columns={"n_labelled": "Labelled n", "policy": "Policy"})
    out += ["## Table 4. Remedy selection, primary criterion (sensitivity >= 0.80; false alerts <= home + 0.05)",
            "", md(t), ""]
    o = oracle.copy()
    o["Setting"] = o.direction.map(direction_title)
    out += ["## Table S1. Correct remedy (from full target data) for every safety criterion", "",
            md(o[["Setting", "s_star", "margin", "f_star", "oracle_remedy"]].round(3)), ""]
    (FIG / "chapter_tables.md").write_text("\n".join(out), encoding="utf-8")
    print("  wrote figures/chapter_tables.md")


def main():
    style()
    ci = pd.read_csv(SEP / "E2_ci.csv")
    summ = pd.read_csv(SEP / f"{SOURCE}_summary.csv")
    runs = pd.read_csv(SEP / f"{SOURCE}_runs.csv", usecols=["direction", "n_labelled", "s_star", "margin",
                                                             "policy", "remedy"])
    oracle = pd.read_csv(SEP / f"{SOURCE}_oracle.csv")
    e1 = pd.read_csv(SEP / "E1_E2_results.csv") if (SEP / "E1_E2_results.csv").exists() else None
    print("Making figures ...")
    fig_workflow()
    fig1_transfer(ci)
    fig2_cab_decisions(runs, oracle)
    fig3_unsafe(summ)
    fig4_overall(summ)
    fig5_baselines(pd.read_csv(SEP / "E10baselines_summary.csv"))
    fig6_labels(pd.read_csv(SEP / "E5_analytic.csv"))
    fig7_validity(pd.read_csv(SEP / "E12_validity.csv"))
    fig8_tolerance(pd.read_csv(SEP / "E11_headroom_sim.csv"))
    fig_labels_tolerance(pd.read_csv(SEP / "E5_analytic.csv"), pd.read_csv(SEP / "E11_headroom_sim.csv"))
    tables(e1, ci, summ, oracle)
    print(f"Done: {FIG}")


if __name__ == "__main__":
    main()
