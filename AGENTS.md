# Wine Tracker - Codex Project Guide

Personal Flask wine cellar app replacing Vivino. Multi-user. Local dev uses SQLite; production uses PostgreSQL on Railway.

- Project root: `C:\Users\steve\wine-tracker`
- Live site: `https://stevenwinecellar.up.railway.app/`
- GitHub: `https://github.com/stevenslywka/wine-tracker`
- Railway deploys automatically from GitHub `main`
- Latest production work noted in this guide: location-aware cellar default — the owner's mobile cellar auto-filters to the residence you're standing in (300 m / 200 m gates, pin chip with session-scoped dismissal, explicit filters never overridden, coordinates owner-only), pushed to GitHub `main` after local verification.

## Current Truth

Trust this section first when older notes or local Git disagree.

- Current inventory lives in `wine_inventory_lots`; do not add individual bottle tracking unless Steve explicitly changes direction.
- `wines.quantity`, `wines.status`, `wines.storage_location`, `wines.location_summary`, source/date/price fields, and `wines.total_price` are cached summaries synced by `db.sync_wine_summary()`.
- Lots use only `in_collection` and `not_shipped`. `drank` is a derived wine summary state plus drink history, not a lot status.
- Drink history lives in `wine_drink_history`; `storage_location` snapshots where the bottle was consumed from, so history remains readable/editable even if lots are merged or deleted.
- Mobile Wine Detail uses compact collapsible sections in this order: Bottles, Cellar, Drink History, Wine details, Purchase. The hero shows a stretched bottle image, editable auto-growing wine name, bottle count/location chips, and drinking window. The sticky header shows the wine name and delete lives in the hamburger menu. The Bottles section has a compact count preview, tinted two-column location stock cards with top-right manage (`...`) and a `- / count / +` stepper row, incoming `Receive Shipment`, compact Drink/Add/Manage sheets, and only shows the top-level `+ Add` button in the zero-inventory state. Drink History is its own line item with tappable rows for edit/delete in a centered dialog.
- Detail-page `+ Add` adds bottles to an existing wine through `/wine/<id>/add-lot`.
- Tap-to-add photo: the mobile hero image and "No photo" placeholder are tappable for the owner (a `<label>` wrapping a hidden `<input type="file" accept="image/*" capture="environment">`). Selection auto-uploads with an "Uploading…" overlay after best-effort client-side downscale (canvas, max 1600 px, JPEG 0.85). `POST /wine/<id>/photo` (ownership-checked) stores the file via the shared `_store_wine_image()` helper (also used by `add_wine`) and updates `wines.image_url`. Cloudinary env vars (`CLOUDINARY_*`) on Railway are required for live-site persistence; without them uploads land in `static/uploads` and are lost on redeploy.
- Location-aware cellar default: when the owner opens their own cellar on mobile (<= 767 px) with no `storage_location` in the URL, the page geolocates (same 300 m / 200 m accuracy gates) and reloads with `storage_location=<residence>&geoloc=1`. The active-filters row shows the filter as a pin chip (📍 Apt); its ✕ removes both params and sets `sessionStorage.geoLocDismissed` so the auto-filter stays off for the rest of the browser session. Explicit filters are never overridden; away from both residences or on permission denial the cellar is unfiltered. Coordinates render for the owner only; position is used client-side and discarded. Bottles still labeled `Cellar` (legacy catch-all) only appear in the unfiltered view.
- Geolocation add-bottle default: when the mobile Add bottles sheet opens without an explicit location, the page asks the browser for position and pre-selects the nearest saved location only if reported accuracy is <= 200 m AND distance <= 300 m; a manual selection is never overridden, and denied/unavailable position falls back silently. Coordinates are rendered into the page for the owner only (`user_location_coords`); the device position is used client-side and discarded, never stored or sent to the server. The `+` on a location card still prefills that card's location explicitly.
- Scan re-buy detection: both scan routes share `_scan_image_with_ai()` and the `SCAN_MODEL` constant (`claude-sonnet-4-6`, product runtime model). `POST /wine/scan-label` matches the scanned label against the user's cellar (`_match_scanned_wine`, `_looks_like_same_wine` plus vintage) and returns a `match` object (`id`, name, vintage, quantity, status, `location_summary`, `url`) or `match: null`. On match the Add Wine scan UIs show an "Already in your cellar" banner with "Add another bottle" deep-linking to `/wine/<id>?rebuy=1`, which auto-opens the mobile Add bottles sheet (add-lot flow) and strips the param from the URL; "Add as new wine" keeps the prefilled Add Wine flow. Batch scan keeps its `duplicate_warning`/`existing_id` response shape.
- Wine-family grouping: `wines.family_key` (nullable TEXT) groups the same wine across vintages and bottle sizes. Auto-assigned from `db.wine_family_key()` (normalized name via `normalize_wine_match_text`, standalone 19xx/20xx year tokens and bottle-size wording like Magnum/375ml/1.5L stripped); `db.migrate()` backfills only NULL keys and re-normalizes existing key groups whole when the algorithm evolves, so manual assignments survive. Manual link adopts the target's key (`POST /wine/<id>/family/link`); unlink sets a unique `wine:<id>` key (`POST /wine/<id>/family/unlink`). Renaming a wine re-derives the key only if it was still the auto-assigned one. Mobile detail shows a collapsible "Vintages" section under the hero (preview `X different vintages`, one row per family member including the current wine); Link/Unlink live in the hamburger menu. Cellar sort/filter is unchanged.
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
- "Vintages" collapsible section (id `vintagesSection`, standard `.mobile-details` styling) sits between the hero and the Bottles section when the wine's family has more than one member. Collapsed preview reads `X different vintages` (distinct vintage years). Expanded rows cover every family member including the current wine: vintage year plus size label when not 750ml (e.g. `2007 Magnum`), then availability (`location_summary`), `N incoming`, and/or `Drank ×N`; the current wine's row shows a `Viewing` tag, other rows link to that wine preserving the `back` param. `Link vintages` (id `linkVintagesAction`) in the hamburger menu opens a searchable dialog (`familyLinkModal`) of the user's other wines; `Unlink this vintage` (id `unlinkVintageAction`) appears only when the family has other members and asks for confirmation.
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

