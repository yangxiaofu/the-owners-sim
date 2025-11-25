# DraftDialogController Specification

## Document Information
- **Version**: 1.0
- **Date**: 2025-11-23
- **Author**: Controller Architecture Specialist (Phase 2 Agent)
- **Status**: Implementation Ready

## Overview

The `DraftDialogController` is a production UI controller that mediates between the `DraftDayDialog` (UI layer) and the draft business logic (`DraftManager`, database APIs). It follows the thin controller pattern (≤10-20 lines per method) with business logic delegated to domain services.

**File Location**: `ui/controllers/draft_dialog_controller.py`

**Design Pattern**: MVC with domain model delegation
```
DraftDayDialog (View)
    ↓
DraftDialogController (Controller - orchestration only)
    ↓
DraftManager + Database APIs (Domain/Business Logic)
```

## Architecture Comparison

### Demo Controller vs Production Controller

| Aspect | DraftDemoController (demo/) | DraftDialogController (ui/) |
|--------|----------------------------|----------------------------|
| **Purpose** | Standalone demo/testing | Production UI integration |
| **Location** | `demo/draft_day_demo/` | `ui/controllers/` |
| **State Management** | In-memory only | Database-backed (DynastyStateAPI) |
| **Resumability** | None | Full save/resume support |
| **Dynasty Isolation** | Partial | Complete |
| **Error Handling** | Basic | Production-grade with fail-loud |
| **Dependencies** | DraftManager + APIs | DraftManager + DynastyStateAPI + APIs |

### Key Differences

**DraftDemoController**:
- Designed for standalone demo usage
- No integration with dynasty state
- No resume capability
- Simpler error handling

**DraftDialogController** (this spec):
- Designed for main UI integration
- Persists draft progress to database
- Supports save/resume across sessions
- Comprehensive error handling
- Integrates with calendar/event system

## Class Structure

### Full Class Definition

