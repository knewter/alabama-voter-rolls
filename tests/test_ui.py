"""Browser checks for the project-page path. Skips when Playwright is absent."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - exercised when the extra is missing
    sync_playwright = None


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class UiTests(unittest.TestCase):
    def setUp(self):
        if sync_playwright is None:
            self.skipTest("playwright is not installed")
        self.port = _free_port()
        self._link_dir = None
        if ROOT.name == "alabama-voter-rolls":
            serve_root = ROOT.parent
        else:
            # GitHub Pages serves this repo at /alabama-voter-rolls/.
            serve_root = Path(os.environ.get("TMPDIR", "/tmp")) / f"pages-ui-{self.port}"
            serve_root.mkdir(parents=True, exist_ok=True)
            link = serve_root / "alabama-voter-rolls"
            link.symlink_to(ROOT)
            self._link_dir = serve_root
        self.server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(self.port), "--bind", "127.0.0.1"],
            cwd=serve_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.base = f"http://127.0.0.1:{self.port}/alabama-voter-rolls/"
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            self.tearDown()
            self.fail("local server did not start")

    def tearDown(self):
        server = getattr(self, "server", None)
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
        link_dir = getattr(self, "_link_dir", None)
        if link_dir is not None:
            link = link_dir / "alabama-voter-rolls"
            if link.is_symlink():
                link.unlink()
            try:
                link_dir.rmdir()
            except OSError:
                pass

    def test_toggle_dialog_keyboard_and_mobile_widths(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            try:
                page = browser.new_page(viewport={"width": 390, "height": 844})
                page.goto(self.base, wait_until="networkidle")
                page.wait_for_function("document.documentElement.dataset.ready === 'true'")
                self.assertIn("100.2%", page.locator("#stat-pct").inner_text())
                self.assertEqual(page.locator("#stat-over").inner_text(), "32 of 67")
                self.assertEqual(page.locator("#stat-bound").inner_text(), "28 of 67")
                self.assertEqual(page.locator("#stat-inactive").inner_text(), "462,824")
                self.assertIn("not proof of illegal votes", page.locator("#finding").inner_text())
                self.assertIn("ACS 2020–2024", page.locator("body").inner_text())

                page.locator("#mode-active").focus()
                page.keyboard.press("Space")
                page.wait_for_function("document.getElementById('stat-over').textContent === '3 of 67'")
                self.assertEqual(page.locator("#stat-bound").inner_text(), "2 of 67")
                self.assertEqual(page.locator("#stat-pct").inner_text(), "88.16%")
                self.assertIn("88.2%", page.locator("#stat-gap").inner_text())

                page.locator("#mode-total").focus()
                page.keyboard.press("Space")
                page.wait_for_function("document.getElementById('stat-over').textContent === '32 of 67'")

                page.locator("#q").focus()
                page.keyboard.type("Lowndes")
                self.assertIn("1 county", page.locator("#result-count").inner_text())
                page.locator("button.named-card[data-county='Lowndes']").focus()
                page.keyboard.press("Enter")
                dialog = page.locator("#county-dialog")
                self.assertTrue(dialog.evaluate("el => el.open"))
                self.assertIn("Lowndes County", page.locator("#d-title").inner_text())
                self.assertIn("not proof of illegal votes", page.locator("#d-read").inner_text())
                page.keyboard.press("Escape")
                page.wait_for_function("!document.getElementById('county-dialog').open")

                csv_href = page.locator("a[href='data/county_results.csv']").get_attribute("href")
                script_href = page.locator("a[href='data/reproduce.py']").get_attribute("href")
                self.assertEqual(csv_href, "data/county_results.csv")
                self.assertEqual(script_href, "data/reproduce.py")
                csv_status = page.evaluate(
                    """async (base) => {
                      const response = await fetch(new URL('data/county_results.csv', base));
                      const text = await response.text();
                      return {status: response.status, start: text.slice(0, 24)};
                    }""",
                    self.base,
                )
                self.assertEqual(csv_status["status"], 200)
                self.assertTrue(csv_status["start"].startswith("county,sos_name"))

                for width in (320, 375, 390, 768):
                    page.set_viewport_size({"width": width, "height": 800})
                    page.wait_for_timeout(50)
                    overflow = page.evaluate(
                        """() => document.documentElement.scrollWidth
                           - document.documentElement.clientWidth"""
                    )
                    self.assertLessEqual(overflow, 1, f"horizontal overflow at {width}px")
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
