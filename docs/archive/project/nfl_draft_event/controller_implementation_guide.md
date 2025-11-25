# DraftDialogController Implementation Guide

## Document Information
- **Version**: 1.0
- **Date**: 2025-11-23
- **Author**: Controller Architecture Specialist
- **Target Audience**: Agent 4 (Implementation Specialist)

## Overview

This guide provides step-by-step implementation instructions for `DraftDialogController`. Follow these steps sequentially to ensure proper integration and testing.

**Target File**: `ui/controllers/draft_dialog_controller.py`

**Estimated Time**: 3-4 hours (including testing)

---

## Implementation Phases

### Phase 1: Class Skeleton and Dependencies (30 minutes)

**Step 1.1: Create File and Add Imports**

Create `ui/controllers/draft_dialog_controller.py` with complete imports:

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

**Testing Checkpoint**: Verify all imports resolve correctly
```bash
python -c "from ui.controllers.draft_dialog_controller import *"
```

---

**Step 1.2: Define Class Skeleton with Signals**

```python
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
        # Implementation in next step
        pass
```

**Testing Checkpoint**: Verify class definition compiles
```python
from ui.controllers.draft_dialog_controller import DraftDialogController
# Should not raise syntax errors
```

---

### Phase 2: Initialization and State Loading (45 minutes)

**Step 2.1: Implement `__init__()` Method**

```python
def __init__(
    self,
    database_path: str,
    dynasty_id: str,
    season_year: int,
    user_team_id: int
):
    super().__init__()

    # Store parameters
    self.db_path = database_path
    self.dynasty_id = dynasty_id
    self.season = season_year
    self.user_team_id = user_team_id

    # Initialize logger
    self.logger = logging.getLogger(__name__)

    # Initialize database APIs
    self.draft_api = DraftClassAPI(database_path)
    self.draft_order_api = DraftOrderDatabaseAPI(database_path)
    self.dynasty_state_api = DynastyStateAPI(database_path)
    self.needs_analyzer = TeamNeedsAnalyzer(database_path, dynasty_id)
    self.team_loader = TeamDataLoader()

    # Initialize DraftManager (business logic)
    self.draft_manager = DraftManager(
        database_path=database_path,
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
            f"No draft class found for dynasty '{dynasty_id}', season {season_year}. "
            f"Generate draft class before starting draft."
        )

    self.logger.info(
        f"Initialized DraftDialogController: dynasty={dynasty_id}, "
        f"season={season_year}, user_team={user_team_id}, "
        f"current_pick={self.current_pick_index}"
    )
```

**Testing Checkpoint**: Create controller instance with test database
```python
# Test with existing test database
controller = DraftDialogController(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="test_dynasty",
    season_year=2025,
    user_team_id=22
)
assert controller.current_pick_index >= 0
assert len(controller.draft_order) == 262
```

---

**Step 2.2: Implement Private Helper `_load_draft_order()`**

```python
def _load_draft_order(self) -> List[DraftPick]:
    """
    Load complete draft order from database.

    Returns:
        List of DraftPick objects ordered by overall_pick

    Raises:
        ValueError: If draft order not found
    """
    draft_order = self.draft_order_api.get_draft_order(
        dynasty_id=self.dynasty_id,
        season=self.season
    )

    if not draft_order:
        raise ValueError(
            f"No draft order found for dynasty '{self.dynasty_id}', "
            f"season {self.season}. Generate draft order before starting draft."
        )

    self.logger.info(f"Loaded {len(draft_order)} draft picks")
    return draft_order
```

**Testing Checkpoint**: Verify draft order loading
```python
# Should raise ValueError if no draft order exists
try:
    controller = DraftDialogController(
        database_path="data/database/nfl_simulation.db",
        dynasty_id="nonexistent_dynasty",
        season_year=2025,
        user_team_id=22
    )
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert "No draft order found" in str(e)
```

---

**Step 2.3: Implement State Persistence Methods**

```python
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

**Testing Checkpoint**: Verify state save/load cycle
```python
# Save state
controller.current_pick_index = 50
controller.save_draft_state()

