# Wine Tracker - Codex Project Guide

Personal Flask wine cellar app replacing Vivino. Multi-user. Local dev uses SQLite; production uses PostgreSQL on Railway.

- Project root: `C:\Users\steve\wine-tracker`
- Live site: `https://stevenwinecellar.up.railway.app/`
- GitHub: `https://github.com/stevenslywka/wine-tracker`
- Railway deploys automatically from GitHub `main`
- Latest production work noted in this guide: mobile Wine Detail polish follow-up with fixed Cellar preview separators, horizontally scrollable long Region/Varietal values, starred Drink History ratings with notepad note marker, improved Drink History edit title/date sizing, and capitalized main cellar header, pushed to GitHub `main` after local verification.

## Current Truth

Trust this section first when older notes or local Git disagree.

- Current inventory lives in `wine_inventory_lots`; do not add individual bottle tracking unless Steve explicitly changes direction.
- `wines.quantity`, `wines.status`, `wines.storage_location`, `wines.location_summary`, source/date/price fields, and `wines.total_price` are cached summaries synced by `db.sync_wine_summary()`.
- Lots use only `in_collection` and `not_shipped`. `drank` is a derived wine summary state plus drink history, not a lot status.
- Drink history lives in `wine_drink_history`; `storage_location` snapshots where the bottle was consumed from, so history remains readable/editable even if lots are merged or deleted.
- Mobile Wine Detail uses compact collapsible sections in this order: Bottles, Cellar, Drink History, Wine details, Purchase. The hero shows a stretched bottle image, editable auto-growing wine name, bottle count/location chips, and drinking window. The sticky header shows the wine name and delete lives in the hamburger menu. The Bottles section has a compact count preview, tinted two-column location stock cards with top-right manage (`...`) and a `- / count / +` stepper row, incoming `Receive Shipment`, compact Drink/Add/Manage sheets, and only shows the top-level `+ Add` button in the zero-inventory state. Drink History is its own line item with tappable rows for edit/delete in a centered dialog.
- Detail-page `+ Add` adds bottles to an existing wine through `/wine/<id>/add-lot`; broader Add Wine re-buy detection is still future work.
- Main Cellar mobile Cards/List and desktop views are separate work areas. Do not change them unless requested.

## Startup Workflow

At the start of a new chat:

1. Read `AGENTS.md` and `NEW_CHAT_PROMPT.md`.
2. Run `git status --short` as a rough dirty-worktree signal.
3. Inspect current files before suggesting or editing.
4. Do not overwrite existing local changes.

Local Git metadata can be stale or locked after GitHub API pushes. Use local Git as a warning system, not final truth. If local Git disagrees with GitHub `main`, compare against GitHub `main` before reverting or overwriting anything.

## Do Not Touch Unless Asked

- `templates/index.html` mobile card layout and compact/list row layout.
- Desktop views in `templates/index.html` and `templates/detail.html`.
- Inventory model semantics: lots, not individual bottles.
- Old whole-wine quantity/status/location routes, except for compatibility fixes.
- Unrelated local changes in files like `parse_emails.py`.

## Current Mobile Detail Layout

File: `templates/detail.html`; route: `GET /wine/<id>` from `app.py -> wine_detail()`.

