"""Scrape the coming week's dance classes from each studio and write docs/data.json.

Standard library only, so the GitHub Action needs no installs.
Run:  python scraper/scrape.py
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from normalise import LEVELS, clean_teacher, clean_title, detect_level, display_name, is_kids

SYDNEY = ZoneInfo("Australia/Sydney")
DAYS_AHEAD = 7
OUT = Path(__file__).resolve().parent.parent / "docs" / "data.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
WIX_BOOKINGS_APP = "13d21c63-b5ec-5912-8397-c3a5ddb27a97"

# id: what the dashboard filters on. label: what it shows.
STUDIOS = [
    # "classpass": the studio's ClassPass venue. Classes found there link straight to that class
    # (classpass.com/schedule/<id>, which opens the ClassPass app); the rest link to the studio page.
    {"id": "imi", "label": "IMI", "kind": "mindbody", "slug": "imi-dance",
     "address": "11 East St, Lidcombe", "book": "https://classpass.com/studios/imi-dance-lidcombe",
     "classpass": {"venue": 209935}},
    {"id": "crossover", "label": "Crossover", "kind": "mindbody", "slug": "crossover-dance-studio",
     "address": "22-26 Goulburn St, Sydney", "book": "https://classpass.com/studios/crossover-dance-studio-sydney",
     "classpass": {"venue": 30476}},
    {"id": "mn-hurstville", "label": "Movement Nation Hursi", "kind": "wix",
     "base": "https://www.movementnationdancestudio.com",
     "address": "38 Humphreys Ln, Hurstville", "book": "https://www.movementnationdancestudio.com/hurstville-bookings"},
    {"id": "mn-parramatta", "label": "Movement Nation Parra", "kind": "wix",
     "base": "https://2020movementnation.wixsite.com/website-1",
     "address": "110 Church St, Parramatta", "book": "https://2020movementnation.wixsite.com/website-1"},
    {"id": "ix", "label": "IX", "kind": "wix", "base": "https://www.ixdancestudio.com",
     "address": "52 Burwood Rd, Burwood", "book": "https://www.ixdancestudio.com"},
]


def http_json(url, body=None, headers=None, retries=3):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def make_class(studio, title, start, end, teacher, room=None, xo2s=False):
    """Build one class record, or None for kids classes."""
    if is_kids(title):
        return None
    level = detect_level(title)
    # IMI's "Basics" level is its Foundations tier; elsewhere treat Basics as Beginner.
    if level == "foundations" and studio["id"] != "imi":
        level = "beginner"
    base, title_room = clean_title(title, strip_teacher_suffix=studio["kind"] == "wix")
    room = room or title_room
    where = studio["label"] + (" XO2S" if xo2s else "")
    if room:
        where += f" · {room}"
    return {
        "studio": studio["id"],
        "where": where,
        "name": display_name(base, level),
        "level": level,
        "teacher": clean_teacher(teacher or ""),
        "start": start.isoformat(),
        "end": end.isoformat() if end else None,
        "raw": title,
        "book": studio["book"],
    }


def scrape_mindbody(studio, start, end):
    url = "https://prod-mkt-gateway.mindbody.io/v1/search/class_times"
    out, page = [], 1
    while True:
        body = {
            "sort": "start_time",
            "page": {"size": 100, "number": page},
            "filter": {
                "radius": 0,
                # Pad by a day each side (the API's timezone handling is ambiguous);
                # results are trimmed to the exact window in main().
                "startTimeRanges": [{"from": (start - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                                     "to": (end + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")}],
                "locationSlugs": [studio["slug"]],
                "include_dynamic_pricing": True,
                "inventory_source": ["MB"],
            },
        }
        j = http_json(url, body)
        staff = {i["id"]: i["attributes"].get("name", "")
                 for i in j.get("included", []) if i.get("type") == "staff"}
        for d in j.get("data", []):
            a = d["attributes"]
            title = a.get("displayName") or ""
            s = datetime.fromisoformat(a["startTime"].replace("Z", "+00:00")).astimezone(SYDNEY)
            e = datetime.fromisoformat(a["endTime"].replace("Z", "+00:00")).astimezone(SYDNEY) if a.get("endTime") else None
            sid = (d.get("relationships", {}).get("staff", {}).get("data") or {}).get("id")
            c = make_class(studio, title, s, e, staff.get(sid, ""), xo2s="xo2s" in title.lower())
            if c:
                out.append(c)
        found = j.get("meta", {}).get("found", 0)
        if page * 100 >= found or not j.get("data"):
            return out
        page += 1


def scrape_wix(studio, start, end):
    base = studio["base"]
    tokens = http_json(f"{base}/_api/v1/access-tokens")
    token = tokens["apps"][WIX_BOOKINGS_APP]["instance"]
    out, cursor = [], None
    while True:
        body = {
            "fromLocalDate": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "toLocalDate": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Australia/Sydney",
            "includeNonBookable": True,
            "cursorPaging": {"limit": 100, **({"cursor": cursor} if cursor else {})},
        }
        j = http_json(f"{base}/_api/service-availability/v2/time-slots/event", body,
                      headers={"Authorization": token})
        for s in j.get("timeSlots", []):
            title = (s.get("eventInfo") or {}).get("eventTitle") or ""
            st = datetime.fromisoformat(s["localStartDate"]).replace(tzinfo=SYDNEY)
            en = datetime.fromisoformat(s["localEndDate"]).replace(tzinfo=SYDNEY) if s.get("localEndDate") else None
            names = [r["name"] for g in s.get("availableResources", []) for r in g.get("resources", [])]
            c = make_class(studio, title, st, en, ", ".join(names))
            if c:
                out.append(c)
        paging = j.get("pagingMetadata") or {}
        cursor = (paging.get("cursors") or {}).get("next")
        if not paging.get("hasNext") or not cursor:
            return out


def _match_key(title, start):
    """Same class in Mindbody and ClassPass: same start minute and same title (ClassPass mirrors Mindbody)."""
    return (start.astimezone(SYDNEY).strftime("%Y-%m-%dT%H:%M"), " ".join(title.lower().split()))


def link_classpass(studio, classes, start, days):
    """Point each class at its own ClassPass page where ClassPass lists it. Returns how many matched."""
    venue = studio["classpass"]["venue"]
    # Visit the studio page first (like a browser would) so the API calls carry its cookies.
    import http.cookiejar
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    browser = {"User-Agent": UA, "Accept-Language": "en-AU,en;q=0.9"}
    page = urllib.request.Request(studio["book"], headers={**browser, "Accept": "text/html,application/xhtml+xml"})
    opener.open(page, timeout=30).read()
    api_headers = {**browser, "Accept": "application/json", "Content-Type": "application/json",
                   "Origin": "https://classpass.com", "Referer": studio["book"]}
    by_key, by_time = {}, {}
    for i in range(days):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        req = urllib.request.Request("https://classpass.com/_api/v3/search/schedules", method="POST",
                                     data=json.dumps({"date": day, "venue": [venue]}).encode(), headers=api_headers)
        with opener.open(req, timeout=30) as r:
            j = json.loads(r.read().decode())
        for s in j.get("schedules", []):
            st = datetime.fromtimestamp(float(s["starttime"]), SYDNEY)
            key = _match_key((s.get("class") or {}).get("name", ""), st)
            by_key[key] = s["id"]
            by_time.setdefault(key[0], []).append(s["id"])
    matched = 0
    for c in classes:
        key = _match_key(c["raw"], datetime.fromisoformat(c["start"]))
        sid = by_key.get(key)
        if sid is None and len(by_time.get(key[0], [])) == 1:
            sid = by_time[key[0]][0]  # only one ClassPass class at that time: safe to match on time alone
        if sid is not None:
            c["book"] = f"https://classpass.com/schedule/{sid}"
            c["via"] = "classpass"
            matched += 1
        else:
            c["via"] = "classpass-studio"
    return matched


def main():
    now = datetime.now(SYDNEY)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=DAYS_AHEAD + 1) - timedelta(seconds=1)

    previous = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text())
        except Exception:
            previous = {}

    classes, status, cp_notes = [], {}, {}
    for studio in STUDIOS:
        try:
            fn = scrape_mindbody if studio["kind"] == "mindbody" else scrape_wix
            got = [c for c in fn(studio, start, end)
                   if start <= datetime.fromisoformat(c["start"]) <= end]
            if studio.get("classpass"):
                try:
                    n = link_classpass(studio, got, start, DAYS_AHEAD + 1)
                    print(f"{studio['label']}: {n}/{len(got)} classes linked to ClassPass")
                    cp_notes[studio["id"]] = f"{n}/{len(got)} linked"
                except Exception as exc:  # ClassPass down: classes still link to the ClassPass studio page
                    for c in got:
                        c["via"] = "classpass-studio"
                    print(f"{studio['label']}: ClassPass lookup failed ({exc})", file=sys.stderr)
                    cp_notes[studio["id"]] = f"failed: {str(exc)[:200]}"
            classes += got
            status[studio["id"]] = {"ok": True, "count": len(got), "updated": now.isoformat()}
            if studio["id"] in cp_notes:
                status[studio["id"]]["classpass"] = cp_notes[studio["id"]]
            print(f"{studio['label']}: {len(got)} classes")
        except Exception as exc:  # keep last good data for a studio that failed
            old = [c for c in previous.get("classes", []) if c["studio"] == studio["id"]]
            classes += old
            prev_status = previous.get("status", {}).get(studio["id"], {})
            status[studio["id"]] = {"ok": False, "error": str(exc)[:200], "count": len(old),
                                    "updated": prev_status.get("updated")}
            print(f"{studio['label']}: FAILED ({exc}); kept {len(old)} old classes", file=sys.stderr)

    classes.sort(key=lambda c: (c["start"], c["where"]))
    data = {
        "generated": now.isoformat(),
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "levels": {k: {"tag": t, "label": l} for k, (t, l) in LEVELS.items()},
        "studios": [{k: s[k] for k in ("id", "label", "address", "book")} for s in STUDIOS],
        "status": status,
        "classes": classes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"Wrote {len(classes)} classes to {OUT}")
    if not any(s["ok"] for s in status.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