# Load state
state = controller.load_draft_state()
assert state['current_pick_index'] == 50
assert state['draft_in_progress'] == True
```

---

### Phase 3: Data Retrieval Methods (30 minutes)

**Step 3.1: Implement Data Retrieval Methods**

```python
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
        List of prospect dicts sorted by specified field
    """
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


def get_team_needs(self, team_id: int) -> List[Dict[str, Any]]:
    """
    Get team needs sorted by urgency.

    Args:
        team_id: Team ID (1-32)

    Returns:
        List of need dicts sorted by urgency (CRITICAL → LOW)
    """
    # Delegate to TeamNeedsAnalyzer
    needs = self.needs_analyzer.analyze_team_needs(
        team_id=team_id,
        season=self.season,
        include_future_contracts=True
    )

    return needs  # Already sorted by urgency
```

**Testing Checkpoint**: Verify data retrieval
```python
# Load draft data
data = controller.load_draft_data()
assert data['total_picks'] == 262
assert data['prospects_available'] > 0

# Get current pick
pick = controller.get_current_pick()
assert pick is not None
assert 'team_name' in pick

# Get prospects
prospects = controller.get_available_prospects(limit=10)
assert len(prospects) <= 10
assert all('overall' in p for p in prospects)

# Get team needs
needs = controller.get_team_needs(22)
assert isinstance(needs, list)
```

---

### Phase 4: Pick Execution Methods (60 minutes)

**Step 4.1: Implement `execute_user_pick()`**

```python
def execute_user_pick(self, player_id: int) -> Dict[str, Any]:
    """
    Execute user's draft pick.

    Validates pick ownership, executes via DraftManager, updates database,
    advances to next pick, and emits signals.

    Args:
        player_id: Player ID of prospect to draft

    Returns:
        Dict with pick result (see specification for full schema)

    Raises:
        ValueError: If not user's pick or player not available
    """
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
    if not prospect:
        raise ValueError(f"Prospect {player_id} not found")
    if prospect['is_drafted']:
        raise ValueError(f"Prospect {player_id} already drafted")

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

    self.logger.info(
        f"User executed pick {pick_obj.overall_pick}: "
        f"{prospect['first_name']} {prospect['last_name']} "
        f"({prospect['position']}, {prospect['overall']} OVR)"
    )

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

**Testing Checkpoint**: Test user pick execution
```python
# Get user's first pick
current_pick = controller.get_current_pick()
if current_pick and current_pick['is_user_pick']:
    # Get best available prospect
    prospects = controller.get_available_prospects(limit=1)
    player_id = prospects[0]['player_id']

    # Execute pick
    result = controller.execute_user_pick(player_id)
    assert result['success'] == True
    assert result['player_id'] == player_id
    assert controller.current_pick_index == 1
```

---

**Step 4.2: Implement `execute_ai_pick()`**

```python
def execute_ai_pick(self) -> Dict[str, Any]:
    """
    Execute AI team's draft pick using needs-based evaluation.

    Uses DraftManager's prospect evaluation to score all available
    prospects based on team needs and selects highest-scoring player.

    Returns:
        Dict with pick result (see specification for full schema)

    Raises:
        ValueError: If current pick belongs to user or no prospects available
    """
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
    if not available_prospects:
        raise ValueError("No prospects available to draft")

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

    # Update draft order state
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

    self.logger.info(
        f"AI executed pick {pick_obj.overall_pick}: "
        f"Team {team_id} selects {best_prospect['first_name']} {best_prospect['last_name']} "
        f"({best_prospect['position']}, {best_prospect['overall']} OVR) "
        f"[Need: {needs_match}, Score: {best_score:.1f}]"
    )

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

**Testing Checkpoint**: Test AI pick execution
```python
# Advance to AI pick
while controller.get_current_pick()['is_user_pick']:
    prospects = controller.get_available_prospects(limit=1)
    controller.execute_user_pick(prospects[0]['player_id'])

# Execute AI pick
result = controller.execute_ai_pick()
assert result['success'] == True
assert 'needs_match' in result
assert 'eval_score' in result
```

---

### Phase 5: Utility Methods (20 minutes)

**Step 5.1: Implement Remaining Methods**

```python
def get_pick_history(self, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Get recent draft picks (most recent first).

    Args:
        limit: Maximum number of picks to return (default 15)

    Returns:
        List of executed pick dicts (most recent first)
    """
    executed_picks = []

    # Iterate backwards from current pick
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


def is_draft_complete(self) -> bool:
    """
    Check if draft is complete.

    Returns:
        True if all 262 picks have been executed
    """
    return self.current_pick_index >= len(self.draft_order)


def get_draft_progress(self) -> Dict[str, Any]:
    """
    Get overall draft progress.

    Returns:
        Dict with draft progress info (see specification)
    """
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

