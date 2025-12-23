"""
HOF Induction Service - Handle Hall of Fame induction ceremonies.

Creates permanent HOF records with:
- Generated speech highlights
- Presenter selection
- Bust description
- Achievement summaries
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
import random
import logging

from game_cycle.database.hof_api import HOFAPI, HOFVotingResult
from game_cycle.database.connection import GameCycleDatabase

if TYPE_CHECKING:
    from game_cycle.services.hof_eligibility_service import HOFCandidate

logger = logging.getLogger(__name__)


# ============================================
# Dataclasses
# ============================================

@dataclass
class InductionSpeechHighlights:
    """
    Generated speech excerpts for induction ceremony.

    Each field contains a quote from the inductee's speech,
    representing different parts of the typical HOF speech structure.
    """
    opening: str           # "Thank you to the Hall selection committee..."
    career_reflection: str # "When I was drafted by the Bears..."
    thank_yous: str        # "I want to thank Coach Smith, my teammates..."
    legacy_statement: str  # "I hope I've made this city proud..."
    closing: str           # "God bless you all, and Go Bears!"

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for serialization."""
        return {
            'opening': self.opening,
            'career_reflection': self.career_reflection,
            'thank_yous': self.thank_yous,
            'legacy_statement': self.legacy_statement,
            'closing': self.closing,
        }


@dataclass
class InductionCeremony:
    """
    Complete induction ceremony data.

    Contains all information needed to display the HOF induction
    in the UI, including speech excerpts, presenter info, and
    career achievements.
    """
    inductee_id: int
    inductee_name: str
    position: str
    induction_season: int

    # Presenter (former teammate, coach, or family)
    presenter_name: str
    presenter_relationship: str

    # Speech content
    speech_highlights: InductionSpeechHighlights

    # Career summary for display
    career_summary: str
    career_stats: Dict[str, Any]
    achievements: List[str]

    # Visual elements
    bust_description: str   # "Bronze bust captures his intense gaze..."
    jacket_moment: str      # "He slipped on the gold jacket..."

    # Voting info
    vote_percentage: float
    is_first_ballot: bool
    years_on_ballot: int

    # Team info
    primary_team: str
    teams_played_for: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'inductee_id': self.inductee_id,
            'inductee_name': self.inductee_name,
            'position': self.position,
            'induction_season': self.induction_season,
            'presenter_name': self.presenter_name,
            'presenter_relationship': self.presenter_relationship,
            'speech_highlights': self.speech_highlights.to_dict(),
            'career_summary': self.career_summary,
            'career_stats': self.career_stats,
            'achievements': self.achievements,
            'bust_description': self.bust_description,
            'jacket_moment': self.jacket_moment,
            'vote_percentage': self.vote_percentage,
            'is_first_ballot': self.is_first_ballot,
            'years_on_ballot': self.years_on_ballot,
            'primary_team': self.primary_team,
            'teams_played_for': self.teams_played_for,
        }


# ============================================
# Speech Templates
# ============================================

SPEECH_TEMPLATES = {
    "opening": [
        "Standing here in Canton, I'm overwhelmed with gratitude.",
        "Thirty years ago, I was just a kid with a dream. Today, that dream is complete.",
        "To be mentioned alongside the legends in this hall... it's beyond words.",
        "This moment represents everything I worked for my entire career.",
        "When I started playing football, I never imagined I'd end up here.",
        "Canton, Ohio. The pinnacle of our sport. I'm truly humbled.",
    ],
    "career_reflection": [
        "When {team} drafted me, I had no idea where this journey would lead.",
        "I remember my first game like it was yesterday. The nerves, the excitement.",
        "Every snap, every hit, every victory and defeat brought me to this moment.",
        "{seasons} seasons. Every single one of them meant something special.",
        "From rookie to veteran, {team} was my home, my family.",
        "The game taught me about perseverance, sacrifice, and brotherhood.",
    ],
    "thank_yous": [
        "To my teammates who went to war with me every Sunday - this is ours.",
        "To the coaches who believed in me when others didn't - thank you.",
        "To my family, who sacrificed so I could chase this dream - I love you.",
        "To the fans who cheered through the wins and stayed through the losses - this is for you.",
        "To every player I competed against - you made me better.",
        "To {team} organization - thank you for giving me a chance.",
    ],
    "legacy": [
        "I hope I represented {team} with honor and pride.",
        "If I inspired one kid to never give up, this was all worth it.",
        "Football gave me everything. I hope I gave something back.",
        "This game is bigger than any one player. I was blessed to be part of it.",
        "The memories we created together will last forever.",
        "I gave this game everything I had. It gave me back even more.",
    ],
    "closing": [
        "Thank you, Canton. Thank you, football. God bless you all.",
        "Go {team}! Forever and always.",
        "To all the young players out there - dream big. This could be you someday.",
        "I'm proud to forever be a part of this fraternity of greatness.",
        "This isn't goodbye. Football will always be in my heart.",
        "Thank you for this incredible honor. I'll cherish it forever.",
    ],
}

