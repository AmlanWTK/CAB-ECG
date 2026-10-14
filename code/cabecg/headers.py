"""Minimal, dependency-free parser for WFDB header (.hea) files.

Handles the Challenge 2021 and ecg-arrhythmia conventions: one record line, one line per
signal (e.g. "E00001.mat 16+24 1000/mV 16 0 -254 21756 0 I"), and comment lines such as
"#Age: 74", "#Sex: Male", "#Dx: 426783006,59118001".
"""

import re
from pathlib import Path

_GAIN = re.compile(r"^([0-9.eE+-]+)(?:\(([-0-9]+)\))?(?:/(\S+))?$")


def _num(text, cast=float):
    try:
        return cast(text)
    except (TypeError, ValueError):
        return None


def parse_header(path):
    path = Path(path)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]

    record_line = lines[0].split()
    n_sig = int(record_line[1])
    fs = float(record_line[2].split("/")[0])
    n_samples = int(record_line[3]) if len(record_line) > 3 else None

    signals = []
    for ln in lines[1:1 + n_sig]:
        f = ln.split()
        fmt = f[1]
        offset = int(fmt.split("+")[1]) if "+" in fmt else 0
        gain, baseline, units = 200.0, None, "mV"  # WFDB defaults
        if len(f) > 2:
            m = _GAIN.match(f[2])
            if m:
                gain = float(m.group(1)) or 200.0
                baseline = int(m.group(2)) if m.group(2) is not None else None
                units = m.group(3) or "mV"
        adc_zero = _num(f[4], int) if len(f) > 4 else 0
        if baseline is None:
            baseline = adc_zero or 0
        lead = f[8] if len(f) > 8 else f[-1]
        signals.append({
            "file": f[0], "format": fmt.split("+")[0], "offset": offset,
            "gain": gain, "baseline": baseline, "units": units, "lead": lead,
        })

    meta = {"age": None, "sex": None, "dx": []}
    for ln in lines[1 + n_sig:]:
        if not ln.startswith("#"):
            continue
        body = ln.lstrip("#").strip()
        if ":" not in body:
            continue
        key, value = body.split(":", 1)
        key, value = key.strip().lower(), value.strip()
        if key == "age":
            age = _num(value)
            meta["age"] = age if age is not None and 0 <= age < 120 else None
        elif key == "sex":
            v = value.lower()
            meta["sex"] = "M" if v.startswith("m") else ("F" if v.startswith("f") else None)
        elif key == "dx":
            meta["dx"] = [c.strip() for c in value.split(",") if c.strip()]

    return {
        "record": record_line[0], "n_sig": n_sig, "fs": fs, "n_samples": n_samples,
        "signals": signals, "comments": [ln for ln in lines if ln.startswith("#")], **meta,
    }
