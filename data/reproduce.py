#!/usr/bin/env python3
"""Reproduce the Nov 10, 2026 claim that Alabama voter rolls exceed Census adult citizens.

Claim (https://x.com/_Patriot1776Q_/status/2120194509128737136), graphic dated
October 2026:

  Statewide official rolls are 100.2% of Census adult citizens.
  32 of 67 counties are over 100%.
  28 of those counties stay over after the Census margin of error.
  Official totals include 462,824 inactive voters still on the rolls.
  Highlighted counties: Madison 109.9% (30,372 over), Baldwin 112.8%
  (24,298 over), Shelby 106.9% (11,846 over), Limestone 104.7% (3,978 over),
  St. Clair 102.8% (2,050 over), Randolph 110.0% (1,774 over),
  Lowndes 122.3% (1,711 over).

Sources used (official, downloaded into ../raw/):

  * Alabama Secretary of State, Voter Registration Statistics - 2026,
    file ALVR-2026.xlsx, October sheet (year-to-date monthly figures).
    Posted at:
    https://www.sos.alabama.gov/sites/default/files/election-data/2026-11/ALVR-2026.xlsx
    Index: https://www.sos.alabama.gov/alabama-votes/voter/election-data
    Column B is total registered (active + inactive). Column L is Total
    Active. Column V is Total Inactive. Statewide inactive in October is
    exactly 462,824.

  * U.S. Census Bureau, Citizen Voting Age Population (CVAP) Special
    Tabulation from the 2020-2024 5-year ACS, County.csv and State.csv,
    line "Total", field cvap_est / cvap_moe (U.S. citizens age 18+).
    Zip: https://www2.census.gov/programs-surveys/decennial/rdo/datasets/2024/2024-cvap/CVAP_2020-2024_ACS_csv_files.zip
    Docs: https://www2.census.gov/programs-surveys/decennial/rdo/technical-documentation/special-tabulation/CVAP_2020-2024_ACS_documentation_v1.pdf
    Landing: https://www.census.gov/programs-surveys/decennial-census/about/voting-rights/cvap/2020-2024-CVAP.html
    Published Jan 30, 2026. ACS MOEs are approximate 90% confidence
    intervals: CVAP_HI = cvap_est + cvap_moe.

Formula:

  pct = 100 * registered_total / cvap_est
  over = registered_total - cvap_est
  over_100 if registered_total > cvap_est
  still_over_after_moe if registered_total > cvap_est + cvap_moe
      (i.e., registrations still exceed the upper end of the ACS 90% CI)
  Percentages on the graphic are rounded to one decimal with half-up
  rounding. "Over" counts are exact integer differences.

This compares a registration count to a survey estimate. It is not proof
of unlawful votes. Inactive registrants remain on the official roll and
may vote after reidentification. The ACS 2020-2024 estimate lags October
2026 registrations by several years, especially in fast-growing counties.
CVAP is citizens age 18+, not the smaller set of currently eligible voters
(it does not remove people disqualified under Alabama law). People can
also be counted in one county by ACS residency rules and registered in
another.

The ACS 5-year Detailed Table B29001 (same vintage) is within ±4 people
of the CVAP special tabulation at the county level, but the graphic's
exact "over" counts match the special tabulation, not B29001.
"""

from __future__ import annotations

import csv
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is required: pip install openpyxl")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
EXPORTS = ROOT / "exports"

SOS_XLSX = RAW / "ALVR-2026.xlsx"
CVAP_COUNTY = RAW / "cvap_2020_2024" / "County.csv"
CVAP_STATE = RAW / "cvap_2020_2024" / "State.csv"
OUT_CSV = EXPORTS / "county_results.csv"

# SOS October sheet uses ST_CLAIR / DEKALB; Census uses St. Clair / DeKalb.
SOS_NAME_TO_CENSUS = {
    "ST_CLAIR": "St. Clair",
    "DEKALB": "DeKalb",
}