```python
"""
Draft Dialog Controller

Business logic controller for interactive NFL draft day dialog.
Orchestrates draft operations between UI and backend systems.

Architecture:
- Thin controller pattern (≤10-20 lines per method)
- Delegates business logic to DraftManager
- Persists state via DynastyStateAPI
- Ensures dynasty isolation throughout

Responsibilities:
- Draft order and prospect retrieval
- User pick execution validation
- AI pick simulation orchestration
- Draft progress persistence
- State recovery for resume capability
"""

from typing import Optional, List, Dict, Any
import logging
from PySide6.QtCore import QObject, Signal

# Business logic imports
from src.database.draft_class_api import DraftClassAPI
from src.database.draft_order_database_api import DraftOrderDatabaseAPI, DraftPick
from src.database.dynasty_state_api import DynastyStateAPI
from src.offseason.draft_manager import DraftManager
from src.offseason.team_needs_analyzer import TeamNeedsAnalyzer
from src.team_management.teams.team_loader import TeamDataLoader


class DraftDialogController(QObject):
    """
    Controller for draft day dialog business logic.

    Manages draft flow, prospect evaluation, and pick execution for both
    user-controlled and AI-controlled teams. Integrates with dynasty state
    for resumable draft sessions.

    Features:
    - Draft order tracking (1-262 picks, 7 rounds)
    - Available prospect retrieval with filtering
    - Team needs analysis integration
    - User pick execution with validation
    - AI pick simulation with needs-based evaluation
    - Pick history tracking
    - Save/resume draft state

    Signals:
        pick_executed: Emitted after successful pick (pick_number, player_id, team_id)
        draft_completed: Emitted when all 262 picks executed
        error_occurred: Emitted on operation failure (error_message)
    """

    # Qt signals for UI updates
    pick_executed = Signal(int, int, int)  # (pick_number, player_id, team_id)
    draft_completed = Signal()
    error_occurred = Signal(str)  # (error_message)

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        user_team_id: int
    ):
        """
        Initialize draft dialog controller.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Dynasty identifier for isolation
            season_year: Draft season year (e.g., 2025)
            user_team_id: User's team ID (1-32)

        Raises:
            ValueError: If draft order or draft class not found
        """

    def load_draft_data(self) -> Dict[str, Any]:
        """
        Load draft order and draft class from database.

        Retrieves complete draft order (262 picks) and available prospects,
        then determines current pick position from dynasty state.

        Returns:
            Dict containing:
            {
                'draft_order': List[DraftPick],
                'total_picks': int,
                'current_pick_index': int,
                'prospects_available': int
            }

        Raises:
            ValueError: If draft order or draft class not found
        """

    def get_current_pick(self) -> Optional[Dict[str, Any]]:
        """
        Get current pick information.

        Returns:
            Dict with pick details, or None if draft is complete:
            {
                'round': int,
                'pick_in_round': int,
                'overall_pick': int,
                'team_id': int,
                'team_name': str,
                'is_user_pick': bool,
                'pick_id': int
            }
        """

    def get_available_prospects(
        self,
        limit: int = 100,
        position_filter: Optional[str] = None,
        sort_by: str = "overall"
    ) -> List[Dict[str, Any]]:
        """
        Get available (undrafted) prospects with optional filtering.

        Args:
            limit: Maximum prospects to return (default 100)
            position_filter: Optional position filter (e.g., "QB", "WR")
            sort_by: Sort field ("overall", "projected_pick_min", "position")

        Returns:
            List of prospect dicts sorted by specified field:
            [
                {
                    'player_id': int,
                    'first_name': str,
                    'last_name': str,
                    'position': str,
                    'overall': int,
                    'college': str,
                    'age': int,
                    'projected_pick_min': int,
                    'projected_pick_max': int,
                    ...
                },
                ...
            ]
        """

    def get_team_needs(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get team needs sorted by urgency.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of need dicts sorted by urgency (CRITICAL → LOW):
            [
                {
                    'position': str,
                    'urgency': NeedUrgency,
                    'urgency_score': int,
                    'starter_overall': int,
                    'depth_count': int,
                    'avg_depth_overall': float,
                    'reason': str
                },
                ...
            ]
        """

    def execute_user_pick(self, player_id: int) -> Dict[str, Any]:
        """
        Execute user's draft pick.

        Validates pick ownership, executes via DraftManager, updates database,
        advances to next pick, and emits signals.

        Args:
            player_id: Player ID of prospect to draft

        Returns:
            Dict with pick result:
            {
                'success': bool,
                'player_id': int,
                'player_name': str,
                'position': str,
                'overall': int,
                'round': int,
                'pick': int,
                'overall_pick': int,
                'team_id': int,
                'team_name': str,
                'college': str,
                'message': str  # (if success=False)
            }

        Raises:
            ValueError: If not user's pick or player not available
        """

    def execute_ai_pick(self) -> Dict[str, Any]:
        """
        Execute AI team's draft pick using needs-based evaluation.

        Uses DraftManager's prospect evaluation to score all available
        prospects based on team needs and selects highest-scoring player.

        Returns:
            Dict with pick result:
            {
                'success': bool,
                'player_id': int,
                'player_name': str,
                'position': str,
                'overall': int,
                'round': int,
                'pick': int,
                'overall_pick': int,
                'team_id': int,
                'team_name': str,
                'college': str,
                'needs_match': str,
                'eval_score': float
            }

        Raises:
            ValueError: If current pick belongs to user or no prospects available
        """

    def get_pick_history(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Get recent draft picks (most recent first).

        Args:
            limit: Maximum number of picks to return (default 15)

        Returns:
            List of executed pick dicts (most recent first):
            [
                {
                    'round': int,
                    'pick': int,
                    'overall_pick': int,
                    'team_id': int,
                    'team_name': str,
                    'player_id': int,
                    'player_name': str,
                    'position': str,
                    'overall': int,
                    'college': str
                },
                ...
            ]
        """

    def is_draft_complete(self) -> bool:
        """
        Check if draft is complete.

        Returns:
            True if all 262 picks have been executed
        """

    def get_draft_progress(self) -> Dict[str, Any]:
        """
        Get overall draft progress.

        Returns:
            Dict with draft progress info:
            {
                'picks_completed': int,
                'picks_remaining': int,
                'total_picks': int,
                'completion_pct': float,
                'current_round': int,
                'is_complete': bool
            }
        """

    def save_draft_state(self) -> bool:
        """
        Save current draft state to database.

        Persists current pick index and draft-in-progress flag to dynasty_state
        table for resume capability.

        Returns:
            True if save successful, False otherwise

        Raises:
            RuntimeError: If database write fails (fail-loud)
        """

    def load_draft_state(self) -> Dict[str, Any]:
        """
        Load saved draft state from database.

        Retrieves current pick index and draft status from dynasty_state table.
        Returns default values if no saved state exists (new draft).

        Returns:
            Dict with saved state:
            {
                'current_pick_index': int,
                'draft_in_progress': bool,
                'last_saved': str  # ISO timestamp
            }
        """
```

