# Stage 2 and 3 Inventory Plan

## Current Status

Stages 2 and 3 have now been implemented on GitHub `main`.

Implemented:
- `POST /wine/<id>/drink-one`
- `POST /wine/<id>/lot/<lot_id>/adjust`
- `POST /wine/<id>/lot/add-location`
- `POST /wine/<id>/add-lot` as a backend endpoint for the future re-buy flow
- mobile detail Inventory section
- per-location current inventory controls
- drink history capture and recent drink history display
- old mobile Qty card changed to read-only so it no longer competes with lot controls

Remaining follow-up work:
- re-buy detection in Add Wine
- polished "Add bottles to existing wine" UI
- "Receive shipment" flow for not-shipped lots
- optional "show all drink history" view when more than the recent rows exist
- future wine family / vertical grouping for same wine across different vintages

The original plan below is retained as background context, but it should no longer be treated as unbuilt work.

This file is a continuation note for the inventory-lots migration. Stage 1 is the data foundation: inventory lots, drink history table, cached wine summaries, migration, and updated add/import paths.

Do not treat the remaining roadmap items as implemented behavior unless CLAUDE.md or the app code says they are live.

## Stage 2: Quantity-Aware Drink Flow

Goal: make "Drank one" operate on inventory lots instead of flipping the whole wine row to drank.

### Backend Behavior

Add a route for drinking one bottle from a wine, probably:

```text
POST /wine/<id>/drink-one
```

The route should:

1. Verify the logged-in user owns the wine.
2. Find available lots:
   - `wine_inventory_lots.status = 'in_collection'`
   - `quantity > 0`
3. If a specific `lot_id` is posted, validate that it belongs to the wine and user.
4. If no `lot_id` is posted and there is exactly one available lot, use that lot.
5. If no `lot_id` is posted and there are multiple available locations, return enough data for the UI to ask the user which location.
6. Decrement selected lot quantity by 1.
7. If the selected lot reaches 0, delete it.
8. Insert a `wine_drink_history` row:
   - `wine_id`
   - `lot_id`
   - `quantity = 1`
   - `drank_date`
   - optional `rating`
   - optional `notes`
9. Optionally update `wines.my_rating` with the submitted rating.
10. Call `db.sync_wine_summary(conn, wine_id)` in the same transaction.

### Mobile UI Behavior

The common case should be fast.

If the wine has available bottles in one location:

```text
Tap Drank one -> confirm/optional notes -> saved
```

If the wine has available bottles in multiple locations:

```text
Tap Drank one -> choose House (4) or Apt (2) -> saved
```

Rating and notes should be optional. Do not make the user fill them out every time.

### Existing UI Integration

Candidate places for the action:

- Mobile detail page bottom/action area
- Detail inventory section once Stage 3 exists
- Later: mobile card quick action, but not required for Stage 2

The existing status chip/filter behavior should continue to read from the cached `wines.status` field.

## Stage 3: Mobile Inventory Breakdown

Goal: show lot-aware inventory on the mobile detail page, without redesigning the main mobile cards yet.

### Backend Data

`wine_detail()` should query and pass:

```text
inventory_lots
available_by_location
not_shipped_count
drink_history
drank_total
```

All lot queries must join through `wines` or use the known wine owner to enforce user ownership.

### Detail Page Section

Add a compact mobile-only section near the current Cellar fields:

```text
Inventory
House        4    [-] [+]
Apt          2    [-] [+]
Not shipped  1
Drank total  3

[Drank one] [Add more]
```

This should be useful but restrained. It should not turn the page into an inventory spreadsheet.

### Increment/Decrement Controls

Add small routes for adjusting lot quantities:

```text
POST /wine/<id>/lot/<lot_id>/increment
POST /wine/<id>/lot/<lot_id>/decrement
```

Possible alternative: one route with `delta`.

Rules:

- Increment adds 1 to an existing lot.
- Decrement subtracts 1.
- Decrement to 0 deletes the lot.
- Every change calls `sync_wine_summary()` in the same transaction.

For adding a new location row, either:

- provide an "Add location" control, or
- wait until the later Add More / Receive Shipment work.

### Drink History Display

Add a collapsed mobile section:

```text
Drink history
Apr 29, 2026 · Drank 1 · 4.3
Mar 12, 2026 · Drank 1
```

For version 1, this can be read-only.

### Main Cellar Cards

Avoid changing the card layout unless explicitly requested.

Minimal possible future change:

```text
Qty 6
House 4 · Apt 2
```

The cached `wines.location_summary` exists for this, but adding it to cards should be a deliberate mobile UI pass, not an accidental Stage 3 side effect.

## Things To Be Careful About

- Do not reintroduce `drank` as a lot status. Lots are current inventory only.
- Do not store `Multiple` in `wines.storage_location`.
- Keep `wines.quantity` as available bottles only.
- Always run lot changes and `sync_wine_summary()` in one transaction.
- Keep desktop views unchanged unless explicitly requested.
- If a wine has no available lots but has not-shipped lots, `wines.status` should be `not_shipped`.
- If a wine has no current lots, `wines.status` should be `drank`.
