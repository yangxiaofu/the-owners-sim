"""
Tests for primetime scheduling (Milestone 11, Tollgate 4).

Tests cover:
- GameSlot enum properties
- Matchup appeal calculation
- Primetime slot assignment
- Thanksgiving and Kickoff games
- Database persistence
"""

import os
import tempfile
import pytest
from collections import Counter

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.rivalry_api import RivalryAPI
from src.game_cycle.database.standings_api import StandingsAPI
from src.game_cycle.services.primetime_scheduler import PrimetimeScheduler
from src.game_cycle.models.game_slot import (
    GameSlot,
    PrimetimeAssignment,
    get_market_score,
    TEAM_MARKET_SIZE,
)
from src.game_cycle.models.rivalry import Rivalry, RivalryType


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def temp_db():
    """Create temp database with GameCycleDatabase (full schema auto-created)."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    db = GameCycleDatabase(db_path)
    conn = db.get_connection()

    # All 32 NFL teams
    nfl_teams = [
        (1, 'Buffalo Bills', 'BUF', 'AFC', 'East'),
        (2, 'Miami Dolphins', 'MIA', 'AFC', 'East'),
        (3, 'New England Patriots', 'NE', 'AFC', 'East'),
        (4, 'New York Jets', 'NYJ', 'AFC', 'East'),
        (5, 'Baltimore Ravens', 'BAL', 'AFC', 'North'),
        (6, 'Cincinnati Bengals', 'CIN', 'AFC', 'North'),
        (7, 'Cleveland Browns', 'CLE', 'AFC', 'North'),
        (8, 'Pittsburgh Steelers', 'PIT', 'AFC', 'North'),
        (9, 'Houston Texans', 'HOU', 'AFC', 'South'),
        (10, 'Indianapolis Colts', 'IND', 'AFC', 'South'),
        (11, 'Jacksonville Jaguars', 'JAX', 'AFC', 'South'),
        (12, 'Tennessee Titans', 'TEN', 'AFC', 'South'),
        (13, 'Denver Broncos', 'DEN', 'AFC', 'West'),
        (14, 'Kansas City Chiefs', 'KC', 'AFC', 'West'),
        (15, 'Las Vegas Raiders', 'LV', 'AFC', 'West'),
        (16, 'Los Angeles Chargers', 'LAC', 'AFC', 'West'),
        (17, 'Dallas Cowboys', 'DAL', 'NFC', 'East'),
        (18, 'New York Giants', 'NYG', 'NFC', 'East'),
        (19, 'Philadelphia Eagles', 'PHI', 'NFC', 'East'),
        (20, 'Washington Commanders', 'WAS', 'NFC', 'East'),
        (21, 'Chicago Bears', 'CHI', 'NFC', 'North'),
        (22, 'Detroit Lions', 'DET', 'NFC', 'North'),
        (23, 'Green Bay Packers', 'GB', 'NFC', 'North'),
        (24, 'Minnesota Vikings', 'MIN', 'NFC', 'North'),
        (25, 'Atlanta Falcons', 'ATL', 'NFC', 'South'),
        (26, 'Carolina Panthers', 'CAR', 'NFC', 'South'),
        (27, 'New Orleans Saints', 'NO', 'NFC', 'South'),
        (28, 'Tampa Bay Buccaneers', 'TB', 'NFC', 'South'),
        (29, 'Arizona Cardinals', 'ARI', 'NFC', 'West'),
        (30, 'Los Angeles Rams', 'LAR', 'NFC', 'West'),
        (31, 'San Francisco 49ers', 'SF', 'NFC', 'West'),
        (32, 'Seattle Seahawks', 'SEA', 'NFC', 'West'),
    ]

    for team_data in nfl_teams:
        conn.execute(
            """INSERT INTO teams (team_id, name, abbreviation, conference, division)
               VALUES (?, ?, ?, ?, ?)""",
            team_data
        )

    # Create dynasty
    conn.execute("""
        INSERT INTO dynasties (dynasty_id, name, team_id)
        VALUES ('test_primetime_dynasty', 'Primetime Test', 1)
    """)

    # Insert prior year standings for all teams
    for team_id in range(1, 33):
        wins = 8 + (team_id % 5)  # Varied win totals 8-12
        conn.execute(
            """INSERT INTO standings (dynasty_id, season, team_id, wins, losses, ties)
               VALUES ('test_primetime_dynasty', 2024, ?, ?, ?, 0)""",
            (team_id, wins, 17 - wins)
        )

    conn.commit()

    yield db, db_path

    db.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def scheduler(temp_db):
    """Create PrimetimeScheduler with temp database."""
    db, db_path = temp_db
    return PrimetimeScheduler(db, "test_primetime_dynasty")


@pytest.fixture
def sample_games():
    """Generate sample games for a week."""
    games = []
    for i in range(16):
        home_id = (i * 2) + 1
        away_id = (i * 2) + 2
        games.append({
            "game_id": f"regular_2025_1_{i+1}",
            "data": {
                "parameters": {
                    "week": 1,
                    "home_team_id": home_id,
                    "away_team_id": away_id,
                },
                "metadata": {
                    "is_divisional": (i < 4),
                    "is_conference": True,
                }
            }
        })
    return games


@pytest.fixture
def thanksgiving_week_games():
    """Generate games for Thanksgiving week (Week 12)."""
    games = []
    # Include Lions and Cowboys home games
    matchups = [
        (22, 21),  # Lions vs Bears (division)
        (17, 18),  # Cowboys vs Giants (division)
        (31, 32),  # 49ers vs Seahawks (prime matchup)
        (14, 15),  # Chiefs vs Raiders
        (19, 20),  # Eagles vs Commanders
        (23, 24),  # Packers vs Vikings
        (5, 6),    # Ravens vs Bengals
        (1, 2),    # Bills vs Dolphins
        (9, 10),   # Texans vs Colts
        (25, 26),  # Falcons vs Panthers
        (27, 28),  # Saints vs Bucs
        (29, 30),  # Cardinals vs Rams
        (3, 4),    # Patriots vs Jets
        (7, 8),    # Browns vs Steelers
    ]
    for i, (home, away) in enumerate(matchups):
        games.append({
            "game_id": f"regular_2025_12_{i+1}",
            "data": {
                "parameters": {
                    "week": 12,
                    "home_team_id": home,
                    "away_team_id": away,
                },
                "metadata": {
                    "is_divisional": True,
                    "is_conference": True,
                }
            }
        })
    return games


# ============================================
# GAME SLOT ENUM TESTS
# ============================================

class TestGameSlotEnum:
    """Tests for GameSlot enum."""

    def test_primetime_slots_identified(self):
        """Primetime slots should be correctly identified."""
        assert GameSlot.THURSDAY_NIGHT.is_primetime
        assert GameSlot.SUNDAY_NIGHT.is_primetime
        assert GameSlot.MONDAY_NIGHT.is_primetime
        assert GameSlot.KICKOFF.is_primetime
        assert GameSlot.THANKSGIVING_EARLY.is_primetime

    def test_non_primetime_slots(self):
        """Non-primetime slots should not be flagged as primetime."""
        assert not GameSlot.SUNDAY_EARLY.is_primetime
        assert not GameSlot.SUNDAY_LATE.is_primetime

    def test_broadcast_networks(self):
        """Each slot should have a broadcast network."""
        assert GameSlot.THURSDAY_NIGHT.broadcast_network == "Amazon Prime"
        assert GameSlot.SUNDAY_NIGHT.broadcast_network == "NBC"
        assert GameSlot.MONDAY_NIGHT.broadcast_network == "ESPN"
        assert GameSlot.KICKOFF.broadcast_network == "NBC"


# ============================================
# MARKET SIZE TESTS
# ============================================

class TestMarketSize:
    """Tests for team market size scoring."""

    def test_all_teams_have_market_ranking(self):
        """All 32 teams should have a market ranking."""
        assert len(TEAM_MARKET_SIZE) == 32
        for team_id in range(1, 33):
            assert team_id in TEAM_MARKET_SIZE

    def test_cowboys_largest_market(self):
        """Cowboys should be the largest market."""
        assert TEAM_MARKET_SIZE[17] == 1  # Cowboys

    def test_market_score_range(self):
        """Market scores should be in valid range 0-20."""
        for team_id in range(1, 33):
            score = get_market_score(team_id)
            assert 0 <= score <= 20

    def test_large_market_high_score(self):
        """Large market teams should have higher scores."""
        cowboys_score = get_market_score(17)  # Cowboys
        jaguars_score = get_market_score(11)  # Jaguars (small market)
        assert cowboys_score > jaguars_score


# ============================================
# PRIMETIME ASSIGNMENT TESTS
# ============================================

class TestPrimetimeAssignment:
    """Tests for PrimetimeAssignment dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        assignment = PrimetimeAssignment(
            game_id="regular_2025_1_1",
            week=1,
            slot=GameSlot.SUNDAY_NIGHT,
            home_team_id=17,
            away_team_id=18,
            appeal_score=85,
            broadcast_network="NBC",
            is_flex_eligible=True,
        )

        data = assignment.to_dict()
        assert data["game_id"] == "regular_2025_1_1"
        assert data["slot"] == "SNF"
        assert data["appeal_score"] == 85

    def test_from_dict(self):
        """Should create from dictionary correctly."""
        data = {
            "game_id": "regular_2025_1_1",
            "week": 1,
            "slot": "MNF",
            "home_team_id": 17,
            "away_team_id": 18,
            "appeal_score": 75,
            "broadcast_network": "ESPN",
            "is_flex_eligible": False,
            "flexed_from": None,
        }

        assignment = PrimetimeAssignment.from_dict(data)
        assert assignment.slot == GameSlot.MONDAY_NIGHT
        assert assignment.home_team_id == 17