## Method Implementation Details

### 1. `__init__()`

**Purpose**: Initialize controller with database connections and load draft order

**Estimated LOC**: 15-18 lines

**Pseudocode**:
```python
def __init__(self, database_path, dynasty_id, season_year, user_team_id):
    super().__init__()

    # Store parameters
    self.db_path = database_path
    self.dynasty_id = dynasty_id
    self.season = season_year
    self.user_team_id = user_team_id

    # Initialize logger
    self.logger = logging.getLogger(__name__)

    # Initialize database APIs
    self.draft_api = DraftClassAPI(db_path)
    self.draft_order_api = DraftOrderDatabaseAPI(db_path)
    self.dynasty_state_api = DynastyStateAPI(db_path)
    self.needs_analyzer = TeamNeedsAnalyzer(db_path, dynasty_id)
    self.team_loader = TeamDataLoader()

    # Initialize DraftManager (business logic)
    self.draft_manager = DraftManager(
        database_path=db_path,
        dynasty_id=dynasty_id,
        season_year=season_year,
        enable_persistence=True
    )

    # Load draft order from database
    self.draft_order = self._load_draft_order()

    # Load saved draft state (resume support)
    state = self.load_draft_state()
    self.current_pick_index = state['current_pick_index']

    # Validate draft class exists
    if not self.draft_api.dynasty_has_draft_class(dynasty_id, season_year):
        raise ValueError(
            f"No draft class found for dynasty '{dynasty_id}', season {season_year}"
        )

    self.logger.info(
        f"Initialized DraftDialogController: dynasty={dynasty_id}, "
        f"season={season_year}, user_team={user_team_id}, "
        f"current_pick={self.current_pick_index}"
    )
```

**Error Handling**:
- Raises `ValueError` if draft order not found
- Raises `ValueError` if draft class not found
- Logs initialization details for debugging

---

### 2. `load_draft_data()`

**Purpose**: Load complete draft data for initial dialog setup

**Estimated LOC**: 12-15 lines

**Pseudocode**:
```python
def load_draft_data(self):
    # Get draft order (already loaded in __init__)
    draft_order = self.draft_order

    # Get available prospects count
    prospects = self.draft_api.get_all_prospects(
        dynasty_id=self.dynasty_id,
        season=self.season,
        available_only=True
    )

    # Load current pick state
    state = self.load_draft_state()

    self.logger.info(
        f"Loaded draft data: {len(draft_order)} picks, "
        f"{len(prospects)} prospects available"
    )

    return {
        'draft_order': draft_order,
        'total_picks': len(draft_order),
        'current_pick_index': state['current_pick_index'],
        'prospects_available': len(prospects)
    }
```

**Error Handling**:
- Raises `ValueError` if draft order empty
- Logs data loading for debugging

---

### 3. `get_current_pick()`

**Purpose**: Retrieve current pick information for UI display

**Estimated LOC**: 10-12 lines

**Pseudocode**:
```python
def get_current_pick(self):
    # Check if draft complete
    if self.current_pick_index >= len(self.draft_order):
        return None

    # Get current pick object
    pick = self.draft_order[self.current_pick_index]

    # Get team name
    team = self.team_loader.get_team_by_id(pick.current_team_id)
    team_name = team.full_name if team else f"Team {pick.current_team_id}"

    return {
        'round': pick.round_number,
        'pick_in_round': pick.pick_in_round,
        'overall_pick': pick.overall_pick,
        'team_id': pick.current_team_id,
        'team_name': team_name,
        'is_user_pick': pick.current_team_id == self.user_team_id,
        'pick_id': pick.pick_id
    }
```

**Error Handling**:
- Returns `None` if draft complete (graceful)
- Handles missing team data with fallback

---

### 4. `get_available_prospects()`

**Purpose**: Retrieve available prospects with filtering and sorting

**Estimated LOC**: 10-12 lines