`id, wine_name, vintage, varietal, region, origin, wine_type, size_ml, unit_price, retail_price, total_price, quantity, retailer, order_date, status, storage_location, location_summary, color_code, drinking_window, drinking_window_source, notes, image_url, family_key, user_id`

`family_key` is a nullable text grouping key for the same wine across vintages; `wine:<id>` marks a manually unlinked wine.

Status values: `in_collection`, `not_shipped`, `drank`.

### `wine_inventory_lots`

`id, wine_id, quantity, status, storage_location, retailer, order_date, unit_price, notes, created_at, updated_at`

Lot status values: `in_collection`, `not_shipped`.

### `wine_drink_history`

`id, wine_id, lot_id, quantity, storage_location, drank_date, rating, notes, created_at`

`lot_id` can become null if the source lot is later deleted.

### `user_locations`

`id, user_id, name, sort_order, latitude, longitude`

Each user has their own saved locations. `latitude`/`longitude` are nullable address-level coordinates used only client-side to pre-select the nearest location when adding bottles; steven's Apt/House are seeded by `db.migrate()` (NULL-only, so manual entries survive). Locations without coordinates never match.

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
- `POST /wine/<id>/family/link` - link this wine into another wine's vintage family (form `target_wine_id`)
- `POST /wine/<id>/family/unlink` - remove this wine from its vintage family
- `POST /wine/<id>/photo` - upload/replace the wine photo (multipart `image`), updates `wines.image_url`

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

## Current Build - Cellar Usability (in progress)

Build these three sections in order, one at a time. Fully finish a section (code
plus `scripts/verify_detail.py` passing) then stop and report before starting the
next; do not run ahead across sections. Follow "Inventory Rules", "Schema Changes",
and "Do Not Touch Unless Asked" above. Do not commit, push, or deploy unless
explicitly asked. Overriding design rule from Steve: keep the mobile UI very
clean, uncluttered, and easy to figure out — prefer fewer, clearer controls.

1. DONE (2026-07-05, pushed to production). Location-aware cellar default. When the owner opens their own cellar on
   mobile with no explicit location filter in the URL, geolocate (same client
   pattern and gates as the detail-page add-bottle default: accuracy <= 200 m,
   distance <= 300 m, silent fallback, position used then discarded, coordinates
   rendered for the owner only) and default the view to that residence's
   bottles, with a clearly visible, dismissible chip showing the active
   location filter. Away from both residences, or on permission denied, show
   the normal unfiltered cellar. Never override an explicit user-chosen filter.
   Do not restructure the existing cards/list/desktop layouts.

2. Home-screen app feel (PWA). Add a web app manifest (name, icons 192/512,
   theme/background colors, `display: standalone`, start URL `/`), an
   apple-touch-icon plus iOS meta tags, and link them from the main templates
   (login, index, detail, analytics). No service worker / offline support in
   this pass. Verify "Add to Home Screen" produces a full-screen app with icon
   on iOS Safari.

