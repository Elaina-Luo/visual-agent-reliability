from pathlib import Path

from playwright.sync_api import sync_playwright


project_dir = Path(__file__).resolve().parent
page_path = project_dir / "environment" / "index.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    page = browser.new_page(
        viewport={"width": 960, "height": 640},
        device_scale_factor=1,
    )

    page.goto(page_path.as_uri())

    input("Try the page. Press Enter here to close the browser.")
    browser.close()