**Pseudocode**:
```python
def get_available_prospects(self, limit=100, position_filter=None, sort_by="overall"):
    # Delegate to DraftClassAPI
    prospects = self.draft_api.get_all_prospects(
        dynasty_id=self.dynasty_id,
        season=self.season,
        available_only=True
    )

    # Apply position filter if specified
    if position_filter:
        prospects = [p for p in prospects if p['position'] == position_filter]

    # Sort by specified field (descending for overall/ratings)
    reverse = sort_by in ["overall", "projected_pick_min"]
    prospects.sort(key=lambda p: p.get(sort_by, 0), reverse=reverse)

    # Return top N
    return prospects[:limit]
```

**Error Handling**:
- Handles invalid sort_by field gracefully (defaults to 0)
- Returns empty list if no prospects available

---

### 5. `get_team_needs()`

**Purpose**: Retrieve team needs for prospect evaluation

**Estimated LOC**: 5-7 lines

**Pseudocode**:
```python
def get_team_needs(self, team_id):
    # Delegate to TeamNeedsAnalyzer
    needs = self.needs_analyzer.analyze_team_needs(
        team_id=team_id,
        season=self.season,
        include_future_contracts=True
    )

    return needs  # Already sorted by urgency (CRITICAL → LOW)
```

**Error Handling**:
- Returns empty list if team has no needs
- Logs team needs for debugging

---

### 6. `execute_user_pick()`

**Purpose**: Execute user's draft pick with validation and state persistence

**Estimated LOC**: 18-20 lines

**Pseudocode**:
```python
def execute_user_pick(self, player_id):
    # Get current pick
    current_pick = self.get_current_pick()
    if not current_pick:
        raise ValueError("Draft is complete, no picks remaining")

    # Validate it's user's pick
    if not current_pick['is_user_pick']:
        raise ValueError(
            f"Not user's pick. Current pick belongs to {current_pick['team_name']}"
        )

    # Verify player is available
    prospect = self.draft_api.get_prospect_by_id(player_id, self.dynasty_id)
    if not prospect or prospect['is_drafted']:
        raise ValueError(f"Prospect {player_id} not available")

    # Execute pick via DraftManager
    pick_obj = self.draft_order[self.current_pick_index]
    result = self.draft_manager.make_draft_selection(
        round_num=pick_obj.round_number,
        pick_num=pick_obj.pick_in_round,
        player_id=player_id,
        team_id=pick_obj.current_team_id
    )

    # Update draft order state
    self.draft_order_api.mark_pick_executed(pick_obj.pick_id, player_id)
    self.draft_order[self.current_pick_index].is_executed = True
    self.draft_order[self.current_pick_index].player_id = player_id

    # Advance to next pick
    self.current_pick_index += 1

    # Save state to database
    self.save_draft_state()

    # Emit signal
    self.pick_executed.emit(pick_obj.overall_pick, player_id, pick_obj.current_team_id)

    # Check if draft complete
    if self.is_draft_complete():
        self.draft_completed.emit()

    # Get team name
    team = self.team_loader.get_team_by_id(pick_obj.current_team_id)
    team_name = team.full_name if team else f"Team {pick_obj.current_team_id}"

    return {
        'success': True,
        'player_id': player_id,
        'player_name': f"{prospect['first_name']} {prospect['last_name']}",
        'position': prospect['position'],
        'overall': prospect['overall'],
        'round': pick_obj.round_number,
        'pick': pick_obj.pick_in_round,
        'overall_pick': pick_obj.overall_pick,
        'team_id': pick_obj.current_team_id,
        'team_name': team_name,
        'college': prospect.get('college', 'Unknown')
    }
```

**Error Handling**:
- Raises `ValueError` for validation failures
- Emits `error_occurred` signal on database errors
- Logs pick execution for debugging

---

### 7. `execute_ai_pick()`

**Purpose**: Execute AI team's pick using needs-based evaluation

**Estimated LOC**: 18-20 lines (similar to execute_user_pick)