**Testing Checkpoint**: Test utility methods
```python
# Get pick history
history = controller.get_pick_history(limit=5)
assert len(history) <= 5
assert all('player_name' in pick for pick in history)

# Check draft complete
is_complete = controller.is_draft_complete()
assert isinstance(is_complete, bool)

# Get draft progress
progress = controller.get_draft_progress()
assert 'picks_completed' in progress
assert 'completion_pct' in progress
assert progress['total_picks'] == 262
```

---

### Phase 6: Testing and Validation (45 minutes)

**Step 6.1: Create Unit Tests**

Create `tests/ui/test_draft_dialog_controller.py`:

```python
import pytest
from unittest.mock import Mock, MagicMock
from ui.controllers.draft_dialog_controller import DraftDialogController


@pytest.fixture
def controller():
    """Create controller with test database."""
    # Use test database with pre-populated draft order and class
    return DraftDialogController(
        database_path="data/database/test_nfl_simulation.db",
        dynasty_id="test_dynasty",
        season_year=2025,
        user_team_id=22
    )


def test_init_loads_draft_order(controller):
    """Test initialization loads draft order."""
    assert len(controller.draft_order) == 262
    assert controller.current_pick_index >= 0


def test_get_current_pick_returns_correct_pick(controller):
    """Test get_current_pick returns valid pick info."""
    pick = controller.get_current_pick()
    assert pick is not None
    assert 'team_name' in pick
    assert 'is_user_pick' in pick


def test_execute_user_pick_validates_ownership(controller):
    """Test user pick validates ownership."""
    # Advance to AI pick
    while controller.get_current_pick()['is_user_pick']:
        prospects = controller.get_available_prospects(limit=1)
        controller.execute_user_pick(prospects[0]['player_id'])

    # Try to execute AI pick as user
    prospects = controller.get_available_prospects(limit=1)
    with pytest.raises(ValueError, match="Not user's pick"):
        controller.execute_user_pick(prospects[0]['player_id'])


def test_save_and_load_draft_state(controller):
    """Test state save/load cycle."""
    # Save state
    controller.current_pick_index = 75
    controller.save_draft_state()

    # Load state
    state = controller.load_draft_state()
    assert state['current_pick_index'] == 75
    assert state['draft_in_progress'] == True


# Add 15+ more tests covering all methods...
```

**Testing Checkpoint**: Run unit tests
```bash
python -m pytest tests/ui/test_draft_dialog_controller.py -v
```

---

**Step 6.2: Integration Testing**

Create integration test for full draft flow:

```python
# tests/integration/test_draft_dialog_integration.py

def test_complete_draft_flow():
    """Test full draft from start to finish."""
    controller = DraftDialogController(
        database_path="data/database/test_nfl_simulation.db",
        dynasty_id="integration_test_dynasty",
        season_year=2025,
        user_team_id=22
    )

    # Execute 10 picks
    for _ in range(10):
        pick = controller.get_current_pick()
        prospects = controller.get_available_prospects(limit=1)

        if pick['is_user_pick']:
            result = controller.execute_user_pick(prospects[0]['player_id'])
        else:
            result = controller.execute_ai_pick()

        assert result['success'] == True

    # Verify progress
    progress = controller.get_draft_progress()
    assert progress['picks_completed'] == 10
    assert progress['picks_remaining'] == 252

    # Verify state saved
    state = controller.load_draft_state()
    assert state['current_pick_index'] == 10
```

---

### Phase 7: Error Handling and Edge Cases (20 minutes)

**Step 7.1: Add Comprehensive Error Handling**

Verify all error handling paths:

1. **Draft Order Not Found**:
```python
# Should raise ValueError in __init__
try:
    controller = DraftDialogController(
        database_path="data/database/nfl_simulation.db",
        dynasty_id="nonexistent_dynasty",
        season_year=2025,
        user_team_id=22
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "No draft order found" in str(e)
```

2. **Draft Class Not Found**:
```python
# Should raise ValueError in __init__
# (Test with dynasty that has draft order but no draft class)
```

3. **Database Write Failure**:
```python
# Mock DynastyStateAPI to raise exception
with patch.object(controller.dynasty_state_api, 'update_draft_state', side_effect=Exception("DB locked")):
    with pytest.raises(RuntimeError, match="Draft state persistence failed"):
        controller.save_draft_state()
```

4. **Invalid Player Selection**:
```python
# Try to draft already-drafted player
with pytest.raises(ValueError, match="already drafted"):
    controller.execute_user_pick(player_id=12345)
```

