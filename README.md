# Résumé Rank

College football rankings built from results alone, with five views of the same season:
**Recursive**, **Opponent wins + schedule**, **Elo**, **My rank** (AP-poll based), a **Compare** tab for any two teams, a **Movers** tab that replays the season week by week, a **Spreads** tab that compares each system's implied point spread with the sportsbook line for this week's games, a **Performance** tab that grades each system with a weekly $5 betting backtest, and a **My picks** tab where you lock in your own picks each week and track them against the models.

The page is a single static `index.html` that reads `data.json`. A GitHub Action refreshes `data.json` from [CollegeFootballData.com](https://collegefootballdata.com) and redeploys the site to GitHub Pages on a schedule.

## Set it up (about 10 minutes)

1. **Create a repository** and add these files, keeping the folder layout:
   ```
   index.html
   data.json
   picks.json
   scripts/build_data.py
   .github/workflows/update.yml
   README.md
   ```
   The `.github` folder is hidden on Mac and Linux, so drag-and-drop uploads can skip it. Push with git or GitHub Desktop, or create `.github/workflows/update.yml` in the GitHub web editor (Add file → Create new file) and paste its contents.

2. **Get a free API key** at https://collegefootballdata.com/key.

3. **Add the key as a secret:** Settings → Secrets and variables → Actions → New repository secret. Name it `CFBD_API_KEY`.

4. **Turn on Pages:** Settings → Pages → Build and deployment → Source: **GitHub Actions**.

5. **Run it once:** Actions → *Update rankings data* → Run workflow. When it finishes, the site is live at `https://<your-user>.github.io/<repo-name>/`.

## My picks: set your password

Anyone can view the site, but only you can submit picks. The site is static, so a password typed into the page can't be checked securely or save anything by itself. Instead, the "password" is a GitHub token that can write to this one repo. Picks are committed to `picks.json`, and the commit history doubles as a timestamped record that each pick went in before kickoff.

1. Go to GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → **Generate new token** (https://github.com/settings/personal-access-tokens/new).
2. Name it something like `cfbranks picks` and pick an expiration (a season-long date is fine).
3. **Repository access:** Only select repositories → this repo.
4. **Permissions → Repository permissions → Contents:** Read and write. Leave everything else at No access.
5. Generate it and copy the token (it starts with `github_pat_`). Keep it somewhere safe; GitHub only shows it once.
6. On the site's **My picks** tab, select your sides, paste the token into the password box, and tap **Lock in picks**. Check "Remember on this device" to skip pasting it next time (it's stored only in that browser, and "Forget saved password" removes it).

How picks work:
- Each pick is a $5 bet at −110 against the median line shown on the site when you submit it. That line is locked with the pick.
- Picks can't be changed after submission, and a game can't be picked once it kicks off.
- Results are graded from the same data feed as everything else, usually within an hour of the game ending on Saturdays.
- The comparison line is the average of the four models' weekly $5 cards (10 bets each) over the weeks you've made picks. Compare ROI for a fair read, since the number of bets differs.
- If the token expires or is revoked, generate a new one the same way.

## When it updates

| When (UTC) | Why |
|---|---|
| Every day at 11:00 | Catches midweek games and corrections |
| Saturday 16:00–23:00, hourly | Saturday games as they finish |
| Sunday 00:00–08:00, hourly | Late Saturday games (West Coast) |
| Sunday 19:30 and 22:30 | The AP poll, released about 2 p.m. ET |

Each run makes 5 API calls during the regular season (games and rankings for the regular season and postseason, plus the season's betting lines) and 6 once bowl games are scheduled, roughly 560 to 680 calls a month. Check CFBD's current free-tier limit if you add more runs. A run commits `data.json` only when there are new games or a new poll, so history stays clean.

The season is picked automatically (July onward counts as the new season). To pin one, add a repository **variable** (not a secret) named `SEASON`, for example `2026`.

## If a run fails

The workflow has two jobs: **build** (refresh `data.json`, commit it, package the site) and **deploy** (publish to Pages). Deploy retries itself twice, after 30 seconds and then 90 seconds, to ride out the occasional "No artifacts named github-pages were found" error. If a run still fails:

- Check whether the failed step is under **build** or **deploy**. A failed deploy doesn't lose anything: the data is already committed, and the site updates on the next run.
- To fix it sooner, open the run and click **Re-run failed jobs**, or start **Update rankings data** again with **Run workflow**.
- Also check https://www.githubstatus.com for Actions or Pages incidents.

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
- **Spreads:** the Vegas line is the median across sportsbooks CFBD returns. Each system's ratings from before the current week are converted to points with a least-squares fit on this season's FBS results (points per rating unit plus home field). The variance score is the gap in points between the model line and Vegas.
- **Performance:** from week 3 on, each system bets $5 at −110 on its 10 biggest variance scores each week, using only games played before that week. Grades come from return on money wagered (A: +10% or better, B: +3% to +10%, C: −3% to +3%, D: −10% to −3%, F: below −10%).

## Files

- `index.html`: the whole app (HTML, CSS and JavaScript). No build step.
- `picks.json`: your locked picks, written by the site when you submit. Each pick records the week, teams, side, line, kickoff and submission time.
- `data.json`: `{season, updated, slate, conf, games, ap}`. `slate` holds the current week's games with the median spread (home-team perspective, negative means the home team is favored). Each game is `[week, date, home, homePts, away, awayPts, homeIsFBS, awayIsFBS, neutral, medianSpread]`, where the spread is from the home team's perspective (negative means the home team was favored) or `null` if no line was posted.
- `scripts/build_data.py`: fetches CFBD data and writes `data.json`. Standard library only.
- `.github/workflows/update.yml`: the schedule, the data refresh and the Pages deploy.
