from pathlib import Path

from playwright.sync_api import sync_playwright


output_dir = Path(__file__).parent / "artifacts"
output_dir.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    page = browser.new_page(
        viewport={"width": 960, "height": 640},
        device_scale_factor=1,
    )

    page.set_content("""
        <html>
        <body style="margin: 0; background: white;">
            <button
                style="position: absolute;
                       left: 100px; top: 100px;
                       width: 200px; height: 100px;
                       font-size: 24px;"
                onclick="this.textContent = 'Selected';
                         this.style.backgroundColor = 'lightgreen';"
            >
                Select
            </button>
        </body>
        </html>
    """)

    # Observation before the action.
    page.screenshot(path=str(output_dir / "before.png"))

    # Execute an actual mouse click at the button center.
    page.mouse.click(200, 150)

    # Allow rendering to advance without checking task success.
    page.evaluate("""
        () => new Promise(resolve => {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => resolve());
            });
        })
    """)

    # Observation after the action.
    page.screenshot(path=str(output_dir / "after.png"))

    print(f"Screenshots saved to: {output_dir}")
    browser.close()