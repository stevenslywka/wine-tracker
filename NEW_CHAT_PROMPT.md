# Wine Tracker New Chat Prompt

Copy/paste this at the start of a new Codex chat:

```text
I am working on my Flask wine cellar app in:
C:\Users\steve\wine-tracker

Please use that folder as the project root. Before changing anything, inspect the current files and check `git status --short`. Be careful not to overwrite existing local changes, especially `templates/index.html`.

Project context:
- Personal multi-user wine cellar tracker replacing Vivino.
- Live site: https://stevenwinecellar.up.railway.app/
- GitHub repo: https://github.com/stevenslywka/wine-tracker
- Railway deploys automatically from GitHub `main`.
- Backend: Flask in `app.py`.
- Database: SQLite locally (`wines.db`), PostgreSQL on Railway.
- DB helper/migrations: `db.py`; schema changes must go through `migrate()`.
- Main cellar UI: `templates/index.html` with Jinja, Bootstrap 5, inline CSS, and vanilla JS.
- Other useful templates: `home.html`, `detail.html`, `analytics.html`, `settings_locations.html`.
- Image storage uses Cloudinary.
- AI features use Anthropic Claude API for receipt scan, label scan, recommendations, and drinking windows.

Inventory-lots work now live:
- The app now uses `wine_inventory_lots` for current inventory and `wine_drink_history` for consumption history.
- `wines.quantity/status/storage_location/location_summary` are cached summaries synced from lots by `db.sync_wine_summary()`.
- Lots are not individual bottles. A lot is current inventory for one wine at one location/status/source/date/price.
- Lot statuses are only `in_collection` and `not_shipped`; `drank` is a derived wine summary state and drink history record.
- Existing/current imported wines create lots through migration, manual Add Wine, receipt/bulk add, batch scan add, and email parsing.
- Mobile detail Inventory section uses per-location lot cards. Each in_collection lot card shows: location name, bottle count, `Drink one` button (opens modal for optional rating/notes before confirming), `Move` button (qty stepper + destination selector), and `Adjust` (inline −/count/+/Done; last-bottle removal uses a custom confirm modal).
- Not-shipped lots appear as amber cards with a `Receive` button (location selector modal, converts lot to in_collection).
- `Drink one` writes `wine_drink_history` with optional rating and notes; always requires a specific lot_id from the per-lot button.
- `Adjust` controls are inventory corrections only and do not write drink history.
- The old mobile Qty card is read-only and points users to Inventory for count changes.
- Inventory routes: `POST /wine/<id>/drink-one`, `POST /wine/<id>/lot/<lot_id>/adjust`, `POST /wine/<id>/lot/add-location`, `POST /wine/<id>/add-lot`, `POST /wine/<id>/lot/<lot_id>/move`, `POST /wine/<id>/lot/<lot_id>/receive`.
- Re-buy detection / "Add bottles to existing wine" UI is not implemented yet. `/wine/<id>/add-lot` exists for that future flow.
- Wine family/vertical grouping is not implemented yet.
- Latest inventory commits on GitHub main include `233b7be`, `2fe0b17`, `142a59e`, and `76c1de4`.

Recent UI work already pushed:
- Mobile Cards view redesigned.
- Compact/List view redesigned.
- Dynamic compact card heights fixed.
- Wine type sash adjusted.
- Available/drank/not-shipped icons updated.
- Storage/status mobile behavior improved.
- Mobile home/cellar header now centers `🍷 Steven's wine cellar`; hamburger opens Menu and the search icon reveals search.
- Mobile Filter and sort sheet is live, with Cards/List toggle on the same row as Filter and sort and the wine counter below.
- Mobile quick carousel is live with one sequence only: Location, Type, Origin, Sticker.
- Origin carousel options are USA, France, Italy, and Earth emoji `Other`. `Other` means anything outside USA/France/Italy, while USA includes common stored US origins like California, Oregon, Washington, and New York.
- "Add" is now "Add Wine"; "all in collection" is now "Available".
- Latest relevant GitHub commits:
  - c8b293e, `Polish mobile wine detail page UI`
  - 512e758, `Refine mobile wine detail bubbles and sticker layout`
  - d85d691, `Center select text in Status and Location quick tiles`
  - 38f5dfc, `Fix Order Date label wrapping and date input alignment`
  - 89d778f, `Color carousel chips by location and wine type`

