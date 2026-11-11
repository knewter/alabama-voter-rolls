"""Headline arithmetic for the published county file. Standard library only."""

from __future__ import annotations

import csv
import json
import unittest
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "county_results.csv"
JSON_PATH = ROOT / "data" / "counties.json"

CLAIMED = {
    "Madison": ("109.9", 30372),
    "Baldwin": ("112.8", 24298),
    "Shelby": ("106.9", 11846),
    "Limestone": ("104.7", 3978),
    "St. Clair": ("102.8", 2050),
    "Randolph": ("110.0", 1774),
    "Lowndes": ("122.3", 1711),
}


def one_decimal(value: str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


class MathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with CSV_PATH.open(newline="", encoding="utf-8") as handle:
            cls.rows = list(csv.DictReader(handle))
        cls.meta = json.loads(JSON_PATH.read_text(encoding="utf-8"))["meta"]
        cls.by_county = {row["county"]: row for row in cls.rows}

    def test_half_up_examples_from_the_page(self):
        self.assertEqual(one_decimal("100.15"), Decimal("100.2"))
        self.assertEqual(one_decimal("100.14"), Decimal("100.1"))
        self.assertEqual(one_decimal("100.194633"), Decimal("100.2"))
        self.assertEqual(one_decimal("88.159777"), Decimal("88.2"))

    def test_county_one_decimal_matches_half_up(self):
        for row in self.rows:
            total = int(row["registered_total"])
            estimate = int(row["cvap_est"])
            ratio = (Decimal(total) * Decimal(100) / Decimal(estimate)).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP
            )
            # The CSV stores a 6-decimal ratio. Re-round that published ratio.
            published = Decimal(row["pct_registered_vs_cvap"])
            self.assertEqual(published, ratio, row["county"])
            self.assertEqual(
                Decimal(row["pct_registered_vs_cvap_1decimal"]),
                one_decimal(row["pct_registered_vs_cvap"]),
                row["county"],
            )

    def test_headline_counts(self):
        self.assertEqual(len(self.rows), 67)
        over = {row["county"] for row in self.rows if row["over_100"] == "True"}
        beyond = {row["county"] for row in self.rows if row["still_over_after_moe"] == "True"}
        self.assertEqual(len(over), 32)
        self.assertEqual(len(beyond), 28)
        self.assertTrue(beyond.issubset(over))
        inactive = sum(int(row["registered_inactive"]) for row in self.rows)
        self.assertEqual(inactive, 462824)

    def test_flags_follow_the_integer_rule(self):
        for row in self.rows:
            total = int(row["registered_total"])
            estimate = int(row["cvap_est"])
            margin = int(row["cvap_moe"])
            self.assertEqual(int(row["cvap_upper_90ci"]), estimate + margin)
            self.assertEqual(int(row["over_count"]), total - estimate)
            self.assertEqual(row["over_100"], "True" if total > estimate else "False")
            self.assertEqual(
                row["still_over_after_moe"],
                "True" if total > estimate + margin else "False",
            )
            active = int(row["registered_active"])
            self.assertEqual(active + int(row["registered_inactive"]), total)
            self.assertEqual(
                row["active_over_100"],
                "True" if active > estimate else "False",
            )

    def test_active_only_sensitivity(self):
        active_over = [
            row["county"] for row in self.rows if row["active_over_100"] == "True"
        ]
        self.assertEqual(sorted(active_over), ["Lowndes", "Perry", "Washington"])
        beyond = []
        inside = []
        for name in active_over:
            row = self.by_county[name]
            active = int(row["registered_active"])
            upper = int(row["cvap_upper_90ci"])
            (beyond if active > upper else inside).append(name)
        self.assertEqual(sorted(beyond), ["Lowndes", "Perry"])
        self.assertEqual(inside, ["Washington"])
        washington = self.by_county["Washington"]
        self.assertEqual(int(washington["registered_active"]), 12164)
        self.assertEqual(int(washington["cvap_upper_90ci"]), 12172)

    def test_claimed_counties(self):
        for county, (pct, over) in CLAIMED.items():
            row = self.by_county[county]
            self.assertEqual(row["pct_registered_vs_cvap_1decimal"], pct)
            self.assertEqual(int(row["over_count"]), over)
            self.assertEqual(row["still_over_after_moe"], "True")

    def test_state_row_in_the_json_matches_the_page(self):
        state = self.meta["state"]
        self.assertEqual(state["registered_total"], 3853181)
        self.assertEqual(state["registered_active"], 3390357)
        self.assertEqual(state["registered_inactive"], 462824)
        self.assertEqual(state["cvap_est"], 3845696)
        self.assertEqual(state["cvap_moe"], 3237)
        self.assertEqual(state["cvap_upper_90ci"], 3848933)
        self.assertEqual(state["over_count"], 7485)
        self.assertEqual(state["over_upper"], 4248)
        self.assertEqual(state["pct_total_1dp"], "100.2")
        self.assertEqual(state["over_estimate"], 32)
        self.assertEqual(state["over_upper_bound"], 28)
        self.assertEqual(state["active_over_estimate"], 3)
        self.assertEqual(state["active_over_upper_bound"], 2)
        self.assertEqual(self.meta["cvap_published"], "January 30, 2026")
        self.assertEqual(self.meta["cvap_vintage"], "2020–2024 ACS")
        self.assertEqual(self.meta["registration_snapshot"], "October 2026")
        county_cvap = sum(int(row["cvap_est"]) for row in self.rows)
        self.assertEqual(county_cvap, 3845715)
        self.assertEqual(state["county_cvap_sum"], county_cvap)
        self.assertEqual(state["county_rounding_gap"], county_cvap - state["cvap_est"])

    def test_four_counties_inside_the_margin(self):
        inside = sorted(
            row["county"]
            for row in self.rows
            if row["over_100"] == "True" and row["still_over_after_moe"] == "False"
        )
        self.assertEqual(inside, ["Chambers", "Covington", "Escambia", "Lawrence"])


if __name__ == "__main__":
    unittest.main()
