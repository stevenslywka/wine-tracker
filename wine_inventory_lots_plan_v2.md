# Wine Tracker Inventory Lots Plan — v2

## Implementation Status

This plan has been partially implemented on GitHub `main`.

Live now:
- Stage 1 data foundation: `wine_inventory_lots`, `wine_drink_history`, `wines.location_summary`, migration, summary sync, and lot creation through add/import flows.
- Stage 2 drink flow: `Drank one` decrements one available lot, asks for a location when needed, records drink history, and defaults the drink date to today.
- Stage 3 mobile detail inventory: per-location lots, `[-]/[+]` inventory corrections, Add location with quantity, recent drink history, and read-only old Qty card.
- Backend route for future re-buy work: `POST /wine/<id>/add-lot`.

Still future:
- Stage 4 re-buy detection and "Add bottles to existing wine" UI.
- Stage 5 shipment receiving flow.
- Wine family / vertical grouping for same producer/line across different vintages.
- Expanded drink history view beyond the recent rows.

Keep the rest of this document as architectural background and roadmap context.

## Purpose

This document is the revised implementation plan for evolving the Flask wine cellar app from a simple "wine rows with quantity" model into a lot-aware inventory model.

The goal is not to track individual physical bottles. The goal is to track groups of bottles called lots, so the app can handle:

- Buying the same wine again
- Having multiple bottles of the same wine
- Drinking one bottle while others remain available
- Knowing which bottles are at which location (House, Apt, etc.)
- Filtering the cellar by location to see what is available there
- Preserving a simple drink history

This should be implemented carefully and in stages, without disrupting the current mobile UI.

---

## Current State

Today the app treats one row in `wines` as both the wine identity and the inventory state.

Current fields on `wines` include:

- `wine_name`, `vintage`, `varietal`, `region`, `origin`, `wine_type`, `size_ml`
- `quantity`, `status`, `storage_location`
- `retailer`, `order_date`, `unit_price`, `total_price`
- `notes`, `my_rating`, `color_code`, `drinking_window`, `image_url`
- `user_id`

This works for simple cases but breaks down when a wine has more than one bottle, or when bottles of the same wine are in different locations.

Example problem: if a wine has `quantity = 3` and the user marks it `drank`, the whole wine becomes drank. There is no clean way to express "I drank one bottle and still have two."

---

## Recommended Conceptual Model

Use two concepts as the core of version 1.

### 1. Wine Identity

The existing `wines` table continues to represent a specific wine identity.

A "wine" means:

> producer / wine name / line + vintage + bottle size

Different vintages should be treated as different wine rows. Same wine name but different vintage = different wine rows. Grouping vintages under a "family" or "vertical" concept is explicitly out of scope for version 1.

Examples:

- `Ridge Geyserville 2021` is one wine
- `Ridge Geyserville 2022` is a different wine

### 2. Inventory Lots

Lots become the source of truth for current inventory.

A lot means:

> A group of bottles of the same wine, at the same location, with the same purchase metadata.

Examples:

- 4 bottles of Wine A at House, bought from K&L
- 2 bottles of Wine A at Apt, from the same purchase
- 3 bottles of Wine B, not shipped yet

**Important: lots represent current state only.** They are not event logs. When bottles are drunk, the lot quantity decrements. When a lot reaches quantity 0, it is deleted (or soft-deleted). The `wine_drink_history` table is the historical record.

**Location is just an attribute of a lot.** There is no "move" flow and no move history. If a wine has bottles in multiple locations, it simply has multiple lot rows — one per location. To update how many bottles are at a given location, the user directly edits lot quantities. This is CRUD, not a workflow.

---

## Proposed New Table: `wine_inventory_lots`

```sql
id             INTEGER PRIMARY KEY
wine_id        INTEGER NOT NULL REFERENCES wines(id) ON DELETE CASCADE
quantity       INTEGER NOT NULL DEFAULT 0
status         TEXT NOT NULL DEFAULT 'in_collection'
storage_location TEXT
retailer       TEXT
order_date     TEXT
unit_price     REAL
notes          TEXT
created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

**Status values for lots:**

```
in_collection
not_shipped
```

That is all. There is no `drank` status on lots. Lots represent current inventory. When a lot's quantity reaches 0, delete it (or soft-delete with a `deleted_at` column). The drink history table records what was consumed.

**Notes on the schema:**

- No `total_price` field. Total price is a derived value (`quantity * unit_price`) and should be computed in queries or Python, never stored. Storing it creates a consistency risk.
- No `user_id` directly on lots. User scoping is enforced by always joining through `wines`, which has `user_id`. Every query against `wine_inventory_lots` must join to `wines` and filter by `wines.user_id`. This must be enforced consistently across all routes.
- `ON DELETE CASCADE` means deleting a wine automatically deletes all its lots.

---

## Proposed New Table: `wine_drink_history`

```sql
id          INTEGER PRIMARY KEY
wine_id     INTEGER NOT NULL REFERENCES wines(id) ON DELETE CASCADE
lot_id      INTEGER REFERENCES wine_inventory_lots(id) ON DELETE SET NULL
quantity    INTEGER NOT NULL DEFAULT 1
drank_date  TEXT
rating      REAL
notes       TEXT
created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