**Pseudocode**:
```python
def execute_ai_pick(self):
    # Get current pick
    current_pick = self.get_current_pick()
    if not current_pick:
        raise ValueError("Draft is complete, no picks remaining")

    # Validate it's AI's pick
    if current_pick['is_user_pick']:
        raise ValueError("Current pick belongs to user, not AI")

    pick_obj = self.draft_order[self.current_pick_index]
    team_id = pick_obj.current_team_id

    # Get available prospects and team needs
    available_prospects = self.get_available_prospects(limit=500)
    team_needs = self.get_team_needs(team_id)

    # Evaluate prospects using DraftManager's AI
    best_prospect = None
    best_score = -1

    for prospect in available_prospects:
        score = self.draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=team_needs,
            pick_position=pick_obj.overall_pick
        )
        if score > best_score:
            best_score = score
            best_prospect = prospect

    if not best_prospect:
        raise ValueError("No suitable prospect found for AI team")

    player_id = best_prospect['player_id']

    # Execute pick via DraftManager
    result = self.draft_manager.make_draft_selection(
        round_num=pick_obj.round_number,
        pick_num=pick_obj.pick_in_round,
        player_id=player_id,
        team_id=team_id
    )

    # Update draft order state (same as user pick)
    self.draft_order_api.mark_pick_executed(pick_obj.pick_id, player_id)
    self.draft_order[self.current_pick_index].is_executed = True
    self.draft_order[self.current_pick_index].player_id = player_id

    # Advance to next pick
    self.current_pick_index += 1

    # Save state
    self.save_draft_state()

    # Emit signal
    self.pick_executed.emit(pick_obj.overall_pick, player_id, team_id)

    # Check completion
    if self.is_draft_complete():
        self.draft_completed.emit()

    # Get team name
    team = self.team_loader.get_team_by_id(team_id)
    team_name = team.full_name if team else f"Team {team_id}"

    # Determine needs match
    needs_match = "NONE"
    for need in team_needs:
        if need['position'] == best_prospect['position']:
            needs_match = need['urgency'].name
            break

    return {
        'success': True,
        'player_id': player_id,
        'player_name': f"{best_prospect['first_name']} {best_prospect['last_name']}",
        'position': best_prospect['position'],
        'overall': best_prospect['overall'],
        'round': pick_obj.round_number,
        'pick': pick_obj.pick_in_round,
        'overall_pick': pick_obj.overall_pick,
        'team_id': team_id,
        'team_name': team_name,
        'college': best_prospect.get('college', 'Unknown'),
        'needs_match': needs_match,
        'eval_score': round(best_score, 1)
    }
```

**Error Handling**:
- Raises `ValueError` for validation failures
- Emits `error_occurred` signal on database errors
- Logs AI pick evaluation details

---

### 8. `get_pick_history()`

**Purpose**: Retrieve recent draft picks for UI history display

**Estimated LOC**: 12-15 lines

**Pseudocode**:
```python
def get_pick_history(self, limit=15):
    executed_picks = []

    # Iterate backwards from current pick (most recent first)
    for idx in range(self.current_pick_index - 1, -1, -1):
        if len(executed_picks) >= limit:
            break

        pick = self.draft_order[idx]

        if not pick.is_executed or not pick.player_id:
            continue

        # Get prospect info
        prospect = self.draft_api.get_prospect_by_id(pick.player_id, self.dynasty_id)
        if not prospect:
            continue

        # Get team name
        team = self.team_loader.get_team_by_id(pick.current_team_id)
        team_name = team.full_name if team else f"Team {pick.current_team_id}"

        executed_picks.append({
            'round': pick.round_number,
            'pick': pick.pick_in_round,
            'overall_pick': pick.overall_pick,
            'team_id': pick.current_team_id,
            'team_name': team_name,
            'player_id': pick.player_id,
            'player_name': f"{prospect['first_name']} {prospect['last_name']}",
            'position': prospect['position'],
            'overall': prospect['overall'],
            'college': prospect.get('college', 'Unknown')
        })

    return executed_picks
```

**Error Handling**:
- Skips picks with missing prospect data
- Returns empty list if no picks executed

---

### 9. `is_draft_complete()`

**Purpose**: Check if all picks have been executed

**Estimated LOC**: 2-3 lines

**Pseudocode**:
```python
def is_draft_complete(self):
    return self.current_pick_index >= len(self.draft_order)
```

---

### 10. `get_draft_progress()`

**Purpose**: Calculate overall draft progress for UI display

**Estimated LOC**: 10-12 lines

**Pseudocode**:
```python
def get_draft_progress(self):
    total_picks = len(self.draft_order)
    picks_completed = self.current_pick_index
    picks_remaining = total_picks - picks_completed

    current_pick = self.get_current_pick()
    current_round = current_pick['round'] if current_pick else 7

    completion_pct = (picks_completed / total_picks * 100) if total_picks > 0 else 0

    return {
        'picks_completed': picks_completed,
        'picks_remaining': picks_remaining,
        'total_picks': total_picks,
        'completion_pct': round(completion_pct, 1),
        'current_round': current_round,
        'is_complete': self.is_draft_complete()
    }
```

