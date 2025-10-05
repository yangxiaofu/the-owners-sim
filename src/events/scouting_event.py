"""
Scouting Event

Example of a result-based event where the VALUE is in the output (scouting reports),
not in the input parameters. Demonstrates the hybrid storage pattern for events
that generate content rather than replay scenarios.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from events.base_event import BaseEvent, EventResult
import random


class ScoutingEvent(BaseEvent):
    """
    Scouting event that generates player evaluation reports.

    This is a **result-based event** where:
    - Parameters are minimal (just scout_type and target positions)
    - The VALUE is in the results (scouting reports generated)
    - Cannot be "replayed" - reports are unique and stored

    Use Case: College scouting, pro day evaluations, free agent assessments

    Storage Pattern:
    - Store WITH results after execution
    - Historical retrieval shows original reports
    - No re-simulation (reports are deterministic per execution)
    """

    def __init__(
        self,
        scout_type: str,
        target_positions: Optional[List[str]] = None,
        num_players: int = 5,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        dynasty_id: str = "default"
    ):
        """
        Initialize scouting event.

        Args:
            scout_type: Type of scouting ("college", "pro", "free_agent")
            target_positions: List of positions to scout (e.g., ["QB", "WR"])
            num_players: Number of players to evaluate
            event_id: Optional event identifier
            timestamp: Optional event timestamp
            dynasty_id: Dynasty context for isolation
        """
        super().__init__(event_id=event_id, timestamp=timestamp or datetime.now(), dynasty_id=dynasty_id)

        self.scout_type = scout_type
        self.target_positions = target_positions or ["QB", "RB", "WR", "TE"]
        self.num_players = num_players

        # Results stored after execution
        self._scouting_reports = None
        self._cached_result = None

    def get_event_type(self) -> str:
        """Return event type identifier"""
        return "SCOUTING"

    def get_game_id(self) -> str:
        """Return game/context identifier"""
        return f"scouting_{self.scout_type}"

    def _get_parameters(self) -> Dict[str, Any]:
        """
        Return minimal parameters - just what type of scouting to run.

        For result-based events, parameters are minimal since the value
        is in the generated output, not the input configuration.

        Returns:
            Dictionary with scout configuration
        """
        return {
            "scout_type": self.scout_type,
            "target_positions": self.target_positions,
            "num_players": self.num_players
        }

    def _get_results(self) -> Optional[Dict[str, Any]]:
        """
        Return scouting reports - this IS the value of the event.

        For result-based events, this is the primary content.

        Returns:
            Dictionary with scouting reports, or None if not yet executed
        """
        if not self._scouting_reports:
            return None

        return {
            "scouting_reports": self._scouting_reports,
            "total_players_evaluated": len(self._scouting_reports),
            "scout_confidence": "high",  # Could calculate based on scout quality
            "generated_at": datetime.now().isoformat(),
            "top_prospect": self._get_top_prospect()
        }

    def _get_metadata(self) -> Dict[str, Any]:
        """
        Return additional scouting context.

        Returns:
            Dictionary with supplementary information
        """
        return {
            "scout_type": self.scout_type,
            "positions_targeted": self.target_positions,
            "scouting_department": "College Scouting",  # Could be configurable
            "region": "National"  # Could be configurable
        }

    def simulate(self) -> EventResult:
        """
        Execute scouting evaluation and generate player reports.

        This is where the core value is created - the scouting reports themselves.

        Returns:
            EventResult with scouting reports in data
        """
        try:
            print(f"\n🔍 Running {self.scout_type} scouting evaluation...")
            print(f"   Positions: {', '.join(self.target_positions)}")
            print(f"   Target: {self.num_players} players")

            # Generate scouting reports (this is the core content)
            self._scouting_reports = self._generate_scouting_reports()

            print(f"✅ Scouting complete: {len(self._scouting_reports)} players evaluated")

            result = EventResult(
                event_id=self.event_id,
                event_type="SCOUTING",
                success=True,
                timestamp=datetime.now(),
                data={
                    "scouting_reports": self._scouting_reports,
                    "scout_type": self.scout_type,
                    "total_evaluated": len(self._scouting_reports)
                }
            )

            # Cache result
            self._cached_result = result

            return result

        except Exception as e:
            error_msg = f"Scouting evaluation failed: {str(e)}"
            print(f"❌ {error_msg}")

            return EventResult(
                event_id=self.event_id,
                event_type="SCOUTING",
                success=False,
                timestamp=datetime.now(),
                data={"scout_type": self.scout_type},
                error_message=error_msg
            )

    def _generate_scouting_reports(self) -> List[Dict[str, Any]]:
        """
        Generate player evaluation reports.

        This is a placeholder that simulates scouting output.
        In a real implementation, this would integrate with:
        - Player database
        - Scouting algorithms
        - Historical performance data

        Returns:
            List of scouting report dictionaries
        """
        reports = []

        # Sample player names for demo
        first_names = ["John", "Mike", "David", "James", "Robert", "Chris", "Matt", "Tom"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson"]

        # Sample strengths/weaknesses by position
        position_traits = {
            "QB": {
                "strengths": ["Arm strength", "Field vision", "Leadership", "Accuracy", "Quick release"],
                "weaknesses": ["Mobility", "Pocket presence", "Decision making", "Touch"]
            },
            "RB": {
                "strengths": ["Speed", "Vision", "Power", "Hands", "Blocking"],
                "weaknesses": ["Durability", "Pass protection", "Fumbles"]
            },
            "WR": {
                "strengths": ["Speed", "Route running", "Hands", "YAC", "Blocking"],
                "weaknesses": ["Drops", "Size", "Physicality"]
            },
            "TE": {
                "strengths": ["Blocking", "Hands", "Size", "Speed", "Route running"],
                "weaknesses": ["Speed", "Route tree", "Separation"]
            }
        }

        grades = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
        draft_rounds = ["1st round", "2nd round", "3rd round", "4th-5th round", "6th-7th round", "UDFA"]

        for i in range(self.num_players):
            position = random.choice(self.target_positions)
            traits = position_traits.get(position, position_traits["WR"])

            player_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            overall_grade = random.choice(grades)

            report = {
                "player_name": player_name,
                "position": position,
                "school": f"University {i+1}",  # Placeholder
                "overall_grade": overall_grade,
                "strengths": random.sample(traits["strengths"], k=min(3, len(traits["strengths"]))),
                "weaknesses": random.sample(traits["weaknesses"], k=min(2, len(traits["weaknesses"]))),
                "draft_projection": random.choice(draft_rounds),
                "nfl_comparison": f"Similar to starter #{i+1}",  # Placeholder
                "scout_notes": f"Evaluated {player_name} during {self.scout_type} scouting. Shows potential at {position}."
            }

            reports.append(report)

        return reports

    def _get_top_prospect(self) -> Optional[Dict[str, Any]]:
        """Get the highest graded prospect from reports"""
        if not self._scouting_reports:
            return None

        # Grade ranking (A+ highest)
        grade_values = {"A+": 100, "A": 95, "A-": 90, "B+": 85, "B": 80, "B-": 75, "C+": 70, "C": 65}

        top_prospect = max(
            self._scouting_reports,
            key=lambda r: grade_values.get(r["overall_grade"], 0)
        )

        return {
            "name": top_prospect["player_name"],
            "position": top_prospect["position"],
            "grade": top_prospect["overall_grade"]
        }

    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate scouting event can execute.

        Returns:
            (True, None) if valid, (False, error_message) if invalid
        """
        if not self.scout_type:
            return False, "Scout type is required"

        valid_scout_types = ["college", "pro", "free_agent"]
        if self.scout_type not in valid_scout_types:
            return False, f"Invalid scout_type: {self.scout_type} (must be one of {valid_scout_types})"

        if self.num_players < 1:
            return False, f"num_players must be positive, got {self.num_players}"

        if not self.target_positions:
            return False, "At least one target position required"

        return True, None

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'ScoutingEvent':
        """
        Reconstruct ScoutingEvent from database data.

        For result-based events, this loads the historical reports
        rather than parameters for replay.

        Args:
            event_data: Dictionary from EventDatabaseAPI.get_event_by_id()

        Returns:
            Reconstructed ScoutingEvent with historical reports
        """
        data = event_data['data']

        # Handle new three-part structure
        if 'parameters' in data:
            params = data['parameters']
        else:
            # Backward compatibility
            params = data

        scout = cls(
            scout_type=params['scout_type'],
            target_positions=params.get('target_positions', []),
            num_players=params.get('num_players', 5),
            event_id=event_data['event_id'],
            dynasty_id=event_data.get('dynasty_id', 'default')
        )

        # Load historical scouting reports (don't regenerate)
        if 'results' in data and data['results']:
            scout._scouting_reports = data['results']['scouting_reports']

            # Recreate cached result
            scout._cached_result = EventResult(
                event_id=event_data['event_id'],
                event_type="SCOUTING",
                success=True,
                timestamp=event_data['timestamp'],
                data=data['results']
            )

        return scout

    def __str__(self) -> str:
        """String representation"""
        return f"ScoutingEvent: {self.scout_type} ({len(self.target_positions)} positions)"

    def __repr__(self) -> str:
        """Detailed representation"""
        return (
            f"ScoutingEvent(scout_type='{self.scout_type}', "
            f"positions={self.target_positions}, id={self.event_id})"
        )