3. Packing list / bulk move between residences. Mobile flow for moving 6-12
   bottles at once (today's per-wine Move flow is the pain point): choose
   source and destination locations, build the list by tapping wines from
   source-location inventory AND optionally by photographing the packed
   bottles - reuse `scan-batch-labels` plus `_match_scanned_wine` to
   pre-select matched wines (unmatched scan results are simply ignored, with
   a count shown). Per-wine quantity steppers, single Confirm. Backend: new
   ownership-checked bulk endpoint (e.g. `POST /wines/move-bulk` with JSON
   `{from_location, to_location, items: [{wine_id, quantity}]}`) that applies
   the existing location-level move semantics per wine in one transaction and
   runs `sync_wine_summary` for each affected wine; reject same-location moves
   frontend and backend; partial-quantity moves allowed.

## Completed Build - Mobile Enhancements (all four sections pushed 2026-07-04/05)

Kept for reference; current behavior is summarized in "Current Truth" above.

1. DONE (2026-07-04, pushed to production). Wine-family grouping across vintages (do first; hardest). Group the same wine
   across vintages: add a nullable grouping key to `wines` via `db.migrate()`
   (Postgres and SQLite), auto-assign by normalized name ignoring vintage (reuse
   `_normalize_wine_match_text`), allow manual link/unlink, and show an "Other
   vintages" strip on mobile detail linking to siblings. Confirm before changing
   cellar sort/filter; do not change desktop or `index.html` card/list layout
   beyond what grouping requires.

2. DONE (2026-07-04, pushed to production). Scan -> identify -> re-buy. Merge `scan-label` and `scan-batch-labels` into one
   helper with a single model constant (keep the current runtime model - this is
   product runtime, not the build model). Add cellar matching to the single-scan
   path (reuse `_looks_like_same_wine` plus vintage). On match, deep-link to
   `/wine/<id>` with an "Add another bottle?" action calling `/wine/<id>/add-lot`;
   on no match, prefill Add Wine.

3. DONE (2026-07-04, pushed to production). Geolocation location default. Add nullable `latitude` and `longitude` to
   `user_locations` via `db.migrate()` (Postgres and SQLite), seeded with the
   coordinates below. At add-bottle time, request device location and pre-select
   the nearest saved location only when within 300 m AND the reading's reported
   accuracy is good enough; the user can override; on permission denied or missing
   coordinates, fall back silently to the current default. Position is used to
   choose and then discarded, never stored. Design columns and logic to support a
   later "Set location here" button and per-location manual entry for other users.

   Seed coordinates (address-level geocodes):
   - Apt   (170 Amsterdam Ave, New York, NY 10023):     lat 40.7760223, lon -73.9839230
   - House (109 Boice Mill Road, Kerhonkson, NY 12446): lat 41.7911949, lon -74.2810933

4. DONE (2026-07-04, pushed to production; Cloudinary confirmed configured on the Railway web service). Tap-to-add photo and photo polish. Factor the image-upload block out of
   `add_wine` into a shared helper; add `POST /wine/<id>/photo` (ownership-checked)
   that updates `wines.image_url`. Make the "No photo" placeholder and the existing
   image tappable (a `<label>` wrapping a hidden
   `<input type="file" accept="image/*" capture="environment">`), auto-submit with
   an uploading state, and downscale the image client-side before upload. Note:
   live-site photo persistence requires Cloudinary env vars (`CLOUDINARY_*`) on
   Railway; without them uploads save to `static/uploads` and are lost on redeploy.
   Confirm Cloudinary is configured before relying on live uploads.

## Recommendation System (current, for future "Tonight picker" work)

`POST /wine/recommend` already exists: takes a free-text mood/occasion prompt
plus optional `storage_location`, `wine_type`, and `stickers` filters, loads up
to 100 matching in-collection wines, and has an AI sommelier (Haiku model)
return 1-3 picks as JSON with one-line reasons. Color stickers are the
price-band/occasion axis and their meanings are documented in the route's
system prompt: Green = everyday, Yellow = solid/reliable, Orange =
quality/higher-end for guests, Red = very special/expensive, Blue =
sentimental (orange/red quality with personal meaning), no sticker = unknown.
A future mobile "What should we drink tonight?" UI should wrap this route
(chips for mood/body and occasion, geolocation-scoped location filter) rather
than build new recommendation machinery. Deferred until Steve asks.

## Future Work

Deferred - not part of the current build above:

- Mobile "What should we drink tonight?" picker wrapping `/wine/recommend` (see above).
- Duplicate-wine merge tool (combine lots + drink history; duplicates are now visible in the Vintages section).
- Expanded/all drink history view if recent rows are not enough.
- Friends permissions beyond current view-only behavior.
- Optional mobile column visibility improvements.