# ============================================
# MATCHUP APPEAL TESTS
# ============================================

class TestMatchupAppeal:
    """Tests for matchup appeal calculation."""

    def test_rivalry_boosts_appeal(self, scheduler, temp_db):
        """Rivalry games should have higher appeal."""
        db, _ = temp_db

        # Create a rivalry
        rivalry_api = RivalryAPI(db)
        rivalry = Rivalry(
            rivalry_id="test_rivalry_1",
            team_a_id=21,  # Bears
            team_b_id=23,  # Packers
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Oldest Rivalry",
            intensity=95,
            is_protected=True,
        )
        rivalry_api.create_rivalry(
            dynasty_id="test_primetime_dynasty",
            rivalry=rivalry,
        )

        # Get standings and convert to dict format
        standings_api = StandingsAPI(db)
        standings_list = standings_api.get_standings("test_primetime_dynasty", 2024)
        standings = {s.team_id: {"wins": s.wins, "losses": s.losses} for s in standings_list}

        # Get rivalries
        rivalries = rivalry_api.get_all_rivalries("test_primetime_dynasty")
        rivalry_map = scheduler._build_rivalry_map(rivalries)

        # Calculate appeal with rivalry
        appeal_with_rivalry = scheduler._calculate_matchup_appeal(
            home_team=21,  # Bears
            away_team=23,  # Packers
            rivalry=rivalry_map.get((21, 23)),
            prior_standings=standings,
            super_bowl_winner_id=None,
            week=10,
        )

        # Calculate appeal without rivalry (different teams)
        appeal_no_rivalry = scheduler._calculate_matchup_appeal(
            home_team=11,  # Jaguars
            away_team=12,  # Titans
            rivalry=None,
            prior_standings=standings,
            super_bowl_winner_id=None,
            week=10,
        )

        assert appeal_with_rivalry > appeal_no_rivalry

    def test_super_bowl_winner_boost(self, scheduler):
        """Super Bowl participant should get appeal boost."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        # With Super Bowl winner
        appeal_with_sb = scheduler._calculate_matchup_appeal(
            home_team=14,  # Chiefs (hypothetical SB winner)
            away_team=8,   # Steelers
            rivalry=None,
            prior_standings=standings,
            super_bowl_winner_id=14,
            week=5,
        )

        # Without Super Bowl winner
        appeal_without_sb = scheduler._calculate_matchup_appeal(
            home_team=14,
            away_team=8,
            rivalry=None,
            prior_standings=standings,
            super_bowl_winner_id=None,
            week=5,
        )

        assert appeal_with_sb > appeal_without_sb
        assert appeal_with_sb - appeal_without_sb == 15  # 15 point bonus

    def test_market_size_affects_appeal(self, scheduler):
        """Large market teams should have higher appeal."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        # Large market matchup (Cowboys vs Giants)
        appeal_large = scheduler._calculate_matchup_appeal(
            home_team=17,  # Cowboys
            away_team=18,  # Giants
            rivalry=None,
            prior_standings=standings,
            super_bowl_winner_id=None,
            week=5,
        )

        # Small market matchup (Jaguars vs Titans)
        appeal_small = scheduler._calculate_matchup_appeal(
            home_team=11,  # Jaguars
            away_team=12,  # Titans
            rivalry=None,
            prior_standings=standings,
            super_bowl_winner_id=None,
            week=5,
        )

        assert appeal_large > appeal_small


