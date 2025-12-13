# Milestone: Draft Direction System

**Feature**: Owner Strategic Guidance for NFL Draft
**Status**: Planned
**Estimated Effort**: 30-42 hours across 4 weeks
**Priority**: Medium
**Dependencies**: Milestone 6 (Trade System) - Complete

---

## Executive Summary

Enable the Owner to provide strategic direction to their GM before and during the NFL Draft. The Owner can set overall draft strategy (BPA vs Needs-Based), prioritize positions, and create a watchlist of target prospects. The GM then executes based on these preferences during auto-pick scenarios.

**Design Philosophy**: "Hire the GM, set the strategy, let them execute."

---

## User Story

**As an Owner**, I want to give my GM strategic guidance for the draft so that the AI makes picks aligned with my team-building philosophy without requiring me to manually select every single pick.

**Scenarios**:
1. Owner wants "Best Player Available" philosophy → Sets BPA strategy → AI ignores needs, picks highest-rated
2. Owner needs offensive line help → Sets Position Focus on OL → AI only considers OL prospects
3. Owner loves a specific QB prospect → Adds to watchlist → AI gets +10 bonus for that prospect if available
4. Owner starts with "Fill Needs", switches to "BPA" after Round 3 → Mid-draft adjustment supported

---

## Current State Analysis

### Draft System Architecture

**AI GM Decision Logic** (`src/game_cycle/services/draft_service.py:708-750`)
```python
def _evaluate_prospect(self, prospect, team_needs, pick_position):
    base_value = prospect["overall"]

    # Need-based bonuses
    if urgency >= 5:  # CRITICAL
        need_boost = 15
    elif urgency >= 4:  # HIGH
        need_boost = 8
    elif urgency >= 3:  # MEDIUM
        need_boost = 3

    # Reach penalty (picking too early)
    if pick_position < projected_min - 20:
        base_value -= 5

    return base_value + need_boost
```

**Team Needs Analysis** (`src/offseason/team_needs_analyzer.py`)
- Evaluates: Starter quality, backup depth, age/contracts, position tier
- Returns urgency levels: CRITICAL (5) → HIGH (4) → MEDIUM (3) → LOW (2) → NONE (1)

**Current Limitation**: NO owner input mechanism - AI always uses Balanced (needs + overall) approach

### Owner Input Patterns in Codebase

**Pattern 1: Immediate Execution** (Franchise Tag)
- UI decision → Controller validates → Service executes → Database updated
- File: `src/game_cycle/services/franchise_tag_service.py`

**Pattern 2: Deferred Collection** (Re-signing)
- UI accumulates decisions → "Process Stage" clicked → Batch execution
- File: `src/game_cycle/services/resigning_service.py`

**Pattern 3: Real-Time Iteration** (Draft Picks)
- User picks one prospect → Executes → Next pick → Repeat
- File: `src/game_cycle/services/draft_service.py`

**Chosen for Draft Direction**: Pattern 2 (Deferred Collection) - set strategy upfront, applies to all auto-picks

---

## Feature Specification

### 1. Draft Strategy Types

#### Best Player Available (BPA)
**Philosophy**: Always draft the highest-rated prospect regardless of need.

**Evaluation Formula**:
```python
adjusted_score = prospect.overall
# Ignores: need boost, reach penalty
```

**Use Case**: Owner believes in stockpiling talent, trusts trades/free agency to fill holes.

**Example**:
```
Pick #15, Team needs QB (CRITICAL)
Available: QB (78), WR (85), OT (80)

BPA selects: WR (85) ← Highest overall
```

---

#### Balanced (Default)
**Philosophy**: Balance talent and need - the current system behavior.

**Evaluation Formula**:
```python
need_boost = {
    CRITICAL: +15,
    HIGH: +8,
    MEDIUM: +3,
    LOW: 0
}
reach_penalty = -5 if picking 20+ spots too early
adjusted_score = overall + need_boost + reach_penalty
```

**Use Case**: Owner wants smart drafting that considers both value and fit.

**Example**:
```
Pick #15, Team needs QB (CRITICAL, projected #20)
Available: QB (78), WR (85), OT (80)

QB: 78 + 15 (need) = 93 ← Selected
WR: 85 + 0 - 5 (reach) = 80
OT: 80 + 0 = 80
```

---

#### Needs-Based
**Philosophy**: Aggressively fill roster holes, willing to reach for positional needs.

**Evaluation Formula**:
```python
need_boost = {
    CRITICAL: +30,  # 2× normal
    HIGH: +18,
    MEDIUM: +10,
    LOW: +5
}
# NO reach penalty
adjusted_score = overall + need_boost
```

**Use Case**: Owner's team has glaring holes that must be addressed immediately.

**Example**:
```
Pick #15, Team needs QB (CRITICAL)
Available: QB (70, projected #45), WR (85)

QB: 70 + 30 = 100 ← Selected (willing to reach)
WR: 85 + 0 = 85
```

---

#### Position Focus
**Philosophy**: Only consider specific positions, exclude everything else.

**Evaluation Formula**:
```python
if position NOT in priority_positions:
    adjusted_score = -100  # Excluded
else:
    priority_rank = priority_positions.index(position) + 1
    position_bonus = (6 - priority_rank) * 5  # 1st=+25, 2nd=+20, ..., 5th=+5
    need_boost = +20 (CRITICAL) | +12 (HIGH) | +6 (MEDIUM)
    adjusted_score = overall + position_bonus + need_boost
```

