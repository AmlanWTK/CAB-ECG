"""CAB Sepsis Monitor: a prototype ICU early-warning application with a certified deployment gate.

  1. Deployment gate  an imported sepsis model arrives with its vendor threshold; the hospital's
                      labelled patients are used to decide KEEP / CALIBRATE / ADAPT / BLOCK, with
                      the exact statistical evidence for each step.
  2. Ward monitor     replays real ICU patients (PhysioNet/CinC Challenge 2019 test split) hour by
                      hour with whatever the gate switched on, or modified NEWS2 if it blocked.
  3. About            what the application does and does not claim.

Research prototype on public retrospective data. Not for clinical use.

Run on the compute desktop, from the repository root (needs E1 models and the data cache):
    streamlit run app\\sepsis_monitor.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import altair as alt  # noqa: E402
import lightgbm as lgb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from cabsepsis.data import REPO, load_all  # noqa: E402
from cabsepsis.deploy import (SiteFrame, draw_labels, gate_explained, model_dict,  # noqa: E402
                              vendor_package)
from cabsepsis.features import load_features  # noqa: E402
from cabsepsis.scores import compute_scores  # noqa: E402
from sepsis_e3_cab import fit_adapt, sigmoid, split_patients  # noqa: E402
from cabsepsis.cab import largest_threshold_for, rates  # noqa: E402

OUT = REPO / "outputs" / "sepsis"
SITE = {"A": "Beth Israel", "B": "Emory"}
ALPHA = 0.05
NEWS2_CUT = 5.0
VITALS_SHOWN = [("HR", "Heart rate (/min)"), ("MAP", "Mean arterial pressure (mmHg)"),
                ("Resp", "Respiratory rate (/min)"), ("Temp", "Temperature (°C)"),
                ("O2Sat", "SpO₂ (%)")]
DECISION_STYLE = {
    "KEEP": ("#1b7f4b", "Keep the imported model as it is",
             "Its home threshold meets both safety requirements here, with proof."),
    "CALIBRATE": ("#2a78d6", "Calibrate: same model, new local threshold",
                  "The model ranks patients well enough here, but needs a new alert threshold."),
    "ADAPT": ("#104281", "Adapt: model updated on local data",
              "Only an updated version of the model meets both requirements here."),
    "BLOCK": ("#a8322d", "Block: do not switch the AI on",
              "No option could be proven safe with the patients labelled so far. "
              "The unit keeps using modified NEWS2."),
}

st.set_page_config(page_title="CAB Sepsis Monitor", page_icon="\U0001fa7a", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.6rem;}
.badge {display:inline-block;padding:.15rem .55rem;border-radius:.35rem;font-weight:600;
        font-size:.85rem;color:white;}
.decision {border-radius:.6rem;padding:1rem 1.2rem;color:white;margin:.4rem 0 1rem 0;}
.decision h3 {color:white;margin:0 0 .25rem 0;font-size:1.25rem;}
.decision p {margin:0;opacity:.95;}
.small {font-size:.85rem;color:#5b5a56;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------------------ data
@st.cache_resource(show_spinner="Loading ICU data and features (first start only, about a minute) ...")
def load():
    df = load_all().sort_values(["pid", "hour"]).reset_index(drop=True)
    split = pd.read_csv(OUT / "splits.csv", index_col=0)["split"]
    df["split"] = df["pid"].map(split)
    X, meta = load_features(df)
    boosters = {s: lgb.Booster(model_file=str(OUT / f"lgbm_site{s}.txt")) for s in "AB"}
    return df, X, meta, boosters


@st.cache_resource(show_spinner="Preparing this hospital's data ...", max_entries=2)
def site_context(src, tgt):
    df, X, meta, boosters = load()
    b = boosters[src]
    mv = (df["site"].eq(src) & df["split"].eq("val")).to_numpy()
    sfv = SiteFrame(meta[mv])
    pv = b.predict(X[mv].to_numpy(np.float32))
    mt = df["site"].eq(tgt).to_numpy()
    sf = SiteFrame(meta[mt])
    Xn = X[mt].to_numpy(np.float32)
    split_pt = df.loc[mt, "split"].to_numpy()[sf.offsets]
    home = src == tgt
    eligible = (split_pt == "test") if home else np.ones(sf.n_patients, bool)
    pool = np.flatnonzero(eligible) if home else np.flatnonzero(split_pt != "test")
    src_raw = b.predict(Xn, raw_score=True)
    raw = df.loc[mt, [c for c, _ in VITALS_SHOWN] + ["Lactate", "WBC", "Age", "Gender", "ICULOS"]]
    return {"sfv": sfv, "pv": pv, "sf": sf, "Xn": Xn, "y": sf.meta["SepsisLabel"].to_numpy(),
            "split_pt": split_pt, "eligible": eligible, "pool": pool, "src_raw": src_raw,
            "srcd": model_dict(sf, sigmoid(src_raw)), "booster": b,
            "news2": compute_scores(X[mt])["NEWS2_mod"].to_numpy(),
            "raw": raw.reset_index(drop=True)}


def onset_hour(sf, p):
    if not sf.septic[p]:
        return None
    s, e = sf.offsets[p], sf.offsets[p] + sf.hours[p]
    lab = sf.meta["SepsisLabel"].to_numpy()[s:e]
    return int(np.argmax(lab)) + 6


# ------------------------------------------------------------------------------------------ gate
def page_gate(src, tgt):
    C = site_context(src, tgt)
    sf = C["sf"]
    control = src == tgt
    st.header("Deployment gate")
    st.markdown(f"The **{SITE[src]}** sepsis model is being installed at **{SITE[tgt]}**"
                + (" (control: the model's own hospital, new patients)." if control else ".")
                + " Before any alert reaches a clinician, the gate checks the hospital's own "
                  "safety requirements on its own labelled patients, and proves them statistically.")

    c1, c2, c3 = st.columns([1.1, 1.1, 1.2], gap="large")
    with c1:
        st.subheader("Safety requirements")
        s_star = st.slider("Septic patients that must be alerted (onset −12 h to +3 h)",
                           0.70, 0.90, 0.80, 0.05, format="%.2f")
        margin = st.slider("Extra non-septic patients alerted, allowed above the home rate",
                           0.00, 0.15, 0.05, 0.01, format="%.2f")
    vp = vendor_package(C["sfv"], C["pv"], s_star, margin)
    with c2:
        st.subheader("Local labelled patients")
        max_n = int(0.9 * len(C["pool"]))
        n = int(st.number_input("How many patients have been labelled?", min_value=250, max_value=max_n,
                                value=min(12000, max_n // 250 * 250), step=250))
        design = st.radio("How were they chosen?", ["Random sample", "Enriched: half are sepsis cases"],
                          horizontal=False)
        seed = int(st.number_input("Sample number (repeat with another sample)", 0, 9999, 0))
    with c3:
        st.subheader("What arrived with the model")
        st.markdown(
            f"- Alert threshold: **{vp['tau']:.4f}**\n"
            f"- Home validation ({vp['home_patients']:,} patients, {vp['home_septic']:,} septic): "
            f"sensitivity **{vp['home_sens']:.1%}** (proven ≥ {s_star:.0%}), "
            f"non-septic patients alerted **{vp['home_fa']:.1%}**\n"
            f"- So this hospital requires: sensitivity ≥ **{s_star:.0%}**, "
            f"non-septic alerted ≤ **{vp['f_star']:.1%}**")
        st.markdown(f"<span class='small'>Each option is tested at level α/4 = {ALPHA / 4:.4f}; "
                    f"the chance of switching on anything unsafe is at most {ALPHA:.0%}.</span>",
                    unsafe_allow_html=True)

    if st.button("Run the gate", type="primary"):
        share = None if design == "Random sample" else 0.5
        if share is not None and n - min(int(0.5 * n), int(0.5 * sf.septic[C["pool"]].sum())) > \
                0.9 * (~sf.septic[C["pool"]]).sum():
            st.error("Not enough non-septic patients in the pool for that many labels.")
            return
        lab, cert, fit = draw_labels(sf, C["pool"], n, seed, share)
        variant = {}

        def get_ada():
            tr, es = split_patients(np.flatnonzero(fit), sf.n_patients, seed)
            v, p = fit_adapt(C["Xn"], C["y"], sf.row_patient, tr, es, C["booster"], C["src_raw"], seed)
            variant["name"] = v
            return model_dict(sf, p)

        with st.spinner("Testing Keep and Calibrate; fitting and testing Adapt if needed ..."):
            remedy, tau, steps, ada = gate_explained(lab, cert, C["srcd"], get_ada, vp["tau"],
                                                     s_star, vp["f_star"], ALPHA)
        model = {"KEEP": C["srcd"], "CALIBRATE": C["srcd"], "ADAPT": ada}.get(remedy)
        comp = C["eligible"] & ~lab
        naive_tau = largest_threshold_for(C["srcd"]["wmax"][lab & sf.septic], s_star)
        check = {"naive": rates(C["srcd"]["wmax"], C["srcd"]["smax"], sf.septic, comp, naive_tau),
                 "naive_apparent": rates(C["srcd"]["wmax"], C["srcd"]["smax"], sf.septic, lab, naive_tau),
                 "asis": rates(C["srcd"]["wmax"], C["srcd"]["smax"], sf.septic, comp, vp["tau"]),
                 "deployed": rates(model["wmax"], model["smax"], sf.septic, comp, tau) if model else None,
                 "n_eval": int(comp.sum())}
        st.session_state["deploy"] = {
            "src": src, "tgt": tgt, "remedy": remedy, "tau": tau, "steps": steps, "s_star": s_star,
            "f_star": vp["f_star"], "n": n, "n_sep": int(sf.septic[lab].sum()), "design": design,
            "score": model["score"] if model else None, "variant": variant.get("name"), "check": check}

    dep = st.session_state.get("deploy")
    if not dep or dep["src"] != src or dep["tgt"] != tgt:
        st.info("Set the requirements and labelled patients, then press **Run the gate**.")
        return
    colour, title, text = DECISION_STYLE[dep["remedy"]]
    st.markdown(f"<div class='decision' style='background:{colour}'><h3>Decision: {title}</h3>"
                f"<p>{text}</p></div>", unsafe_allow_html=True)
    st.caption(f"Based on {dep['n']:,} labelled patients ({dep['n_sep']:,} septic), {dep['design'].lower()}."
               + (f" Adapted model: {dep['variant']}." if dep["remedy"] == "ADAPT" and dep["variant"] else ""))

    st.subheader("Evidence for each option, cheapest first")
    rows = []
    for s in dep["steps"]:
        if "threshold" not in s:
            rows.append({"Option": s["step"], "Tested on": s["data"],
                         "Result": "\u274c not possible: " + s.get("note", "")})
            continue
        rows.append({
            "Option": s["step"], "Tested on": s["data"], "Threshold": f"{s['threshold']:.4f}",
            "Septic alerted": f"{s['detected']}/{s['septic_n']} ({s['sens_observed']:.1%})",
            "Sensitivity proven ≥": f"{s['sens_lower_bound']:.1%}" + (" ✅" if s["sens_ok"] else " ❌"),
            "Non-septic alerted": f"{s['alerted']}/{s['nonseptic_n']} ({s['fa_observed']:.1%})",
            "False alerts proven ≤": f"{s['fa_upper_bound']:.1%}" + (" ✅" if s["fa_ok"] else " ❌"),
            "Result": "✅ passes" if s["passed"] else "❌ fails"})
    st.dataframe(pd.DataFrame(rows).fillna(""), hide_index=True, width="stretch")
    st.caption(f"Requirements: sensitivity ≥ {dep['s_star']:.0%} and non-septic alerted ≤ "
               f"{dep['f_star']:.1%}. A bound is the one-sided exact (Clopper–Pearson) limit at "
               f"level α/4. Keep and Calibrate use all labelled patients; Adapt is fitted on one half "
               f"and tested on the other.")

    with st.expander("Simulation check: what actually happened on the unlabelled patients", expanded=True):
        ck = dep["check"]
        st.markdown(f"Only possible in a retrospective simulation: {ck['n_eval']:,} patients the gate never saw.")
        def verdict(sens, fa):
            ok = sens >= dep["s_star"] and fa <= dep["f_star"]
            return f"sensitivity {sens:.1%}, non-septic alerted {fa:.1%} → " + \
                ("**meets both requirements**" if ok else "**breaks a requirement**")
        st.markdown(f"- **Imported model as it is:** {verdict(*ck['asis'])}")
        a_s, a_f = ck["naive_apparent"]
        st.markdown(f"- **Simple recalibration** (threshold set to hit {dep['s_star']:.0%} on the labelled "
                    f"patients, no proof): looked like sensitivity {a_s:.1%}, non-septic alerted {a_f:.1%}; "
                    f"in reality {verdict(*ck['naive'])}")
        if ck["deployed"]:
            st.markdown(f"- **What the gate switched on ({dep['remedy'].title()}):** {verdict(*ck['deployed'])}")
        else:
            st.markdown("- **The gate switched nothing on**, so no AI alerts can break the requirements.")


# ------------------------------------------------------------------------------------------ ward
def page_ward(src, tgt):
    C = site_context(src, tgt)
    sf = C["sf"]
    dep = st.session_state.get("deploy")
    active = dep is not None and dep["src"] == src and dep["tgt"] == tgt
    if active and dep["remedy"] != "BLOCK":
        score, tau = dep["score"], dep["tau"]
        mode = f"AI model ({DECISION_STYLE[dep['remedy']][1].split(':')[0]}), certified by the gate"
        unit = "risk"
    else:
        score, tau = C["news2"], NEWS2_CUT
        mode = ("Modified NEWS2 ≥ 5: the gate blocked the AI" if active else
                "Modified NEWS2 ≥ 5: run the deployment gate to switch the AI on")
        unit = "NEWS2"

    st.header(f"Ward monitor — {SITE[tgt]} ICU")
    left, right = st.columns([3, 1])
    with right:
        ward_seed = int(st.number_input("Ward sample", 0, 999, 7))
        reveal = st.toggle("Show true sepsis onset (simulation only)", value=False)
    with left:
        clock = st.slider("Replay: hours since each patient's ICU admission", 1, 72, 24)

    test = np.flatnonzero((C["split_pt"] == "test") & (sf.hours >= 12))
    rng = np.random.default_rng(ward_seed)
    sep_ids, non_ids = test[sf.septic[test]], test[~sf.septic[test]]
    ward = np.concatenate([rng.choice(sep_ids, size=min(4, len(sep_ids)), replace=False),
                           rng.choice(non_ids, size=min(12, len(non_ids)), replace=False)])
    rng.shuffle(ward)

    rows = []
    for bed, p in enumerate(ward, start=1):
        s0, los = sf.offsets[p], int(sf.hours[p])
        h = min(clock, los)
        sc = np.nan_to_num(score[s0:s0 + h], nan=0.0)
        al = sc >= tau
        run = 0
        for v in al[::-1]:
            if not v:
                break
            run += 1
        rows.append({"Bed": f"Bed {bed:02d}", "Patient": sf.pids[p], "p": p,
                     "Status": "in ICU" if clock <= los else "left ICU",
                     "ICU hour": h, "Score": float(sc[-1]), "× threshold": float(sc[-1] / tau),
                     "Alert": ("● ALERT" if al[-1] else ""), "Alert for": f"{run} h" if al[-1] else "",
                     "Trend (last 24 h)": [float(v) for v in sc[-24:]]})
    ward_df = pd.DataFrame(rows)
    in_icu = ward_df[ward_df.Status == "in ICU"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Patients in ICU", len(in_icu))
    m2.metric("Active alerts", int((in_icu.Alert != "").sum()))
    m3.metric("Alert threshold", f"{tau:.4f}" if unit == "risk" else "NEWS2 ≥ 5")
    m4.markdown(f"<div class='small'>Alerting system in use</div><b>{mode}</b>", unsafe_allow_html=True)

    view = ward_df.sort_values(["Status", "× threshold"], ascending=[True, False])
    st.dataframe(
        view.drop(columns=["p"]), hide_index=True, width="stretch", height=600,
        column_config={
            "Score": st.column_config.NumberColumn("Score", format="%.4f" if unit == "risk" else "%.0f"),
            "× threshold": st.column_config.ProgressColumn("Score ÷ threshold", min_value=0.0,
                                                                max_value=3.0, format="%.2f"),
            "Trend (last 24 h)": st.column_config.LineChartColumn("Trend (last 24 h)"),
        })

    st.subheader("Patient detail")
    choice = st.selectbox("Patient", list(view.Bed + " · " + view.Patient), index=0)
    p = int(view.p.iloc[list(view.Bed + " · " + view.Patient).index(choice)])
    s0, los = sf.offsets[p], int(sf.hours[p])
    h = min(clock, los)
    raw = C["raw"].iloc[s0:s0 + h].reset_index(drop=True)
    info = C["raw"].iloc[s0]
    st.markdown(f"Age **{info.Age:.0f}**, {'male' if info.Gender == 1 else 'female'} · "
                f"ICU hour **{h}** of {los}"
                + (f" · <span class='badge' style='background:#a8322d'>sepsis onset at hour "
                   f"{onset_hour(sf, p)}</span>" if reveal and sf.septic[p] else
                   (" · no sepsis during this stay" if reveal else "")), unsafe_allow_html=True)

    t = pd.DataFrame({"ICU hour": np.arange(h), "Score": np.nan_to_num(score[s0:s0 + h], nan=0.0)})
    t["Alert"] = t.Score >= tau
    base = alt.Chart(t).encode(x=alt.X("ICU hour:Q", scale=alt.Scale(domain=[0, max(h, 12)])))
    risk = (base.mark_line(color="#2a78d6", strokeWidth=2).encode(
                y=alt.Y("Score:Q", title="Sepsis risk score" if unit == "risk" else "Modified NEWS2"))
            + base.transform_filter("datum.Alert").mark_point(color="#a8322d", filled=True, size=40)
                  .encode(y="Score:Q", tooltip=["ICU hour", alt.Tooltip("Score:Q", format=".4f")])
            + alt.Chart(pd.DataFrame({"y": [tau]})).mark_rule(strokeDash=[5, 4], color="#52514e")
                  .encode(y="y:Q"))
    if reveal and sf.septic[p]:
        o = onset_hour(sf, p)
        risk = risk + alt.Chart(pd.DataFrame({"ICU hour": [o]})).mark_rule(color="#a8322d", strokeWidth=2) \
            .encode(x="ICU hour:Q")
    st.altair_chart(risk.properties(height=220, title="Risk score (dashed line: alert threshold)"),
                    width="stretch")

    long = raw[[c for c, _ in VITALS_SHOWN]].ffill().assign(**{"ICU hour": np.arange(h)})
    long = long.melt("ICU hour", var_name="Vital", value_name="Value").dropna()
    names = dict(VITALS_SHOWN)
    long["Vital"] = long.Vital.map(names)
    vit = (alt.Chart(long).mark_line(color="#52514e", strokeWidth=1.5)
           .encode(x=alt.X("ICU hour:Q", scale=alt.Scale(domain=[0, max(h, 12)])),
                   y=alt.Y("Value:Q", title=None, scale=alt.Scale(zero=False)),
                   tooltip=["ICU hour", "Vital", alt.Tooltip("Value:Q", format=".1f")])
           .properties(height=90, width=760)
           .facet(row=alt.Row("Vital:N", title=None, sort=[n for _, n in VITALS_SHOWN],
                              header=alt.Header(labelAngle=0, labelAlign="left", labelFontSize=12)))
           .resolve_scale(y="independent"))
    st.altair_chart(vit, width="stretch")
    labs = raw[["Lactate", "WBC"]].assign(**{"ICU hour": np.arange(h)}).dropna(how="all", subset=["Lactate", "WBC"])
    if len(labs):
        st.caption("Laboratory results this stay")
        st.dataframe(labs.tail(8), hide_index=True)


# ------------------------------------------------------------------------------------------ about
def page_about():
    st.header("About this prototype")
    st.markdown("""
