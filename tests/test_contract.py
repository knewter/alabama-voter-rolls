"""File contract: caveats, relative project-page URLs, and the published data files."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_pages_files_present(self):
        for relative in (
            "index.html",
            "css/site.css",
            "js/site.js",
            "favicon.svg",
            "data/county_results.csv",
            "data/reproduce.py",
            "data/counties.json",
            "fonts/newsreader-latin.woff2",
            "fonts/newsreader-latin-italic.woff2",
            "fonts/public-sans-latin.woff2",
            ".nojekyll",
            ".github/workflows/pages.yml",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_survey_vintage_and_not_proof_caveats(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("not proof of illegal votes", page)
        self.assertIn("survey estimate", page)
        self.assertIn("ACS 2020–2024", page)
        self.assertIn("January 30, 2026", page)
        self.assertIn("October 2026", page)
        self.assertIn("462,824", page)
        self.assertIn("32 of 67", page)
        self.assertIn("28 of 67", page)
        self.assertIn("Lowndes 105.1%", page)
        self.assertIn("Perry 104.3%", page)
        self.assertIn("Washington 100.7%", page)
        script = (ROOT / "data" / "reproduce.py").read_text(encoding="utf-8")
        self.assertIn("not proof", script)
        self.assertIn("survey estimate", script)
        self.assertIn("2020-2024", script)
        self.assertIn("Jan 30, 2026", script)
        self.assertIn("462,824", script)

    def test_local_assets_are_relative(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        refs = re.findall(r'(?:href|src)="([^"]+)"', page)
        local = []
        for ref in refs:
            if ref.startswith(("#", "http://", "https://", "mailto:")):
                continue
            local.append(ref)
            self.assertFalse(ref.startswith("/"), ref)
            self.assertNotIn("://", ref)
        self.assertIn("css/site.css", local)
        self.assertIn("js/site.js", local)
        self.assertIn("favicon.svg", local)
        self.assertIn("data/county_results.csv", local)
        self.assertIn("data/reproduce.py", local)
        css = (ROOT / "css" / "site.css").read_text(encoding="utf-8")
        font_urls = re.findall(r'url\("([^"]+)"\)', css)
        self.assertEqual(
            font_urls,
            [
                "../fonts/newsreader-latin.woff2",
                "../fonts/newsreader-latin-italic.woff2",
                "../fonts/public-sans-latin.woff2",
            ],
        )
        script = (ROOT / "js" / "site.js").read_text(encoding="utf-8")
        self.assertIn('fetch("data/counties.json")', script)
        self.assertNotIn('fetch("/', script)

    def test_json_matches_csv_bytes(self):
        raw = (ROOT / "data" / "county_results.csv").read_bytes()
        meta = json.loads((ROOT / "data" / "counties.json").read_text(encoding="utf-8"))["meta"]
        self.assertEqual(meta["csv_bytes"], len(raw))
        self.assertEqual(meta["csv_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(json.loads((ROOT / "data" / "counties.json").read_text())["counties"]), 67)

    def test_pages_workflow_publishes_root_site(self):
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("actions/deploy-pages", workflow)
        self.assertIn("actions/upload-pages-artifact", workflow)
        for piece in ("index.html", "css", "js", "data", "fonts", ".nojekyll"):
            self.assertIn(piece, workflow)


if __name__ == "__main__":
    unittest.main()