**Use Case**: Owner has specific positional targets for this draft (e.g., "OL only in first 3 rounds").

**Example**:
```
Pick #15, Priorities: [QB, WR, OT]
Available: QB (75), WR (82), CB (88)

QB: 75 + 25 (1st priority) + 20 (CRITICAL) = 120 ← Selected
WR: 82 + 20 (2nd priority) + 0 = 102
CB: 88 + (-100) [excluded] = -12
```

---

### 2. Watchlist System
**Feature**: Owner marks specific prospects as targets.

**Bonus**: +10 to adjusted score (all strategies)

**UI Flow**:
1. Owner clicks "Add to Watchlist" in prospects table
2. Prospect highlighted with ⭐ icon
3. AI gets +10 bonus when evaluating that prospect

**Example**:
```
Strategy: Balanced
Pick #15, Watchlisted QB (78, CRITICAL need)

Normal: 78 + 15 = 93
With watchlist: 78 + 15 + 10 = 103 ← Stronger preference
```

---

### 3. Position Priorities
**Feature**: Owner ranks 1-5 positions in order of importance.

**Used By**: Position Focus strategy (required), Balanced/Needs-Based (optional enhancement in Phase 3)

**UI**: 5 dropdowns with all positions, order matters (1st highest priority)

**Example**:
```
Priorities:
1. QB
2. WR
3. OT
4. CB
5. EDGE
```

---

## User Experience Design

### Pre-Draft Strategy Dialog

```
┌────────────────────────────────────────────────────────┐
│  Draft Strategy Configuration                          │
│  Your Team: Detroit Lions | Season: 2025               │
├────────────────────────────────────────────────────────┤
│  Overall Strategy:                                     │
│  ○ Best Player Available (BPA)                         │
│      Ignore needs, always pick highest-rated prospect  │
│                                                        │
│  ● Balanced (Recommended)                              │
│      Balance talent and need (current system)          │
│                                                        │
│  ○ Needs-Based                                         │
│      Aggressively fill holes, willing to reach         │
│                                                        │
│  ○ Position Focus                                      │
│      Only consider specific positions                  │
│                                                        │
├────────────────────────────────────────────────────────┤
│  Position Priorities (Optional):                       │
│  1. [Dropdown: QB        ▼]                            │
│  2. [Dropdown: WR        ▼]                            │
│  3. [Dropdown: OT        ▼]                            │
│  4. [Dropdown: None      ▼]                            │
│  5. [Dropdown: None      ▼]                            │
│                                                        │
│  Note: Required for Position Focus strategy            │
│                                                        │
├────────────────────────────────────────────────────────┤
│  Your Team Needs (AI Analysis):                        │
│  🔴 Critical: QB, LT                                   │
│  🟠 High: WR, CB, EDGE                                 │
│  🟡 Medium: FS, DT                                     │
│                                                        │
├────────────────────────────────────────────────────────┤
│  Preview: What This Means                              │
│  With Balanced strategy:                               │
│  • AI will prefer QB and LT (critical needs)           │
│  • Still considers overall prospect rating             │
│  • Avoids reaching too early                           │
│                                                        │
│  You can adjust this strategy mid-draft if needed.     │
│                                                        │
│         [Cancel]    [Use Default]    [Save Strategy]   │
└────────────────────────────────────────────────────────┘
```

### Integration into Draft View

**New UI Elements**:

1. **Strategy Badge** (Top-right corner)
   ```
   Strategy: Balanced ⚙️
   ```

2. **"Adjust Strategy" Button** (Always visible)
   - Reopens dialog mid-draft
   - Changes apply to remaining picks

3. **Watchlist Icons** (In prospects table)
   ```
   | Name           | Pos | Overall | College | ⭐ |
   | -------------- | --- | ------- | ------- | -- |
   | John Smith     | QB  | 85      | Alabama | ⭐ |  ← Watchlisted
   | Jane Doe       | WR  | 82      | Ohio St |    |
   ```

---

## Technical Architecture

### Data Model

**File**: `src/game_cycle/models/draft_direction.py` (NEW)

```python
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class DraftStrategy(Enum):
    """Overall draft strategy types."""
    BEST_PLAYER_AVAILABLE = "bpa"
    BALANCED = "balanced"
    NEEDS_BASED = "needs_based"
    POSITION_FOCUS = "position_focus"


@dataclass
class DraftDirection:
    """
    Owner's strategic direction for the draft.

    Ephemeral context - passed from UI → Handler → Service.
    Not persisted to database (cleared after draft completion).

    Attributes:
        strategy: Overall strategy type
        priority_positions: List of 1-5 positions in priority order
        watchlist_prospect_ids: List of targeted prospect IDs
    """
    strategy: DraftStrategy = DraftStrategy.BALANCED
    priority_positions: List[str] = field(default_factory=list)
    watchlist_prospect_ids: List[int] = field(default_factory=list)

    def validate(self) -> tuple[bool, str]:
        """
        Validate draft direction settings.

        Returns:
            (is_valid, error_message)
        """
        if self.strategy == DraftStrategy.POSITION_FOCUS:
            if not self.priority_positions:
                return (False, "Position Focus requires at least 1 priority position")

        if len(self.priority_positions) > 5:
            return (False, "Maximum 5 priority positions allowed")

        return (True, "")


@dataclass
class DraftDirectionResult:
    """Result of applying draft direction to prospect evaluation."""
    prospect_id: int
    prospect_name: str
    original_score: float
    adjusted_score: float
    strategy_bonus: float
    position_bonus: float
    watchlist_bonus: float
    reach_penalty: float
    reason: str  # Human-readable explanation

    def __str__(self) -> str:
        return (
            f"{self.prospect_name}: {self.original_score:.1f} → {self.adjusted_score:.1f} "
            f"(Strategy: +{self.strategy_bonus:.1f}, Position: +{self.position_bonus:.1f}, "
            f"Watchlist: +{self.watchlist_bonus:.1f}, Reach: {self.reach_penalty:.1f})"
        )
```

