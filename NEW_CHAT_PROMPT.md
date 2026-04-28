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

Current mobile detail page context:
- Separate page at `GET /wine/<id>`, rendered by `templates/detail.html`. Tapping a card in `index.html` navigates here via `data-detail-url`. Do not change the mobile Cards/List layout unless I explicitly ask.
- `app.py -> wine_detail()` passes `user_locations`, `wine_types`, `bottle_sizes`, and `sticker_colors`.
- Mobile-only layout in the same template; desktop detail view is separate and should not be changed unless requested.
- Current mobile detail layout:
  - Hero: bottle image in `.mobile-bottle-wrap` with diagonal type sash (same color scheme as card). Right: type · vintage kicker with sticker dot, editable wine name, flag+region row, grape+varietal row.
  - Quick strip (3 pill badges): Status (green/amber/burgundy tint), Location (loc-color-* matching cards), Drinking Window (color-coded). Colors update live via JS on select change. Select text is center-aligned.
  - Main body (2×2 grid): Qty, Source, Sticker, Rating — then full-width Notes. Sticker is 2 rows of 3: Green/Yellow/Orange then Red/Blue/None. Rating shows as large gold number (no star).
  - Collapsed sections with rotating ▾ chevron: "Wine details" (🍷 🍇 📍 🌍 🍾) and "Purchase" (🗓️ 💳 🏷️ 💰). Label column 100px; date input left-aligned.
  - Bottom bar: ← Back, ★ Rate, ✏️ Notes, ✓ Drank.
- Naming: use `Location` (not `Storage`), `Source` (not `Retailer`).

Mobile carousel (index.html) — current state:
- Location chips use `loc-color-*` classes (Apt=blue loc-color-0, House=red loc-color-1). Active state uses standard gold highlight.
- Wine type chips (Red/White/Rose) use `.type-Red/.type-White/.type-Rose` with sash colors.

Local file note:
- Local `templates/index.html` was accidentally blank earlier and was restored from GitHub `main`; it is no longer blank.
- Because Codex sometimes updates GitHub through the Contents API, local `git status` may show files as modified even after changes are already pushed. Compare against GitHub `main` before reverting anything.

Design preferences:
- Do not touch the mobile card layout or compact/list wine row layout in `index.html` unless I explicitly ask.
- Desktop views in both `index.html` and `detail.html` should not be changed unless requested.

Important workflow notes:
- Local Git writes to `.git` sometimes fail in Codex with `index.lock` permission errors.
- If normal `git add/commit/push` fails, use the GitHub Contents API instead of fighting local `.git`.
- A GitHub auth token is available from the prior-chat `GH_CONFIG_DIR`:
  C:\Users\steve\Documents\Codex\codex-auth\gh\hosts.yml
- Do not print or expose the token.
- Use the token to call the GitHub API and update files on branch `main`.
- After GitHub `main` updates, Railway auto-deploys.
- Because of the local `.git` issue, local `git status` may still show `templates/index.html` as modified even when GitHub is already up to date. Treat GitHub `main` as the source of truth if this happens.
- If PowerShell `Invoke-RestMethod` or Git HTTPS fails, use Node/fetch with the same token; that worked in the prior chat.

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