---

### Phase 8: Documentation and Code Review (15 minutes)

**Step 8.1: Add Module Docstring**

Verify module-level docstring is complete and accurate.

**Step 8.2: Verify Method Docstrings**

Ensure all methods have:
- Clear one-line summary
- Args section with types
- Returns section with type and description
- Raises section (if applicable)
- Example usage (for complex methods)

**Step 8.3: Code Review Checklist**

- [ ] All methods follow thin controller pattern (≤10-20 lines)
- [ ] Business logic delegated to DraftManager/APIs
- [ ] All database operations wrapped in try/except
- [ ] All signals emitted at appropriate times
- [ ] Dynasty isolation maintained throughout
- [ ] State saved after each pick
- [ ] Error messages are clear and actionable
- [ ] Logging statements added for debugging
- [ ] No hardcoded values or magic numbers
- [ ] All type hints correct and complete

---

## Common Implementation Mistakes to Avoid

### 1. **Forgetting to Save State After Pick**
```python
# BAD
self.current_pick_index += 1
# Missing save_draft_state()!

# GOOD
self.current_pick_index += 1
self.save_draft_state()
```

### 2. **Not Emitting Signals**
```python
# BAD
return result  # UI won't update!

# GOOD
self.pick_executed.emit(pick_number, player_id, team_id)
return result
```

### 3. **Silent Error Handling**
```python
# BAD
except Exception as e:
    return False  # Silent failure!

# GOOD
except Exception as e:
    self.error_occurred.emit(str(e))
    raise RuntimeError(f"Operation failed: {e}")
```

### 4. **Modifying Business Logic**
```python
# BAD - Controller doing business logic
conn = sqlite3.connect(...)
cursor.execute("UPDATE ...")

# GOOD - Delegate to DraftManager
self.draft_manager.make_draft_selection(...)
```

### 5. **Not Validating Pick Ownership**
```python
# BAD
result = self.draft_manager.make_draft_selection(...)

# GOOD
if not current_pick['is_user_pick']:
    raise ValueError("Not user's pick")
result = self.draft_manager.make_draft_selection(...)
```

---

## Debugging Tips

### 1. **Enable Debug Logging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. **Test Database State**
```bash
# Check dynasty_state table
sqlite3 data/database/nfl_simulation.db \
  "SELECT current_pick_index, draft_in_progress FROM dynasty_state WHERE dynasty_id='test_dynasty';"
```

### 3. **Monitor Signal Emissions**
```python
# In test code
def on_pick_executed(pick_number, player_id, team_id):
    print(f"Pick executed: {pick_number}, Player: {player_id}, Team: {team_id}")

controller.pick_executed.connect(on_pick_executed)
```

### 4. **Validate Draft Order State**
```python
# Check executed picks
executed_count = sum(1 for pick in controller.draft_order if pick.is_executed)
print(f"Executed picks: {executed_count}/{len(controller.draft_order)}")
```

---

## Performance Optimization

### Database Operations

**Per-Pick Overhead**: 5 database operations
- Keep transactions short (avoid long-running locks)
- Use `IMMEDIATE` transaction mode
- Save state after each pick (cannot batch)

### Memory Management

**Memory Footprint**: ~205 KB (acceptable)
- No lazy loading needed
- Full draft order cached in memory
- Prospects loaded on demand

---

## Final Checklist

Before submitting implementation:

- [ ] All 13 methods implemented
- [ ] All docstrings complete
- [ ] All type hints correct
- [ ] 15+ unit tests passing
- [ ] Integration test passing
- [ ] Error handling comprehensive
- [ ] Signals emitted correctly
- [ ] State persistence verified
- [ ] Dynasty isolation verified
- [ ] Code review checklist complete
- [ ] No lint errors
- [ ] No type check errors
- [ ] Documentation updated

---

## Support Resources

**Specification**: `docs/project/nfl_draft_event/controller_specification.md`

**Related Code**:
- `demo/draft_day_demo/draft_demo_controller.py` - Demo reference
- `src/offseason/draft_manager.py` - Business logic
- `ui/controllers/simulation_controller.py` - Controller pattern example

**Testing Examples**:
- `tests/ui/test_simulation_controller.py` - Controller test patterns

**Questions?**
- Review architecture document: `docs/project/nfl_draft_event/architecture.md`
- Check requirements: `docs/project/nfl_draft_event/requirements.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-23
**Author**: Controller Architecture Specialist