Current mobile UI state as of Apr 28, 2026 (supersedes older mobile bullets below if they conflict):
- Main Cellar mobile carousel order is Location, Type, Origin, Sticker, Status. Status is last, after Sticker.
- Status carousel chips are Available, Not Shipped, Drank. Available is green, Not Shipped is beige, Drank is dark red/burgundy. Active carousel chips keep their normal color; active state only thickens the border/font. Do not restore the old red active background.
- Origin carousel chips are USA, France, Italy, and Earth emoji `Other`. `Other` filters origins outside USA/France/Italy; USA also includes common stored US origins like California, Oregon, Washington, and New York.
- Mobile search has an X clear button and uses 16px font to avoid iOS zoom sticking after focus.
- The old tiny bottom-left result counter is removed. When no filters/search are active, the mobile summary says `Viewing - All Wines`; filtered states show the active view and counts.
- Mobile Select mode has bulk Edit: tap `Select`, tap cards or `All`, tap `Edit`, then use inline carousel-style chips/fields for Location, Status, Sticker, Source, or Order Date. These actions post selected IDs to `/wines/bulk-edit`. Location marks selected wines Available and assigns the chosen location. Do not treat this as inventory-history or quantity-drinking behavior.
- Mobile Batch Scan is live in Add Wine: one multi-bottle photo, client-side compression, `/wine/scan-batch-labels` extraction, editable review cards, and `/wine/add-batch-scan` insert. It uses `origin` (not `location`), leaves `image_url` null for group photos, flags likely duplicates, and does not reuse receipt `/wine/add-bulk`.
- Empty mobile results say `No wines yet - tap Add Wine to get started` in white.
- Wine cards without images show a dark `No photo` bottle silhouette placeholder.
- Bottom mobile cellar button says `Need a Wine Rec?`.
- Mobile detail page has a sticky wine-cellar header matching the Main Cellar page: hamburger menu on the left, centered cellar title, and a square trash icon on the right. The trash icon opens the delete confirmation.
- Detail hero shows the editable wine name first, then vintage/sticker. The type word and type sash were removed from the detail hero.
- Detail page wines without images use the same dark `No photo` silhouette.
- Detail page Inventory section uses per-location lot cards with `Drink one`, `Move`, and `Adjust` actions per lot. Not-shipped lots show a `Receive` button. The old Qty card in the priority grid is read-only. Drinking Window placeholder gives `e.g. 2024-2030` style guidance; expected format remains `YYYY-YYYY`.
- Detail notes textarea starts short and auto-grows.
- Detail bottom action bar is Back to Cellar, Previous Wine, Next Wine. Delete is only in the sticky header. Back uses `back_url`, not `history.back()`.
- Previous/Next on detail preserve the filtered Main Cellar list: mobile card clicks pass `list=<filtered ids>` and `back=<current cellar URL>` query params to `GET /wine/<id>`.
- `app.py -> wine_detail()` now passes `cellar_username`, `cellar_display_name`, `back_url`, `prev_wine_url`, and `next_wine_url` in addition to the detail picker lists.
- Delete confirmation text is `Are you sure? This cannot be undone.` and posts to `/wine/<id>/delete` only after confirmation.
- Recent relevant commits include `bd33cd2`, `e47502b`, `3317196`, `9c64bb2`, `5ccb08c`, `cfdf307`, `e50b04b`, and `d50c8d8`.