CLAIMED_ROWS = {
    "Madison": (Decimal("109.9"), 30372),
    "Baldwin": (Decimal("112.8"), 24298),
    "Shelby": (Decimal("106.9"), 11846),
    "Limestone": (Decimal("104.7"), 3978),
    "St. Clair": (Decimal("102.8"), 2050),
    "Randolph": (Decimal("110.0"), 1774),
    "Lowndes": (Decimal("122.3"), 1711),
}


def one_decimal(x: float) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def census_name(sos_name: str) -> str:
    if sos_name in SOS_NAME_TO_CENSUS:
        return SOS_NAME_TO_CENSUS[sos_name]
    return sos_name.title()


def load_sos_october(path: Path) -> dict[str, dict[str, int]]:
    wb = openpyxl.load_workbook(path, data_only=True)
    if "October" not in wb.sheetnames:
        raise RuntimeError(f"Expected an October sheet; found {wb.sheetnames}")
    ws = wb["October"]
    out: dict[str, dict[str, int]] = {}
    for row in ws.iter_rows(min_row=3, values_only=True):
        name, total, active, inactive = row[0], row[1], row[11], row[21]
        if name is None:
            continue
        if total != active + inactive:
            raise RuntimeError(f"{name}: total {total} != active {active} + inactive {inactive}")
        out[name] = {
            "registered_total": int(total),
            "registered_active": int(active),
            "registered_inactive": int(inactive),
        }
    if "TOTAL" not in out or len(out) != 68:  # 67 counties + TOTAL
        raise RuntimeError(f"Unexpected SOS row count: {len(out)}")
    return out