---

### 11. `save_draft_state()`

**Purpose**: Persist current draft state to database (fail-loud)

**Estimated LOC**: 8-10 lines

**Pseudocode**:
```python
def save_draft_state(self):
    try:
        # Delegate to DynastyStateAPI
        self.dynasty_state_api.update_draft_state(
            dynasty_id=self.dynasty_id,
            current_pick_index=self.current_pick_index,
            draft_in_progress=not self.is_draft_complete()
        )

        self.logger.debug(
            f"Draft state saved: pick={self.current_pick_index}, "
            f"complete={self.is_draft_complete()}"
        )

        return True

    except Exception as e:
        self.logger.error(f"Failed to save draft state: {e}", exc_info=True)
        self.error_occurred.emit(f"Failed to save draft state: {str(e)}")
        raise RuntimeError(f"Draft state persistence failed: {e}")
```

**Error Handling**:
- Raises `RuntimeError` on database failure (fail-loud)
- Emits `error_occurred` signal for UI notification
- Logs error details for debugging

---

### 12. `load_draft_state()`

**Purpose**: Load saved draft state from database

**Estimated LOC**: 8-10 lines

**Pseudocode**:
```python
def load_draft_state(self):
    try:
        # Delegate to DynastyStateAPI
        state = self.dynasty_state_api.get_draft_state(self.dynasty_id)

        return {
            'current_pick_index': state.get('current_pick_index', 0),
            'draft_in_progress': state.get('draft_in_progress', False),
            'last_saved': state.get('last_updated', '')
        }

    except Exception as e:
        self.logger.warning(f"Failed to load draft state: {e}")
        # Return defaults for new draft
        return {
            'current_pick_index': 0,
            'draft_in_progress': False,
            'last_saved': ''
        }
```

**Error Handling**:
- Returns default values on failure (graceful degradation)
- Logs warning for debugging

---

### 13. `_load_draft_order()` (Private Helper)

**Purpose**: Load complete draft order from database

**Estimated LOC**: 8-10 lines

**Pseudocode**:
```python
def _load_draft_order(self):
    # Delegate to DraftOrderDatabaseAPI
    draft_order = self.draft_order_api.get_draft_order(
        dynasty_id=self.dynasty_id,
        season=self.season
    )

    if not draft_order:
        raise ValueError(
            f"No draft order found for dynasty '{self.dynasty_id}', "
            f"season {self.season}. Generate draft order first."
        )

    self.logger.info(f"Loaded {len(draft_order)} draft picks")
    return draft_order
```

**Error Handling**:
- Raises `ValueError` if draft order not found
- Logs draft order size

---

## Dependencies

### Required Imports

```python
from typing import Optional, List, Dict, Any
import logging
from PySide6.QtCore import QObject, Signal

# Database APIs
from src.database.draft_class_api import DraftClassAPI
from src.database.draft_order_database_api import DraftOrderDatabaseAPI, DraftPick
from src.database.dynasty_state_api import DynastyStateAPI

# Business logic
from src.offseason.draft_manager import DraftManager
from src.offseason.team_needs_analyzer import TeamNeedsAnalyzer

# Utilities
from src.team_management.teams.team_loader import TeamDataLoader
```

### Database API Integration Points

| API | Methods Used | Purpose |
|-----|-------------|---------|
| **DraftClassAPI** | `dynasty_has_draft_class()`, `get_all_prospects()`, `get_prospect_by_id()` | Prospect retrieval and validation |
| **DraftOrderDatabaseAPI** | `get_draft_order()`, `mark_pick_executed()` | Draft order loading and pick tracking |
| **DynastyStateAPI** | `update_draft_state()`, `get_draft_state()` | Draft progress persistence |
| **DraftManager** | `make_draft_selection()`, `_evaluate_prospect()` | Pick execution and AI evaluation |
| **TeamNeedsAnalyzer** | `analyze_team_needs()` | Team needs for prospect evaluation |
| **TeamDataLoader** | `get_team_by_id()` | Team name lookup |

---

## Error Handling Strategy

### Error Categories

**1. Validation Errors** (raise `ValueError`):
- Draft order not found
- Draft class not found
- Player not available
- Invalid pick ownership (user vs AI)