Purpose:

- Record that the user drank one or more bottles, with optional date, rating, and notes.
- `lot_id` is nullable because the lot may be deleted later; the drink record should survive.
- `ON DELETE CASCADE` on `wine_id` means deleting a wine clears its drink history too.

For version 1, `wines.notes` and `wines.my_rating` remain the main visible notes/rating fields. Drink history is displayed simply and can be expanded later.

---

## Keep Existing `wines` Fields As Cached Summaries

To avoid rewriting the whole app at once, keep these fields on `wines` as synced summary values:

- `quantity` — sum of available bottles
- `status` — derived from lots
- `storage_location` — primary location (see rules below)
- `location_summary` — new field, human-readable breakdown e.g. `"House 4 · Apt 2"`
- `retailer`, `order_date`, `unit_price`, `total_price` — most recent available lot's values

The existing mobile cards, filters, and detail page can continue reading from `wines` while the backend gradually becomes lot-aware.

### `wines.location_summary` — New Field

Add a `location_summary TEXT` column to `wines`. This replaces any use of the string `'Multiple'` as a location value. Examples:

- `"House 6"` — all bottles in one location
- `"House 4 · Apt 2"` — split across two locations
- `""` or `NULL` — not shipped or no available bottles

**Never store `'Multiple'` in `wines.storage_location`.** That is a magic string that will leak into carousel filters, color classes, and UI logic. Instead, `wines.storage_location` holds the primary location (the one with the most available bottles), and `wines.location_summary` holds the full display string.

---

## Wine Summary Sync Rules

Whenever lots change for a wine, call a helper function `_sync_wine_summary(conn, wine_id)` that resyncs the parent `wines` row. This function must run **in the same database transaction** as the lot change. Do not run it in a separate transaction or after committing — if the sync fails, the lot change should roll back too.

The sync function should be a single SQL UPDATE (not a Python loop).

### Quantity

```
wines.quantity = SUM(lot.quantity WHERE lot.status = 'in_collection')
```

Available bottles only. Not-shipped bottles are not included in `wines.quantity`.

### Status

```
if any lot has status = 'in_collection' and quantity > 0:
    wines.status = 'in_collection'
elif any lot has status = 'not_shipped' and quantity > 0:
    wines.status = 'not_shipped'
else:
    wines.status = 'drank'
```

Note: `wines.status = 'drank'` means no lots remain with inventory. The status on `wines` can still be `drank` even though lots only have `in_collection` and `not_shipped` — it is a derived summary value.

### Storage Location and Location Summary

```python
# Group in_collection lots by location, sorted by quantity descending
lots = SELECT storage_location, SUM(quantity) as qty
       FROM wine_inventory_lots
       WHERE wine_id = ? AND status = 'in_collection' AND quantity > 0
       GROUP BY storage_location
       ORDER BY qty DESC

if len(lots) == 0:
    wines.storage_location = NULL
    wines.location_summary = NULL
elif len(lots) == 1:
    wines.storage_location = lots[0].storage_location
    wines.location_summary = f"{lots[0].storage_location} {lots[0].qty}"
else:
    wines.storage_location = lots[0].storage_location  # primary = largest
    wines.location_summary = " · ".join(f"{l.storage_location} {l.qty}" for l in lots)
```

### Price and Source

Set `wines.retailer`, `wines.order_date`, `wines.unit_price` from the most recent available lot (by `order_date` or `created_at`). Update `wines.total_price = wines.unit_price * wines.quantity`.

---

## Migration Strategy

The migration runs through `db.py → migrate()` as always. It must be idempotent, support both SQLite locally and PostgreSQL on Railway, and not duplicate data if it runs multiple times.

### Steps

1. Create `wine_inventory_lots` table if it does not exist.
2. Create `wine_drink_history` table if it does not exist.
3. Add `location_summary TEXT` column to `wines` if it does not exist (using the standard dual-DB pattern from CLAUDE.md).
4. For every wine that has no lots yet, create one initial lot:

```python
INSERT INTO wine_inventory_lots (wine_id, quantity, status, storage_location,
    retailer, order_date, unit_price, notes)
SELECT id, quantity, status, storage_location,
    retailer, order_date, unit_price, NULL
FROM wines w
WHERE NOT EXISTS (
    SELECT 1 FROM wine_inventory_lots l WHERE l.wine_id = w.id
)
```

5. Run `_sync_wine_summary` for every wine (to populate `location_summary`).

The `NOT EXISTS` check is the idempotency guard — no additional migration state table needed.

---

## Lot Consolidation Rule

When creating or updating a lot that results from a split or addition to an existing location, always check for an existing lot with the same `(wine_id, status, storage_location, retailer, order_date)` before inserting. If one exists, increment its quantity instead of creating a new row.

This prevents a wine from accumulating many tiny lots from repeated small edits.

---

## Core User Flows

### Default Mobile Cellar

The default mobile cellar emphasizes available wines. Location filtering remains first-class.

When filtering to a location (e.g. House), show wines that have at least one `in_collection` lot at that location with `quantity > 0`.

The query to find wine IDs for a location filter:

```sql
SELECT DISTINCT wine_id
FROM wine_inventory_lots
WHERE storage_location = 'House'
  AND status = 'in_collection'
  AND quantity > 0
```

Cards display `location_summary` from `wines` (e.g. `House 4 · Apt 2`). When filtered to a location, optionally show only that location's count.

### Drink One

This is the most important inventory-aware action.

If the wine has available bottles in only one location:

1. User taps `Drank one`.
2. App finds the single `in_collection` lot for this wine.
3. App decrements that lot's quantity by 1.
4. If lot quantity reaches 0, delete the lot.
5. App inserts a `wine_drink_history` row.
6. App calls `_sync_wine_summary(conn, wine_id)` in the same transaction.

If the wine has available bottles in multiple locations:

1. User taps `Drank one`.
2. App shows a simple location picker with counts: `House (4)`, `Apt (2)`.
3. Default selection is the location with the most bottles.
4. User confirms.
5. App decrements the selected location's lot.
6. If lot quantity reaches 0, delete the lot.
7. App inserts `wine_drink_history`.
8. App calls `_sync_wine_summary`.

Rating and notes are optional. Keep the default flow fast — one or two taps for the common case.

### Location-Aware Inventory on Detail Page

Add a compact inventory section to the mobile detail page:

```
Inventory
  House   4   [−] [+]
  Apt     2   [−] [+]
  Not shipped  1
  Drank   3 total

  [Drank one]  [Add more]
```

`[−]` and `[+]` directly decrement/increment the lot quantity for that location. Decrement to 0 deletes the lot. Each tap calls the sync function.

There is no separate "Move" flow. If the user wants to record that 2 bottles moved from House to Apt, they tap `[−]` twice on House and `[+]` twice on Apt. The app handles lot consolidation automatically (creates the Apt lot if it does not exist, increments it if it does).

### Add Same Wine Again

Add Wine should detect likely matches.

**Strong match** (same normalized wine name + same vintage + same size):

```
Looks familiar
You already have/had this wine.

Available: 4 at House · 2 at Apt
Drank: 3 total
Last rating: 4.3

[Add bottles to existing wine]
[Add as separate wine]
[Cancel]
```

Default: `Add bottles to existing wine`. This creates a new lot under the existing wine.

**Same name but different vintage:**

```
You have other vintages of this wine.
[vintage list]
```

Default: `Add as new vintage` (creates a new wine row, not a lot under the existing wine).

**Name normalization for matching:** lowercase, strip punctuation, collapse whitespace. Do not use fuzzy/trigram scoring in version 1 — just show the candidate and let the user confirm.

Do not auto-merge without user confirmation.

### Receiving a Shipment (Later)

Not in version 1, but the lot model supports it cleanly. Future flow: user taps `Receive shipment`, sees their `not_shipped` lots, selects one, chooses a location, and the lot status changes to `in_collection` at that location.

---

## Receipt Scan and Batch Scan Integration

The existing import flows (`fetch_emails.py`, `/wine/add-bulk`, `/wine/add-batch-scan`) create `wines` rows directly. In the lot-aware model, these flows must also create an initial lot for each wine they insert.

When any of these flows inserts a new wine row, immediately after the insert also run:

```python
INSERT INTO wine_inventory_lots (wine_id, quantity, status, storage_location,
    retailer, order_date, unit_price)
VALUES (new_wine_id, quantity, status, storage_location, retailer, order_date, unit_price)
```