**Why No Database Table?**
- Ephemeral by nature (draft happens once, direction not reused)
- Passed as context parameter (like re-signing decisions)
- No historical tracking needed
- Simpler implementation (no migrations, no cleanup)

---

### Backend Service Layer

**File**: `src/game_cycle/services/draft_service.py` (MODIFY)

**New Methods**:

```python
def _evaluate_prospect_with_direction(
    self,
    prospect: Dict[str, Any],
    team_needs: List[Dict[str, Any]],
    pick_position: int,
    direction: Optional[DraftDirection] = None
) -> DraftDirectionResult:
    """
    Main dispatcher - routes to strategy-specific evaluators.

    Args:
        prospect: Prospect data dict
        team_needs: List of needs with urgency scores
        pick_position: Overall pick number (1-224)
        direction: Owner's draft direction (None = default Balanced)

    Returns:
        DraftDirectionResult with scores and explanation
    """
    if direction is None:
        direction = DraftDirection(strategy=DraftStrategy.BALANCED)

    base_score = prospect["overall"]

    # Route to strategy-specific evaluator
    if direction.strategy == DraftStrategy.BEST_PLAYER_AVAILABLE:
        result = self._evaluate_bpa(prospect, base_score)
    elif direction.strategy == DraftStrategy.BALANCED:
        result = self._evaluate_balanced(prospect, team_needs, pick_position, base_score)
    elif direction.strategy == DraftStrategy.NEEDS_BASED:
        result = self._evaluate_needs_based(prospect, team_needs, base_score)
    elif direction.strategy == DraftStrategy.POSITION_FOCUS:
        result = self._evaluate_position_focus(
            prospect, team_needs, direction.priority_positions, base_score
        )

    # Apply watchlist bonus (all strategies)
    if prospect["player_id"] in direction.watchlist_prospect_ids:
        result.watchlist_bonus = 10
        result.adjusted_score += 10
        result.reason += " | Watchlist target (+10)"

    return result
```

**Strategy Implementations**:

```python
def _evaluate_bpa(
    self,
    prospect: Dict[str, Any],
    base_score: float
) -> DraftDirectionResult:
    """Best Player Available - ignore needs entirely."""
    return DraftDirectionResult(
        prospect_id=prospect["player_id"],
        prospect_name=prospect["name"],
        original_score=base_score,
        adjusted_score=base_score,
        strategy_bonus=0,
        position_bonus=0,
        watchlist_bonus=0,
        reach_penalty=0,
        reason="BPA: Highest overall rating"
    )


def _evaluate_balanced(
    self,
    prospect: Dict[str, Any],
    team_needs: List[Dict[str, Any]],
    pick_position: int,
    base_score: float
) -> DraftDirectionResult:
    """Balanced - current system (needs + reach penalty)."""
    # Find need urgency
    position_urgency = 0
    for need in team_needs:
        if need["position"] == prospect["position"]:
            position_urgency = need.get("urgency_score", 0)
            break

    # Apply need boost
    if position_urgency >= 5:  # CRITICAL
        need_boost = 15
    elif position_urgency >= 4:  # HIGH
        need_boost = 8
    elif position_urgency >= 3:  # MEDIUM
        need_boost = 3
    else:
        need_boost = 0

    # Reach penalty
    projected_min = prospect.get("projected_pick_min", pick_position)
    reach_penalty = -5 if pick_position < projected_min - 20 else 0

    adjusted_score = base_score + need_boost + reach_penalty

    urgency_label = {5: "CRITICAL", 4: "HIGH", 3: "MEDIUM"}.get(position_urgency, "LOW")

    return DraftDirectionResult(
        prospect_id=prospect["player_id"],
        prospect_name=prospect["name"],
        original_score=base_score,
        adjusted_score=adjusted_score,
        strategy_bonus=need_boost,
        position_bonus=0,
        watchlist_bonus=0,
        reach_penalty=reach_penalty,
        reason=f"Balanced: {urgency_label} need (+{need_boost})"
    )


def _evaluate_needs_based(
    self,
    prospect: Dict[str, Any],
    team_needs: List[Dict[str, Any]],
    base_score: float
) -> DraftDirectionResult:
    """Needs-Based - aggressive need bonuses, no reach penalty."""
    position_urgency = 0
    for need in team_needs:
        if need["position"] == prospect["position"]:
            position_urgency = need.get("urgency_score", 0)
            break

    # Double the need boosts
    if position_urgency >= 5:  # CRITICAL
        need_boost = 30
    elif position_urgency >= 4:  # HIGH
        need_boost = 18
    elif position_urgency >= 3:  # MEDIUM
        need_boost = 10
    elif position_urgency >= 2:  # LOW
        need_boost = 5
    else:
        need_boost = 0

    # NO reach penalty - willing to reach for needs
    adjusted_score = base_score + need_boost

    urgency_label = {5: "CRITICAL", 4: "HIGH", 3: "MEDIUM", 2: "LOW"}.get(position_urgency, "NONE")

    return DraftDirectionResult(
        prospect_id=prospect["player_id"],
        prospect_name=prospect["name"],
        original_score=base_score,
        adjusted_score=adjusted_score,
        strategy_bonus=need_boost,
        position_bonus=0,
        watchlist_bonus=0,
        reach_penalty=0,
        reason=f"Needs-Based: {urgency_label} need (+{need_boost}), willing to reach"
    )


def _evaluate_position_focus(
    self,
    prospect: Dict[str, Any],
    team_needs: List[Dict[str, Any]],
    priority_positions: List[str],
    base_score: float
) -> DraftDirectionResult:
    """Position Focus - only consider priority positions."""
    position = prospect["position"]

    # Exclude non-priority positions
    if position not in priority_positions:
        return DraftDirectionResult(
            prospect_id=prospect["player_id"],
            prospect_name=prospect["name"],
            original_score=base_score,
            adjusted_score=-100,  # Excluded
            strategy_bonus=0,
            position_bonus=0,
            watchlist_bonus=0,
            reach_penalty=0,
            reason=f"Position Focus: {position} not in priorities (excluded)"
        )

    # Rank bonus (1st priority = +25, 2nd = +20, ..., 5th = +5)
    priority_rank = priority_positions.index(position) + 1
    position_bonus = (6 - priority_rank) * 5

    # Still apply need boost (smaller than Needs-Based)
    position_urgency = 0
    for need in team_needs:
        if need["position"] == position:
            position_urgency = need.get("urgency_score", 0)
            break

    if position_urgency >= 5:
        need_boost = 20
    elif position_urgency >= 4:
        need_boost = 12
    elif position_urgency >= 3:
        need_boost = 6
    else:
        need_boost = 0

    adjusted_score = base_score + position_bonus + need_boost

    return DraftDirectionResult(
        prospect_id=prospect["player_id"],
        prospect_name=prospect["name"],
        original_score=base_score,
        adjusted_score=adjusted_score,
        strategy_bonus=need_boost,
        position_bonus=position_bonus,
        watchlist_bonus=0,
        reach_penalty=0,
        reason=f"Position Focus: #{priority_rank} priority (+{position_bonus})"
    )
```