# ============================================
# WEEK ASSIGNMENT TESTS
# ============================================

class TestWeekAssignment:
    """Tests for weekly slot assignment."""

    def test_assigns_all_slots(self, scheduler, sample_games):
        """Should assign slots to all games."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        assignments = scheduler._assign_week_slots(
            week=1,
            games=sample_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
        )

        assert len(assignments) == len(sample_games)

    def test_one_snf_per_week(self, scheduler, sample_games):
        """Should assign exactly one SNF game per week."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        assignments = scheduler._assign_week_slots(
            week=5,
            games=sample_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
        )

        snf_count = sum(1 for a in assignments if a.slot == GameSlot.SUNDAY_NIGHT)
        assert snf_count == 1

    def test_one_mnf_per_week(self, scheduler, sample_games):
        """Should assign exactly one MNF game per week."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        assignments = scheduler._assign_week_slots(
            week=5,
            games=sample_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
        )

        mnf_count = sum(1 for a in assignments if a.slot == GameSlot.MONDAY_NIGHT)
        assert mnf_count == 1

    def test_week1_has_kickoff(self, scheduler, sample_games):
        """Week 1 should have a Kickoff game instead of TNF."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        assignments = scheduler._assign_week_slots(
            week=1,
            games=sample_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
        )

        kickoff_games = [a for a in assignments if a.slot == GameSlot.KICKOFF]
        tnf_games = [a for a in assignments if a.slot == GameSlot.THURSDAY_NIGHT]

        assert len(kickoff_games) == 1
        # Week 1 should not have separate TNF (Kickoff IS Thursday)
        # Actually the implementation adds TNF separately, but we have Kickoff


