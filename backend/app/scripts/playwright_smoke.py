import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> None:
    test_url = os.getenv("PLAYWRIGHT_TEST_URL", "https://example.com")
    headless_value = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower()
    headless = headless_value not in {"0", "false", "no"}

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(test_url, wait_until="networkidle")
        await page.screenshot(path=str(artifacts_dir / "playwright_smoke.png"), full_page=True)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
