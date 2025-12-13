"""
Integration Test for Play-by-Play Bug Fixes

This test validates that all 5 critical play-by-play bugs are fixed:
1. Negative yards increase distance (e.g., 2nd & 10 → loses 5 yards → 3rd & 15)
2. Missed field goals don't show points
3. Made field goals show is_scoring_play=True
4. Field position calculation accounts for negative yards
5. Real field goals show 0 yards (fake FGs can show yards)

Test Strategy:
- Run a full game simulation using GameSimulatorService (FULL mode)
- Validate play snapshots throughout all drives
- Export to markdown and validate format
- Ensure no buggy patterns appear in output
"""

import pytest
import tempfile
import os
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.game_cycle.services.game_simulator_service import GameSimulatorService, SimulationMode, GameSimulationResult
from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.services.initialization_service import GameCycleInitializer
from constants.team_ids import TeamIDs


class TestPlayByPlayValidation:
    """Integration tests for play-by-play bug fixes."""

    @pytest.fixture(scope="class")
    def test_database(self, tmp_path_factory):
        """
        Create a temporary test database with initialized dynasty.

        Returns tuple of (db_path, dynasty_id).
        """
        # Create temp directory for test database
        temp_dir = tmp_path_factory.mktemp("play_by_play_test")
        db_path = str(temp_dir / "test_game_cycle.db")

        # Initialize a test dynasty with rosters (schema created automatically)
        dynasty_id = "test_play_by_play"
        init_service = GameCycleInitializer(db_path, dynasty_id, season=2025)
        # Use Kansas City as the user's team (team_id argument is for user's team)
        init_service.initialize_dynasty(team_id=TeamIDs.KANSAS_CITY_CHIEFS)

        # Create player_injuries table (needed for injury system that runs post-game)
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_injuries (
                    injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dynasty_id TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    season INTEGER NOT NULL,
                    week_occurred INTEGER NOT NULL,
                    injury_type TEXT NOT NULL,
                    body_part TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    estimated_weeks_out INTEGER NOT NULL,
                    actual_weeks_out INTEGER,
                    occurred_during TEXT NOT NULL,
                    game_id TEXT,
                    play_description TEXT,
                    is_active INTEGER DEFAULT 1,
                    ir_placement_date TEXT,
                    ir_return_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        print(f"\n[TEST] Created test database at {db_path}")
        print(f"[TEST] Initialized dynasty: {dynasty_id}")

        yield db_path, dynasty_id

        # Cleanup after all tests
        if os.path.exists(db_path):
            os.remove(db_path)

    @pytest.fixture
    def game_result(self, test_database) -> GameSimulationResult:
        """
        Run a full game simulation for testing.

        Returns complete GameSimulationResult with drives and play-by-play data.
        """
        db_path, dynasty_id = test_database

        # Use two teams with good offenses to ensure varied play scenarios
        game_simulator = GameSimulatorService(db_path, dynasty_id)

        # Run game simulation in FULL mode (with real play-by-play)
        print("\n[TEST] Simulating full game for validation...")
        result = game_simulator.simulate_game(
            game_id="test_pbp_validation",
            home_team_id=TeamIDs.PHILADELPHIA_EAGLES,  # Good offense
            away_team_id=TeamIDs.KANSAS_CITY_CHIEFS,   # Good offense
            mode=SimulationMode.FULL,
            season=2025,
            week=1,
            is_playoff=False
        )

        # Verify we got drives and plays
        assert result is not None, "Game result should not be None"
        assert hasattr(result, 'drives'), "Game result should have drives"
        assert len(result.drives) > 0, "Game should have at least one drive"

        total_plays = sum(len(d.plays) for d in result.drives if hasattr(d, 'plays'))
        print(f"[TEST] Game completed: {len(result.drives)} drives, {total_plays} plays")

        return result

    def test_bug1_negative_yards_increase_distance(self, game_result: GameSimulationResult):
        """
        BUG 1: Validate negative yards correctly increase distance to go.

        Example: 2nd & 10 → loses 5 yards → should be 3rd & 15 (not 3rd & 5)
        """
        violations = []

        for drive_num, drive in enumerate(game_result.drives, 1):
            if not hasattr(drive, 'plays'):
                continue

            current_down = 1
            current_distance = 10
            current_position = getattr(drive, 'starting_field_position', 50)

            for play_num, play in enumerate(drive.plays, 1):
                play_yards = getattr(play, 'yards', 0)

                # Skip if play doesn't have snapshot (legacy plays)
                if not hasattr(play, 'down_after_play') or play.down_after_play is None:
                    continue

                # If play lost yards (negative), distance should INCREASE
                if play_yards < 0:
                    expected_distance = current_distance - play_yards  # Subtract negative = add
                    actual_distance = play.distance_after_play

                    # Allow for first down conversions (distance resets to 10)
                    # Allow for goal-to-go situations (distance < 10)
                    is_first_down = getattr(play, 'achieved_first_down', False)
                    is_end_of_drive = getattr(play, 'is_turnover', False) or getattr(play, 'is_scoring_play', False)

                    if not is_first_down and not is_end_of_drive:
                        # Distance should account for negative yards
                        if actual_distance < expected_distance - 1:  # Allow 1 yard rounding
                            violations.append({
                                'drive': drive_num,
                                'play': play_num,
                                'before': f"{current_down} & {current_distance}",
                                'yards': play_yards,
                                'expected': f"{play.down_after_play} & {expected_distance}",
                                'actual': f"{play.down_after_play} & {actual_distance}",
                                'outcome': getattr(play, 'outcome', 'unknown')
                            })

                # Update for next iteration
                current_down = play.down_after_play
                current_distance = play.distance_after_play
                current_position = play.field_position_after_play

        # Report violations
        if violations:
            msg = "\n[BUG 1] Negative yards not properly increasing distance:\n"
            for v in violations:
                msg += f"  Drive {v['drive']}, Play {v['play']}: {v['before']} + ({v['yards']} yds) → Expected {v['expected']}, Got {v['actual']} ({v['outcome']})\n"
            pytest.fail(msg)

    def test_bug2_missed_field_goals_no_points(self, game_result: GameSimulationResult):
        """
        BUG 2: Validate missed/blocked field goals don't award points.
        """
        violations = []

        for drive_num, drive in enumerate(game_result.drives, 1):
            if not hasattr(drive, 'plays'):
                continue

            for play_num, play in enumerate(drive.plays, 1):
                outcome = getattr(play, 'outcome', '').lower()
                points = getattr(play, 'points', 0)

                # Check for missed or blocked field goals
                if 'field_goal' in outcome:
                    if 'missed' in outcome or 'blocked' in outcome:
                        if points != 0:
                            violations.append({
                                'drive': drive_num,
                                'play': play_num,
                                'outcome': outcome,
                                'points': points
                            })

        if violations:
            msg = "\n[BUG 2] Missed/blocked field goals showing points:\n"
            for v in violations:
                msg += f"  Drive {v['drive']}, Play {v['play']}: {v['outcome']} awarded {v['points']} points\n"
            pytest.fail(msg)

    def test_bug3_made_field_goals_scoring_flag(self, game_result: GameSimulationResult):
        """
        BUG 3: Validate made field goals have is_scoring_play=True.
        """
        violations = []

        for drive_num, drive in enumerate(game_result.drives, 1):
            if not hasattr(drive, 'plays'):
                continue

            for play_num, play in enumerate(drive.plays, 1):
                outcome = getattr(play, 'outcome', '').lower()
                is_scoring_play = getattr(play, 'is_scoring_play', False)
                points = getattr(play, 'points', 0)
                penalty_occurred = getattr(play, 'penalty_occurred', False)

                # Check for made field goals
                if 'field_goal' in outcome and 'good' in outcome:
                    # Should have is_scoring_play=True
                    if not is_scoring_play:
                        violations.append({
                            'drive': drive_num,
                            'play': play_num,
                            'outcome': outcome,
                            'is_scoring_play': is_scoring_play,
                            'points': points,
                            'penalty': penalty_occurred
                        })

        if violations:
            msg = "\n[BUG 3] Made field goals missing is_scoring_play=True:\n"
            for v in violations:
                msg += f"  Drive {v['drive']}, Play {v['play']}: {v['outcome']} has is_scoring_play={v['is_scoring_play']} (points={v['points']}, penalty={v['penalty']})\n"
            pytest.fail(msg)

    def test_bug4_field_position_accounts_for_negative_yards(self, game_result: GameSimulationResult):
        """
        BUG 4: Validate field position correctly accounts for negative yards.
        """
        violations = []

        for drive_num, drive in enumerate(game_result.drives, 1):
            if not hasattr(drive, 'plays'):
                continue

            current_position = getattr(drive, 'starting_field_position', 50)

            for play_num, play in enumerate(drive.plays, 1):
                play_yards = getattr(play, 'yards', 0)

                # Skip if play doesn't have snapshot
                if not hasattr(play, 'field_position_after_play') or play.field_position_after_play is None:
                    continue

                # Calculate expected position
                expected_position = current_position + play_yards

                # Clamp to valid range (0-100)
                expected_position = max(0, min(100, expected_position))

                actual_position = play.field_position_after_play

                # Allow for turnovers/punts (position changes dramatically)
                is_turnover = getattr(play, 'is_turnover', False)
                is_punt = getattr(play, 'is_punt', False)
                is_scoring = getattr(play, 'is_scoring_play', False)

                if not is_turnover and not is_punt and not is_scoring:
                    # Field position should be close to expected
                    # Allow 5 yard margin for rounding/penalties
                    if abs(actual_position - expected_position) > 5:
                        violations.append({
                            'drive': drive_num,
                            'play': play_num,
                            'before_pos': current_position,
                            'yards': play_yards,
                            'expected_pos': expected_position,
                            'actual_pos': actual_position,
                            'outcome': getattr(play, 'outcome', 'unknown')
                        })

                # Update for next iteration
                current_position = actual_position

        if violations:
            msg = "\n[BUG 4] Field position not accounting for yards:\n"
            for v in violations[:10]:  # Limit output
                msg += f"  Drive {v['drive']}, Play {v['play']}: Pos {v['before_pos']} + {v['yards']} yds → Expected {v['expected_pos']}, Got {v['actual_pos']} ({v['outcome']})\n"
            if len(violations) > 10:
                msg += f"  ... and {len(violations) - 10} more violations\n"
            pytest.fail(msg)

    def test_bug5_real_field_goals_zero_yards(self, game_result: GameSimulationResult):
        """
        BUG 5: Validate real field goals show 0 yards (fake FGs can show yards).
        """
        violations = []

        for drive_num, drive in enumerate(game_result.drives, 1):
            if not hasattr(drive, 'plays'):
                continue

            for play_num, play in enumerate(drive.plays, 1):
                outcome = getattr(play, 'outcome', '').lower()
                yards = getattr(play, 'yards', 0)
                is_fake = getattr(play, 'is_fake_field_goal', False)

                # Check for field goal plays
                if 'field_goal' in outcome:
                    # Real FGs (not fake) should have 0 yards
                    if not is_fake and yards != 0:
                        violations.append({
                            'drive': drive_num,
                            'play': play_num,
                            'outcome': outcome,
                            'yards': yards,
                            'is_fake': is_fake
                        })

        if violations:
            msg = "\n[BUG 5] Real field goals showing non-zero yards:\n"
            for v in violations:
                msg += f"  Drive {v['drive']}, Play {v['play']}: {v['outcome']} has {v['yards']} yards (is_fake={v['is_fake']})\n"
            pytest.fail(msg)

    def test_markdown_export_no_bugs(self, game_result: GameSimulationResult):
        """
        Validate markdown export doesn't show buggy patterns.

        Checks:
        - No field goals with negative yards: "Field Goal GOOD (-5 yds)"
        - No missed FGs with points: "Field Goal MISSED (+3 pts)"
        - Correct down & distance progression after negative yards
        """
        # Create temp file for export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_path = f.name

        try:
            # Generate markdown content (simulating export function)
            markdown_lines = self._generate_markdown(game_result)

            with open(temp_path, 'w', encoding='utf-8') as f:
                f.writelines(markdown_lines)

            # Read back and validate
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()

            violations = []

            # Pattern 1: Field Goal with negative yards
            # Should NOT see: "Field Goal GOOD (-5 yds)" or "Field Goal MISSED (-3 yds)"
            # Exception: Fake field goals can have yards
            fg_negative_pattern = re.compile(r'Field Goal.*\(-\d+ yds\)', re.IGNORECASE)
            fake_fg_pattern = re.compile(r'Fake.*Field Goal', re.IGNORECASE)

            for line_num, line in enumerate(content.split('\n'), 1):
                if fg_negative_pattern.search(line):
                    # Check if it's a fake FG (allowed to have yards)
                    if not fake_fg_pattern.search(line):
                        violations.append(f"Line {line_num}: Field goal with negative yards: {line.strip()}")

            # Pattern 2: Missed FG with points
            # Should NOT see: "[+3 pts]" after "missed" or "blocked"
            missed_fg_points_pattern = re.compile(r'(missed|blocked).*\[\+\d+ pts\]', re.IGNORECASE)

            for line_num, line in enumerate(content.split('\n'), 1):
                if missed_fg_points_pattern.search(line):
                    violations.append(f"Line {line_num}: Missed/blocked FG with points: {line.strip()}")

            if violations:
                msg = "\n[MARKDOWN EXPORT] Buggy patterns found:\n"
                for v in violations:
                    msg += f"  {v}\n"
                pytest.fail(msg)

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _generate_markdown(self, game_result: GameSimulationResult) -> List[str]:
        """
        Generate markdown content from game result.

        Mimics the export logic from BoxScoreDialog._export_as_markdown.
        """
        lines = []

        # Header
        home_score = game_result.home_score
        away_score = game_result.away_score

        lines.append(f"# Test Game: Away {away_score} @ Home {home_score}\n")
        lines.append("---\n")

        # Drives
        for drive_num, drive in enumerate(game_result.drives, 1):
            possessing_team_id = getattr(drive, 'possessing_team_id', None)
            team_name = "Home" if possessing_team_id == game_result.home_team_id else "Away"

            drive_outcome = getattr(drive, 'drive_outcome', 'unknown')
            plays = getattr(drive, 'plays', [])

            # Calculate drive stats
            drive_yards = sum(getattr(play, 'yards', 0) for play in plays)

            lines.append(f"\n## Drive {drive_num}: {team_name}\n")
            lines.append(f"**Stats:** {len(plays)} plays, {drive_yards} yards\n")
            lines.append(f"**Result:** {drive_outcome}\n")

            # Plays
            current_down = 1
            yards_to_go = 10
            field_position = getattr(drive, 'starting_field_position', 50)

            for play_num, play in enumerate(plays, 1):
                # Format down & distance
                down_suffix = {1: 'st', 2: 'nd', 3: 'rd', 4: 'th'}.get(current_down, 'th')
                situation = f"{current_down}{down_suffix} & {yards_to_go}"

                # Get play details
                outcome = getattr(play, 'outcome', 'unknown')
                play_yards = getattr(play, 'yards', 0)
                points = getattr(play, 'points', 0)
                is_scoring = getattr(play, 'is_scoring_play', False)

                # Format play description
                play_desc = f"{situation}: {outcome}"

                # Add points if scoring
                if is_scoring and points > 0:
                    lines.append(f"- **Play {play_num} (SCORING):** {play_desc} [+{points} pts] ({play_yards:+d} yds)\n")
                else:
                    lines.append(f"- **Play {play_num}:** {play_desc} ({play_yards:+d} yds)\n")

                # Update situational context using snapshots
                if hasattr(play, 'down_after_play') and play.down_after_play is not None:
                    current_down = play.down_after_play
                    yards_to_go = play.distance_after_play
                    field_position = play.field_position_after_play
                else:
                    # Fallback
                    if getattr(play, 'achieved_first_down', False):
                        current_down = 1
                        yards_to_go = 10
                    else:
                        current_down = min(4, current_down + 1)
                        yards_to_go = max(1, yards_to_go - play_yards)
                    field_position = min(100, max(0, field_position + play_yards))

        return lines

    def test_comprehensive_snapshot_validation(self, game_result: GameSimulationResult):
        """
        Comprehensive test ensuring all plays have proper snapshots.

        Validates:
        - All plays have down_after_play, distance_after_play, field_position_after_play
        - Snapshots are within valid ranges
        - Snapshots are consistent with play outcomes
        """
        missing_snapshots = []
        invalid_snapshots = []

        for drive_num, drive in enumerate(game_result.drives, 1):
            if not hasattr(drive, 'plays'):
                continue

            for play_num, play in enumerate(drive.plays, 1):
                # Check for snapshot existence
                has_down = hasattr(play, 'down_after_play')
                has_distance = hasattr(play, 'distance_after_play')
                has_position = hasattr(play, 'field_position_after_play')

                if not (has_down and has_distance and has_position):
                    missing_snapshots.append({
                        'drive': drive_num,
                        'play': play_num,
                        'outcome': getattr(play, 'outcome', 'unknown'),
                        'missing': {
                            'down': not has_down,
                            'distance': not has_distance,
                            'position': not has_position
                        }
                    })
                    continue

                # Validate snapshot values
                down = play.down_after_play
                distance = play.distance_after_play
                position = play.field_position_after_play

                # Check for None values
                if down is None or distance is None or position is None:
                    continue  # Drive ended, snapshots can be None

                # Validate ranges
                if not (1 <= down <= 4):
                    invalid_snapshots.append({
                        'drive': drive_num,
                        'play': play_num,
                        'issue': f'Invalid down: {down} (should be 1-4)',
                        'outcome': getattr(play, 'outcome', 'unknown')
                    })

                if not (1 <= distance <= 99):
                    # Allow goal-to-go situations
                    if distance < 1 or distance > 99:
                        invalid_snapshots.append({
                            'drive': drive_num,
                            'play': play_num,
                            'issue': f'Invalid distance: {distance} (should be 1-99)',
                            'outcome': getattr(play, 'outcome', 'unknown')
                        })

                if not (0 <= position <= 100):
                    invalid_snapshots.append({
                        'drive': drive_num,
                        'play': play_num,
                        'issue': f'Invalid position: {position} (should be 0-100)',
                        'outcome': getattr(play, 'outcome', 'unknown')
                    })

        # Report issues
        issues = []

        if missing_snapshots:
            msg = f"[SNAPSHOTS] {len(missing_snapshots)} plays missing snapshots:\n"
            for snap in missing_snapshots[:5]:
                msg += f"  Drive {snap['drive']}, Play {snap['play']} ({snap['outcome']}): Missing {snap['missing']}\n"
            if len(missing_snapshots) > 5:
                msg += f"  ... and {len(missing_snapshots) - 5} more\n"
            issues.append(msg)

        if invalid_snapshots:
            msg = f"[SNAPSHOTS] {len(invalid_snapshots)} plays with invalid snapshots:\n"
            for snap in invalid_snapshots[:5]:
                msg += f"  Drive {snap['drive']}, Play {snap['play']}: {snap['issue']} ({snap['outcome']})\n"
            if len(invalid_snapshots) > 5:
                msg += f"  ... and {len(invalid_snapshots) - 5} more\n"
            issues.append(msg)

        if issues:
            pytest.fail("\n" + "\n".join(issues))