**Modified Methods**:

```python
def process_ai_pick(
    self,
    team_id: int,
    pick_info: Dict[str, Any],
    draft_direction: Optional[DraftDirection] = None  # NEW PARAMETER
) -> Dict[str, Any]:
    """
    Process an AI team's draft pick.

    Args:
        team_id: Team making the pick
        pick_info: Current pick details
        draft_direction: Owner's direction (only applies to user's team)

    Returns:
        Dict with pick result
    """
    # Get team needs
    team_needs = self._get_team_needs(team_id)

    # Get available prospects
    available = self.get_available_prospects()

    # Evaluate each prospect
    best_prospect = None
    best_score = -999

    for prospect in available:
        # Use direction-aware evaluation
        result = self._evaluate_prospect_with_direction(
            prospect,
            team_needs,
            pick_info["overall_pick"],
            direction=draft_direction
        )

        if result.adjusted_score > best_score:
            best_score = result.adjusted_score
            best_prospect = prospect

    # Execute the pick
    self.execute_pick(pick_info["overall_pick"], best_prospect["player_id"])

    return {
        "prospect": best_prospect,
        "evaluation": result,
        "reason": result.reason
    }


def sim_to_user_pick(
    self,
    user_team_id: int,
    draft_direction: Optional[DraftDirection] = None  # NEW PARAMETER
) -> List[Dict[str, Any]]:
    """
    Simulate AI picks until user's next pick.

    Args:
        user_team_id: User's team ID
        draft_direction: Strategy for user's team (AI teams use default)

    Returns:
        List of picks made
    """
    picks_made = []

    while True:
        current_pick = self.get_current_pick()
        if not current_pick:
            break  # Draft complete

        if current_pick["current_team_id"] == user_team_id:
            break  # User's turn

        # AI pick - only use direction if it's the user's team
        direction = draft_direction if current_pick["current_team_id"] == user_team_id else None

        pick_result = self.process_ai_pick(
            team_id=current_pick["current_team_id"],
            pick_info=current_pick,
            draft_direction=direction
        )

        picks_made.append(pick_result)

    return picks_made
```

---

### UI Layer

**File**: `game_cycle_ui/dialogs/draft_direction_dialog.py` (NEW)