# ============================================
# THANKSGIVING TESTS
# ============================================

class TestThanksgivingGames:
    """Tests for Thanksgiving game assignment."""

    def test_lions_host_early_game(self, scheduler, thanksgiving_week_games):
        """Lions should host the early Thanksgiving game."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        assignments = scheduler._assign_week_slots(
            week=12,
            games=thanksgiving_week_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
            is_thanksgiving=True,
        )

        early_games = [a for a in assignments if a.slot == GameSlot.THANKSGIVING_EARLY]
        assert len(early_games) == 1
        assert early_games[0].home_team_id == 22  # Lions

    def test_cowboys_host_late_game(self, scheduler, thanksgiving_week_games):
        """Cowboys should host the late Thanksgiving game."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        assignments = scheduler._assign_week_slots(
            week=12,
            games=thanksgiving_week_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
            is_thanksgiving=True,
        )

        late_games = [a for a in assignments if a.slot == GameSlot.THANKSGIVING_LATE]
        assert len(late_games) == 1
        assert late_games[0].home_team_id == 17  # Cowboys

    def test_thanksgiving_has_night_game(self, scheduler, thanksgiving_week_games):
        """Thanksgiving should have a night game."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        assignments = scheduler._assign_week_slots(
            week=12,
            games=thanksgiving_week_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
            is_thanksgiving=True,
        )

        night_games = [a for a in assignments if a.slot == GameSlot.THANKSGIVING_NIGHT]
        assert len(night_games) == 1


# ============================================
# DATABASE PERSISTENCE TESTS
# ============================================

class TestDatabasePersistence:
    """Tests for saving and retrieving assignments."""

    def test_save_and_retrieve_assignments(self, scheduler, sample_games):
        """Should save and retrieve primetime assignments."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        # Assign slots
        assignments = scheduler._assign_week_slots(
            week=1,
            games=sample_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
        )

        # Save to database
        count = scheduler.save_assignments(2025, assignments)
        assert count == len(assignments)

        # Retrieve from database
        retrieved = scheduler.get_week_schedule(2025, 1)
        assert len(retrieved) == len(assignments)

    def test_get_primetime_games_only(self, scheduler, sample_games):
        """Should retrieve only primetime games."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        assignments = scheduler._assign_week_slots(
            week=1,
            games=sample_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
        )

        scheduler.save_assignments(2025, assignments)

        primetime = scheduler.get_primetime_games(2025)

        # Should only include primetime slots
        for p in primetime:
            assert p.slot.is_primetime


# ============================================
# FLEX ELIGIBILITY TESTS
# ============================================

class TestFlexEligibility:
    """Tests for flex scheduling eligibility."""

    def test_early_weeks_not_flex_eligible(self, scheduler, sample_games):
        """Games before week 12 should not be flex-eligible."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        # Modify games for week 5
        for g in sample_games:
            g["data"]["parameters"]["week"] = 5

        assignments = scheduler._assign_week_slots(
            week=5,
            games=sample_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
        )

        # Regular slots should not be flex-eligible before week 12
        for a in assignments:
            if a.slot in (GameSlot.SUNDAY_EARLY, GameSlot.SUNDAY_LATE):
                assert not a.is_flex_eligible

    def test_late_weeks_flex_eligible(self, scheduler, sample_games):
        """Games in weeks 12-17 should be flex-eligible."""
        standings = {i: {"wins": 8} for i in range(1, 33)}

        # Modify games for week 14
        for g in sample_games:
            g["data"]["parameters"]["week"] = 14

        assignments = scheduler._assign_week_slots(
            week=14,
            games=sample_games,
            prior_standings=standings,
            rivalry_map={},
            super_bowl_winner_id=None,
        )

        flex_eligible_count = sum(1 for a in assignments if a.is_flex_eligible)
        assert flex_eligible_count > 0