def load_cvap_counties(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["lntitle"] != "Total" or not row["geoname"].endswith(", Alabama"):
                continue
            short = row["geoname"].replace(" County, Alabama", "")
            out[short] = {
                "geoid": row["geoid"],
                "cvap_est": int(row["cvap_est"]),
                "cvap_moe": int(row["cvap_moe"]),
            }
    if len(out) != 67:
        raise RuntimeError(f"Expected 67 Alabama counties, got {len(out)}")
    return out


def load_cvap_state(path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["geoname"] == "Alabama" and row["lntitle"] == "Total":
                return {
                    "cvap_est": int(row["cvap_est"]),
                    "cvap_moe": int(row["cvap_moe"]),
                }
    raise RuntimeError("Alabama state Total row not found")


def build_rows(sos: dict, cvap: dict) -> list[dict]:
    rows = []
    for sos_name, counts in sos.items():
        if sos_name == "TOTAL":
            continue
        county = census_name(sos_name)
        if county not in cvap:
            raise RuntimeError(f"No CVAP row for SOS county {sos_name} ({county})")
        total = counts["registered_total"]
        active = counts["registered_active"]
        inactive = counts["registered_inactive"]
        est = cvap[county]["cvap_est"]
        moe = cvap[county]["cvap_moe"]
        pct = 100.0 * total / est
        active_pct = 100.0 * active / est
        rows.append(
            {
                "county": county,
                "sos_name": sos_name,
                "geoid": cvap[county]["geoid"],
                "registered_total": total,
                "registered_active": active,
                "registered_inactive": inactive,
                "cvap_est": est,
                "cvap_moe": moe,
                "cvap_upper_90ci": est + moe,
                "pct_registered_vs_cvap": round(pct, 6),
                "pct_registered_vs_cvap_1decimal": str(one_decimal(pct)),
                "over_count": total - est,
                "over_100": total > est,
                "still_over_after_moe": total > est + moe,
                "pct_active_vs_cvap": round(active_pct, 6),
                "pct_active_vs_cvap_1decimal": str(one_decimal(active_pct)),
                "active_over_100": active > est,
                "registration_source": "AL SOS ALVR-2026.xlsx October sheet",
                "cvap_source": "Census CVAP special tabulation 2020-2024 ACS, County.csv Total",
            }
        )
    rows.sort(key=lambda r: (-r["over_count"], r["county"]))
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    sos = load_sos_october(SOS_XLSX)
    cvap = load_cvap_counties(CVAP_COUNTY)
    state = load_cvap_state(CVAP_STATE)
    rows = build_rows(sos, cvap)
    write_csv(rows, OUT_CSV)

    state_total = sos["TOTAL"]["registered_total"]
    state_active = sos["TOTAL"]["registered_active"]
    state_inactive = sos["TOTAL"]["registered_inactive"]
    state_cvap = state["cvap_est"]
    state_moe = state["cvap_moe"]
    state_pct = 100.0 * state_total / state_cvap
    county_cvap_sum = sum(r["cvap_est"] for r in rows)

    n_over = sum(r["over_100"] for r in rows)
    n_still = sum(r["still_over_after_moe"] for r in rows)
    n_active_over = sum(r["active_over_100"] for r in rows)

    print("Alabama voter-roll reproduction")
    print("Numerator: AL SOS official registered voters, October 2026 (active + inactive)")
    print(f"  file: {SOS_XLSX}")
    print(f"  statewide total={state_total:,}  active={state_active:,}  inactive={state_inactive:,}")
    print("Denominator: Census CVAP special tabulation, 2020-2024 ACS, citizens age 18+")
    print(f"  state cvap_est={state_cvap:,}  cvap_moe=±{state_moe:,}  (90% CI)")
    print(f"  sum of 67 county cvap_est={county_cvap_sum:,}  (independent rounding, {county_cvap_sum - state_cvap:+d} vs state table)")
    print()
    print(f"Statewide rate: {state_pct:.6f}% -> {one_decimal(state_pct)}%  (claim: 100.2%)")
    print(f"Inactive on official rolls: {state_inactive:,}  (claim: 462,824)  match={state_inactive == 462824}")
    print(f"Counties over 100% (total registrations > cvap_est): {n_over} of 67  (claim: 32)")
    print(f"Of those, still over after MOE (total > cvap_est + cvap_moe): {n_still}  (claim: 28)")
    print(f"Active-only sensitivity (active > cvap_est): {n_active_over} of 67 counties")
    print(f"Active-only statewide: {100.0 * state_active / state_cvap:.2f}%")
    print()

    print("Claimed seven rows:")
    all_match = True
    for county, (claim_pct, claim_over) in CLAIMED_ROWS.items():
        r = next(x for x in rows if x["county"] == county)
        got_pct = Decimal(r["pct_registered_vs_cvap_1decimal"])
        match = got_pct == claim_pct and r["over_count"] == claim_over
        all_match = all_match and match
        print(
            f"  {county:12} {r['registered_total']:,} / {r['cvap_est']:,} = "
            f"{r['pct_registered_vs_cvap']:.6f}% -> {got_pct}%  "
            f"{r['over_count']:,} over  claimed {claim_pct}% {claim_over:,} over  "
            f"MATCH={match}  still_after_moe={r['still_over_after_moe']}"
        )
    print()
    print(f"Seven claimed rows all match: {all_match}")
    print(f"Headline counts match (32 / 28 / 462,824 / 100.2%): "
          f"{n_over == 32 and n_still == 28 and state_inactive == 462824 and one_decimal(state_pct) == Decimal('100.2')}")
    print()
    print("Four counties are over 100% at the point estimate but not after adding the 90% CI MOE:")
    for r in rows:
        if r["over_100"] and not r["still_over_after_moe"]:
            print(
                f"  {r['county']}: {r['pct_registered_vs_cvap_1decimal']}%  "
                f"{r['over_count']} over  MOE ±{r['cvap_moe']}  "
                f"upper bound {r['cvap_upper_90ci']:,}"
            )
    print()
    print("Active-only counties still over 100%:")
    for r in rows:
        if r["active_over_100"]:
            print(
                f"  {r['county']}: active {r['registered_active']:,} / {r['cvap_est']:,} = "
                f"{r['pct_active_vs_cvap_1decimal']}%"
            )
    print()
    print(f"Wrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