Current mobile detail page context:
- Separate page at `GET /wine/<id>`, rendered by `templates/detail.html`. Tapping a card in `index.html` navigates here via `data-detail-url`. Do not change the mobile Cards/List layout unless I explicitly ask.
- `app.py -> wine_detail()` passes `user_locations`, `wine_types`, `bottle_sizes`, `sticker_colors`, `inventory_lots`, `drink_history`, `drank_total`, and `not_shipped_count`.
- Mobile-only layout in the same template; desktop detail view is separate and should not be changed unless requested.
- Current mobile detail layout:
  - Hero: bottle image in `.mobile-bottle-wrap` with diagonal type sash (same color scheme as card). Right: type · vintage kicker with sticker dot, editable wine name, flag+region row, grape+varietal row.
  - Quick strip (2 tiles): Location (read-only, shows `wine.location_summary` e.g. "House 4 · Apt 2"; `loc-color-*` based on primary location), Drinking Window (editable, color-coded). Status tile removed.
  - Inventory section: per-location lot cards. Each card: location name, bottle count, `Drink one` (rating/notes modal), `Move` (qty+destination modal), `Adjust` (inline stepper, last-bottle uses custom confirm modal). Not-shipped cards show `Receive`. Footer: Drank total + `+ Add here`.
  - Main body (2×2 grid): Qty is read-only and points to Inventory for count changes. Source, Sticker, Rating follow, then full-width Notes. Sticker is 2 rows of 3: Green/Yellow/Orange then Red/Blue/None. Rating shows as large gold number (no star).
  - Collapsed sections with rotating ▾ chevron: "Wine details" (🍷 🍇 📍 🌍 🍾) and "Purchase" (🗓️ 💳 🏷️ 💰). Label column 100px; date input left-aligned.
  - Bottom bar: ← Back, ★ Rate, ✏️ Notes, ✓ Drank.
- Naming: use `Location` (not `Storage`), `Source` (not `Retailer`).

Mobile carousel (index.html) — current state:
- Location chips use `loc-color-*` classes (Apt=blue loc-color-0, House=red loc-color-1). Active state uses standard gold highlight.
- Wine type chips (Red/White/Rose) use `.type-Red/.type-White/.type-Rose` with sash colors.

Local file note:
- Local `templates/index.html` was accidentally blank earlier and was restored from GitHub `main`; it is no longer blank.
- Because Codex sometimes updates GitHub through the Contents API, local `git status` may show files as modified even after changes are already pushed. Compare against GitHub `main` before reverting anything.
- As of Apr 28, 2026, local `templates/index.html`, `templates/detail.html`, and `NEW_CHAT_PROMPT.md` matched GitHub `main` exactly by SHA. `CLAUDE.md` and `app.py` had the same line-by-line content as GitHub but differed by line endings.
- A local virtual environment exists at `.venv`; Steve created it from normal PowerShell and installed `requirements.txt`. Use `.\.venv\Scripts\python.exe app.py` to run the Flask dev server at `http://127.0.0.1:5000`. `.venv/` and `.pip-tmp/` are ignored.

Design preferences:
- Do not touch the mobile card layout or compact/list wine row layout in `index.html` unless I explicitly ask.
- Desktop views in both `index.html` and `detail.html` should not be changed unless requested.

Important workflow notes:
- Local Git writes to `.git` sometimes fail in Codex with `index.lock` or `FETCH_HEAD` permission errors.
- If normal `git add/commit/push` fails, use the GitHub Contents API instead of fighting local `.git`.
- A GitHub auth token is available from the prior-chat `GH_CONFIG_DIR`:
  C:\Users\steve\Documents\Codex\codex-auth\gh\hosts.yml
- Do not print or expose the token.
- Use the token to call the GitHub API and update files on branch `main`.
- After GitHub `main` updates, Railway auto-deploys.
- Because of the local `.git` issue, local `git status` or `ahead/behind` may be misleading when `origin/main` is stale. Treat GitHub `main` as the source of truth if this happens.
- If PowerShell `Invoke-RestMethod` or Git HTTPS fails, use Node/fetch with the same token; that worked in the prior chat.

Local dev command:
```powershell
cd C:\Users\steve\wine-tracker
.\.venv\Scripts\python.exe app.py
```

If `.venv` ever needs to be recreated, Steve can run from normal Windows PowerShell:
```powershell
cd C:\Users\steve\wine-tracker
Remove-Item -Recurse -Force .venv,.pip-tmp -ErrorAction SilentlyContinue
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

When pushing with the GitHub API:
1. Read the current file SHA from:
   `GET https://api.github.com/repos/stevenslywka/wine-tracker/contents/<path>?ref=main`
2. Base64 encode the updated file.
3. Update with:
   `PUT https://api.github.com/repos/stevenslywka/wine-tracker/contents/<path>`
4. Body should include `message`, `content`, `sha`, and `branch: "main"`.
5. Verify with:
   `GET https://api.github.com/repos/stevenslywka/wine-tracker/commits/main`

Please explain steps in plain language because I am nontechnical. For UI work, verify mobile and desktop behavior carefully. If you need to delete local files or transmit/push data, ask for confirmation first.
```
