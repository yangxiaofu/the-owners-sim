"""
Shared fixtures for owner pressure modifier tests.
"""

import pytest

from contract_valuation.context import JobSecurityContext, OwnerContext


@pytest.fixture
def secure_job_security():
    """JobSecurityContext for a secure GM (low pressure)."""
    return JobSecurityContext.create_secure()


@pytest.fixture
def hot_seat_job_security():
    """JobSecurityContext for a GM on the hot seat (high pressure)."""
    return JobSecurityContext.create_hot_seat()


@pytest.fixture
def new_hire_job_security():
    """JobSecurityContext for a newly hired GM (moderate pressure)."""
    return JobSecurityContext.create_new_hire()


@pytest.fixture
def secure_context(secure_job_security):
    """OwnerContext with secure GM (low pressure)."""
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=secure_job_security,
        owner_philosophy="balanced",
        team_philosophy="maintain",
        win_now_mode=False,
        max_contract_years=5,
        max_guaranteed_pct=0.60,
    )


@pytest.fixture
def hot_seat_context():
    """OwnerContext with GM on hot seat (high pressure > 0.7)."""
    # Manually construct high-pressure job security
    # Formula: (tenure * 0.3) + (win * 0.7) - playoff_bonus - patience
    # Target: > 0.7
    # tenure=1 -> 0.6, win_pct=0.20 -> 0.8, playoffs=0 -> 0, patience=0.1 -> 0.03
    # = 0.6*0.3 + 0.8*0.7 - 0 - 0.03 = 0.18 + 0.56 - 0.03 = 0.71
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=JobSecurityContext(
            tenure_years=1,
            playoff_appearances=0,
            recent_win_pct=0.20,
            owner_patience=0.1,
        ),
        owner_philosophy="aggressive",
        team_philosophy="win_now",
        win_now_mode=True,
        max_contract_years=6,
        max_guaranteed_pct=0.70,
    )


@pytest.fixture
def rebuild_context():
    """OwnerContext for rebuilding team with patient owner."""
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=JobSecurityContext.create_new_hire(),
        owner_philosophy="conservative",
        team_philosophy="rebuild",
        win_now_mode=False,
        max_contract_years=4,
        max_guaranteed_pct=0.50,
    )


@pytest.fixture
def normal_pressure_context():
    """OwnerContext with normal (middle) pressure in 0.3-0.7 range."""
    # Formula: (tenure * 0.3) + (win * 0.7) - playoff_bonus - patience
    # Target: 0.3 - 0.7
    # tenure=2 -> 0.4, win_pct=0.40 -> 0.5, playoffs=0 -> 0, patience=0.3 -> 0.09
    # = 0.4*0.3 + 0.5*0.7 - 0 - 0.09 = 0.12 + 0.35 - 0.09 = 0.38
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=JobSecurityContext(
            tenure_years=2,
            playoff_appearances=0,
            recent_win_pct=0.40,
            owner_patience=0.3,
        ),
        owner_philosophy="balanced",
        team_philosophy="maintain",
        win_now_mode=False,
        max_contract_years=5,
        max_guaranteed_pct=0.60,
    )


@pytest.fixture
def win_now_context():
    """OwnerContext for a win-now team."""
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=JobSecurityContext(
            tenure_years=4,
            playoff_appearances=2,
            recent_win_pct=0.60,
            owner_patience=0.6,
        ),
        owner_philosophy="aggressive",
        team_philosophy="win_now",
        win_now_mode=True,
        max_contract_years=6,
        max_guaranteed_pct=0.65,
    )


@pytest.fixture
def aggressive_context():
    """OwnerContext with aggressive owner philosophy."""
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=JobSecurityContext.create_secure(),
        owner_philosophy="aggressive",
        team_philosophy="maintain",
        win_now_mode=False,
        max_contract_years=6,
        max_guaranteed_pct=0.70,
    )


@pytest.fixture
def conservative_context():
    """OwnerContext with conservative owner philosophy."""
    return OwnerContext(
        dynasty_id="test",
        team_id=1,
        job_security=JobSecurityContext.create_secure(),
        owner_philosophy="conservative",
        team_philosophy="maintain",
        win_now_mode=False,
        max_contract_years=4,
        max_guaranteed_pct=0.50,
    )


@pytest.fixture
def base_aav():
    """Standard base AAV for testing."""
    return 10_000_000  # $10M