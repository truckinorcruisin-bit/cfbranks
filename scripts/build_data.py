#!/usr/bin/env python3
"""Build data.json for the Résumé Rank page from CollegeFootballData.com (CFBD).

Usage:
  CFBD_API_KEY=... python scripts/build_data.py            # current season
  CFBD_API_KEY=... SEASON=2026 python scripts/build_data.py

Writes data.json next to index.html. Uses only the Python standard library.
Get a free API key at https://collegefootballdata.com/key
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://api.collegefootballdata.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def truthy(v):
    return v is True or str(v).strip().lower() == "true"


def get(path, params, key):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def local_date(start):
    # Shift UTC kickoff back 6 hours so late-night games land on the calendar day they were played in the US.
    t = dt.datetime.fromisoformat(str(start).replace("Z", "+00:00")) - dt.timedelta(hours=6)
    return t.date().isoformat()


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def num(v):
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


def target_week(games):
    """The week to show spreads for: the earliest week that still has unplayed FBS games."""
    open_games = [g for g in games if not truthy(g.get("completed"))
                  and "fbs" in (g.get("homeClassification"), g.get("awayClassification"))]
    if not open_games:
        return None
    order = {"regular": 0, "postseason": 1}
    g = min(open_games, key=lambda g: (order.get(g.get("seasonType", "regular"), 2), int(g["week"])))
    return int(g["week"]), g.get("seasonType", "regular")


def transform(games, rankings, season, lines=None):
    """Turn CFBD games + rankings (+ this week's betting lines) into the compact shape the page reads."""
    regular = [g for g in games if g.get("seasonType", "regular") == "regular"]
    reg_max = max((int(g["week"]) for g in regular), default=0)

    def week_of(obj):
        w = int(obj["week"])
        return w + reg_max if obj.get("seasonType") == "postseason" else w

    # Median sportsbook spread per game (home-team perspective: negative = home favored).
    line_by_id, line_by_key = {}, {}
    for ln in lines or []:
        spreads = [num(x.get("spread")) for x in ln.get("lines", []) if num(x.get("spread")) is not None]
        ous = [num(x.get("overUnder")) for x in ln.get("lines", []) if num(x.get("overUnder")) is not None]
        rec = {"sp": median(spreads), "ou": median(ous), "books": len(spreads)}
        line_by_id[str(ln.get("id"))] = rec
        line_by_key[(ln.get("seasonType", "regular"), str(ln.get("week")), ln.get("homeTeam"), ln.get("awayTeam"))] = rec

    def line_for(g):
        return (line_by_id.get(str(g.get("id")))
                or line_by_key.get((g.get("seasonType", "regular"), str(g.get("week")), g.get("homeTeam"), g.get("awayTeam")))
                or {})

    conf, rows = {}, []
    for g in games:
        if not truthy(g.get("completed")):
            continue
        if g.get("homePoints") in (None, "") or g.get("awayPoints") in (None, ""):
            continue
        h_fbs = g.get("homeClassification") == "fbs"
        a_fbs = g.get("awayClassification") == "fbs"
        if not (h_fbs or a_fbs):
            continue
        if h_fbs:
            conf[g["homeTeam"]] = g.get("homeConference") or "FBS Independents"
        if a_fbs:
            conf[g["awayTeam"]] = g.get("awayConference") or "FBS Independents"
        rows.append([
            week_of(g), local_date(g["startDate"]),
            g["homeTeam"], int(float(g["homePoints"])),
            g["awayTeam"], int(float(g["awayPoints"])),
            h_fbs, a_fbs, truthy(g.get("neutralSite")),
            line_for(g).get("sp"),
        ])
    rows.sort(key=lambda r: (r[1], r[0], r[2]))

    # AP poll by week. CFBD week N is the poll released going into week N.
    ap = {}
    for wk in rankings or []:
        for poll in wk.get("polls", []):
            if poll.get("poll") != "AP Top 25":
                continue
            ranks = [r for r in poll.get("ranks", []) if r.get("school")]
            top = [r["school"] for r in sorted(ranks, key=lambda r: r.get("rank") or 999) if (r.get("rank") or 999) <= 25]
            extra = [r for r in ranks if (r.get("rank") or 999) > 25]
            votes = [[r["school"], int(r.get("points") or 0)] for r in sorted(extra, key=lambda r: -(r.get("points") or 0))]
            ap[str(week_of(wk))] = {"top": top, "votes": votes}

    # This week's slate with the median sportsbook line (home-team perspective: negative = home favored).
    slate = None
    tw = target_week(games)
    if tw:
        week, stype = tw
        sg = []
        for g in games:
            if int(g["week"]) != week or g.get("seasonType", "regular") != stype:
                continue
            h_fbs = g.get("homeClassification") == "fbs"
            a_fbs = g.get("awayClassification") == "fbs"
            if not (h_fbs or a_fbs):
                continue
            ln = line_for(g)
            done = truthy(g.get("completed")) and g.get("homePoints") not in (None, "")
            sg.append({
                "h": g["homeTeam"], "a": g["awayTeam"], "hF": h_fbs, "aF": a_fbs,
                "n": truthy(g.get("neutralSite")), "t": g["startDate"], "done": bool(done),
                "hp": int(float(g["homePoints"])) if done else None,
                "ap": int(float(g["awayPoints"])) if done else None,
                "sp": ln.get("sp"), "ou": ln.get("ou"), "books": ln.get("books", 0),
            })
        sg.sort(key=lambda x: (x["t"], x["h"]))
        slate = {"week": week + (reg_max if stype == "postseason" else 0), "seasonType": stype, "games": sg}

    return {
        "season": season,
        "slate": slate,
        "updated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "conf": conf,
        "games": rows,
        "ap": ap,
    }


def main():
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        sys.exit("Set CFBD_API_KEY (free key at https://collegefootballdata.com/key).")
    today = dt.date.today()
    season = int(os.environ.get("SEASON") or (today.year if today.month >= 7 else today.year - 1))

    games, rankings = [], []
    for st in ("regular", "postseason"):
        games += get("/games", {"year": season, "seasonType": st}, key)
        rankings += get("/rankings", {"year": season, "seasonType": st}, key)

    # Betting lines for the whole season (needed to grade each model week by week).
    lines = []
    for st in ("regular", "postseason"):
        if st == "postseason" and not any(g.get("seasonType") == "postseason" for g in games):
            continue
        try:
            lines += get("/lines", {"year": season, "seasonType": st}, key)
        except Exception as e:  # spreads are optional; rankings still update
            print(f"Could not fetch {st} lines: {e}")

    data = transform(games, rankings, season, lines)
    if not data["games"]:
        sys.exit("No completed games returned; leaving data.json unchanged.")

    out = os.path.join(ROOT, "data.json")
    try:
        with open(out, encoding="utf-8") as f:
            old = json.load(f)
        if {k: v for k, v in old.items() if k != "updated"} == {k: v for k, v in data.items() if k != "updated"}:
            print("No new games or polls; data.json left as is.")
            return
    except (OSError, ValueError):
        pass
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    sl = data.get("slate") or {}
    priced = sum(1 for r in data["games"] if r[9] is not None)
    print(f"Wrote {len(data['games'])} games, {len(data['conf'])} FBS teams, AP polls for weeks {sorted(map(int, data['ap']))}, "
          f"{priced} played games with lines, week {sl.get('week')} slate with {sum(1 for g in sl.get('games', []) if g['sp'] is not None)} lines.")


if __name__ == "__main__":
    main()