- Sticky mobile header: menu left, centered wine name, spacer right. Delete wine is a hamburger menu item using `id="deleteWineAction"`.
- Hero: stretched image/no-photo placeholder, editable auto-growing name, vintage/sticker, region/origin, varietal, plus a compact row for total bottles, color-coded location chips, and drinking window.
- Bottles section is collapsed by default, with a preview like `2 total · 1 Apt · 1 House`. Expanded content shows the `+ Add` button (id `openAddBottleSheet`) only when there is no available or incoming inventory; available locations render as faint-tint location cards with accented labels/counts and a `- / count / +` stepper row. Location colors are assigned from the user's saved location order, not the visible filtered order, so House remains red even when it is the only location shown. A single available location collapses to a compact horizontal row; trailing odd cards in 3+ location grids still span full width. Not-shipped lots show an incoming `Receive Shipment` strip. When inventory is completely empty, a zero-state CTA is shown instead of cards.
- `-` opens Drink one for that location with a single-line location/count title plus optional inline rating, notes, and date.
- `+` opens Add bottles, prefilled to that location, with side-by-side Qty/Location controls. `Not Shipped` appears as a Location option and maps to lot status `not_shipped`; saved locations map to `in_collection`. Purchase details include Source, a left-aligned placeholder-driven Purchase Date field, and Paid each.
- Pencil icon (SVG) opens a Manage sheet with a single-line location/count title, top-right X close button, and separate Move bottles and Set count sections; Set count corrections do not create drink history and setting a location to 0 requires confirmation.
- Not-shipped inventory appears as an incoming `Receive Shipment` strip. The Receive Shipment sheet uses Qty/Location controls and can partially receive an incoming lot, preserving the remainder as not shipped.
- Drink History is its own collapsed section after Cellar and before Wine details, with a latest-entry preview. Expanded rows are one-line tasting-journal entries with `m/d/yy`, optional `×N`, saved-location color dot/name, inline optional starred rating, optional notepad note marker, and chevron. The first 4 rows show initially; a "View all N ›" button reveals the rest inline.
- Drink History rows open a centered edit dialog titled `Drink History · date · location`. Save/delete handlers and row `data-*` attributes are intentionally preserved. Deleting restores the bottle to the selected/source location.
- Cellar section is collapsed by default, with a preview of starred Rating, Drinking Window, Sticker Color, and Source. Expanded content contains Source, Sticker, Rating, Drinking Window, then full-width Notes; Source and Drinking Window values are centered.
- Collapsed sections: Wine details preview shows Region and Varietal only; long Region/Varietal values inside Wine details can be dragged horizontally on mobile. Purchase preview is left-aligned. Purchase Order Date is left-aligned to match Paid each and Total paid.
- Bottom bar: Back to Cellar, Previous Wine, Next Wine.

## Inventory Rules

- Always run lot changes and `sync_wine_summary(conn, wine_id)` in the same transaction.
- Lot routes must verify ownership and that `lot_id` belongs to the URL `wine_id`.
- For final-bottle drink operations, insert `wine_drink_history` before deleting the source lot.
- `Correct count` is an inventory correction only and must not create drink history.
- `Move` must reject same-location moves on frontend and backend.
- `Receive` should delete/upsert so received bottles merge into an existing matching available lot.
- Do not store `Multiple` in `wines.storage_location`; use primary location there and full display text in `wines.location_summary`.

## Schema Summary

### `wines`

`id, wine_name, vintage, varietal, region, origin, wine_type, size_ml, unit_price, retail_price, total_price, quantity, retailer, order_date, status, storage_location, location_summary, color_code, drinking_window, drinking_window_source, notes, image_url, user_id`

Status values: `in_collection`, `not_shipped`, `drank`.

### `wine_inventory_lots`

`id, wine_id, quantity, status, storage_location, retailer, order_date, unit_price, notes, created_at, updated_at`

Lot status values: `in_collection`, `not_shipped`.

### `wine_drink_history`

`id, wine_id, lot_id, quantity, storage_location, drank_date, rating, notes, created_at`

`lot_id` can become null if the source lot is later deleted.

### `user_locations`

`id, user_id, name, sort_order`

Each user has their own saved locations.

## Schema Changes

Always add schema changes to `db.py -> migrate()`. Never run raw one-off `ALTER TABLE` outside migrations.

Use DB placeholders through existing helpers. Do not hardcode `?` or `%s` in shared route logic.

```python
p = ph()
cur.execute(f"SELECT * FROM wines WHERE id = {p}", (wine_id,))
```

For migrations, handle PostgreSQL and SQLite separately with `information_schema` / `ALTER TABLE ... IF NOT EXISTS` for Postgres and `PRAGMA table_info(...)` for SQLite.

## Key Routes

### Detail and inventory

