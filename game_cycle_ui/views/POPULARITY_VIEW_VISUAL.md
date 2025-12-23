# PopularityView Visual Reference

## Layout Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PLAYER POPULARITY RANKINGS                                                  │
│                                                                             │
│  Tier: [All Tiers ▼]  Position: [All Positions ▼]  [Refresh]              │
├─────────────────────────────────────────────────────────────────────────────┤
│ POPULARITY SUMMARY                                                          │
│  Players Tracked: 50   Avg Popularity: 67.5   Top Player: Patrick Mahomes  │
│  Week: 10                                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Rank │ Player          │ Pos │ Team │ Score │ Tier  │ Trend    │ Perf │...│
├──────┼─────────────────┼─────┼──────┼───────┼───────┼──────────┼──────┼───┤
│  1   │ Patrick Mahomes │ QB  │ KC   │ 95.3  │ TRANS │ ↑ +2.5  │  92  │...│
│  2   │ Josh Allen      │ QB  │ BUF  │ 91.2  │ TRANS │ ↑ +1.3  │  88  │...│
│  3   │ Justin Jefferson│ WR  │ MIN  │ 87.8  │ STAR  │ → 0.0   │  85  │...│
│  4   │ Nick Bosa       │ EDGE│ SF   │ 84.5  │ STAR  │ ↓ -0.8  │  90  │...│
│  5   │ Travis Kelce    │ TE  │ KC   │ 82.1  │ STAR  │ → +0.2  │  83  │...│
│ ...  │ ...             │ ... │ ...  │ ...   │ ...   │ ...     │  ... │...│
│ 50   │ Derek Carr      │ QB  │ NO   │ 52.3  │ KNOWN │ ↓ -1.5  │  55  │...│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Header Section

```
┌─────────────────────────────────────────────────────────────────────┐
│ PLAYER POPULARITY RANKINGS                    [Filters] [Refresh]  │
└─────────────────────────────────────────────────────────────────────┘

Title: Large bold heading (Typography.H4)
Filters: Two dropdowns (Tier, Position)
Refresh: Blue button (SECONDARY_BUTTON_STYLE)
```

## Summary Panel

```
┌─────────────────────────────────────────────────────────────────────┐
│ POPULARITY SUMMARY                                                  │
│                                                                     │
│  Players Tracked        Avg Popularity      Top Player      Week   │
│       50                    67.5        Patrick Mahomes      10    │
└─────────────────────────────────────────────────────────────────────┘

Background: Dark group box (#263238)
Stats: H4 font size, centered
Labels: Small gray text above values
```

## Table Columns

### Column 1-4: Basic Info

```
┌──────┬──────────────────┬─────┬──────┐
│ Rank │ Player           │ Pos │ Team │
├──────┼──────────────────┼─────┼──────┤
│  1 ★ │ Patrick Mahomes  │ QB  │ KC   │  ← Rank 1 in gold
│  2   │ Josh Allen       │ QB  │ BUF  │
│  3   │ Justin Jefferson │ WR  │ MIN  │
└──────┴──────────────────┴─────┴──────┘

Rank: Center-aligned, bold for #1, gold color for #1
Player: Left-aligned, clickable (double-click for details)
Pos: Center-aligned, abbreviated
Team: Center-aligned, 2-3 letter code
```

### Column 5-7: Popularity Metrics

```
┌───────┬───────┬──────────┐
│ Score │ Tier  │ Trend    │
├───────┼───────┼──────────┤
│ 95.3  │ TRANS │ ↑ +2.5  │  ← Gold (Transcendent)
│ 91.2  │ TRANS │ ↑ +1.3  │  ← Gold
│ 87.8  │ STAR  │ → 0.0   │  ← Silver (Star)
│ 84.5  │ STAR  │ ↓ -0.8  │  ← Silver
│ 52.3  │ KNOWN │ ↓ -1.5  │  ← Green (Known)
└───────┴───────┴──────────┘

Score: Center-aligned, color-coded by tier
  - 90-100: Gold (#FFD700)
  - 75-89: Silver (#C0C0C0)
  - 50-74: Green (#4CAF50)
  - 25-49: Blue (#1976D2)
  - 0-24: Gray (#666666)

Tier: Bold badge, same colors as score
  - TRANS (Transcendent)
  - STAR
  - KNOWN
  - ROLE (Role Player)
  - UNK (Unknown)

Trend: Arrow + change value
  - ↑ +X.X (green for positive)
  - ↓ -X.X (red for negative)
  - → 0.0 (gray for stable)
```

