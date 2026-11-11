# Rolls & the Estimate

An independent, static website that checks a November 10, 2026 public claim about Alabama voter registration against two primary sources:

- Alabama Secretary of State, `ALVR-2026.xlsx`, October worksheet (active + inactive).
- U.S. Census Bureau, Citizen Voting Age Population special tabulation, 2020–2024 ACS, line “Total” (`cvap_est`, `cvap_moe`).

The published totals reproduce: statewide **100.2%** (3,853,181 ÷ 3,845,696), **32 of 67** counties above the estimate, **28 of 67** above the upper end of the 90% interval, and **462,824** inactive registrations.

This is a registration count compared with a survey estimate. It is not proof of illegal votes. CVAP counts U.S. citizens age 18 and older. It does not remove disqualifications under Alabama law. The roll is an October 2026 snapshot. The estimate is ACS 2020–2024, published January 30, 2026.

The site is not a website of the State of Alabama or the U.S. Census Bureau. It has no accounts, no database, and no runtime dependencies.

## Run locally

From this directory:

```bash
python3 -m http.server 8741
```

Open http://127.0.0.1:8741

## Tests

```bash
python3 -m unittest discover -s tests -v
```

`tests/test_math.py` and `tests/test_contract.py` use only the standard library. They lock the published totals: 32 of 67 counties above the estimate, 28 of 67 above the upper end of the 90% interval, 462,824 inactive registrations, and the active-only sensitivity check (3 counties above the estimate, 2 above the upper bound). They also require the survey-vintage wording and the statement that the comparison is not proof of illegal votes.

`tests/test_ui.py` drives system Chrome through Playwright (`pip install playwright`) and checks the toggle, the county dialog, keyboard use, and that the page does not scroll sideways at 320, 375, 390, and 768 pixels. It serves the site under `/alabama-voter-rolls/`, the GitHub Pages project path. The UI test skips when Playwright is not installed, so the standard-library tests still run.

Regenerate `data/counties.json` after any change to the CSV:

```bash
python3 scripts/build_data.py
```

The script refuses to write if the CSV disagrees with the half-up rule or the headline counts. `scripts/build_data.py` and `scripts/package_site.sh` were not in the imported site archive. This repository already contains the generated `data/counties.json` and `data/county_results.csv`.

## Downloads on the site

- `data/county_results.csv` — all 67 counties.
- `data/reproduce.py` — the original methodology, unchanged. It expects to live in a subfolder and reads `raw/ALVR-2026.xlsx`, `raw/cvap_2020_2024/County.csv`, and `raw/cvap_2020_2024/State.csv`. It needs `openpyxl`. The website does not run it.

## Deploy

No environment variables, database, or custom domain are required. Do not put the site behind a login. This repository publishes with GitHub Pages, not Vercel.

### GitHub Pages

The public site is the project page:

https://knewter.github.io/alabama-voter-rolls/

`index.html` stays at the repository root. Styles, scripts, fonts, and `data/` use relative URLs, so they resolve under `/alabama-voter-rolls/` and also from a local server at `/`. `.nojekyll` is in the repository root and is copied into the published folder so GitHub does not run Jekyll.

`.github/workflows/pages.yml` runs the standard-library tests, then uploads the static site and deploys it with the official GitHub Pages actions. The workflow runs on pushes to `main`. Pages settings, if they have to be changed by hand:

https://github.com/knewter/alabama-voter-rolls/settings/pages

Source should be **GitHub Actions**. No custom domain.

Confirm the deploy reached a terminal status under the Actions tab, then open these URLs with no login:

- https://knewter.github.io/alabama-voter-rolls/
- https://knewter.github.io/alabama-voter-rolls/data/county_results.csv
- https://knewter.github.io/alabama-voter-rolls/data/reproduce.py

### Any static host

Unzip `dist/alabama-rolls-and-the-estimate.zip` and publish that folder as the site root. `index.html` is at the top level. Relative URLs also work in a subfolder.

### Railway

The container listens on Railway’s `PORT` (default 8080) and serves the same files with nginx.

```bash
docker build -t alabama-rolls .
docker run --rm -p 8741:8080 alabama-rolls
```

On Railway: create an empty project, deploy this directory (or the zip) with the included `Dockerfile` and `railway.toml`, and use the `*.up.railway.app` hostname Railway assigns. No variables. Health check path is `/`.

### Package the zip again

```bash
sh scripts/package_site.sh
```