```python
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton,
    QComboBox, QLabel, QPushButton, QGroupBox, QButtonGroup
)
from PySide6.QtCore import Signal

from src.game_cycle.models.draft_direction import DraftDirection, DraftStrategy


class DraftDirectionDialog(QDialog):
    """
    Dialog for configuring draft strategy.

    Allows owner to set:
    - Overall strategy (BPA, Balanced, Needs-Based, Position Focus)
    - Position priorities (1-5 positions)
    - Team needs preview (read-only)

    Emits:
        direction_saved: DraftDirection object when saved
    """

    direction_saved = Signal(object)  # DraftDirection

    def __init__(self, team_needs: List[Dict], current_direction: DraftDirection = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Draft Strategy Configuration")
        self.resize(600, 700)

        self._team_needs = team_needs
        self._current_direction = current_direction or DraftDirection()

        self._setup_ui()
        self._load_current_direction()

    def _setup_ui(self):
        """Create the dialog UI."""
        layout = QVBoxLayout(self)

        # Strategy section
        strategy_group = self._create_strategy_group()
        layout.addWidget(strategy_group)

        # Position priorities section
        priorities_group = self._create_priorities_group()
        layout.addWidget(priorities_group)

        # Team needs section (read-only)
        needs_group = self._create_needs_group()
        layout.addWidget(needs_group)

        # Preview section
        preview_group = self._create_preview_group()
        layout.addWidget(preview_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        default_btn = QPushButton("Use Default")
        default_btn.clicked.connect(self._use_default)

        save_btn = QPushButton("Save Strategy")
        save_btn.clicked.connect(self._save_direction)
        save_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(default_btn)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_strategy_group(self) -> QGroupBox:
        """Create the strategy selection group."""
        group = QGroupBox("Overall Strategy")
        layout = QVBoxLayout()

        self._strategy_group = QButtonGroup(self)

        # BPA
        bpa_radio = QRadioButton("Best Player Available (BPA)")
        bpa_radio.setToolTip("Ignore needs, always pick highest-rated prospect")
        self._strategy_group.addButton(bpa_radio, DraftStrategy.BEST_PLAYER_AVAILABLE.value)
        layout.addWidget(bpa_radio)

        # Balanced
        balanced_radio = QRadioButton("Balanced (Recommended)")
        balanced_radio.setToolTip("Balance talent and need - current system behavior")
        self._strategy_group.addButton(balanced_radio, DraftStrategy.BALANCED.value)
        layout.addWidget(balanced_radio)

        # Needs-Based
        needs_radio = QRadioButton("Needs-Based")
        needs_radio.setToolTip("Aggressively fill holes, willing to reach")
        self._strategy_group.addButton(needs_radio, DraftStrategy.NEEDS_BASED.value)
        layout.addWidget(needs_radio)

        # Position Focus
        position_radio = QRadioButton("Position Focus")
        position_radio.setToolTip("Only consider specific positions")
        self._strategy_group.addButton(position_radio, DraftStrategy.POSITION_FOCUS.value)
        layout.addWidget(position_radio)

        group.setLayout(layout)
        return group

    def _create_priorities_group(self) -> QGroupBox:
        """Create the position priorities group."""
        group = QGroupBox("Position Priorities (Optional)")
        layout = QVBoxLayout()

        label = QLabel("Note: Required for Position Focus strategy")
        layout.addWidget(label)

        self._priority_combos = []

        positions = ["None", "QB", "RB", "WR", "TE", "OT", "OG", "C",
                    "EDGE", "DT", "LB", "CB", "S", "K", "P"]

        for i in range(5):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{i+1}."))

            combo = QComboBox()
            combo.addItems(positions)
            self._priority_combos.append(combo)

            row.addWidget(combo)
            layout.addLayout(row)

        group.setLayout(layout)
        return group

    def _create_needs_group(self) -> QGroupBox:
        """Create the team needs display group."""
        group = QGroupBox("Your Team Needs (AI Analysis)")
        layout = QVBoxLayout()

        # Group needs by urgency
        critical = [n for n in self._team_needs if n.get("urgency_score", 0) >= 5]
        high = [n for n in self._team_needs if n.get("urgency_score", 0) == 4]
        medium = [n for n in self._team_needs if n.get("urgency_score", 0) == 3]

        if critical:
            critical_text = "🔴 Critical: " + ", ".join([n["position"] for n in critical])
            layout.addWidget(QLabel(critical_text))

        if high:
            high_text = "🟠 High: " + ", ".join([n["position"] for n in high])
            layout.addWidget(QLabel(high_text))

        if medium:
            medium_text = "🟡 Medium: " + ", ".join([n["position"] for n in medium])
            layout.addWidget(QLabel(medium_text))

        group.setLayout(layout)
        return group

    def _create_preview_group(self) -> QGroupBox:
        """Create the preview/explanation group."""
        group = QGroupBox("Preview: What This Means")
        layout = QVBoxLayout()

        self._preview_label = QLabel("Select a strategy to see what it does")
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label)

        group.setLayout(layout)

        # Connect strategy change to update preview
        self._strategy_group.buttonClicked.connect(self._update_preview)

        return group

    def _update_preview(self):
        """Update the preview text based on selected strategy."""
        selected_id = self._strategy_group.checkedId()

        if selected_id == DraftStrategy.BEST_PLAYER_AVAILABLE.value:
            text = ("With BPA strategy:\n"
                   "• AI will always pick the highest-rated prospect\n"
                   "• Ignores team needs completely\n"
                   "• Best for stockpiling talent")
        elif selected_id == DraftStrategy.BALANCED.value:
            text = ("With Balanced strategy:\n"
                   "• AI will prefer prospects that fill team needs\n"
                   "• Still considers overall prospect rating\n"
                   "• Avoids reaching too early")
        elif selected_id == DraftStrategy.NEEDS_BASED.value:
            text = ("With Needs-Based strategy:\n"
                   "• AI will aggressively target critical needs\n"
                   "• Willing to reach for needed positions\n"
                   "• Best when you have glaring holes")
        elif selected_id == DraftStrategy.POSITION_FOCUS.value:
            text = ("With Position Focus strategy:\n"
                   "• AI will ONLY consider your priority positions\n"
                   "• All other positions excluded\n"
                   "• Requires at least 1 priority position set")
        else:
            text = "Select a strategy to see what it does"

        self._preview_label.setText(text)

    def _load_current_direction(self):
        """Load current direction into UI."""
        # Set strategy radio button
        for button in self._strategy_group.buttons():
            if self._strategy_group.id(button) == self._current_direction.strategy.value:
                button.setChecked(True)
                break

        # Set priorities
        for i, position in enumerate(self._current_direction.priority_positions):
            if i < 5:
                self._priority_combos[i].setCurrentText(position)

        # Update preview
        self._update_preview()

    def _use_default(self):
        """Reset to default Balanced strategy."""
        # Find Balanced button and check it
        for button in self._strategy_group.buttons():
            if self._strategy_group.id(button) == DraftStrategy.BALANCED.value:
                button.setChecked(True)
                break

        # Clear priorities
        for combo in self._priority_combos:
            combo.setCurrentIndex(0)  # "None"

        self._update_preview()

    def _save_direction(self):
        """Validate and save the direction."""
        # Get selected strategy
        selected_id = self._strategy_group.checkedId()
        if selected_id == -1:
            QMessageBox.warning(self, "No Strategy", "Please select a draft strategy")
            return

        strategy = DraftStrategy(selected_id)

        # Get priorities
        priorities = []
        for combo in self._priority_combos:
            pos = combo.currentText()
            if pos != "None":
                priorities.append(pos)

        # Create direction
        direction = DraftDirection(
            strategy=strategy,
            priority_positions=priorities,
            watchlist_prospect_ids=self._current_direction.watchlist_prospect_ids  # Preserve
        )

        # Validate
        is_valid, error_msg = direction.validate()
        if not is_valid:
            QMessageBox.warning(self, "Invalid Configuration", error_msg)
            return

        # Emit and close
        self.direction_saved.emit(direction)
        self.accept()
```

