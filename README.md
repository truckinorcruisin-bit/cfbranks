# Résumé Rank

College football rankings built from results alone, with five views of the same season:
**Recursive**, **Opponent wins + schedule**, **Elo**, **My rank** (AP-poll based), a **Compare** tab for any two teams, and a **Movers** tab that replays the season week by week.

The page is a single static `index.html` that reads `data.json`. A GitHub Action refreshes `data.json` from [CollegeFootballData.com](https://collegefootballdata.com) and redeploys the site to GitHub Pages on a schedule.

## Set it up (about 10 minutes)

1. **Create a repository** and add these files, keeping the folder layout:
   ```
   index.html
   data.json
   scripts/build_data.py
   .github/workflows/update.yml
   README.md
   ```
   The `.github` folder is hidden on Mac and Linux, so drag-and-drop uploads can skip it. Push with git or GitHub Desktop, or create `.github/workflows/update.yml` in the GitHub web editor (Add file → Create new file) and paste its contents.

2. **Get a free API key** at https://collegefootballdata.com/key.

3. **Add the key as a secret:** Settings → Secrets and variables → Actions → New repository secret. Name it `CFBD_API_KEY`.

4. **Turn on Pages:** Settings → Pages → Build and deployment → Source: **GitHub Actions**.

5. **Run it once:** Actions → *Update rankings data* → Run workflow. When it finishes, the site is live at `https://<your-user>.github.io/<repo-name>/`.

## When it updates

| When (UTC) | Why |
|---|---|
| Every day at 11:00 | Catches midweek games and corrections |
| Saturday 16:00–23:00, hourly | Saturday games as they finish |
| Sunday 00:00–08:00, hourly | Late Saturday games (West Coast) |
| Sunday 19:30 and 22:30 | The AP poll, released about 2 p.m. ET |

Each run makes 4 API calls (games and rankings for the regular season and postseason), roughly 450 calls a month. Check CFBD's current free-tier limit if you add more runs. A run commits `data.json` only when there are new games or a new poll, so history stays clean.

The season is picked automatically (July onward counts as the new season). To pin one, add a repository **variable** (not a secret) named `SEASON`, for example `2026`.

## Run it locally

```bash
CFBD_API_KEY=your_key python scripts/build_data.py
python -m http.server 8000   # then open http://localhost:8000
```

Opening `index.html` directly from disk won't work because browsers block `fetch` for local files, so use the small server above.

## How the data is used

- **FCS games** are dropped everywhere: no credit for beating an FCS team, and they're removed from every team's record.
- **Game dates** are shifted six hours back from UTC so late games land on the right calendar day.
- **AP poll by week:** CFBD's poll for week *N* is the one released going into week *N*. The Movers tab scores week *W* with the poll released after week *W* (CFBD week *W+1*), falling back to the latest poll available.
- **AP ranks 26–40:** CFBD usually returns only the 25 ranked teams. My rank fills ranks 26–40 from others-receiving-votes when present, otherwise by Elo rating. Expect small differences from a hand-entered poll that includes vote totals.
- **Postseason** weeks are numbered after the last regular-season week.

## Files

- `index.html`: the whole app (HTML, CSS and JavaScript). No build step.
- `data.json`: `{season, updated, conf, games, ap}`. Each game is `[week, date, home, homePts, away, awayPts, homeIsFBS, awayIsFBS, neutral]`.
- `scripts/build_data.py`: fetches CFBD data and writes `data.json`. Standard library only.
- `.github/workflows/update.yml`: the schedule, the data refresh and the Pages deploy.
