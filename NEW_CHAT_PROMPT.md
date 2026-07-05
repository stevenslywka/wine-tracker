# Wine Tracker New Chat Prompt

Copy/paste this at the start of a new Codex or Claude chat:

```text
I am working on my Flask wine cellar app in:
C:\Users\steve\wine-tracker

Use that folder as the project root.

Start by reading:
1. AGENTS.md
2. NEW_CHAT_PROMPT.md

Then run `git status --short` as a rough dirty-worktree signal and inspect the relevant current files before suggesting or editing. Do not overwrite existing local changes.

Important workflow guardrails:
- Treat `AGENTS.md` as the source of truth for project rules, schema, inventory behavior, verification, and deploy notes.
- Local Git metadata may be stale or locked because some pushes are done through the GitHub API. If local Git disagrees with GitHub `main`, treat GitHub `main` as source of truth.
- If local Git metadata writes fail, do not fight it. Use the GitHub API workflow in `AGENTS.md` only if I explicitly ask you to push.
- When pushing behavior/UI changes that alter current project truth, update `AGENTS.md` and `NEW_CHAT_PROMPT.md` in the same push or in an immediate follow-up push.
- Do not delete local files, push/transmit data, or use external network access unless I explicitly ask or approve.
- Please explain steps in plain language.

Project context:
- Live site: https://stevenwinecellar.up.railway.app/
- GitHub repo: https://github.com/stevenslywka/wine-tracker
- Railway deploys automatically from GitHub `main`.
- Flask app: `app.py`; DB helpers/migrations: `db.py`; main cellar: `templates/index.html`; wine detail: `templates/detail.html`.
- Local database is SQLite `wines.db`; production is PostgreSQL.
- Schema changes must go through `db.py -> migrate()`.
- Latest production UI work: home-screen PWA (manifest, icons, standalone mode, 90-day sessions) and an Analytics page crash fix; part of the in-progress Cellar Usability build (see AGENTS.md).

Inventory truth:
- Current inventory uses `wine_inventory_lots`, not individual bottle records.
- `wines.quantity/status/storage_location/location_summary`, source/date/price fields, and total price are cached summaries synced by `db.sync_wine_summary()`.
- Lots use only `in_collection` and `not_shipped`; `drank` is a derived wine summary state plus drink history.
- Drink history lives in `wine_drink_history` and keeps a `storage_location` snapshot.
- Mobile detail inventory changes usually stay in `templates/detail.html`; backend behavior is needed for inventory semantics such as partial Receive Shipment.
- On mobile detail, Add bottles uses `Not Shipped` as a Location option that maps to lot status `not_shipped`; saved locations map to available inventory. Receive Shipment can partially receive incoming lots.
- Tap-to-add photo: the mobile hero image/placeholder is tappable for the owner and auto-uploads (client-side downscale) via ownership-checked `POST /wine/<id>/photo`; `_store_wine_image()` is shared with `add_wine`. Live persistence needs `CLOUDINARY_*` env vars on Railway; otherwise uploads land in `static/uploads` and vanish on redeploy.
- Home-screen app: `static/manifest.json` + `static/icons/` and PWA/iOS meta tags in every template head; standalone display, no service worker; login sessions are permanent (90 days) so the installed app stays signed in.
- Location-aware cellar default: the owner's mobile cellar auto-filters to the residence you're standing in (`storage_location=<loc>&geoloc=1`, pin chip with ✕ that sets `sessionStorage.geoLocDismissed`); explicit filters never overridden, silent fallback elsewhere.
- Geolocation default: `user_locations` has nullable `latitude`/`longitude` (steven's Apt/House seeded via `db.migrate()`). The mobile Add bottles sheet pre-selects the nearest saved location when opened without an explicit one (accuracy <= 200 m, distance <= 300 m, owner only, silent fallback); position is used client-side and discarded, never stored.
- Scan re-buy: `POST /wine/scan-label` matches the scanned label against the cellar and returns `match` with a `/wine/<id>?rebuy=1` deep link that auto-opens the mobile Add bottles sheet; the Add Wine scan UIs show an "Already in your cellar" banner with "Add another bottle" / "Add as new wine". Both scan routes share one AI helper and the `SCAN_MODEL` constant.
- Wine-family grouping: `wines.family_key` (nullable) groups the same wine across vintages and bottle sizes, auto-assigned from the normalized name ignoring vintage-year tokens and bottle-size wording (Magnum, 375ml, 1.5L, ...). Mobile detail shows a collapsible "Vintages" section under the hero — preview `X different vintages`, expanded rows for every family member including the current wine with availability/incoming/drank info. Link vintages / Unlink this vintage live in the hamburger menu (`POST /wine/<id>/family/link` and `/family/unlink`). Unlinked wines get a unique `wine:<id>` key so migration backfill never re-links them; migration re-normalizes existing key groups whole when the key algorithm changes.
- Mobile detail section order is Bottles, Cellar, Drink History, Wine Details, Purchase. Bottles and Cellar are collapsed by default; Bottles previews counts like `2 total · 1 Apt · 1 House`; Cellar previews starred Rating, Drinking Window, Sticker Color, and Source. The hero shows bottle/location/drinking-window context, the sticky header shows the wine name, delete lives in the hamburger menu, and Set Count to 0 requires confirmation. Expanded Cellar Source and Drinking Window values are centered; long Region/Varietal values can be dragged horizontally on mobile.

Do not touch unless I explicitly ask:
- `templates/index.html` mobile Cards/List layout.
- Desktop views in `templates/index.html` or `templates/detail.html`.
- Inventory model semantics: lots, not physical individual bottles.
- Unrelated dirty files, especially local parser or data files.
- The local database `wines.db`.

For detail-page or inventory work, verify with:
```powershell
cd C:\Users\steve\wine-tracker
& 'C:\Users\steve\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\verify_detail.py
```

For local dev:
```powershell
cd C:\Users\steve\wine-tracker
.\.venv\Scripts\python.exe app.py
```
```