---

**File**: `game_cycle_ui/views/draft_view.py` (MODIFY)

```python
# Add signal
draft_direction_changed = Signal(object)  # DraftDirection

# Add instance variable
self._current_direction: Optional[DraftDirection] = None

# Add "Set Strategy" button
self._strategy_btn = QPushButton("⚙️ Set Strategy")
self._strategy_btn.clicked.connect(self._show_draft_direction_dialog)

# Add strategy badge
self._strategy_badge = QLabel("Strategy: Balanced")

# New methods
def _show_draft_direction_dialog(self):
    """Show the draft direction configuration dialog."""
    from game_cycle_ui.dialogs.draft_direction_dialog import DraftDirectionDialog

    # Get team needs for preview
    team_needs = self._get_team_needs()

    dialog = DraftDirectionDialog(
        team_needs=team_needs,
        current_direction=self._current_direction,
        parent=self
    )

    dialog.direction_saved.connect(self._on_direction_saved)
    dialog.exec()

def _on_direction_saved(self, direction: DraftDirection):
    """Handle saved draft direction."""
    self._current_direction = direction
    self.draft_direction_changed.emit(direction)

    # Update badge
    strategy_names = {
        DraftStrategy.BEST_PLAYER_AVAILABLE: "BPA",
        DraftStrategy.BALANCED: "Balanced",
        DraftStrategy.NEEDS_BASED: "Needs-Based",
        DraftStrategy.POSITION_FOCUS: "Position Focus"
    }
    self._strategy_badge.setText(f"Strategy: {strategy_names[direction.strategy]}")

def _get_team_needs(self) -> List[Dict]:
    """Get team needs from backend for preview."""
    # Call TeamNeedsAnalyzer via controller
    return []  # Placeholder
```

---

### Integration Layer

**File**: `game_cycle_ui/controllers/stage_controller.py` (MODIFY)

```python
# Connect signal
draft_view.draft_direction_changed.connect(self._on_draft_direction_changed)

# Handler
def _on_draft_direction_changed(self, direction: DraftDirection):
    """Store draft direction for execution context."""
    self._draft_direction = direction

# Execution context
def _on_simulate_to_pick(self):
    context = {
        "dynasty_id": self._dynasty_id,
        "season": self._season,
        "user_team_id": self._user_team_id,
        "db_path": self._database_path,
        "sim_to_user_pick": True,
        "draft_direction": self._draft_direction  # NEW
    }
    result = self._backend.execute_current_stage(extra_context=context)
```

**File**: `src/game_cycle/handlers/offseason.py` (MODIFY)

```python
def _execute_draft(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
    # Extract direction from context
    draft_direction = context.get("draft_direction")

    # Pass to service
    if context.get("sim_to_user_pick"):
        picks = draft_service.sim_to_user_pick(
            user_team_id=user_team_id,
            draft_direction=draft_direction  # NEW
        )
```

---

## Implementation Plan

### Phase 1: MVP - Basic Strategy Toggle (Week 1-2)

**Estimated Effort**: 12-16 hours

**Goal**: Get 3 basic strategies working (BPA, Balanced, Needs-Based) with simple dialog.

**Tasks**:
1. Create `src/game_cycle/models/draft_direction.py` (3 strategies only)
2. Add `_evaluate_bpa()`, `_evaluate_balanced()`, `_evaluate_needs_based()` to DraftService
3. Add `_evaluate_prospect_with_direction()` dispatcher
4. Modify `process_ai_pick()` to accept `draft_direction` parameter
5. Create simple DraftDirectionDialog (radio buttons only, no priorities)
6. Add "Set Strategy" button to DraftView
7. Add strategy badge to DraftView
8. Connect signal flow: View → Controller → Handler → Service
9. Write 15+ unit tests for strategy evaluation