# Bust description templates by position group
BUST_TEMPLATES = {
    "QB": [
        "The bronze bust captures {name}'s trademark intensity, eyes scanning the field for an open receiver.",
        "Cast in bronze, {name}'s confident gaze reflects the poise that defined his career.",
        "The sculptor perfectly captured {name}'s focused determination, arm cocked and ready to deliver.",
    ],
    "RB": [
        "The bronze captures {name}'s powerful build and determined eyes, ready to break through the line.",
        "{name}'s bust shows the fierce determination of a runner who never went down easy.",
        "In bronze, {name}'s chiseled features reflect the toughness that defined his running style.",
    ],
    "WR": [
        "The bust captures {name}'s intense focus, eyes locked on an imaginary football.",
        "{name}'s bronze likeness shows the concentration of a receiver tracking a deep ball.",
        "The sculptor captured {name}'s confident smile, the look of a player who knew he was open.",
    ],
    "TE": [
        "The bust shows {name}'s versatile nature - part receiver, part blocker, all warrior.",
        "{name}'s bronze captures the intelligence and toughness of football's most demanding position.",
        "In bronze, {name}'s focused expression reflects the cerebral approach he brought to tight end.",
    ],
    "OL": [
        "The bust captures {name}'s stoic determination, the face of protection and sacrifice.",
        "{name}'s bronze shows the quiet strength of an offensive lineman - the unsung hero.",
        "The sculptor captured {name}'s steady gaze, the look of a player who never missed an assignment.",
    ],
    "DL": [
        "The bronze captures {name}'s intimidating presence, the face that haunted quarterbacks.",
        "{name}'s bust shows the relentless aggression of a true pass-rushing terror.",
        "In bronze, {name}'s fierce expression reflects the dominance he brought every snap.",
    ],
    "LB": [
        "The bust captures {name}'s fierce intensity, the heart of every defense he anchored.",
        "{name}'s bronze shows the combination of instinct and aggression that made him great.",
        "The sculptor captured {name}'s commanding presence - a true field general.",
    ],
    "DB": [
        "The bust captures {name}'s calculating eyes, always reading the quarterback's intentions.",
        "{name}'s bronze shows the confidence of a player who owned his side of the field.",
        "In bronze, {name}'s alert expression reflects the anticipation of another interception.",
    ],
    "K": [
        "The bust captures {name}'s calm focus, the composure of a clutch performer.",
        "{name}'s bronze shows the concentration of a player who thrived under pressure.",
        "The sculptor captured {name}'s steady gaze - ice in his veins, gold on his foot.",
    ],
    "P": [
        "The bust captures {name}'s precision focus, the specialist's attention to detail.",
        "{name}'s bronze shows the quiet confidence of a player who changed field position.",
        "In bronze, {name}'s composed expression reflects the consistency he brought every punt.",
    ],
}

# Jacket moment templates
JACKET_MOMENT_TEMPLATES = [
    "As {name} slipped on the gold jacket, tears welled in his eyes.",
    "The gold jacket fit perfectly on {name}'s shoulders - a moment years in the making.",
    "{name} buttoned the iconic gold jacket, officially joining football's immortals.",
    "With trembling hands, {name} accepted the gold jacket that symbolizes football's highest honor.",
    "The gold jacket ceremony brought {name} to tears as the weight of the moment set in.",
]

