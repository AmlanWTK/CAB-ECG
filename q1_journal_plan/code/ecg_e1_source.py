"""E1 (ECG): train the vendor's model on PTB-XL and score every cohort with it.

A small 1-D ResNet with one sigmoid output per panel finding. PTB-XL folds 1-8 train it,
fold 9 stops training (best mean AUROC), fold 10 is the vendor's home test set.
For every record of every cached source, writes the six scores and the 256-d embedding
(input to the ADAPT head) to outputs/ecg/scores/<source>.npz, and a summary of home and
imported AUROC per finding to outputs/ecg/E1_source.md.

Run from the repository root after ecg_cache.py (about 20-30 minutes on an Apple M5):
    python q1_journal_plan/code/ecg_e1_source.py [--epochs 40 --seed 0]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score
from torch import nn

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cabecg.labels import PANEL  # noqa: E402
from cabecg.paths import INDEX_CSV, OUTPUTS  # noqa: E402
from ecg_cache import CACHE, load_cache  # noqa: E402

OUT = OUTPUTS / "ecg"
SCORES = OUT / "scores"
DEVICE = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")


class Block(nn.Module):
    def __init__(self, c_in, c_out, stride):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv1d(c_in, c_out, 9, stride, 4, bias=False), nn.BatchNorm1d(c_out), nn.ReLU(),
            nn.Conv1d(c_out, c_out, 9, 1, 4, bias=False), nn.BatchNorm1d(c_out))
        self.skip = (nn.Identity() if c_in == c_out and stride == 1 else
                     nn.Sequential(nn.Conv1d(c_in, c_out, 1, stride, bias=False), nn.BatchNorm1d(c_out)))

    def forward(self, x):
        return torch.relu(self.body(x) + self.skip(x))


class ResNet1d(nn.Module):
    def __init__(self, n_out=len(PANEL), width=(64, 128, 128, 256)):
        super().__init__()
        self.stem = nn.Sequential(nn.Conv1d(12, width[0], 15, 2, 7, bias=False),
                                  nn.BatchNorm1d(width[0]), nn.ReLU())
        layers, c = [], width[0]
        for w in width:
            layers += [Block(c, w, 2), Block(w, w, 1)]
            c = w
        self.layers = nn.Sequential(*layers)
        self.head = nn.Linear(c, n_out)

    def embed(self, x):
        return self.layers(self.stem(x)).mean(dim=2)

    def forward(self, x):
        return self.head(self.embed(x))


def batches(X, idx, size, shuffle, rng):
    idx = rng.permutation(idx) if shuffle else idx
    for i in range(0, len(idx), size):
        j = np.sort(idx[i:i + size])
        yield j, torch.from_numpy(np.asarray(X[j], dtype=np.float32))


@torch.no_grad()
def predict(model, X, size=512):
    model.eval()
    scores, embs = [], []
    for _, xb in batches(X, np.arange(len(X)), size, False, None):
        e = model.embed(xb.to(DEVICE))
        scores.append(torch.sigmoid(model.head(e)).cpu().numpy())
        embs.append(e.cpu().numpy())
    return np.concatenate(scores), np.concatenate(embs).astype(np.float32)


def mean_auroc(y, p):
    return np.nanmean([roc_auc_score(y[:, k], p[:, k]) if 0 < y[:, k].sum() < len(y) else np.nan
                       for k in range(y.shape[1])])


def train(model, X, y, tr, va, a, rng):
    """Train with early stopping on validation mean AUROC; leaves the best weights in model."""
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, a.epochs)
    pos = y[tr].mean(0)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(np.sqrt((1 - pos) / pos), device=DEVICE))
    best, best_state, wait = -1, None, 0
    for ep in range(a.epochs):
        model.train()
        t0 = time.time()
        for j, xb in batches(X, tr, 128, True, rng):
            xb = xb.to(DEVICE)
            shift = int(rng.integers(-50, 51))          # small random time shift as augmentation
            xb = torch.roll(xb, shift, dims=2)
            loss = loss_fn(model(xb), torch.from_numpy(y[j]).to(DEVICE))
            opt.zero_grad()
            loss.backward()
            opt.step()
        sched.step()
        p_va, _ = predict(model, X[va])
        auc = mean_auroc(y[va], p_va)
        print(f"  epoch {ep + 1}: val mean AUROC {auc:.4f} ({time.time() - t0:.0f}s)", flush=True)
        if auc > best:
            best, wait = auc, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            wait += 1
            if wait >= a.patience:
                break
    model.load_state_dict(best_state)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--score-only", action="store_true", help="reuse the saved model, e.g. after new cohorts are cached")
    a = ap.parse_args()
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)

    idx = pd.read_csv(INDEX_CSV, low_memory=False).set_index("record_id")
    X, ids = load_cache("ptbxl")
    meta = idx.loc[ids["record_id"]]
    y = meta[PANEL].to_numpy(np.float32)
    fold = meta["strat_fold"].to_numpy()
    tr, va = np.flatnonzero(fold <= 8), np.flatnonzero(fold == 9)
    print(f"device {DEVICE}; train {len(tr)}, val {len(va)}; positives in train: "
          + ", ".join(f"{k} {int(y[tr, i].sum())}" for i, k in enumerate(PANEL)))

    model = ResNet1d().to(DEVICE)
    weights = OUT / f"source_resnet_seed{a.seed}.pt"
    if a.score_only:
        model.load_state_dict(torch.load(weights))
        best = mean_auroc(y[va], predict(model, X[va])[0])
    else:
        best = train(model, X, y, tr, va, a, rng)
        OUT.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), weights)

    SCORES.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in sorted(CACHE.glob("*_ids.csv")):
        source = f.name[: -len("_ids.csv")]
        Xs, ids_s = load_cache(source)
        p, e = predict(model, Xs)
        np.savez(SCORES / f"{source}.npz", record_id=ids_s["record_id"].to_numpy(), score=p, emb=e)
        m = idx.loc[ids_s["record_id"]]
        keep = (m["strat_fold"].to_numpy() == 10) if source == "ptbxl" else np.ones(len(m), bool)
        for k, name in enumerate(PANEL):
            yk = m[name].to_numpy()[keep]
            ok = ~np.isnan(yk.astype(float))
            n_pos = int(np.nansum(yk))
            auc = roc_auc_score(yk[ok], p[keep][ok, k]) if 0 < n_pos < ok.sum() else np.nan
            rows.append({"source": source, "finding": name, "records": int(ok.sum()),
                         "positives": n_pos, "auroc": auc})
        print(f"scored {source}")
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "E1_source.csv", index=False)
    table = res.pivot(index="source", columns="finding", values="auroc")[PANEL].round(3)
    npos = res.pivot(index="source", columns="finding", values="positives")[PANEL]
    lines = ["# E1 (ECG): PTB-XL model at home (fold 10) and imported", "",
             f"Best validation mean AUROC {best:.4f}. Seed {a.seed}.", "",
             "AUROC:", "", "```", table.to_string(), "```", "",
             "Positives:", "", "```", npos.to_string(), "```", ""]
    (OUT / "E1_source.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