**Deliverables**:
- 3 working strategies
- Basic UI dialog
- Integration with draft execution
- Comprehensive unit tests

**Success Criteria**:
- Owner can select BPA → AI picks highest overall
- Owner can select Balanced → Current behavior maintained
- Owner can select Needs-Based → AI reaches for needs
- All tests pass

---

### Phase 2: Position Priorities (Week 3)

**Estimated Effort**: 8-12 hours

**Goal**: Add Position Focus strategy and priority system.

**Tasks**:
1. Add `DraftStrategy.POSITION_FOCUS` enum
2. Implement `_evaluate_position_focus()` method
3. Add position priority dropdowns to dialog (5 slots)
4. Add team needs display section to dialog
5. Add priority validation (Position Focus requires ≥1 priority)
6. Update `DraftDirection.priority_positions` field
7. Pre-populate dropdowns with team's top needs
8. Write 10+ additional tests for position focus

**Deliverables**:
- Position Focus strategy working
- Position priority UI functional
- Team needs preview visible
- Validation prevents invalid configs

**Success Criteria**:
- Owner sets priorities [QB, WR, OT] → AI only considers those 3 positions
- Position Focus without priorities → Error message shown
- Team needs display matches AI analysis

---

### Phase 3: Watchlist & Targeting (Week 4)

**Estimated Effort**: 10-14 hours

**Goal**: Add watchlist system for targeting specific prospects.

**Tasks**:
1. Add `DraftDirection.watchlist_prospect_ids` field
2. Add watchlist bonus (+10) to all strategy evaluators
3. Add ⭐ column to prospects table in DraftView
4. Add "Add to Watchlist" button in prospects table
5. Add watchlist section to DraftDirectionDialog
6. Create ProspectBrowserDialog (browse/search all prospects)
7. Visual indicators (⭐ icon) for watchlisted prospects
8. Persist watchlist across dialog reopens (same draft)
9. Write 8+ additional tests for watchlist

**Deliverables**:
- Watchlist bonus working in all strategies
- UI for adding/removing watchlist targets
- Visual feedback in prospects table
- Prospect browser dialog

**Success Criteria**:
- Owner marks QB prospect → AI gets +10 bonus when evaluating
- Watchlist persists when dialog reopened mid-draft
- Visual indicators clear and helpful

---

## File Structure

### New Files (6)

1. `src/game_cycle/models/__init__.py` (10 lines)
2. `src/game_cycle/models/draft_direction.py` (150 lines)
3. `game_cycle_ui/dialogs/draft_direction_dialog.py` (600 lines)
4. `tests/game_cycle/services/test_draft_direction.py` (300 lines)
5. `tests/game_cycle/services/test_draft_with_direction.py` (200 lines)
6. `tests/game_cycle_ui/test_draft_direction_dialog.py` (150 lines)

**Total New**: ~1,410 lines

### Modified Files (5)

1. `src/game_cycle/services/draft_service.py` (+350 lines)
   - Add strategy evaluator methods
   - Modify `process_ai_pick()`, `sim_to_user_pick()`

2. `game_cycle_ui/views/draft_view.py` (+100 lines)
   - Add button, badge, signal, methods

3. `game_cycle_ui/dialogs/__init__.py` (+2 lines)
   - Import DraftDirectionDialog

4. `game_cycle_ui/controllers/stage_controller.py` (+30 lines)
   - Connect signal, pass direction in context

5. `src/game_cycle/handlers/offseason.py` (+10 lines)
   - Extract direction from context

**Total Modified**: ~492 lines

**Grand Total**: ~1,900 lines across 11 files

---

## Testing Strategy

### Unit Tests

**File**: `tests/game_cycle/services/test_draft_direction.py`

```python
def test_bpa_ignores_needs():
    """BPA should ignore team needs completely."""
    service = DraftService(...)

    prospect = {"player_id": 1, "name": "John Smith", "position": "QB", "overall": 75}
    team_needs = [{"position": "QB", "urgency_score": 5}]  # CRITICAL need

    direction = DraftDirection(strategy=DraftStrategy.BEST_PLAYER_AVAILABLE)
    result = service._evaluate_prospect_with_direction(prospect, team_needs, 15, direction)

    assert result.adjusted_score == 75  # No boost
    assert result.strategy_bonus == 0

def test_balanced_applies_need_boost():
    """Balanced should apply +15 for CRITICAL needs."""
    # ... (similar structure)
    assert result.strategy_bonus == 15

def test_needs_based_applies_double_boost():
    """Needs-based should apply +30 for CRITICAL."""
    # ...
    assert result.strategy_bonus == 30

def test_position_focus_excludes_non_priority():
    """Position focus should exclude non-priority positions."""
    direction = DraftDirection(
        strategy=DraftStrategy.POSITION_FOCUS,
        priority_positions=["QB", "WR"]
    )

    cb_prospect = {"position": "CB", "overall": 90}
    result = service._evaluate_prospect_with_direction(cb_prospect, [], 15, direction)

    assert result.adjusted_score == -100  # Excluded

def test_watchlist_applies_bonus_to_all_strategies():
    """Watchlist +10 should work with any strategy."""
    for strategy in DraftStrategy:
        direction = DraftDirection(strategy=strategy, watchlist_prospect_ids=[1])
        result = service._evaluate_prospect_with_direction(prospect, needs, 15, direction)
        assert result.watchlist_bonus == 10
```

