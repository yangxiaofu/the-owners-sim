# Depth Chart Drag-and-Drop UI Specification

**Version**: 1.0
**Last Updated**: 2025-10-11
**Status**: Draft

## Overview

The Depth Chart tab in the Team View provides a visual, interactive interface for managing team depth charts using drag-and-drop mechanics. Users can reorder players within positions, set starters, and manage the complete team depth chart through intuitive mouse interactions.

## Goals

1. **Intuitive Reordering**: Users can drag players to reorder depth charts without clicking through menus
2. **Visual Feedback**: Clear visual indicators during drag operations (ghost image, drop targets, hover states)
3. **Immediate Updates**: Changes persist to database automatically on drop
4. **Position Validation**: Prevent invalid drops (e.g., QB can't be dropped on RB depth chart)
5. **Undo Capability**: Users can revert changes if needed
6. **Performance**: Smooth animations and responsive interactions

## Current UI Structure

### Layout Hierarchy

```
DepthChartWidget (QWidget)
└── Sections (QGroupBox)
    ├── OFFENSE
    │   ├── QB Position Card
    │   ├── RB Position Card
    │   ├── WR Position Cards
    │   └── ... (all offensive positions)
    ├── DEFENSE (3-4 Base)
    │   ├── DE Position Cards
    │   ├── LB Position Cards
    │   ├── DB Position Cards
    │   └── ... (all defensive positions)
    └── SPECIAL TEAMS
        ├── K Position Card
        ├── P Position Card
        └── ... (all special teams positions)
```

### Position Card Structure

Each `PositionCardWidget` displays:
- **Header**: Position label (e.g., "QB", "RB")
- **Starter** (depth #1): Highlighted background (#E3F2FD blue)
- **Backup** (depth #2): Normal background (white)

**Current Limitation**: Only shows 2 players (starter + 1 backup)

## Proposed Drag-and-Drop Design

### Visual Design

#### Expanded Position Card (Draggable List)

Replace fixed 2-player cards with expandable depth chart lists:

```
┌─────────────────────────────┐
│ QB                    [▼]   │  ← Position header (clickable to expand/collapse)
├─────────────────────────────┤
│ ☰ 1. C.J. Stroud      87 ⋮  │  ← Starter (blue background, drag handle, context menu)
│ ☰ 2. Davis Mills      73 ⋮  │  ← Backup #1 (white background)
│ ☰ 3. Graham Mertz     69 ⋮  │  ← Backup #2 (white background)
└─────────────────────────────┘
```

**Elements**:
- **☰ Drag Handle**: Visual indicator that item is draggable (left side)
- **Depth Number**: Sequential (1, 2, 3...) automatically updated on reorder
- **Player Name**: Bold text, truncate if too long
- **Overall Rating**: Right-aligned, smaller font
- **⋮ Context Menu**: Right-click for additional actions (promote to starter, remove from depth, etc.)
- **▼ Collapse/Expand**: Toggle to show/hide backups (collapsed shows only starter)

#### Drag States

**1. Idle State (Default)**
```
┌─────────────────────────────┐
│ ☰ 1. C.J. Stroud      87 ⋮  │  ← Normal appearance
└─────────────────────────────┘
```

**2. Hover State (Mouse over drag handle)**
```
┌─────────────────────────────┐
│ ☰ 1. C.J. Stroud      87 ⋮  │  ← Cursor: grabbing hand icon
│   ^^^^^^^^^^^^^^^^^^^^^^^^   │     Background: slightly darker
└─────────────────────────────┘
```

**3. Dragging State (Item being dragged)**
```
┌─────────────────────────────┐
│ ☰ 2. Davis Mills      73 ⋮  │  ← Original position: dashed outline placeholder
└─────────────────────────────┘

     [Ghost Image]
     ┌──────────────────────┐
     │ ☰ 1. C.J. Stroud  87 │  ← Semi-transparent drag ghost (50% opacity)
     └──────────────────────┘
```

**4. Valid Drop Target (Hover over valid position)**
```
┌─────────────────────────────┐
│ ☰ 1. C.J. Stroud      87 ⋮  │
├═════════════════════════════┤  ← Drop indicator: thick green line (2px)
│ ☰ 2. Davis Mills      73 ⋮  │  ← Insert position
└─────────────────────────────┘
```

**5. Invalid Drop Target (Hover over wrong position/section)**
```
┌─────────────────────────────┐
│ RB                      [▼] │  ← Entire card: red border (2px solid)
├─────────────────────────────┤     Cursor: "no drop" icon (🚫)
│ ☰ 1. Nick Chubb       83 ⋮  │
│ ☰ 2. Joe Mixon        81 ⋮  │
└─────────────────────────────┘
```

### Interaction Flow

#### Workflow 1: Reorder Within Same Position

**User Action**: Drag QB2 (Davis Mills) above QB1 (C.J. Stroud) to promote to starter

1. **Mouse Down on Drag Handle**
   - Change cursor to grabbing hand (Qt::ClosedHandCursor)
   - Start drag operation (QDrag)
   - Create ghost image (semi-transparent QPixmap of player row)

2. **Mouse Move (Dragging)**
   - Ghost image follows cursor
   - Original position shows dashed placeholder
   - Highlight valid drop targets (green line between players)
   - Show "no drop" cursor on invalid targets

3. **Mouse Up (Drop)**
   - If valid drop:
     - Remove ghost image
     - Animate players sliding into new positions (200ms)
     - Update depth numbers (1→2, 2→1)
     - Call API: `depth_chart_api.swap_depth_positions(player1_id, player2_id)`
     - Show toast notification: "✅ Depth chart updated"
   - If invalid drop:
     - Animate ghost returning to original position (bounce-back effect)
     - Show toast notification: "❌ Invalid drop position"

**Result**: C.J. Stroud demoted to backup, Davis Mills promoted to starter

#### Workflow 2: Move Player to Different Depth

**User Action**: Drag QB3 (Graham Mertz) to QB1 position (promote to starter)

1. **Drag QB3 ghost over QB1 position**
2. **Green drop indicator appears above QB1**
3. **Drop**
   - Graham Mertz → depth 1 (new starter)
   - C.J. Stroud → depth 2 (demoted)
   - Davis Mills → depth 3 (pushed down)
   - Call API: `depth_chart_api.set_starter(player_id=mertz_id, position="quarterback")`

**Result**: Complete reordering with automatic depth number updates

#### Workflow 3: Remove from Depth Chart

**User Action**: Right-click on QB3 → "Remove from Depth Chart"

1. **Context menu appears** with options:
   - Promote to Starter
   - Move to Backup #2
   - Remove from Depth Chart
   - View Player Details

2. **Click "Remove from Depth Chart"**
   - Confirmation dialog: "Remove Graham Mertz from QB depth chart?"
   - On confirm:
     - Call API: `depth_chart_api.remove_from_depth_chart(player_id=mertz_id)`
     - Player row fades out (300ms animation)
     - Remaining players compact (QB1→QB1, QB2→QB2)
     - Show toast: "✅ Player removed from depth chart"

**Result**: Graham Mertz set to depth_chart_order=99 (unassigned)

#### Workflow 4: Add Player to Depth Chart (From Roster Tab)

**User Action**: Drag player from Roster tab onto Depth Chart tab

1. **Enable cross-widget drag-and-drop** (requires inter-tab communication)
2. **Drag player from Roster table**
3. **Switch to Depth Chart tab** (auto-switch on hover near tab bar)
4. **Drop on position card**
   - Validate player plays this position
   - Insert at bottom of depth chart (or user-specified position)
   - Call API: `depth_chart_api.set_backup(player_id, position, backup_order=N)`

**Result**: Player added to depth chart at specified position

### Technical Implementation

#### Qt Drag-and-Drop Components

**1. Draggable Player Row Widget (`DraggablePlayerRow`)**

```python
from PySide6.QtCore import Qt, QMimeData, QByteArray
from PySide6.QtGui import QDrag, QPixmap, QPainter
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

class DraggablePlayerRow(QWidget):
    """
    Individual player row within depth chart, supports drag-and-drop.
    """

    def __init__(self, player_id: int, player_name: str, overall: int,
                 depth_order: int, position: str, parent=None):
        super().__init__(parent)
        self.player_id = player_id
        self.player_name = player_name
        self.overall = overall
        self.depth_order = depth_order
        self.position = position

        # Enable drag
        self.setAcceptDrops(False)  # Rows don't accept drops, parent list does

        self._setup_ui()

    def mousePressEvent(self, event):
        """Handle mouse press for drag initiation."""
        if event.button() == Qt.LeftButton:
            # Start drag operation
            drag = QDrag(self)
            mime_data = QMimeData()

            # Store player data as JSON in MIME data
            import json
            player_data = {
                'player_id': self.player_id,
                'player_name': self.player_name,
                'overall': self.overall,
                'depth_order': self.depth_order,
                'position': self.position
            }
            mime_data.setText(json.dumps(player_data))
            drag.setMimeData(mime_data)

            # Create ghost image (semi-transparent)
            pixmap = self.grab()
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            painter.fillRect(pixmap.rect(), QColor(255, 255, 255, 128))  # 50% opacity
            painter.end()

            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())

            # Execute drag (blocks until drop)
            drag.exec(Qt.MoveAction)
```

**2. Drop Target List Widget (`DepthChartListWidget`)**

```python
from PySide6.QtWidgets import QListWidget
from PySide6.QtCore import Qt, Signal

class DepthChartListWidget(QListWidget):
    """
    List widget that accepts drops and manages player depth chart ordering.
    """

    depth_chart_changed = Signal(str, list)  # (position, ordered_player_ids)

    def __init__(self, position: str, parent=None):
        super().__init__(parent)
        self.position = position
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)

        # Visual styling
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)

    def dragEnterEvent(self, event):
        """Accept drag if player plays this position."""
        mime_data = event.mimeData()
        if mime_data.hasText():
            import json
            player_data = json.loads(mime_data.text())

            # Validate position match
            if player_data['position'] == self.position:
                event.acceptProposedAction()
                self._highlight_drop_zone(True)
            else:
                event.ignore()
                self._show_invalid_drop()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Remove drop zone highlighting."""
        self._highlight_drop_zone(False)

    def dropEvent(self, event):
        """Handle drop and reorder depth chart."""
        mime_data = event.mimeData()
        if mime_data.hasText():
            import json
            player_data = json.loads(mime_data.text())

            # Get drop position (index)
            drop_index = self.indexAt(event.pos()).row()
            if drop_index == -1:
                drop_index = self.count()  # Drop at end

            # Reorder internal list
            # (Implementation: remove from old position, insert at new position)

            # Emit signal with new order
            ordered_player_ids = self._get_ordered_player_ids()
            self.depth_chart_changed.emit(self.position, ordered_player_ids)

            event.acceptProposedAction()
            self._highlight_drop_zone(False)
        else:
            event.ignore()

    def _get_ordered_player_ids(self) -> list[int]:
        """Get player IDs in current visual order."""
        return [
            self.item(i).data(Qt.UserRole)  # Store player_id in UserRole
            for i in range(self.count())
        ]
```

**3. Enhanced Position Card (`DepthChartPositionCard`)**

```python
class DepthChartPositionCard(QWidget):
    """
    Enhanced position card with expandable depth chart list.
    """

    def __init__(self, position: str, parent=None):
        super().__init__(parent)
        self.position = position
        self.is_expanded = True

        # Depth chart list (draggable)
        self.depth_chart_list = DepthChartListWidget(position, self)
        self.depth_chart_list.depth_chart_changed.connect(self._on_depth_chart_changed)

        self._setup_ui()

    def _on_depth_chart_changed(self, position: str, ordered_player_ids: list[int]):
        """Handle depth chart reorder from drag-and-drop."""
        # Call API to persist changes
        from depth_chart import DepthChartAPI

        api = DepthChartAPI(self.db_path)
        success = api.reorder_position_depth(
            dynasty_id=self.dynasty_id,
            team_id=self.team_id,
            position=position,
            ordered_player_ids=ordered_player_ids
        )

        if success:
            self._show_toast("✅ Depth chart updated")
            self._refresh_depth_numbers()  # Update 1, 2, 3... labels
        else:
            self._show_toast("❌ Failed to update depth chart")
            self._revert_to_previous_order()
```

#### API Integration Points

| User Action | API Method Called | Parameters |
|-------------|-------------------|------------|
| Drag player to different depth | `reorder_position_depth()` | position, ordered_player_ids |
| Right-click → Promote to Starter | `set_starter()` | player_id, position |
| Right-click → Set as Backup #N | `set_backup()` | player_id, position, backup_order |
| Right-click → Remove from Depth Chart | `remove_from_depth_chart()` | player_id |
| Swap two adjacent players | `swap_depth_positions()` | player1_id, player2_id |

#### Data Flow

```
┌─────────────────┐
│   User Action   │  (Drag QB2 to QB1 position)
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Qt Drag-and-Drop Event  │  (dropEvent triggered)
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ DepthChartListWidget            │  (Extract new order from UI)
│  - Get ordered_player_ids       │
│  - Emit depth_chart_changed     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ DepthChartPositionCard          │  (Receive signal)
│  - Call API via domain model    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ TeamDataModel                   │  (Business logic layer)
│  - Validate player position     │
│  - Call depth_chart_api         │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ DepthChartAPI                   │  (Database operations)
│  - reorder_position_depth()     │
│  - Update team_rosters table    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Database (SQLite)               │  (Persist changes)
│  - UPDATE team_rosters          │
│    SET depth_chart_order = ...  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ UI Update                       │  (Refresh display)
│  - Update depth numbers (1→2)   │
│  - Show success toast           │
│  - Trigger animations           │
└─────────────────────────────────┘
```

### Edge Cases and Validation

#### Validation Rules

1. **Position Mismatch**
   - **Scenario**: User drags QB onto RB depth chart
   - **Behavior**: Show red border, "no drop" cursor, reject drop
   - **Error**: Toast notification "❌ QB cannot be assigned to RB position"

2. **Empty Depth Chart**
   - **Scenario**: All players removed from position (depth_chart_order=99)
   - **Behavior**: Show placeholder "No players assigned - drag players here"
   - **API**: Allow drops even on empty list

3. **Single Player**
   - **Scenario**: Only one player at position (no backup)
   - **Behavior**: Drag still works (for future when more players added)
   - **Context Menu**: "Remove" option shows warning "This will leave position unassigned"

4. **Duplicate Depth Orders**
   - **Scenario**: Database has two players at depth 1 (data corruption)
   - **Behavior**: On load, show error banner "Depth chart conflicts detected - click to auto-fix"
   - **Auto-Fix**: Call `reset_position_depth_chart()` to regenerate by overall

5. **Cross-Tab Drag**
   - **Scenario**: Drag player from Roster tab to Depth Chart tab
   - **Behavior**: Require Ctrl+drag for safety (prevent accidental moves)
   - **Validation**: Check if player already on depth chart (prevent duplicates)

6. **Network/Database Error**
   - **Scenario**: API call fails (database locked, network timeout)
   - **Behavior**: Revert UI to previous state with bounce animation
   - **Error**: Toast notification "❌ Failed to save changes - please try again"
   - **Undo**: Keep previous order in memory for quick rollback

#### Error Handling Strategy

```python
class DepthChartPositionCard(QWidget):
    """Enhanced error handling for depth chart operations."""

    def _on_depth_chart_changed(self, position: str, ordered_player_ids: list[int]):
        """Handle depth chart reorder with error recovery."""
        # Store previous order for undo
        self._previous_order = self._get_current_order()

        try:
            # Call API
            api = DepthChartAPI(self.db_path)
            success = api.reorder_position_depth(
                dynasty_id=self.dynasty_id,
                team_id=self.team_id,
                position=position,
                ordered_player_ids=ordered_player_ids
            )

            if success:
                self._show_toast("✅ Depth chart updated", duration=2000)
                self._refresh_depth_numbers()
                self._add_to_undo_stack()  # Enable Ctrl+Z
            else:
                # API returned False (validation failed)
                self._revert_to_previous_order()
                self._show_toast("❌ Invalid depth chart change", duration=3000)

        except Exception as e:
            # Database error, network error, etc.
            self._revert_to_previous_order()
            self._show_toast(f"❌ Error: {str(e)}", duration=5000)

            # Log to console for debugging
            import traceback
            print(f"[ERROR] Depth chart update failed: {e}")
            traceback.print_exc()

    def _revert_to_previous_order(self):
        """Undo depth chart change with bounce animation."""
        # Animate items sliding back to original positions
        for i, player_id in enumerate(self._previous_order):
            item = self._find_item_by_player_id(player_id)
            self._animate_item_to_position(item, i, duration=300)
```

### Keyboard Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| **Ctrl+Z** | Undo | Revert last depth chart change |
| **Ctrl+Y** | Redo | Re-apply undone change |
| **Up/Down Arrows** | Navigate | Move selection up/down depth chart |
| **Ctrl+Up** | Promote | Move selected player up one position |
| **Ctrl+Down** | Demote | Move selected player down one position |
| **Delete** | Remove | Remove selected player from depth chart |
| **F2** | Edit | (Future) Edit player nickname/notes |
| **Ctrl+Shift+A** | Auto-Generate | Auto-generate all depth charts by overall |

### Animations and Visual Feedback

#### Animation Timeline

**1. Drag Start** (instant)
- Change cursor to grabbing hand (0ms)
- Show ghost image (0ms)
- Darken original position (fade to 30% opacity, 100ms)

**2. Drag Move** (continuous)
- Ghost follows cursor (0ms lag)
- Update drop indicator position (instant)
- Highlight valid/invalid targets (instant)

**3. Valid Drop** (smooth)
- Hide ghost image (0ms)
- Slide players into new positions (200ms ease-in-out)
- Update depth numbers (fade out old, fade in new, 150ms)
- Show success toast (slide in from top, 300ms)

**4. Invalid Drop** (bounce)
- Ghost bounces back to origin (300ms ease-out)
- Red flash on invalid target (100ms)
- Show error toast (slide in from top, 300ms)

#### Color Palette

| Element | State | Color | Usage |
|---------|-------|-------|-------|
| Starter Background | Normal | #E3F2FD | Light blue highlight |
| Backup Background | Normal | #FFFFFF | White |
| Drag Handle | Hover | #BDBDBD | Gray |
| Drop Indicator | Valid | #4CAF50 | Green (2px line) |
| Invalid Target | Error | #F44336 | Red border |
| Ghost Image | Dragging | 50% opacity | Semi-transparent |
| Placeholder | Empty | #E0E0E0 | Dashed border |

### Accessibility

1. **Keyboard Navigation**: All drag-and-drop actions accessible via keyboard shortcuts
2. **Screen Reader Support**: ARIA labels for depth positions ("Starter", "First Backup", etc.)
3. **Focus Indicators**: Clear visual focus rectangles for keyboard navigation
4. **Contrast Ratios**: Minimum 4.5:1 for text, 3:1 for UI components (WCAG AA)
5. **Motion Reduction**: Respect `prefers-reduced-motion` media query, disable animations if set

### Performance Considerations

1. **Large Depth Charts** (>10 players per position)
   - Use virtualized list (QListView with custom model)
   - Lazy-load player data on scroll
   - Limit visible items to viewport +/- 5 rows

2. **Many Positions** (~50 total positions)
   - Collapsed state by default (show only starters)
   - Load expanded data on demand
   - Cache depth chart data in memory (invalidate on change)

3. **Drag Performance**
   - Use hardware-accelerated rendering (Qt::AA_UseOpenGLES)
   - Throttle drag move events (max 60fps)
   - Create ghost image once (don't regenerate on every move)

### Future Enhancements

1. **Multi-Player Drag**: Select multiple players (Ctrl+click) and drag as group
2. **Copy to Clipboard**: Ctrl+C to copy depth chart as text (for sharing/pasting)
3. **Import/Export**: Save/load depth chart presets (e.g., "Week 1 vs Packers", "Nickel Package")
4. **Injury Indicators**: Red cross icon on injured players, auto-promote backups
5. **Snap Count Tracking**: Show percentage of snaps each player took (read-only data)
6. **Formation-Specific Depth Charts**: Different depth charts for base defense, nickel, dime, etc.
7. **AI Suggestions**: "Suggested Depth Chart" button based on player ratings + matchups

## Implementation Checklist

- [ ] **Phase 1: Basic Drag-and-Drop** (Week 1)
  - [ ] Convert PositionCardWidget to expandable list format
  - [ ] Implement DraggablePlayerRow with ghost image
  - [ ] Add drop target highlighting (valid/invalid)
  - [ ] Integrate with `reorder_position_depth()` API
  - [ ] Add success/error toast notifications

- [ ] **Phase 2: Advanced Features** (Week 2)
  - [ ] Add context menu (promote, demote, remove)
  - [ ] Implement keyboard shortcuts (Ctrl+Up/Down, Delete)
  - [ ] Add undo/redo functionality
  - [ ] Implement animations (slide, bounce, fade)
  - [ ] Add empty state placeholders

- [ ] **Phase 3: Polish & Edge Cases** (Week 3)
  - [ ] Error recovery and rollback
  - [ ] Validation messages for all edge cases
  - [ ] Performance optimization for large rosters
  - [ ] Accessibility improvements (ARIA, keyboard nav)
  - [ ] User testing and refinements

- [ ] **Phase 4: Integration** (Week 4)
  - [ ] Connect to live team data (via TeamDataModel)
  - [ ] Add auto-save indicator ("Saving..." spinner)
  - [ ] Integration testing with full UI
  - [ ] Bug fixes and final polish

## Testing Strategy

### Unit Tests
- Drag-and-drop event handling (mousePressEvent, dropEvent)
- MIME data serialization/deserialization
- API call parameter validation

### Integration Tests
- End-to-end drag operation → database update
- Cross-widget communication (Roster tab → Depth Chart tab)
- Error recovery scenarios (database errors, validation failures)

### Manual Testing Scenarios
1. Reorder within same position (promote backup to starter)
2. Invalid drop (drag QB to RB position)
3. Remove player from depth chart (right-click menu)
4. Auto-generate depth chart (reset all positions)
5. Undo/redo sequence (Ctrl+Z, Ctrl+Y)
6. Keyboard-only navigation (no mouse)
7. Large roster stress test (100+ players across all positions)

## References

- **Qt Drag-and-Drop Documentation**: https://doc.qt.io/qt-6/dnd.html
- **Depth Chart API Specification**: `docs/api/depth_chart_api_specification.md`
- **UI Architecture**: `docs/architecture/ui_layer_separation.md`
- **OOTP UI Reference**: Similar drag-and-drop patterns in Out of the Park Baseball
- **Madden NFL Reference**: Depth chart management interface

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-11 | Initial | First draft of specification |