**2. Persistence Errors** (raise `RuntimeError`, fail-loud):
- Database write failures
- State save failures
- Transaction conflicts

**3. Recovery Errors** (graceful degradation):
- Missing team data (fallback to "Team X")
- Failed state load (default to pick 0)
- Missing prospect details (skip in history)

### Signal Emissions

```python
# Success signals
self.pick_executed.emit(pick_number, player_id, team_id)
self.draft_completed.emit()

# Error signal
self.error_occurred.emit("Failed to execute pick: Database locked")
```

---

## State Persistence Design

### Dynasty State Schema

**New columns in `dynasty_state` table**:
```sql
ALTER TABLE dynasty_state ADD COLUMN current_draft_pick INTEGER DEFAULT 0;
ALTER TABLE dynasty_state ADD COLUMN draft_in_progress BOOLEAN DEFAULT FALSE;
```

### Persistence Flow

```
User makes pick
  → execute_user_pick()
    → DraftManager.make_draft_selection()
      → Update draft_order table (mark_pick_executed)
      → Update draft_prospects table (mark_prospect_drafted)
      → Create player record + rookie contract
    → Advance current_pick_index
    → save_draft_state()
      → DynastyStateAPI.update_draft_state()
        → UPDATE dynasty_state SET current_draft_pick=X, draft_in_progress=TRUE
    → Emit pick_executed signal
```

### Resume Flow

```
Dialog reopens
  → __init__()
    → load_draft_state()
      → DynastyStateAPI.get_draft_state()
        → SELECT current_draft_pick, draft_in_progress FROM dynasty_state
    → Set self.current_pick_index = loaded_value
  → Dialog displays "Pick X of 262"
```

---

## Performance Considerations

### Database Operations

**Per-Pick Overhead**:
- 1 SELECT (get prospect)
- 1 UPDATE (mark pick executed)
- 1 INSERT (create player record)
- 1 INSERT (create rookie contract)
- 1 UPDATE (save draft state)
- **Total: 5 database operations per pick**

**Optimization**: Transaction batching not applicable (need state saved after each pick for resume)

**Mitigation**: Use `IMMEDIATE` transaction mode to prevent lock contention

### Memory Footprint

**Loaded Data**:
- Draft order: 262 DraftPick objects (~50 KB)
- Available prospects: 300 prospect dicts (~150 KB)
- Pick history: 15 pick dicts (~5 KB)
- **Total: ~205 KB in memory**

**Optimization**: No lazy loading needed (dataset small enough)

---

## Testing Checkpoints

### Unit Tests

**File**: `tests/ui/test_draft_dialog_controller.py`

**Test Coverage**:
```python
# Initialization tests
def test_init_loads_draft_order()
def test_init_raises_if_no_draft_order()
def test_init_raises_if_no_draft_class()
def test_init_loads_saved_state()

# Data retrieval tests
def test_load_draft_data_returns_complete_data()
def test_get_current_pick_returns_correct_pick()
def test_get_current_pick_returns_none_when_complete()
def test_get_available_prospects_filters_by_position()
def test_get_team_needs_returns_sorted_needs()

# Pick execution tests
def test_execute_user_pick_success()
def test_execute_user_pick_validates_ownership()
def test_execute_user_pick_validates_availability()
def test_execute_user_pick_advances_index()
def test_execute_user_pick_emits_signals()
def test_execute_ai_pick_uses_needs_evaluation()

# State persistence tests
def test_save_draft_state_persists_to_database()
def test_save_draft_state_raises_on_failure()
def test_load_draft_state_returns_saved_values()
def test_load_draft_state_returns_defaults_on_failure()

# Progress tracking tests
def test_get_draft_progress_calculates_correctly()
def test_is_draft_complete_returns_true_at_262()
def test_get_pick_history_returns_recent_picks()
```

---

## Common Pitfalls to Avoid

### 1. **Not Validating Pick Ownership**
❌ **Bad**:
```python
def execute_user_pick(self, player_id):
    # Missing validation!
    result = self.draft_manager.make_draft_selection(...)
```

✅ **Good**:
```python
def execute_user_pick(self, player_id):
    current_pick = self.get_current_pick()
    if not current_pick['is_user_pick']:
        raise ValueError("Not user's pick")
    # ... proceed with pick
```

### 2. **Not Saving State After Each Pick**
❌ **Bad**:
```python
def execute_user_pick(self, player_id):
    # Execute pick
    self.current_pick_index += 1
    # State NOT saved - data loss on crash!
```