**What it is.** An ICU sepsis early-warning application with a *deployment gate*. A model trained at
one hospital is checked against the receiving hospital's own safety requirements before any alert
reaches clinicians. The gate tries the cheapest option first: keep the model as it is, set a new
local threshold (calibrate), update the model on local data (adapt), or refuse (block). An option
is switched on only when exact statistical tests on the hospital's labelled patients show that it
meets both requirements, so the chance of switching on an unsafe system is at most 5%.

**Data.** PhysioNet/CinC Challenge 2019 (Beth Israel Deaconess Medical Center and Emory University
Hospital), 40,336 ICU stays, hourly vital signs, laboratory values and demographics; Sepsis-3 labels.
The ward monitor replays test-split patients the models never saw.

**Requirements checked.** (1) Share of septic patients alerted between 12 h before and 3 h after
sepsis onset. (2) Share of non-septic patients alerted at least once during their ICU stay.

**Not for clinical use.** Research prototype on retrospective public data. Bedside scores are
*modified* (no consciousness level, oxygen flag only as FiO₂ > 0.21, no urine output).
""")


# ------------------------------------------------------------------------------------------ main
def main():
    with st.sidebar:
        st.markdown("### \U0001fa7a CAB Sepsis Monitor")
        st.caption("Research prototype — not for clinical use")
        page = st.radio("Screen", ["Deployment gate", "Ward monitor", "About"])
        src = st.selectbox("Imported model trained at", ["A", "B"], format_func=lambda s: SITE[s], index=0)
        tgt = st.selectbox("Deploying at", ["B", "A"], format_func=lambda s: SITE[s], index=0)
        dep = st.session_state.get("deploy")
        if dep and dep["src"] == src and dep["tgt"] == tgt:
            colour = DECISION_STYLE[dep["remedy"]][0]
            st.markdown(f"Gate decision: <span class='badge' style='background:{colour}'>"
                        f"{dep['remedy']}</span>", unsafe_allow_html=True)
    if page == "Deployment gate":
        page_gate(src, tgt)
    elif page == "Ward monitor":
        page_ward(src, tgt)
    else:
        page_about()


main()