# Presenter relationship templates
PRESENTER_RELATIONSHIPS = [
    ("Former Head Coach", "head_coach"),
    ("Former Teammate", "teammate"),
    ("Position Coach", "position_coach"),
    ("Former General Manager", "gm"),
    ("Family Member", "family"),
]


# ============================================
# HOFInductionService Class
# ============================================

class HOFInductionService:
    """
    Handles Hall of Fame induction ceremonies.

    Responsibilities:
    - Create permanent HOF record in database
    - Generate speech highlights using templates
    - Select presenter based on available relationships
    - Generate bust description and ceremony narrative
    - Build achievement summary list
    """

    # Position group mapping for bust templates
    POSITION_TO_GROUP = {
        'QB': 'QB',
        'RB': 'RB', 'HB': 'RB', 'FB': 'RB',
        'WR': 'WR',
        'TE': 'TE',
        'LT': 'OL', 'LG': 'OL', 'C': 'OL', 'RG': 'OL', 'RT': 'OL',
        'LE': 'DL', 'DT': 'DL', 'RE': 'DL', 'NT': 'DL', 'EDGE': 'DL', 'DE': 'DL',
        'LOLB': 'LB', 'MLB': 'LB', 'ROLB': 'LB', 'ILB': 'LB', 'OLB': 'LB', 'LB': 'LB',
        'CB': 'DB', 'FS': 'DB', 'SS': 'DB', 'S': 'DB',
        'K': 'K',
        'P': 'P',
    }

    def __init__(
        self,
        db: Optional[GameCycleDatabase] = None,
        dynasty_id: Optional[str] = None,
        seed: Optional[int] = None
    ):
        """
        Initialize induction service.

        Args:
            db: Optional GameCycleDatabase for persisting records
            dynasty_id: Optional dynasty ID for database operations
            seed: Optional random seed for reproducible generation
        """
        self.db = db
        self.dynasty_id = dynasty_id
        if seed is not None:
            random.seed(seed)

    def create_induction(
        self,
        voting_result: HOFVotingResult,
        candidate: "HOFCandidate",
        persist: bool = True
    ) -> InductionCeremony:
        """
        Create induction record and ceremony data.

        Args:
            voting_result: HOFVotingResult from voting engine
            candidate: HOFCandidate with career data
            persist: Whether to save to database (requires db and dynasty_id)

        Returns:
            InductionCeremony with complete ceremony data
        """
        # Build achievements list
        achievements = self._build_achievements_list(candidate)

        # Generate speech highlights
        speech = self._generate_speech(
            player_name=candidate.player_name,
            position=candidate.primary_position,
            teams=candidate.teams_played_for,
            achievements=achievements,
            career_seasons=candidate.career_seasons
        )

        # Select presenter
        presenter_name, presenter_relationship = self._select_presenter(
            player_name=candidate.player_name,
            teams=candidate.teams_played_for,
            position=candidate.primary_position
        )

        # Generate bust description
        bust_description = self._generate_bust_description(
            player_name=candidate.player_name,
            position=candidate.primary_position
        )

        # Generate jacket moment
        jacket_moment = self._generate_jacket_moment(candidate.player_name)

        # Build career summary
        career_summary = self._build_career_summary(candidate, achievements)

        # Get primary team (first team or most recent)
        primary_team = candidate.teams_played_for[0] if candidate.teams_played_for else "Unknown"

        # Create ceremony object
        ceremony = InductionCeremony(
            inductee_id=candidate.player_id,
            inductee_name=candidate.player_name,
            position=candidate.primary_position,
            induction_season=voting_result.voting_season,
            presenter_name=presenter_name,
            presenter_relationship=presenter_relationship,
            speech_highlights=speech,
            career_summary=career_summary,
            career_stats=candidate.career_stats,
            achievements=achievements,
            bust_description=bust_description,
            jacket_moment=jacket_moment,
            vote_percentage=voting_result.vote_percentage,
            is_first_ballot=voting_result.is_first_ballot,
            years_on_ballot=voting_result.years_on_ballot,
            primary_team=primary_team,
            teams_played_for=candidate.teams_played_for,
        )

        # Persist to database if configured
        if persist and self.db and self.dynasty_id:
            self._save_inductee(ceremony, candidate)

        return ceremony

    def create_batch_inductions(
        self,
        voting_results: List[HOFVotingResult],
        candidates: List["HOFCandidate"],
        persist: bool = True
    ) -> List[InductionCeremony]:
        """
        Create induction ceremonies for multiple inductees.

        Args:
            voting_results: List of HOFVotingResult (inducted only)
            candidates: List of corresponding HOFCandidate objects
            persist: Whether to save to database

        Returns:
            List of InductionCeremony objects
        """
        # Build candidate lookup by player_id
        candidate_map = {c.player_id: c for c in candidates}

        ceremonies = []
        for result in voting_results:
            candidate = candidate_map.get(result.player_id)
            if candidate:
                ceremony = self.create_induction(result, candidate, persist)
                ceremonies.append(ceremony)
            else:
                logger.warning(f"No candidate found for inducted player {result.player_id}")

        return ceremonies

    def _generate_speech(
        self,
        player_name: str,
        position: str,
        teams: List[str],
        achievements: List[str],
        career_seasons: int
    ) -> InductionSpeechHighlights:
        """
        Generate speech excerpts for the inductee.

        Uses templates with variable substitution for personalization.

        Args:
            player_name: Inductee's name
            position: Primary position
            teams: List of teams played for
            achievements: List of achievement strings
            career_seasons: Total career seasons

        Returns:
            InductionSpeechHighlights with generated excerpts
        """
        primary_team = teams[0] if teams else "my team"

        # Build substitution context
        context = {
            'name': player_name,
            'team': primary_team,
            'seasons': str(career_seasons),
            'position': position,
        }

        # Select random template for each section and apply substitutions
        opening = self._select_and_format(SPEECH_TEMPLATES['opening'], context)
        career_reflection = self._select_and_format(SPEECH_TEMPLATES['career_reflection'], context)
        thank_yous = self._select_and_format(SPEECH_TEMPLATES['thank_yous'], context)
        legacy = self._select_and_format(SPEECH_TEMPLATES['legacy'], context)
        closing = self._select_and_format(SPEECH_TEMPLATES['closing'], context)

        return InductionSpeechHighlights(
            opening=opening,
            career_reflection=career_reflection,
            thank_yous=thank_yous,
            legacy_statement=legacy,
            closing=closing,
        )

    def _select_and_format(
        self,
        templates: List[str],
        context: Dict[str, str]
    ) -> str:
        """
        Select random template and apply context substitutions.

        Args:
            templates: List of template strings
            context: Dict of substitution values

        Returns:
            Formatted string with substitutions applied
        """
        template = random.choice(templates)
        try:
            return template.format(**context)
        except KeyError:
            # If template has unmatched keys, return as-is
            return template

    def _select_presenter(
        self,
        player_name: str,
        teams: List[str],
        position: str
    ) -> Tuple[str, str]:
        """
        Select presenter for induction ceremony.

        In a full implementation, this would query staff/player records
        to find actual former coaches or teammates. For now, generates
        plausible presenter based on position and team.

        Args:
            player_name: Inductee's name
            teams: List of teams played for
            position: Primary position

        Returns:
            Tuple of (presenter_name, presenter_relationship)
        """
        primary_team = teams[0] if teams else "Team"

        # Generate plausible presenter based on relationship type
        relationship_type = random.choice(PRESENTER_RELATIONSHIPS)
        relationship_display, relationship_key = relationship_type

        # Generate presenter name based on relationship
        if relationship_key == "head_coach":
            presenter_name = self._generate_coach_name()
        elif relationship_key == "teammate":
            presenter_name = self._generate_player_name()
        elif relationship_key == "position_coach":
            presenter_name = self._generate_coach_name()
        elif relationship_key == "gm":
            presenter_name = self._generate_executive_name()
        else:  # family
            # Use last name from inductee
            last_name = player_name.split()[-1] if player_name else "Smith"
            presenter_name = f"{random.choice(['John', 'Michael', 'Sarah', 'Lisa'])} {last_name}"
            relationship_display = "Family Member"

        return presenter_name, relationship_display

    def _generate_coach_name(self) -> str:
        """Generate a plausible coach name."""
        first_names = ["Bill", "Mike", "John", "Tom", "Dan", "Jim", "Bob", "Steve", "Andy", "Sean"]
        last_names = ["Johnson", "Williams", "Brown", "Davis", "Wilson", "Anderson", "Thompson", "Martinez"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def _generate_player_name(self) -> str:
        """Generate a plausible player name."""
        first_names = ["Marcus", "James", "Derek", "Brandon", "Chris", "Anthony", "Kevin", "David"]
        last_names = ["Smith", "Jackson", "Thomas", "Harris", "Robinson", "Clark", "Lewis", "Walker"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def _generate_executive_name(self) -> str:
        """Generate a plausible executive name."""
        first_names = ["Richard", "George", "Robert", "William", "Charles", "Edward", "Thomas"]
        last_names = ["Morgan", "Bennett", "Harrison", "Sullivan", "Crawford", "Patterson"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def _generate_bust_description(
        self,
        player_name: str,
        position: str
    ) -> str:
        """
        Generate narrative description of bronze bust.

        Args:
            player_name: Inductee's name
            position: Primary position

        Returns:
            Bust description string
        """
        # Get position group for template selection
        pos_group = self.POSITION_TO_GROUP.get(position.upper(), 'LB')
        templates = BUST_TEMPLATES.get(pos_group, BUST_TEMPLATES['LB'])

        template = random.choice(templates)
        return template.format(name=player_name)

    def _generate_jacket_moment(self, player_name: str) -> str:
        """
        Generate the gold jacket ceremony moment description.

        Args:
            player_name: Inductee's name

        Returns:
            Jacket moment description
        """
        template = random.choice(JACKET_MOMENT_TEMPLATES)
        return template.format(name=player_name)

    def _build_achievements_list(self, candidate: "HOFCandidate") -> List[str]:
        """
        Build list of achievement strings for display.

        Args:
            candidate: HOFCandidate with career data

        Returns:
            List of achievement strings (e.g., "2x MVP", "3x Super Bowl Champion")
        """
        achievements = []

        # MVP
        if candidate.mvp_awards > 0:
            if candidate.mvp_awards == 1:
                achievements.append("MVP")
            else:
                achievements.append(f"{candidate.mvp_awards}x MVP")

        # Super Bowl
        if candidate.super_bowl_wins > 0:
            if candidate.super_bowl_wins == 1:
                achievements.append("Super Bowl Champion")
            else:
                achievements.append(f"{candidate.super_bowl_wins}x Super Bowl Champion")

        # All-Pro First Team
        if candidate.all_pro_first_team > 0:
            if candidate.all_pro_first_team == 1:
                achievements.append("First-Team All-Pro")
            else:
                achievements.append(f"{candidate.all_pro_first_team}x First-Team All-Pro")

        # All-Pro Second Team
        if candidate.all_pro_second_team > 0:
            if candidate.all_pro_second_team == 1:
                achievements.append("Second-Team All-Pro")
            else:
                achievements.append(f"{candidate.all_pro_second_team}x Second-Team All-Pro")

        # Pro Bowl
        if candidate.pro_bowl_selections > 0:
            if candidate.pro_bowl_selections == 1:
                achievements.append("Pro Bowl")
            else:
                achievements.append(f"{candidate.pro_bowl_selections}x Pro Bowl")

        # Career length
        achievements.append(f"{candidate.career_seasons} Seasons")

        return achievements

    def _build_career_summary(
        self,
        candidate: "HOFCandidate",
        achievements: List[str]
    ) -> str:
        """
        Build career summary narrative.

        Args:
            candidate: HOFCandidate with career data
            achievements: List of achievements

        Returns:
            Career summary paragraph
        """
        teams_str = ", ".join(candidate.teams_played_for) if candidate.teams_played_for else "multiple teams"

        # Build position-specific stats string
        stats_str = self._format_career_stats(candidate.primary_position, candidate.career_stats)

        summary = (
            f"{candidate.player_name} played {candidate.career_seasons} seasons "
            f"at {candidate.primary_position} for {teams_str}. "
        )

        if stats_str:
            summary += f"Career totals: {stats_str}. "

        if achievements:
            summary += f"Honors: {', '.join(achievements[:5])}."

        return summary

    def _format_career_stats(
        self,
        position: str,
        career_stats: Dict[str, Any]
    ) -> str:
        """
        Format career stats for display based on position.

        Args:
            position: Primary position
            career_stats: Dict of career statistics

        Returns:
            Formatted stats string
        """
        stats_parts = []

        # Passing stats
        if career_stats.get('pass_yards', 0) > 0:
            stats_parts.append(f"{career_stats['pass_yards']:,} passing yards")
        if career_stats.get('pass_tds', 0) > 0:
            stats_parts.append(f"{career_stats['pass_tds']} passing TDs")

        # Rushing stats
        if career_stats.get('rush_yards', 0) > 0:
            stats_parts.append(f"{career_stats['rush_yards']:,} rushing yards")
        if career_stats.get('rush_tds', 0) > 0:
            stats_parts.append(f"{career_stats['rush_tds']} rushing TDs")

        # Receiving stats
        if career_stats.get('receptions', 0) > 0:
            stats_parts.append(f"{career_stats['receptions']} receptions")
        if career_stats.get('rec_yards', 0) > 0:
            stats_parts.append(f"{career_stats['rec_yards']:,} receiving yards")
        if career_stats.get('rec_tds', 0) > 0:
            stats_parts.append(f"{career_stats['rec_tds']} receiving TDs")

        # Defensive stats
        if career_stats.get('sacks', 0) > 0:
            stats_parts.append(f"{career_stats['sacks']} sacks")
        if career_stats.get('tackles', 0) > 0:
            stats_parts.append(f"{career_stats['tackles']} tackles")
        if career_stats.get('interceptions', 0) > 0:
            stats_parts.append(f"{career_stats['interceptions']} interceptions")

        # Kicking stats
        if career_stats.get('fg_made', 0) > 0:
            stats_parts.append(f"{career_stats['fg_made']} field goals")

        return ", ".join(stats_parts[:4])  # Limit to 4 stats

    def _save_inductee(
        self,
        ceremony: InductionCeremony,
        candidate: "HOFCandidate"
    ) -> None:
        """
        Save inductee to database via HOFAPI.

        Args:
            ceremony: InductionCeremony with ceremony data
            candidate: HOFCandidate with career data
        """
        if not self.db or not self.dynasty_id:
            logger.warning("Cannot save inductee: database or dynasty_id not configured")
            return

        hof_api = HOFAPI(self.db, self.dynasty_id)

        # Build player_data dict
        player_data = {
            'player_name': candidate.player_name,
            'primary_position': candidate.primary_position,
            'career_seasons': candidate.career_seasons,
            'final_team_id': candidate.final_team_id,
            'teams_played_for': candidate.teams_played_for,
            'super_bowl_wins': candidate.super_bowl_wins,
            'mvp_awards': candidate.mvp_awards,
            'all_pro_first_team': candidate.all_pro_first_team,
            'all_pro_second_team': candidate.all_pro_second_team,
            'pro_bowl_selections': candidate.pro_bowl_selections,
            'career_stats': candidate.career_stats,
            'hof_score': candidate.hof_score,
        }

        # Build ceremony_data dict
        ceremony_data = {
            'presenter_name': ceremony.presenter_name,
            'presenter_relationship': ceremony.presenter_relationship,
            'speech_highlights': ceremony.speech_highlights.to_dict(),
        }

        try:
            hof_api.add_inductee(
                player_id=candidate.player_id,
                induction_season=ceremony.induction_season,
                years_on_ballot=ceremony.years_on_ballot,
                vote_percentage=ceremony.vote_percentage,
                player_data=player_data,
                ceremony_data=ceremony_data,
            )
            logger.info(f"Saved HOF inductee: {candidate.player_name}")
        except Exception as e:
            logger.error(f"Failed to save HOF inductee {candidate.player_name}: {e}")
            raise