- `GET /wine/<id>` - mobile/desktop detail page
- `POST /wine/<id>/drink-one` - decrement one available lot and write drink history
- `POST /wine/<id>/lot/<lot_id>/adjust` - lot-level inventory correction only
- `POST /wine/<id>/lot/add-location` - add current inventory to a saved location
- `POST /wine/<id>/add-lot` - add bottles to an existing wine, available or not-shipped
- `POST /wine/<id>/lot/<lot_id>/move` - move from one lot to another location
- `POST /wine/<id>/lot/<lot_id>/receive` - receive a not-shipped lot
- `POST /wine/<id>/location/move` - Bottle Ledger location-level move
- `POST /wine/<id>/location/correct` - Bottle Ledger location-level correction
- `POST /wine/<id>/drink-history/<history_id>/update` - edit drink history
- `POST /wine/<id>/drink-history/<history_id>/delete` - delete drink history and restore bottle

### Other important routes

- `GET /cellar/<username>` - main cellar view
- `POST /wines/bulk-edit` - mobile Select mode bulk updates; not inventory-history semantics
- `POST /wine/add`, `/wine/add-bulk`, `/wine/add-batch-scan`
- `POST /wine/scan-receipt`, `/wine/scan-label`, `/wine/recommend`, `/wine/enrich-drinking-windows`
- `GET/POST /settings/locations`
- `GET /api/wines`, `GET /export/csv`, `GET /analytics`

Compatibility note: mobile inventory counts should use Bottle Ledger controls. Older whole-wine quantity/status/location routes still exist and may collapse lots.

## Frontend Conventions

- Main cellar inline editing uses `.editable-cell` with `data-wine-id`, `data-field`, and related attributes.
- Popup close listeners in `index.html` should use capture-phase `mousedown` because cells call `stopPropagation()`.
- Scrollable table layout depends on a flex `min-height: 0` chain. Only `#tableScroll` should scroll.
- Location color classes are `loc-color-0` through `loc-color-4`.
- Use `Location` rather than `Storage` in user-facing mobile detail copy; use `Source` rather than `Retailer` where the UI says so.

## Verification Checklist

For detail-page or inventory changes, run:

```powershell
cd C:\Users\steve\wine-tracker
& 'C:\Users\steve\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\verify_detail.py
```

The helper checks:

- Python syntax for `app.py` and `db.py`.
- `db.migrate()` against local SQLite.
- Flask test-client render of a real `/wine/<id>` page.
- Presence of Bottles ledger and history edit markup.
- Inline script syntax by extracting the rendered `<script>` and checking it with Node when available.

For production pushes, also verify:

- GitHub `main` commit SHA after push.
- Live `/login` returns HTTP 200. PowerShell TLS can be flaky in this sandbox; Python `urllib` was more reliable.

## Local Dev

```powershell
cd C:\Users\steve\wine-tracker
.\.venv\Scripts\python.exe app.py
```

Local app: `http://127.0.0.1:5000`

The local `.venv` may refuse to launch inside Codex with `Access is denied`; use the bundled Codex Python plus `.venv\Lib\site-packages` for verification if needed.

## Deploy / Push

Normal Git may fail in Codex because `.git/index` or `.git/FETCH_HEAD` can be locked/stale. If normal Git fails or looks suspicious, use the GitHub API.

When pushing behavior/UI changes that alter current project truth, update `AGENTS.md` and `NEW_CHAT_PROMPT.md` in the same push or in an immediate follow-up push.

Token path:

```text
C:\Users\steve\Documents\Codex\codex-auth\gh\hosts.yml
```

Rules:

- Never print or expose the token.
- Use repo `stevenslywka/wine-tracker`, branch `main`.
- Push only the files intentionally changed.
- Verify final commit with `GET /repos/stevenslywka/wine-tracker/commits/main`.
- Railway auto-deploys from GitHub `main`.

## Markdown Update Workflow

For `AGENTS.md` and `NEW_CHAT_PROMPT.md`, prefer scripted stable-prefix replacements or a deliberate full rewrite. Avoid repeated fragile `apply_patch` attempts against prose containing emoji/mojibake. Verify with `rg`.

## Future Work

- Re-buy detection in Add Wine, using existing `/wine/<id>/add-lot`.
- Expanded/all drink history view if recent rows are not enough.
- Wine family / vertical grouping across vintages.
- Friends permissions beyond current view-only behavior.
- Optional mobile column visibility improvements.
