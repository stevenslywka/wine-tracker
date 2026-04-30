# Wine Tracker New Chat Prompt

Copy/paste this at the start of a new Codex chat:

```text
I am working on my Flask wine cellar app in:
C:\Users\steve\wine-tracker

Please use that folder as the project root. Start by reading `AGENTS.md` and this `NEW_CHAT_PROMPT.md`, then inspect the current files and run `git status --short` before changing anything. Do not overwrite existing local changes.

High-signal project context:
- Live site: https://stevenwinecellar.up.railway.app/
- GitHub repo: https://github.com/stevenslywka/wine-tracker
- Railway deploys from GitHub `main`.
- Flask app: `app.py`; migrations/helpers: `db.py`; main cellar: `templates/index.html`; wine detail: `templates/detail.html`.
- Local DB is SQLite `wines.db`; production is PostgreSQL.
- Schema changes must go through `db.py -> migrate()`.

Current truth:
- Current inventory lives in `wine_inventory_lots`; do not add individual bottle tracking unless I explicitly ask.
- `wines.quantity/status/storage_location/location_summary`, source/date/price, and total price are cached summaries synced by `db.sync_wine_summary()`.
- Lots use `in_collection` and `not_shipped`; `drank` is derived from no available/incoming lots plus drink history.
- Drink history lives in `wine_drink_history` and includes `storage_location` so rows can show/edit where a bottle was consumed from.
- Mobile Wine Detail now uses a compact `Bottles` stock-control panel: dotted location summary, two-column location cards with `-`, `+`, and `...`; Drink History rows are tappable for edit/delete.
- Detail-page `+ Add` uses `/wine/<id>/add-lot`; broader Add Wine re-buy detection is still future work.

Do not touch unless I explicitly ask:
- `templates/index.html` mobile Cards/List layout.
- Desktop views in `templates/index.html` or `templates/detail.html`.
- Inventory model semantics: lots, not physical individual bottles.
- Unrelated dirty files.

Current mobile Wine Detail shape:
- Sticky header with menu, centered cellar title, trash icon.
- Hero: image/no-photo, editable name, vintage/sticker, region/origin, varietal.
- Quick strip: Drinking Window only.
- Bottles panel: summary by location; `-` drinks one from that location; `+` opens Add bottles; `...` opens move/correct count; incoming lots show `Receive`; Drink History rows open edit/delete.
- Main body: Source, Sticker, Rating, Notes; then Wine details and Purchase sections.
- Bottom action bar: Back to Cellar, Previous Wine, Next Wine.

Important routes:
- `GET /wine/<id>`
- `POST /wine/<id>/drink-one`
- `POST /wine/<id>/add-lot`
- `POST /wine/<id>/location/move`
- `POST /wine/<id>/location/correct`
- `POST /wine/<id>/drink-history/<history_id>/update`
- `POST /wine/<id>/drink-history/<history_id>/delete`
- Existing lot routes remain: `/lot/<lot_id>/adjust`, `/move`, `/receive`, `/lot/add-location`.

Verification shortcut for detail/inventory work:
```powershell
cd C:\Users\steve\wine-tracker
& 'C:\Users\steve\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\verify_detail.py
```

Local dev:
```powershell
cd C:\Users\steve\wine-tracker
.\.venv\Scripts\python.exe app.py
```

Notes:
- Local Git metadata may be stale/locked after GitHub API pushes. Treat GitHub `main` as source of truth if local Git disagrees.
- GitHub token path for API pushes: `C:\Users\steve\Documents\Codex\codex-auth\gh\hosts.yml`. Never print the token.
- Please explain steps in plain language. For UI work, verify mobile and desktop behavior carefully. If deleting local files or pushing/transmitting data, ask first unless I have already asked for that action.
```