Then call `_sync_wine_summary`. This must be part of Stage 1, not a later stage — otherwise imported wines will exist without lots.

---

## Mobile UI Changes Summary

### Card Display

For version 1, minimal card changes. Add `location_summary` display below the quantity badge:

```
Qty 6
House 4 · Apt 2
```

When filtered to a location, show only that location's count.

### Detail Page

Add the inventory section described above under "Location-Aware Inventory on Detail Page."

Add drink history section (collapsed by default):

```
Drink history
Apr 29, 2026 · Drank 1 · ★ 4.3
Mar 12, 2026 · Drank 1
```

### Do Not Change

- Mobile card layout (`index.html`) — do not change unless explicitly asked.
- Desktop views in `index.html` and `detail.html` — do not change unless explicitly asked.
- Location carousel filter behavior — it now queries via lots but the chip UI stays the same.

---

## Suggested Implementation Stages

### Stage 1: Data Foundation

- Add `wine_inventory_lots` table.
- Add `wine_drink_history` table.
- Add `location_summary TEXT` column to `wines`.
- Migrate all existing wines into one initial lot each (idempotent).
- Write `_sync_wine_summary(conn, wine_id)` helper.
- Run sync for all wines after migration.
- Update all import flows (`add-bulk`, `add-batch-scan`, receipt scan) to also create a lot on insert.
- Do not change the visible UI yet.

### Stage 2: Quantity-Aware Drink Flow

- Change the `Drank` action on mobile detail to decrement one available bottle.
- If the wine has lots at multiple locations, show a location picker (default: largest lot).
- Record `wine_drink_history` row.
- Call `_sync_wine_summary` in the same transaction.
- Keep all existing status chips and card display working.

### Stage 3: Inventory Breakdown On Detail Page

- Add the inventory section to the mobile detail page.
- Show per-location lot quantities with `[−]` and `[+]` controls.
- Show not-shipped count.
- Show drink history (collapsed).
- Location `[−]` and `[+]` write directly to lots and call sync.

### Stage 4: Re-Buy Detection In Add Wine

- Detect same wine + same vintage on the Add Wine flow.
- Show "Looks familiar" prompt with current inventory and drink history.
- "Add bottles to existing wine" creates a new lot under the existing wine.
- "Add as new vintage" creates a new wine row as normal.
- Detect other vintages and display without merging.

### Stage 5: Shipment Receiving

- Build a "Receive shipment" flow for `not_shipped` lots.
- User selects a not-shipped lot, assigns a location.
- Lot status changes to `in_collection`.
- Sync runs.

---

## Resolved Design Decisions

| Question | Decision |
|---|---|
| Drank lots: keep qty or zero? | No `drank` status on lots. Drinking decrements lot quantity; lot is deleted at 0. Drink history holds the record. |
| `wines.quantity` = available only or total ever? | Available only: `SUM(in_collection lots)`. |
| Location when split across multiple? | `wines.storage_location` = primary (largest). `wines.location_summary` = full breakdown string. Never store `'Multiple'`. |
| Move flow? | No move flow. Location is a direct attribute of a lot. Users edit lot quantities via `[−]`/`[+]` on the detail page. |
| Move history? | Not tracked. Only current state matters. |
| Drink notes/rating update `wines.notes`/`my_rating`? | No auto-overwrite of `wines.notes`. Optionally cache last drink's rating into `wines.my_rating`. |
| Fuzzy name matching? | Normalize (lowercase, strip punctuation) and show candidate to user for confirmation. No fuzzy scoring in v1. |
| Verticals/family grouping? | Out of scope for v1. |
| Default cellar shows all statuses or available only? | Keep current behavior (all statuses visible, location filter does the heavy lifting). |
| Not-shipped + available for same wine? | Show both: `2 available · 6 incoming` on detail page. |
| Analytics use lots? | Yes — lots are cleaner for cellar value and bottle counts than the current `wines.quantity`. |
| `total_price` on lots? | Not stored. Computed as `unit_price * quantity` wherever needed. |
| User scoping on lots? | Enforced by always joining `wine_inventory_lots` through `wines` on `wines.user_id`. No `user_id` column on lots directly. |
| Lot consolidation on partial edits? | Before inserting a new lot, check for existing lot with same `(wine_id, status, storage_location, retailer, order_date)`. If found, increment quantity instead of inserting. |
| `_sync_wine_summary` transaction safety? | Must run in the same transaction as the lot change. Single SQL UPDATE, not a Python loop. |
