# Bottles Section UI Redesign

Implemented on April 30, 2026 in `templates/detail.html` inside the mobile
`@media (max-width: 767px)` CSS block.

## Goal

Reduce the visual dominance of the location stock cards in the mobile Bottles
section while keeping the same controls, data attributes, and event handlers.
The section should feel lighter and closer to the warm dark detail-page hero.

## Scope

CSS-only changes in `templates/detail.html`.

Do not change:

- Desktop view (`.desktop-detail-page`)
- JavaScript event handlers or `data-*` attributes
- Ledger summary dot line
- Incoming strip (`.ledger-incoming-strip`)
- Drink History rows or heading
- Backend routes or Python behavior

## Multi-Location Cards

For two or more available locations:

- Location cards use faint `loc-color-*` tinted backgrounds instead of solid
  saturated blocks.
- Borders keep the location color at reduced opacity.
- `.ledger-card-count` is larger and uses the location accent color.
- `.ledger-card-loc` is a small uppercase accent label.
- Card `min-height` and internal `gap` are reduced.
- Stepper buttons and the pencil/manage button keep their existing sizing and
  behavior.

## Single-Location Row

When `.ledger-cards` has exactly one `.ledger-card`, the card becomes a compact
horizontal row:

- Location label on the left.
- Stepper controls on the right.
- Normal-case location text for readability.
- Same faint location tint as the multi-location card.

Important template detail: the current HTML has only one `.ledger-card-count`,
and it lives inside `.ledger-card-stepper`. Do not hide it in the single-row
layout, or the count disappears entirely.

## Odd Trailing Card

Keep the `last-child:nth-child(odd)` behavior separate from `:only-child`.
For three or more locations, the trailing odd card should still span both grid
columns.

## Verification

Run:

```powershell
cd C:\Users\steve\wine-tracker
& 'C:\Users\steve\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\verify_detail.py
```

Expected checks:

- Python syntax for `app.py` and `db.py`
- `db.migrate()` against local SQLite
- Render of a real `/wine/<id>` detail page
- Bottles ledger and history edit markup
- Inline detail-page script syntax