### Column 8-10: Component Breakdown

```
┌──────┬────────────┬────────┐
│ Perf │ Visibility │ Market │
├──────┼────────────┼────────┤
│  92  │   2.50x    │ 1.80x  │
│  88  │   2.20x    │ 1.50x  │
│  85  │   1.90x    │ 1.60x  │
└──────┴────────────┴────────┘

Perf: Performance score (0-100)
Visibility: Multiplier (0.50x - 3.00x)
Market: Multiplier (0.80x - 2.00x)

All center-aligned, standard white text
```

## Filter Dropdowns

### Tier Filter

```
┌──────────────────────────┐
│ Tier: [All Tiers      ▼] │
└──────────────────────────┘

Options:
  • All Tiers (default)
  • Transcendent (90-100)
  • Star (75-89)
  • Known (50-74)
  • Role Player (25-49)
  • Unknown (0-24)
```

### Position Filter

```
┌──────────────────────────┐
│ Position: [All Positions▼│
└──────────────────────────┘

Options:
  • All Positions (default)
  • QB, RB, WR, TE
  • EDGE, DT, LB, CB, S
  • K, P
```

## Sorting Behavior

Click any column header to sort:
- **Rank**: Ascending (1 → 50)
- **Player**: Alphabetical (A → Z)
- **Score**: Descending (100 → 0) [default]
- **Trend**: By change value
- **Performance**: Descending

Click again to reverse sort order.

## Interaction Patterns

### Double-Click on Player
```
Double-click row
    ↓
Opens PlayerDetailDialog
    ↓
Shows full player stats, contract, history
```

### Filter Selection
```
Change Tier dropdown
    ↓
Filters table to selected tier
    ↓
Updates summary panel
```

### Refresh Button
```
Click Refresh
    ↓
Emits refresh_requested signal
    ↓
Recalculates popularity scores
    ↓
Reloads table data
```

## Color Palette

### Tier Colors
- **Transcendent**: #FFD700 (Gold) - 90-100
- **Star**: #C0C0C0 (Silver) - 75-89
- **Known**: #4CAF50 (Green) - 50-74
- **Role Player**: #1976D2 (Blue) - 25-49
- **Unknown**: #666666 (Gray) - 0-24

### Trend Colors
- **Rising**: #2E7D32 (Green)
- **Falling**: #C62828 (Red)
- **Stable**: #666666 (Gray)

### Background Colors
- **Table**: #1a1a1a (Dark)
- **Row Hover**: #2a4a6a (Blue-gray)
- **Alternate Rows**: #222222 (Slightly lighter)
- **Summary Panel**: #263238 (Blue-gray)

## Typography

- **Title**: Arial 16px Bold
- **Summary Labels**: Arial 11px Regular
- **Summary Values**: Arial 16px Bold
- **Table Headers**: Arial 10px Bold
- **Table Cells**: Arial 11px Regular
- **Rank #1**: Arial 11px Bold

## Dimensions

- **Window**: 1400×800px recommended
- **Row Height**: 32px
- **Header Height**: 60px
- **Summary Height**: 80px
- **Table**: Remaining space (stretch)

## Example Screenshots (Text-Based)