### Integration Tests

**File**: `tests/game_cycle/services/test_draft_with_direction.py`

```python
def test_full_draft_with_bpa_strategy():
    """Run full draft with BPA strategy."""
    service = DraftService(...)
    direction = DraftDirection(strategy=DraftStrategy.BEST_PLAYER_AVAILABLE)

    # Simulate entire draft
    for pick in range(1, 225):
        current_pick = service.get_current_pick()
        result = service.process_ai_pick(
            team_id=current_pick["current_team_id"],
            pick_info=current_pick,
            draft_direction=direction
        )

        # Verify highest overall was selected
        available = service.get_available_prospects()
        highest = max(available, key=lambda p: p["overall"])
        assert result["prospect"]["player_id"] == highest["player_id"]

def test_draft_with_position_focus():
    """Verify only priority positions drafted."""
    direction = DraftDirection(
        strategy=DraftStrategy.POSITION_FOCUS,
        priority_positions=["QB", "WR", "OT"]
    )

    # Run draft for user team
    picks = service.sim_to_user_pick(user_team_id=1, draft_direction=direction)

    # Verify all picks are QB/WR/OT only
    for pick in picks:
        assert pick["prospect"]["position"] in ["QB", "WR", "OT"]
```

---

## Success Metrics

### Phase 1 (MVP)
- [ ] 3 strategies functional (BPA, Balanced, Needs-Based)
- [ ] Dialog opens/closes without errors
- [ ] Strategy selection persists during draft
- [ ] 15+ unit tests passing
- [ ] AI picks reflect selected strategy

### Phase 2 (Priorities)
- [ ] Position Focus strategy functional
- [ ] Priority dropdowns work correctly
- [ ] Team needs display accurate
- [ ] Validation prevents invalid configs
- [ ] 10+ additional tests passing

### Phase 3 (Watchlist)
- [ ] Watchlist bonus applies correctly
- [ ] UI for adding/removing targets works
- [ ] Visual indicators clear
- [ ] Prospect browser functional
- [ ] 8+ additional tests passing

**Overall Success**: Owner has full control over draft strategy, AI executes based on preferences, feature feels natural within existing offseason flow.

---

## Migration to Milestone Document

**Recommended Location**: `docs/09_MILESTONE_Draft_Direction/`

**Files to Create**:
1. `docs/09_MILESTONE_Draft_Direction/PLAN.md` (this document)
2. `docs/09_MILESTONE_Draft_Direction/IMPLEMENTATION_NOTES.md` (track progress)
3. `docs/09_MILESTONE_Draft_Direction/TESTING_CHECKLIST.md` (QA checklist)

**Update**: `docs/DEVELOPMENT_PRIORITIES.md` - Add Milestone 9 to roadmap

---

## Dependencies

**Required Milestones (Complete)**:
- ✅ Milestone 1: Game Cycle
- ✅ Milestone 6: Trade System (uses draft picks)

**Recommended Order**:
1. Milestone 9 (Draft Direction) ← This feature
2. Milestone 10: Advanced Analytics (use draft data)

**No Blocking Dependencies** - Can start immediately

---

## Risk Assessment

### Low Risk
- Extends existing draft service (not rewriting)
- Follows established patterns (re-signing, franchise tag)
- No database migrations needed
- Backwards compatible (default Balanced = current behavior)

### Medium Risk
- Strategy evaluation logic complexity (4 different algorithms)
- UI complexity (dialog with multiple sections)
- Testing coverage (need comprehensive tests for all strategies)

### Mitigation
- Start with MVP (3 strategies only)
- Extensive unit testing (each strategy in isolation)
- Manual QA for each phase
- Rollback plan: Remove feature flag, system falls back to Balanced

---

## Rollback Plan

If feature causes issues:

1. **Immediate**: Set all users to `DraftStrategy.BALANCED` (current behavior)
2. **Short-term**: Hide "Set Strategy" button in UI (feature disabled)
3. **Long-term**: Remove direction parameter from service methods (restore original code)

**Data Loss**: None (no database persistence)
**User Impact**: Minimal (falls back to current behavior)

---

## Appendix: Alternative Approaches Considered

### Alternative 1: Database Persistence
**Approach**: Store draft direction in `draft_strategies` table.

**Pros**: Can analyze historical strategy choices, persist across sessions

**Cons**: Overkill for ephemeral context, adds cleanup logic, more complex

**Decision**: REJECTED - Ephemeral context passing is simpler

---

### Alternative 2: Per-Round Strategies
**Approach**: Allow different strategy for each of 7 rounds.

**Pros**: Maximum flexibility (BPA in R1, Needs-Based in R3-5)

**Cons**: Decision fatigue, complex UI, hard to predict AI behavior

**Decision**: REJECTED - Single strategy with mid-draft adjustment is sufficient

---

### Alternative 3: AI Recommendations
**Approach**: AI suggests strategy changes mid-draft based on board state.

**Pros**: Helps inexperienced users, dynamic optimization

**Cons**: Interrupts flow, may confuse users, "too smart" AI

**Decision**: DEFERRED - Could add in Phase 4 as optional hints

---

**End of Plan**
