# Dance Classes Timetable

https://oiocha1.github.io/Dance-Classes-Timetable/

A weekly scrape of dance class timetables from a select few dance studios in Sydney, shown on a phone-friendly dashboard. 

For personal use purposes, it defaults to **Absolute Beginner** classes, plus IMI's **Foundations** classes.

| Studio | Source |
|---|---|
| IMI (Lidcombe) | ClassPass |
| Crossover (Sydney CBD + XO2S) | ClassPass |
| Movement Nation Hurstville | Wix Bookings |
| Movement Nation Parramatta | Wix Bookings |
| IX (Burwood) | Wix Bookings |

- **Runs:** every Sunday morning (Sydney), on demand via the dashboard's Refresh button, and whenever the code changes.
- **Shows:** today through the next 7 days, hiding classes that have already finished.
- **Excludes:** kids and youth classes.

## One-time setup

1. **Turn on GitHub Pages.** Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. **Run it once.** Repo **Actions → Scrape timetables → Run workflow**. It takes about a minute.
3. **Open the dashboard** at `https://oiocha1.github.io/Dance-Classes-Timetable/`. On iPhone, tap **Share → Add to Home Screen** for an app icon.
4. **Optional: set up the Refresh button.** It needs a GitHub token that stays on your phone only.
   - GitHub **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
   - Repository access: **Only select repositories → Dance-Classes-Timetable**.
   - Permissions: **Actions → Read and write**. Nothing else.
   - On the dashboard, tap ⚙️ and paste the token.

   Without a token, you can still refresh from the GitHub app: **Actions → Scrape timetables → Run workflow**.

> GitHub Pages is free for **public** repos. A private repo needs a paid GitHub plan for Pages.

## How it works

- `scraper/scrape.py` calls each studio's booking-system API. It writes `docs/data.json`.
  - It uses only the Python standard library.
  - If a studio fails, its classes from the last good run are kept. The dashboard then says that studio "didn't update".
- `scraper/normalise.py` turns titles like `Class@XO2S | Popping (Absolute Beginners)` into a clean name and a standard level: **Popping (Abs Beg)**.
  - IMI's *Basics* tier shows as **Foundations**.
  - Classes with no level in the title show as **Unlabelled**.
- `scraper/test_normalise.py` checks those rules against real class titles. It runs before every scrape.
- `docs/index.html` is the dashboard. Your filter choices are remembered on each device.

## Adding a studio

If it uses Mindbody or Wix Bookings, add an entry to `STUDIOS` in `scraper/scrape.py`:

- **Mindbody:** needs the location slug from its `mindbodyonline.com/explore/locations/<slug>` URL.
- **Wix:** needs the site's base URL.