### Top 10 Players (Full Width)
```
═══════════════════════════════════════════════════════════════════════════════════════════════════
 #  │ PLAYER             │ POS │ TEAM │ SCORE │ TIER  │ TREND    │ PERF │ VIS   │ MKT
═══════════════════════════════════════════════════════════════════════════════════════════════════
 1★ │ Patrick Mahomes    │ QB  │ KC   │ 95.3  │ TRANS │ ↑ +2.5  │  92  │ 2.50x │ 1.80x
 2  │ Josh Allen         │ QB  │ BUF  │ 91.2  │ TRANS │ ↑ +1.3  │  88  │ 2.20x │ 1.50x
 3  │ Justin Jefferson   │ WR  │ MIN  │ 87.8  │ STAR  │ → 0.0   │  85  │ 1.90x │ 1.60x
 4  │ Nick Bosa          │ EDGE│ SF   │ 84.5  │ STAR  │ ↓ -0.8  │  90  │ 1.70x │ 1.40x
 5  │ Travis Kelce       │ TE  │ KC   │ 82.1  │ STAR  │ → +0.2  │  83  │ 1.85x │ 1.80x
 6  │ Christian McCaffrey│ RB  │ SF   │ 79.8  │ STAR  │ ↑ +3.1  │  87  │ 1.60x │ 1.40x
 7  │ Tyreek Hill        │ WR  │ MIA  │ 78.5  │ STAR  │ → -0.5  │  84  │ 1.75x │ 1.30x
 8  │ Jalen Hurts        │ QB  │ PHI  │ 76.2  │ STAR  │ ↓ -2.1  │  82  │ 1.80x │ 1.50x
 9  │ Micah Parsons      │ EDGE│ DAL  │ 74.9  │ KNOWN │ ↑ +1.8  │  89  │ 1.55x │ 1.80x
10  │ Lamar Jackson      │ QB  │ BAL  │ 73.6  │ KNOWN │ → +0.1  │  81  │ 1.70x │ 1.40x
═══════════════════════════════════════════════════════════════════════════════════════════════════
```

### Filtered by Tier: Transcendent Only
```
═══════════════════════════════════════════════════════════════════════════════════════════════════
Tier: [Transcendent (90-100) ▼]  Position: [All Positions ▼]  [Refresh]
───────────────────────────────────────────────────────────────────────────────────────────────────
 #  │ PLAYER             │ POS │ TEAM │ SCORE │ TIER  │ TREND    │ PERF │ VIS   │ MKT
═══════════════════════════════════════════════════════════════════════════════════════════════════
 1★ │ Patrick Mahomes    │ QB  │ KC   │ 95.3  │ TRANS │ ↑ +2.5  │  92  │ 2.50x │ 1.80x
 2  │ Josh Allen         │ QB  │ BUF  │ 91.2  │ TRANS │ ↑ +1.3  │  88  │ 2.20x │ 1.50x
═══════════════════════════════════════════════════════════════════════════════════════════════════
Total: 2 players
```

### Filtered by Position: Quarterbacks Only
```
═══════════════════════════════════════════════════════════════════════════════════════════════════
Tier: [All Tiers ▼]  Position: [QB ▼]  [Refresh]
───────────────────────────────────────────────────────────────────────────────────────────────────
 #  │ PLAYER             │ POS │ TEAM │ SCORE │ TIER  │ TREND    │ PERF │ VIS   │ MKT
═══════════════════════════════════════════════════════════════════════════════════════════════════
 1★ │ Patrick Mahomes    │ QB  │ KC   │ 95.3  │ TRANS │ ↑ +2.5  │  92  │ 2.50x │ 1.80x
 2  │ Josh Allen         │ QB  │ BUF  │ 91.2  │ TRANS │ ↑ +1.3  │  88  │ 2.20x │ 1.50x
 3  │ Jalen Hurts        │ QB  │ PHI  │ 76.2  │ STAR  │ ↓ -2.1  │  82  │ 1.80x │ 1.50x
 4  │ Lamar Jackson      │ QB  │ BAL  │ 73.6  │ KNOWN │ → +0.1  │  81  │ 1.70x │ 1.40x
 5  │ Joe Burrow         │ QB  │ CIN  │ 71.8  │ KNOWN │ ↑ +0.9  │  85  │ 1.50x │ 1.40x
═══════════════════════════════════════════════════════════════════════════════════════════════════
Total: 5 quarterbacks
```

## Accessibility

- **Keyboard Navigation**: Tab through filters, Enter to select
- **Screen Readers**: Table headers and row labels announced
- **High Contrast**: Color coding supplemented with text (arrows, badges)
- **Sorting Indicators**: Visual arrows in headers when sorted

## Responsive Design

- Minimum width: 1200px (to fit all columns)
- Recommended width: 1400px
- Height: Flexible (table stretches to fill)
- Horizontal scrolling: Disabled (all columns visible)
