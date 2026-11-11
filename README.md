# Trading Intelligence Dashboard — GitHub Pages

## Publish each day's dashboard

When you have a new standalone `trading_dashboard_YYYY-MM-DD.html` file:

**Simple browser-only method**

1. Upload the new HTML file into the `archive/` folder on GitHub.
2. Edit `data/latest.json` to set `date` to the new date, `file` to `archive/trading_dashboard_YYYY-MM-DD.html`, and `published_at` to the publication timestamp.
3. Commit both changes to `main`. The workflow deploys automatically.

**Faster local method** (Python 3 installed):

```bash
python publish.py /path/to/trading_dashboard_2026-11-12.html
git add archive data/latest.json
git commit -m "Publish trading dashboard 2026-11-12"
git push
```

The `publish.py` script refuses to overwrite a previous archived daily HTML file.

## What updates automatically?

- **GitHub Actions** republishes the site whenever you push to `main`.
- The open dashboard checks `data/latest.json` every **five minutes** and when you return to its tab. If the published date changes, it loads the newly published HTML file.
- If no new report is published, it keeps showing the previous report **and warns that the snapshot is old**.
- The scheduled ChatGPT task **does not automatically write into GitHub**. You must publish the generated HTML file, or separately connect an authorized automation to your repository. A GitHub schedule by itself cannot generate verified Forex Factory/Bigdata.com intelligence.

## Security and reliability

No API keys, passwords, external JavaScript libraries, tracking scripts or TradingView widgets are needed for the wrapper. Published dashboards are public; don't add private notes or secrets. Individual archived HTML files may contain their own links. Prices and news are fixed snapshots, not investment advice.

## File map

- `index.html` — permanent dashboard page and refresh checker
- `data/latest.json` — pointer to the latest published report
- `archive/` — immutable dated HTML dashboards
- `.github/workflows/deploy.yml` — GitHub Pages deployment workflow
- `publish.py` — optional local publishing helper
