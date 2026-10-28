"""Chapter figures of the prototype application (CAB Sepsis Monitor), captured from the running app.

Start the app first (from the repository root):
    .venv/bin/python -m streamlit run app/sepsis_monitor.py --server.headless true --server.port 8501
then:
    .venv/bin/python scripts/app_screenshots.py
Needs Playwright (pip install playwright) and Google Chrome; no browser download is used.
Runs the gate with the app's defaults (Beth Israel model at Emory, 12,000 random labels, primary
criterion), then opens the ward monitor. Writes outputs/sepsis/figures/fig_app_gate.png and
fig_app_ward.png (main panel only, 2x resolution).
"""

import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "outputs" / "sepsis" / "figures"
URL = "http://localhost:8501"
SCALE = 2
W, H = 1440, 2300


def idle(pg):
    time.sleep(4)
    pg.wait_for_function("!document.querySelector('[data-testid=stStatusWidget]')", timeout=900_000)
    time.sleep(3)


def crop_main(png, out, main_box, bottom_box):
    """Keep the main content column, from its top down to the given element's bottom edge."""
    im = Image.open(png)
    pad = 16
    left = int(main_box["x"]) * SCALE
    right = int(main_box["x"] + main_box["width"] + pad) * SCALE
    top = int(main_box["y"] + 40) * SCALE
    bottom = int(bottom_box["y"] + bottom_box["height"] + pad) * SCALE
    im.crop((max(left, 0), top, min(right, im.width), min(bottom, im.height))).save(out, dpi=(300, 300))
    print(f"wrote {out.relative_to(ROOT)}")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    tmp = FIG / "_capture.png"
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
        pg.goto(URL)
        pg.get_by_role("button", name="Run the gate").click(timeout=300_000)
        idle(pg)
        pg.screenshot(path=str(tmp))
        main = pg.locator("[data-testid=stMainBlockContainer]").bounding_box()
        crop_main(tmp, FIG / "fig_app_gate.png", main,
                  pg.locator("[data-testid=stExpander]").last.bounding_box())
        pg.get_by_text("Ward monitor", exact=True).click()
        idle(pg)
        pg.screenshot(path=str(tmp))
        main = pg.locator("[data-testid=stMainBlockContainer]").bounding_box()
        crop_main(tmp, FIG / "fig_app_ward.png", main,
                  pg.locator("[data-testid=stVegaLiteChart]").first.bounding_box())
        b.close()
    tmp.unlink()


if __name__ == "__main__":
    main()
