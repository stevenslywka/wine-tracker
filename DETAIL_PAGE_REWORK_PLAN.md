# Wine Detail Page — Mobile Rework Plan

This file captures the completed gameplan for fixing and redesigning the mobile detail page (`templates/detail.html`). Implemented and pushed in commit `eb33c35` (`Rework mobile wine detail bottles section`). Desktop view was not intentionally changed.

---

## 1. Bug Fix — Inventory Buttons Do Nothing

**Root cause:** All inventory event listener code is inside one large `if (canEditMobile) { ... }` block (line ~1661). A single uncaught JS runtime error anywhere in that block (e.g. a null reference during color picker or drinking window setup) aborts the rest of it — so Drink one, Move, Adjust, and Add here click handlers never get attached.

**Fix:** Before touching anything else, open the detail page in a desktop browser with DevTools → Console open. Identify the red error(s) on page load. The fix will likely be wrapping the failing early section in a try/catch or guarding a null reference, which will allow the rest of the listener attachment to run normally.

---

## 2. Remove the Location Quick Tile

**Current state:** The quick strip has two tiles side by side — Location (read-only) and Drinking Window (editable). They look identical visually, but Location has no input and is not interactive. This creates confusion because it looks tappable.

**Change:** Remove the Location tile from the quick strip entirely. The Inventory/Bottles section directly below already shows every location and bottle count — the Location tile is redundant. The quick strip becomes a single full-width Drinking Window tile only.

**Do not** restyle the Location tile into a "plain summary" as Codex suggested — removing it is cleaner.

---

## 3. Rename Section and Clean Up the Lot Cards

### Section header
- Rename `"Inventory"` → `"Bottles"` — shorter and more literal.

### Lot card actions — reduce visual noise
Currently every lot card shows three buttons side by side: `Drink one` / `Move` / `Adjust`. On a small screen this is cluttered.

**New layout per lot card:**
- `Drink one` stays as the primary action: full-width burgundy pill button.
- `Move` and `Adjust` move behind a secondary `"⋯"` or small `"Edit"` tap that expands them inline below the primary button. They only appear when the user taps to expand.
- This way first glance shows one clear action per card.

### Button rename
- `"Adjust"` → `"Correct count"` (or `"Fix count"`) — "Adjust" is vague.
- `"+ Add here"` → `"Add bottles"` or `"Add to location"` — current label sounds connected to "Drank total" which it is not.
- `"Drink one"` — keep as-is, it's specific and clear.

---

## 4. Move "Drank Total" Out of the Inventory Footer

**Current state:** "Drank total" appears as a footer row inside the Inventory section, directly above the "+ Add here" button. This is confusing — it looks like it belongs to the lot list.

**Change:** Remove it from the Inventory footer entirely. Move it into the Drink History section as a label at the top of that section (e.g. `"Drink History · 4 total"`).

---

## 5. Remove the Qty Read-Only Card from the Priority Grid

**Current state:** The 2×2 priority grid below Inventory has a `Qty` card that is read-only and says "Use Inventory to change counts." This is redundant noise — the user just saw the bottle counts in the Inventory/Bottles section.

**Change:** Remove the Qty card entirely. Replace it with a total bottle count in the Bottles section header itself, e.g. `"Bottles · 4 total"` as part of the `section-title` line.

---

## 6. Open Drink History by Default

**Current state:** Drink History is a `<details>` element that starts collapsed. After drinking a bottle, the user has no immediate feedback that history was recorded.

**Change:** Open the Drink History `<details>` by default (add the `open` attribute). Show the last 3 entries. If there are more than 3, show a "See all" link or button that expands the full list.

---

## Summary of Changes

| Area | Change |
|---|---|
| JS bug | Find and fix runtime error that kills all inventory button handlers |
| Location quick tile | Remove entirely from quick strip |
| Quick strip | Single full-width Drinking Window tile only |
| Section header | Rename "Inventory" → "Bottles", show total count inline |
| Lot card buttons | Drink one = primary full-width; Move + Adjust = secondary expandable |
| Button labels | "Adjust" → "Correct count"; "+ Add here" → "Add bottles" |
| Drank total | Move from Inventory footer into Drink History section header |
| Qty card | Remove from priority grid |
| Drink History | Open by default, show last 3 with expand option |

---

## Doc Update Workflow

Hard rule for Codex: do not use repeated apply_patch attempts against prose in project markdown notes.

Use scripted line/prefix replacements only. Print target lines as JSON-escaped strings if needed; replace by stable line prefix or section heading, not by full paragraphs containing emoji, smart punctuation, or mojibake. Make scripts idempotent, verify with `rg`, then push only the markdown files that changed.

---

## What Not to Change
- Desktop view (`desktop-detail-page`) — do not touch.
- Mobile card layout in `index.html` — do not touch.
- Drinking Window tile behavior — keep as-is.
- `Receive` button on not-shipped lot cards — keep as-is.
- Backend routes — no backend changes needed for this rework.