✅ **Good**:
```python
def execute_user_pick(self, player_id):
    # Execute pick
    self.current_pick_index += 1
    self.save_draft_state()  # Always save after advancing!
```

### 3. **Silent Failure on Database Errors**
❌ **Bad**:
```python
def save_draft_state(self):
    try:
        self.dynasty_state_api.update_draft_state(...)
    except Exception as e:
        return False  # Silent failure!
```

✅ **Good**:
```python
def save_draft_state(self):
    try:
        self.dynasty_state_api.update_draft_state(...)
    except Exception as e:
        self.error_occurred.emit(str(e))
        raise RuntimeError(f"Draft state persistence failed: {e}")
```

### 4. **Not Emitting Signals**
❌ **Bad**:
```python
def execute_user_pick(self, player_id):
    # Execute pick
    self.current_pick_index += 1
    return result  # UI won't update!
```

✅ **Good**:
```python
def execute_user_pick(self, player_id):
    # Execute pick
    self.current_pick_index += 1
    self.pick_executed.emit(pick_number, player_id, team_id)  # UI updates!
    return result
```

### 5. **Thick Controller Anti-Pattern**
❌ **Bad**:
```python
def execute_user_pick(self, player_id):
    # Controller doing business logic!
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE draft_prospects SET is_drafted=1 WHERE player_id=?", ...)
    cursor.execute("INSERT INTO players VALUES (?, ?, ...)", ...)
    # 50+ lines of SQL logic...
```

✅ **Good**:
```python
def execute_user_pick(self, player_id):
    # Delegate to DraftManager (business logic)
    result = self.draft_manager.make_draft_selection(...)
    # Controller only orchestrates and emits signals
    self.pick_executed.emit(...)
```

---

## Integration with DraftDayDialog

### Signal/Slot Connections

```python
# In DraftDayDialog.__init__()
self.controller = DraftDialogController(...)

# Connect controller signals
self.controller.pick_executed.connect(self._on_pick_executed)
self.controller.draft_completed.connect(self._on_draft_completed)
self.controller.error_occurred.connect(self._on_error)

# User makes pick
def _on_make_pick_button_clicked(self):
    player_id = self._get_selected_player_id()
    result = self.controller.execute_user_pick(player_id)
    # UI updates via signal emission
```

### Data Flow

```
DraftDayDialog (View)
    ↓
[User clicks "Make Pick"]
    ↓
DraftDialogController.execute_user_pick(player_id)
    ↓
DraftManager.make_draft_selection()
    ↓
Database APIs (DraftOrderDatabaseAPI, DraftClassAPI, PlayerRosterAPI, ContractManager)
    ↓
DraftDialogController emits pick_executed signal
    ↓
DraftDayDialog._on_pick_executed() updates UI
```

---

## Estimated Implementation Effort

**Total Estimated LOC**: ~200-220 lines (excluding imports and docstrings)

**Breakdown by Method**:
- `__init__()`: 18 lines
- `load_draft_data()`: 15 lines
- `get_current_pick()`: 12 lines
- `get_available_prospects()`: 12 lines
- `get_team_needs()`: 7 lines
- `execute_user_pick()`: 20 lines
- `execute_ai_pick()`: 20 lines
- `get_pick_history()`: 15 lines
- `is_draft_complete()`: 3 lines
- `get_draft_progress()`: 12 lines
- `save_draft_state()`: 10 lines
- `load_draft_state()`: 10 lines
- `_load_draft_order()`: 10 lines

**Implementation Time**: 3-4 hours (including docstrings and testing)

---

## References

**Related Documentation**:
- `docs/project/nfl_draft_event/architecture.md` - System architecture
- `docs/project/nfl_draft_event/requirements.md` - Functional requirements
- `docs/architecture/ui_layer_separation.md` - MVC pattern guidelines
- `demo/draft_day_demo/draft_demo_controller.py` - Demo controller reference

**Related Code**:
- `src/offseason/draft_manager.py` - Business logic
- `src/database/draft_order_database_api.py` - Draft order API
- `src/database/draft_class_api.py` - Draft class API
- `src/database/dynasty_state_api.py` - State persistence
- `ui/controllers/simulation_controller.py` - Production controller pattern

---

**Document Version**: 1.0
**Last Updated**: 2025-11-23
**Author**: Controller Architecture Specialist
