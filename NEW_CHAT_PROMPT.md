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
  - 6506d12, `Polish mobile cellar UI`
  - 8f80a27, `Refine mobile carousel and filter controls`
  - 7556545, `Remove duplicate mobile carousel groups`
  - deaa4e9, `Add other origin mobile filter`
  - 5c091ad, `Support mobile wine detail editing`
  - 79384d1, `Redesign mobile wine detail page`
  - 695f980, `Refine mobile wine detail profile`
  - 8d004bb, `Compact mobile wine detail layout`
  - 0c8103c, `Polish mobile wine detail fields`

Current mobile detail page context:
- We are now iterating on the separate wine detail page only: `GET /wine/<id>` rendered by `templates/detail.html`.
- Mobile card/list items in `templates/index.html` navigate to this page through `data-detail-url`. Do not change the mobile Cards/List layout unless I explicitly ask.
- `app.py -> wine_detail()` now passes detail-page option data: `user_locations`, `wine_types`, `bottle_sizes`, and `sticker_colors`.
- The mobile detail page has a mobile-only layout while desktop detail remains separate in the same template.
- Current mobile detail layout:
  - Hero with bottle image, type/vintage, current sticker dot, editable wine name, inferred flag, region/origin, grape emoji, and varietal.
  - One compact editable top row: Status, Location, Drinking Window.
  - Drinking Window uses the same color logic as the main cellar view: hold, ready/prime, drink soon, overdue, and drank.
  - Main visible body combines Cellar + Rating/Notes: Qty, Source, Sticker, Rating in a compact four-cell grid, with Notes below.
  - Lower priority info is collapsed under `Wine details` and `Purchase`.
  - Bottom action bar: Back, Rate, Notes, Drank. Rate/Notes jump to and focus those fields.
- Naming preference: use `Location`, not `Storage`; use `Source`, not `Retailer`.
- Current design-feedback goal: critique this mobile detail page and suggest how to make it feel more like the redesigned mobile Cards layout: visual, dense, easy to scan, creative with icons/buttons/graphics, and not like a clunky form.
- Unless I ask for implementation, give design feedback first. If implementing, touch only `templates/detail.html` unless route data in `app.py` is truly required.

Local file note:
- Local `templates/index.html` was accidentally blank earlier and was restored from GitHub `main`; it is no longer blank.
- Because Codex sometimes updates GitHub through the Contents API, local `git status` may show files as modified even after changes are already pushed. Compare against GitHub `main` before reverting anything.

Current design preference:
- Do not touch the mobile card layout or compact/list wine row layout unless I explicitly ask. It is okay to work on the mobile header, top controls, filters, and carousel when requested.
- Current active focus is the separate mobile wine detail page (`templates/detail.html`), not the mobile card/list layout.

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
