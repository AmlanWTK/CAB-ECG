"""Helpers for running the extractors on the full databases (eICU-CRD v2.0, MIMIC-IV), not only
the demos, on a 16 GB machine.

The large tables (eICU vitalPeriodic ~147 M rows, nurseCharting ~151 M; MIMIC-IV chartevents
~313 M, labevents ~118 M) do not fit in memory as rows. They are read in chunks, and each chunk
is reduced at once:
  - to hourly aggregates (HourlyAgg: sum and count, min or max per stay-hour and variable) in
    dense arrays over the stay-hour grid, when only the hourly value is needed;
  - to compact numeric columns (no strings, 32-bit numbers) when the event times are needed
    (PaO2/FiO2 pairing, GCS parts charted together).

cached() stores each finished piece under <out>_cache/, so a run that stops can be restarted and
skips what is done, and the labelling definitions (relaxed, challenge) share the feature tables.
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

CHUNK = 500_000   # rows per chunk; peak memory grows with this, not with the table


def chunks(path, usecols, filt=None, chunksize=CHUNK, **kw):
    """Yield the chunks of a csv(.gz), each passed through filt (which may drop rows and columns)."""
    t0, n = time.time(), 0
    for c in pd.read_csv(path, usecols=usecols, chunksize=chunksize, low_memory=False, **kw):
        n += len(c)
        out = filt(c) if filt else c
        if out is not None and len(out):
            yield out
    print(f"    read {Path(path).name}: {n:,} rows in {time.time() - t0:.0f}s", flush=True)


def read(path, usecols, filt=None, **kw):
    """The whole (filtered) table; for tables that are small once filtered."""
    parts = list(chunks(path, usecols, filt, **kw))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=usecols)


class Grid:
    """The stay-hour grid (hour 0 .. hours-1 of each stay), as row numbers for dense arrays."""

    def __init__(self, stay, hours):
        self.stay = pd.Index(np.asarray(stay))
        self.hours = np.maximum(np.asarray(hours, dtype=np.int64), 1)
        self.start = np.cumsum(self.hours) - self.hours
        self.n = int(self.hours.sum())

    def rows(self, stay, hour):
        """Grid row of each (stay, hour), or -1 when the stay is unknown or the hour is outside it."""
        pos = self.stay.get_indexer(np.asarray(stay))
        hour = np.asarray(hour, dtype=np.int64)
        ok = (pos >= 0) & (hour >= 0)
        ok[ok] &= hour[ok] < self.hours[pos[ok]]
        return np.where(ok, self.start[np.maximum(pos, 0)] + hour, -1)

    def frame(self):
        return make_grid(self.stay, self.hours)


class HourlyAgg:
    """Hourly aggregate per grid row and variable, built chunk by chunk in dense arrays (one row
    per stay-hour, one column per variable), so memory is fixed by the grid, not by the table.

    add() takes a frame with columns stay, hour, var, value; result() gives a frame in grid order
    indexed by (stay, hour), one column per variable. how: mean, min, max or sum. Hours outside a
    stay are dropped, as joining to the grid did before."""

    def __init__(self, how, grid, variables, dtype=np.float64):
        assert how in ("mean", "min", "max", "sum")
        self.how, self.grid, self.vars = how, grid, list(variables)
        self.code = {v: i for i, v in enumerate(self.vars)}
        fill = {"min": np.inf, "max": -np.inf}.get(how, 0)
        self.acc = np.full((grid.n, len(self.vars)), fill, dtype=dtype)
        self.cnt = np.zeros((grid.n, len(self.vars)), dtype=np.uint16) if how == "mean" else None

    def add(self, ev):
        ev = ev.dropna(subset=["value"])
        if not len(ev):
            return
        r = self.grid.rows(ev["stay"].to_numpy(), ev["hour"].to_numpy())
        var = ev["var"]
        c = (np.full(len(ev), self.code[var], np.int64) if isinstance(var, str)
             else var.map(self.code).to_numpy(dtype=float))
        ok = (r >= 0) & ~np.isnan(c)
        idx = (r[ok], c[ok].astype(np.int64))
        v = ev["value"].to_numpy(dtype=np.float64)[ok]
        if self.how in ("mean", "sum"):
            np.add.at(self.acc, idx, v)
            if self.cnt is not None:
                np.add.at(self.cnt, idx, 1)
        elif self.how == "min":
            np.minimum.at(self.acc, idx, v)
        else:
            np.maximum.at(self.acc, idx, v)

    @classmethod
    def merged(cls, aggs):
        """One aggregate over the union of the variables of several (same grid and how)."""
        variables = list(dict.fromkeys(v for a in aggs for v in a.vars))
        out = cls(aggs[0].how, aggs[0].grid, variables, aggs[0].acc.dtype)
        for a in aggs:
            j = [out.code[v] for v in a.vars]
            if a.how in ("mean", "sum"):
                out.acc[:, j] += a.acc
                if out.cnt is not None:
                    out.cnt[:, j] += a.cnt
            elif a.how == "min":
                out.acc[:, j] = np.minimum(out.acc[:, j], a.acc)
            else:
                out.acc[:, j] = np.maximum(out.acc[:, j], a.acc)
        return out

    def values(self, dtype=np.float32):
        if self.how == "mean":
            with np.errstate(invalid="ignore", divide="ignore"):
                v = np.divide(self.acc, self.cnt, dtype=np.result_type(self.acc.dtype, np.float32)).astype(dtype, copy=False)
            v[self.cnt == 0] = np.nan
        elif self.how == "sum":
            v = self.acc.astype(dtype)
        else:
            v = self.acc.astype(dtype)
            v[~np.isfinite(self.acc)] = np.nan
        return v

    def result(self, dtype=np.float32):
        g = self.grid.frame()
        return pd.DataFrame(self.values(dtype), columns=self.vars,
                            index=pd.MultiIndex.from_frame(g)).dropna(how="all")

    def series(self, var):
        """One variable as a float64 Series indexed by (stay, hour), measured hours only."""
        j = self.code[var]
        v = self.values(np.float64)[:, j]
        g = self.grid.frame()
        ok = ~np.isnan(v)
        return pd.Series(v[ok], index=pd.MultiIndex.from_frame(g[ok]), name=var)


def make_grid(stay, hours):
    """One row per stay-hour: hour 0 .. hours-1 for each stay (vectorised)."""
    hours = np.maximum(np.asarray(hours, dtype=np.int64), 1)
    s = np.repeat(np.asarray(stay), hours)
    start = np.repeat(np.cumsum(hours) - hours, hours)
    return pd.DataFrame({"stay": s, "hour": np.arange(len(s)) - start})


def cached(cache_dir, name, fn):
    """fn() once; later runs load the stored result."""
    path = Path(cache_dir) / f"{name}.pkl"
    if path.exists():
        print(f"  {name}: from cache", flush=True)
        return pd.read_pickle(path)
    t0 = time.time()
    out = fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(out, path)
    print(f"  {name}: done in {time.time() - t0:.0f}s", flush=True)
    return out
