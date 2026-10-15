"""gate_explained() must make exactly the same decisions as cab_select(). Run:
    python tests\\test_deploy.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from cabsepsis.cab import cab_select  # noqa: E402
from cabsepsis.deploy import gate_explained  # noqa: E402


def random_case(rng):
    n = int(rng.integers(50, 3000))
    septic = rng.random(n) < rng.uniform(0.03, 0.5)
    shift = rng.uniform(0, 3)
    def model(sh):
        w = np.where(septic, rng.normal(sh, 1, n), -np.inf)
        s = rng.normal(0, 1, n) + np.where(septic, sh, 0)
        return {"wmax": w, "smax": s, "septic": septic}
    lab = rng.random(n) < rng.uniform(0.3, 1.0)
    cert = lab & (rng.random(n) < 0.5)
    return lab, cert, model(shift), model(shift + rng.uniform(0, 3)), rng.normal(0.5, 1), rng.uniform(0.6, 0.9), rng.uniform(0.1, 0.8)


def main(trials=3000):
    rng = np.random.default_rng(0)
    seen = {}
    for _ in range(trials):
        lab, cert, src, ada, tau_home, s_star, f_star = random_case(rng)
        r1, t1 = cab_select(lab, cert, src, ada, tau_home, s_star, f_star, 0.05)
        r2, t2, _, _ = gate_explained(lab, cert, src, lambda: ada, tau_home, s_star, f_star, 0.05)
        assert r1 == r2 and (np.isnan(t1) and np.isnan(t2) or t1 == t2), (r1, t1, r2, t2)
        seen[r1] = seen.get(r1, 0) + 1
    print(f"OK: {trials} random cases, identical decisions. Decisions seen: {seen}")


if __name__ == "__main__":
    main()
