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
- Do not delete local files, push/transmit data, or use external network access unless I explicitly ask or approve.
- Please explain steps in plain language.

Project context:
- Live site: https://stevenwinecellar.up.railway.app/
- GitHub repo: https://github.com/stevenslywka/wine-tracker
- Railway deploys automatically from GitHub `main`.
- Flask app: `app.py`; DB helpers/migrations: `db.py`; main cellar: `templates/index.html`; wine detail: `templates/detail.html`.
- Local database is SQLite `wines.db`; production is PostgreSQL.
- Schema changes must go through `db.py -> migrate()`.
- Latest production UI work: mobile Drink History is a collapsed tasting-journal section with one-line rows, an edit bottom sheet, and saved-location color mapping so House stays red even when it is the only visible location.

Inventory truth:
- Current inventory uses `wine_inventory_lots`, not individual bottle records.
- `wines.quantity/status/storage_location/location_summary`, source/date/price fields, and total price are cached summaries synced by `db.sync_wine_summary()`.
- Lots use only `in_collection` and `not_shipped`; `drank` is a derived wine summary state plus drink history.
- Drink history lives in `wine_drink_history` and keeps a `storage_location` snapshot.
- Mobile detail inventory changes should stay in `templates/detail.html` unless backend behavior is explicitly requested.

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
