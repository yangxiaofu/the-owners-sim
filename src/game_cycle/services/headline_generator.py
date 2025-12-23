"""
Headline Generator Service - Event-driven headline generation.

Part of Milestone 12: Media Coverage, Tollgate 3.

Generates headlines for various events:
- Game results (recap, blowout, upset, comeback)
- Injuries
- Milestones
- Trades and signings
- Awards
- Rumors

Uses template-based generation with conditional selection,
sentiment analysis, and priority scoring.
"""

import json
import logging
import random
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.media_coverage_api import MediaCoverageAPI, Headline
from src.game_cycle.database.box_scores_api import BoxScoresAPI, BoxScore
from src.game_cycle.database.standings_api import StandingsAPI
from src.game_cycle.database.rivalry_api import RivalryAPI
from src.game_cycle.database.analytics_api import AnalyticsAPI
from src.game_cycle.database.play_grades_api import PlayGradesAPI
from src.game_cycle.database.schedule_api import ScheduleAPI
from src.game_cycle.database.head_to_head_api import HeadToHeadAPI


class HeadlineType(str, Enum):
    """Types of headlines that can be generated."""
    GAME_RECAP = "GAME_RECAP"
    BLOWOUT = "BLOWOUT"
    UPSET = "UPSET"
    COMEBACK = "COMEBACK"
    INJURY = "INJURY"
    MILESTONE = "MILESTONE"
    TRADE = "TRADE"
    SIGNING = "SIGNING"
    AWARD = "AWARD"
    RUMOR = "RUMOR"
    POWER_RANKING = "POWER_RANKING"
    STREAK = "STREAK"
    PREVIEW = "PREVIEW"  # Upcoming game previews for rivalry/critical matchups
    # NEW: Player-focused game headlines
    PLAYER_PERFORMANCE = "PLAYER_PERFORMANCE"  # Star player carries team
    DUAL_THREAT = "DUAL_THREAT"  # QB-WR combo, two stars
    DEFENSIVE_SHOWCASE = "DEFENSIVE_SHOWCASE"  # Defensive player dominates
    # Transaction-specific headline types
    RESIGNING = "RESIGNING"  # Contract extensions and departures
    FRANCHISE_TAG = "FRANCHISE_TAG"  # Franchise tag applications
    ROSTER_CUT = "ROSTER_CUT"  # Surprise cuts and final roster
    WAIVER_CLAIM = "WAIVER_CLAIM"  # Notable waiver acquisitions


class Sentiment(str, Enum):
    """Sentiment classification for headlines."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    HYPE = "HYPE"
    CRITICAL = "CRITICAL"


@dataclass
class HeadlineTemplate:
    """
    Template for generating headlines.

    Attributes:
        template: String with placeholders like {team}, {player}
        conditions: Dict of conditions that must be met to use this template
        sentiment: Sentiment of the headline
        priority_boost: Amount to add to base priority
        subheadline_template: Optional template for subheadline
    """
    template: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    sentiment: Sentiment = Sentiment.NEUTRAL
    priority_boost: int = 0
    subheadline_template: Optional[str] = None


# =============================================================================
# BASE PRIORITIES BY EVENT TYPE
# =============================================================================

BASE_PRIORITIES = {
    HeadlineType.GAME_RECAP: 50,
    HeadlineType.BLOWOUT: 60,
    HeadlineType.UPSET: 70,
    HeadlineType.COMEBACK: 75,
    HeadlineType.INJURY: 65,
    HeadlineType.MILESTONE: 70,
    HeadlineType.TRADE: 80,
    HeadlineType.SIGNING: 60,
    HeadlineType.AWARD: 65,
    HeadlineType.RUMOR: 40,
    HeadlineType.POWER_RANKING: 45,
    HeadlineType.STREAK: 55,
    HeadlineType.PREVIEW: 55,  # Slightly above game recaps, boosted by criticality
    # NEW: Player-focused headlines
    HeadlineType.PLAYER_PERFORMANCE: 68,  # Higher than BLOWOUT (60)
    HeadlineType.DUAL_THREAT: 72,  # Higher than UPSET (70)
    HeadlineType.DEFENSIVE_SHOWCASE: 75,  # Equal to COMEBACK
    # Transaction-specific headline types
    HeadlineType.RESIGNING: 65,  # Contract extensions (higher than SIGNING)
    HeadlineType.FRANCHISE_TAG: 75,  # Always newsworthy ($15-30M decisions)
    HeadlineType.ROSTER_CUT: 55,  # Base priority, boosted for stars
    HeadlineType.WAIVER_CLAIM: 50,  # Base priority, boosted for notable claims
}


# =============================================================================
# TEAM IDS BY CONFERENCE (for playoff headlines)
# =============================================================================

# AFC teams (IDs 1-16)
AFC_TEAM_IDS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}

# NFC teams (IDs 17-32)
NFC_TEAM_IDS = {17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32}


# =============================================================================
# POSITION CATEGORIES (for stat line formatting)
# =============================================================================

QB_POSITIONS = {"QB", "QUARTERBACK"}
RB_POSITIONS = {"RB", "RUNNING_BACK", "HALFBACK", "FULLBACK", "FB"}
RECEIVER_POSITIONS = {"WR", "WIDE_RECEIVER", "TE", "TIGHT_END"}
DEFENSIVE_POSITIONS = {
    "LB", "MLB", "OLB", "LOLB", "ROLB",
    "DE", "DT", "LE", "RE", "EDGE",
    "CB", "FS", "SS", "S"
}


# =============================================================================
# PLAYER IMPACT WEIGHTS (for star player identification)
# =============================================================================

IMPACT_WEIGHTS = {
    # Offensive stats
    "passing_yards": 0.04,       # ~10 pts per 250 yards
    "passing_tds": 4,
    "passing_interceptions": -3,  # Negative for turnovers
    "rushing_yards": 0.1,         # ~10 pts per 100 yards
    "rushing_tds": 6,
    "receiving_yards": 0.1,
    "receiving_tds": 6,

    # Defensive stats (rebalanced to increase defensive player visibility)
    "tackles_total": 1.0,         # Increased from 0.5 to 1.0 (10 tackles = 10.0 impact)
    "tackles_for_loss": 2.0,      # NEW: 1 TFL = 2.0 impact (high-value play)
    "sacks": 3,
    "interceptions": 5,           # Defensive interceptions
    "passes_defended": 2.0,       # NEW: 1 PD = 2.0 impact (rewards coverage)
    "forced_fumbles": 4.0,        # NEW: 1 FF = 4.0 impact (high-value turnover creation)
}


# =============================================================================
# SEASON CONTEXT (week-aware article generation)
# =============================================================================

SEASON_CONTEXT = {
    "week_1": {
        "label": "season opener",
        "period": "opening week",
        "phrases": [
            "kicks off their season",
            "in the first game of the year",
            "to start the campaign",
            "in their season debut",
        ],
        "outlook_phrases": [
            "It's just one game, but early impressions matter.",
            "The long road to the playoffs begins with a single step.",
            "Seventeen more weeks to go, but this is how you want to start.",
        ],
    },
    "early_season": {  # weeks 2-4
        "label": "early season",
        "period": "early in the season",
        "phrases": [
            "still finding their rhythm",
            "early in the year",
            "as the season gets underway",
            "with plenty of football ahead",
        ],
        "outlook_phrases": [
            "It's still early, but patterns are beginning to emerge.",
            "The sample size is small, but the trend is notable.",
        ],
    },
    "mid_season": {  # weeks 5-12
        "label": "mid-season",
        "period": "at the midpoint",
        "phrases": [
            "with the season in full swing",
            "as the schedule intensifies",
            "in a pivotal mid-season matchup",
            "with playoff positioning beginning to take shape",
        ],
        "outlook_phrases": [
            "The playoff picture is starting to crystallize.",
            "We're learning who these teams really are.",
        ],
    },
    "late_season": {  # weeks 13-16
        "label": "late season",
        "period": "down the stretch",
        "phrases": [
            "with the playoff picture taking shape",
            "down the stretch",
            "with postseason implications",
            "as the regular season winds down",
            "in a crucial late-season contest",
        ],
        "outlook_phrases": [
            "Every game matters now.",
            "The margin for error has shrunk to almost nothing.",
            "This is when contenders separate themselves from pretenders.",
        ],
    },
    "week_17_18": {  # final weeks
        "label": "season finale",
        "period": "in the final stretch",
        "phrases": [
            "in a pivotal season finale",
            "with everything on the line",
            "in the final game of the regular season",
            "with playoff seeding at stake",
            "to close out the regular season",
        ],
        "outlook_phrases": [
            "The regular season is over. Now the real games begin.",
            "Playoff positioning is set. Time to shift focus to January.",
        ],
    },
}


# =============================================================================
# TEAM STATUS CATEGORIES (playoff contention awareness)
# =============================================================================

class TeamStatus:
    """Team status classifications for contextual article generation."""
    CONTENDER = "contender"      # Playoff seed locked or likely
    BUBBLE = "bubble"            # On the playoff bubble
    REBUILDING = "rebuilding"    # Below .500, building for future
    ELIMINATED = "eliminated"    # Mathematically or effectively out


# =============================================================================
# GAME RECAP TEMPLATES (50+)
# =============================================================================

GAME_RECAP_TEMPLATES = [
    # Standard wins
    HeadlineTemplate(
        template="{winner} Defeats {loser}, {score}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0,
        subheadline_template="{winner_city} improves to {winner_record}"
    ),
    HeadlineTemplate(
        template="{winner} Takes Down {loser} in Week {week}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0
    ),
    HeadlineTemplate(
        template="{winner} Tops {loser}, {score}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0
    ),
    HeadlineTemplate(
        template="{winner} Gets Past {loser}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0
    ),
    HeadlineTemplate(
        template="{winner} Handles {loser} in Week {week} Matchup",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0
    ),
    # Close games (margin <= 7)
    HeadlineTemplate(
        template="{winner} Edges {loser} in Thriller, {score}",
        conditions={"margin_max": 7},
        sentiment=Sentiment.HYPE,
        priority_boost=10,
        subheadline_template="A back-and-forth battle comes down to the final minutes"
    ),
    HeadlineTemplate(
        template="{winner} Survives {loser} Scare, {score}",
        conditions={"margin_max": 3},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{winner} Holds Off {loser} in Nail-Biter",
        conditions={"margin_max": 7},
        sentiment=Sentiment.HYPE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{winner} Escapes with Win Over {loser}",
        conditions={"margin_max": 7},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="Down to the Wire: {winner} Nips {loser}, {score}",
        conditions={"margin_max": 3},
        sentiment=Sentiment.HYPE,
        priority_boost=15
    ),
    # Comfortable wins (margin 8-13)
    HeadlineTemplate(
        template="{winner} Pulls Away from {loser}, {score}",
        conditions={"margin_min": 8, "margin_max": 13},
        sentiment=Sentiment.POSITIVE,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="{winner} Handles Business Against {loser}",
        conditions={"margin_min": 8, "margin_max": 13},
        sentiment=Sentiment.POSITIVE,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="{winner} Takes Care of {loser}, {score}",
        conditions={"margin_min": 8, "margin_max": 13},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0
    ),
    # Dominant wins (margin 14-20)
    HeadlineTemplate(
        template="{winner} Cruises Past {loser}, {score}",
        conditions={"margin_min": 14, "margin_max": 20},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10,
        subheadline_template="{winner_nickname} control game from start to finish"
    ),
    HeadlineTemplate(
        template="{winner} Rolls Over {loser} in One-Sided Affair",
        conditions={"margin_min": 14, "margin_max": 20},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{winner} Dominates {loser}, {score}",
        conditions={"margin_min": 14, "margin_max": 20},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    # Home/Away specific
    HeadlineTemplate(
        template="{winner} Protects Home Turf Against {loser}",
        conditions={"winner_is_home": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=0
    ),
    HeadlineTemplate(
        template="{winner} Wins on the Road in {loser_city}",
        conditions={"winner_is_home": False},
        sentiment=Sentiment.POSITIVE,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="{winner} Steals One in {loser_city}, {score}",
        conditions={"winner_is_home": False, "margin_max": 7},
        sentiment=Sentiment.HYPE,
        priority_boost=10
    ),
    # Division/Rivalry
    HeadlineTemplate(
        template="{winner} Takes Division Clash Against {loser}",
        conditions={"is_divisional": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{winner} Wins Heated Rivalry Game Over {loser}",
        conditions={"is_rivalry": True},
        sentiment=Sentiment.HYPE,
        priority_boost=15,
        subheadline_template="The {rivalry_name} continues to deliver drama"
    ),
    HeadlineTemplate(
        template="{winner} Extends Series Lead Against Rival {loser}",
        conditions={"is_rivalry": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    # Primetime
    HeadlineTemplate(
        template="{winner} Shines Under the Lights Against {loser}",
        conditions={"is_primetime": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{winner} Wins Primetime Showdown with {loser}",
        conditions={"is_primetime": True},
        sentiment=Sentiment.HYPE,
        priority_boost=10
    ),
    # Playoff implications
    HeadlineTemplate(
        template="{winner} Keeps Playoff Hopes Alive with Win Over {loser}",
        conditions={"winner_playoff_relevant": True},
        sentiment=Sentiment.HYPE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{winner} Clinches Playoff Berth with Victory Over {loser}",
        conditions={"clinches_playoff": True},
        sentiment=Sentiment.HYPE,
        priority_boost=25,
        subheadline_template="{winner_city} punches ticket to the postseason"
    ),
    HeadlineTemplate(
        template="{winner} Locks Up Division Title Against {loser}",
        conditions={"clinches_division": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
]

# =============================================================================
# BLOWOUT TEMPLATES (25+)
# =============================================================================

BLOWOUT_TEMPLATES = [
    HeadlineTemplate(
        template="{winner} Demolishes {loser} in {margin}-Point Rout",
        conditions={"margin_min": 21},
        sentiment=Sentiment.POSITIVE,
        priority_boost=20,
        subheadline_template="A dominant performance from start to finish"
    ),
    HeadlineTemplate(
        template="{winner} Embarrasses {loser}, {score}",
        conditions={"margin_min": 21},
        sentiment=Sentiment.CRITICAL,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{winner} Steamrolls {loser} in Lopsided Contest",
        conditions={"margin_min": 21},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{loser} Humiliated in {margin}-Point Loss to {winner}",
        conditions={"margin_min": 28},
        sentiment=Sentiment.CRITICAL,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{winner} Runs Away with It: {score} Over {loser}",
        conditions={"margin_min": 21},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Statement Made: {winner} Crushes {loser}",
        conditions={"margin_min": 21},
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{winner} Makes Easy Work of {loser}, {score}",
        conditions={"margin_min": 21},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{loser} Has No Answer for {winner} in Blowout Loss",
        conditions={"margin_min": 21},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{winner} Puts {loser} to the Sword, {score}",
        conditions={"margin_min": 28},
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Mercy Rule? {winner} Annihilates {loser}",
        conditions={"margin_min": 35},
        sentiment=Sentiment.CRITICAL,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{winner} Sends Message with Dominant Win Over {loser}",
        conditions={"margin_min": 21},
        sentiment=Sentiment.HYPE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{winner} Flexes Muscle in Blowout of {loser}",
        conditions={"margin_min": 21},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Historic Beatdown: {winner} {score} {loser}",
        conditions={"margin_min": 35},
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{winner}'s Defense Suffocates {loser} in Shutout Win",
        conditions={"margin_min": 21, "loser_score": 0},
        sentiment=Sentiment.HYPE,
        priority_boost=35,
        subheadline_template="First shutout of the season"
    ),
    HeadlineTemplate(
        template="{winner} Blanks {loser} in Defensive Masterpiece",
        conditions={"loser_score": 0},
        sentiment=Sentiment.HYPE,
        priority_boost=35
    ),
    HeadlineTemplate(
        template="Total Domination: {winner} Shuts Out {loser}",
        conditions={"loser_score": 0},
        sentiment=Sentiment.POSITIVE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{loser} Embarrassed at Home in {margin}-Point Loss",
        conditions={"margin_min": 21, "winner_is_home": False},
        sentiment=Sentiment.CRITICAL,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{winner} Goes to {loser_city} and Dominates, {score}",
        conditions={"margin_min": 21, "winner_is_home": False},
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Questions Mount as {loser} Blown Out by {winner}",
        conditions={"margin_min": 21},
        sentiment=Sentiment.CRITICAL,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{winner} Piles On in {margin}-Point Victory Over {loser}",
        conditions={"margin_min": 28},
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
]

# =============================================================================
# UPSET TEMPLATES (20+)
# =============================================================================

UPSET_TEMPLATES = [
    HeadlineTemplate(
        template="Stunning Upset: {underdog} Takes Down {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=25,
        subheadline_template="{underdog} enters as {spread}-point underdog"
    ),
    HeadlineTemplate(
        template="{underdog} Shocks {favorite} in Massive Upset",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="Giant Killer: {underdog} Upsets {favorite}, {score}",
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{favorite} Falls to {underdog} in Upset",
        sentiment=Sentiment.NEGATIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{underdog} Pulls Off Shocking Win Over {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="Nobody Saw This Coming: {underdog} {score} {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{underdog} Ruins {favorite}'s Perfect Week",
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="What Just Happened? {underdog} Defeats {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{underdog} Proves Doubters Wrong Against {favorite}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Upset Alert: {underdog} Knocks Off {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{favorite} Exposed in Loss to {underdog}",
        sentiment=Sentiment.CRITICAL,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{underdog} Makes Statement, Upsets {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Are They for Real? {underdog} Shocks {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{underdog} Stuns {favorite} on the Road",
        conditions={"underdog_is_away": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{favorite} Stunned at Home by {underdog}",
        conditions={"favorite_is_home": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="David vs Goliath: {underdog} Takes Down Mighty {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{underdog} Sends Shockwaves Through League",
        sentiment=Sentiment.HYPE,
        priority_boost=25,
        subheadline_template="Defeat of {favorite} could shake up playoff picture"
    ),
    HeadlineTemplate(
        template="Bracket Buster: {underdog} Defeats {favorite}",
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
]

# =============================================================================
# COMEBACK TEMPLATES (20+)
# =============================================================================

COMEBACK_TEMPLATES = [
    HeadlineTemplate(
        template="{team} Completes {deficit}-Point Comeback Against {opponent}",
        sentiment=Sentiment.HYPE,
        priority_boost=25,
        subheadline_template="One of the greatest comebacks of the season"
    ),
    HeadlineTemplate(
        template="Incredible! {team} Rallies from {deficit} Down to Beat {opponent}",
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{team} Storms Back from {deficit}-Point Deficit",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="Never Say Die: {team} Overcomes {deficit}-Point Hole",
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{team} Mounts Epic Comeback Against {opponent}",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{opponent} Blows {deficit}-Point Lead to {team}",
        sentiment=Sentiment.CRITICAL,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="Historic Collapse: {opponent} Loses After Leading by {deficit}",
        conditions={"deficit_min": 21},
        sentiment=Sentiment.CRITICAL,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{team} Refuses to Quit, Rallies Past {opponent}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Down But Not Out: {team} {score} {opponent}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team}'s Second-Half Surge Stuns {opponent}",
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Resilient {team} Overcomes {deficit}-Point Deficit",
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{team} Erases {deficit}-Point Lead in Stunning Fashion",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="How Did They Do It? {team} Comes Back from {deficit} Down",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{team} Pulls Off Miraculous Comeback vs {opponent}",
        conditions={"deficit_min": 21},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="Fourth-Quarter Magic: {team} Rallies to Beat {opponent}",
        conditions={"fourth_quarter_comeback": True},
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{team} Completes Largest Comeback in Team History",
        conditions={"is_record_comeback": True},
        sentiment=Sentiment.HYPE,
        priority_boost=35
    ),
    HeadlineTemplate(
        template="From the Brink: {team} Survives {deficit}-Point Deficit",
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
]

# =============================================================================
# PLAYER PERFORMANCE TEMPLATES (20) - Star Player Carries Team
# =============================================================================

PLAYER_PERFORMANCE_TEMPLATES = [
    HeadlineTemplate(
        template="{player_name}'s Heroics Lead {winner} Past {loser}, {score}",
        sentiment=Sentiment.HYPE,
        priority_boost=15,
        subheadline_template="{player_name} posts {stat_highlight} in Week {week} victory"
    ),
    HeadlineTemplate(
        template="{player_name} Dominates as {winner} Tops {loser}, {score}",
        sentiment=Sentiment.HYPE,
        priority_boost=15,
        subheadline_template="{player_name} posts {stat_highlight} in dominant performance"
    ),
    HeadlineTemplate(
        template="{player_name} Explodes for {stat_highlight} in {winner} Win",
        sentiment=Sentiment.HYPE,
        priority_boost=18,
        subheadline_template="{winner} defeats {loser} {score} in Week {week}"
    ),
    HeadlineTemplate(
        template="{player_name} Torches {loser} Defense: {stat_highlight}",
        sentiment=Sentiment.HYPE,
        priority_boost=16,
        subheadline_template="{winner} wins {score} in Week {week}"
    ),
    HeadlineTemplate(
        template="{player_name} Puts On a Clinic: {winner} {score} {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=14,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name}'s {stat_highlight} Powers {winner} Past {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=13,
        subheadline_template="{winner} defeats {loser} {score}"
    ),
    HeadlineTemplate(
        template="{player_name} Unstoppable in {winner}'s {score} Win Over {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=15,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name} Carries {winner} to Victory: {stat_highlight}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=14,
        subheadline_template="{winner} defeats {loser} {score} in Week {week}"
    ),
    HeadlineTemplate(
        template="{player_name} Takes Over: {winner} Defeats {loser}, {score}",
        sentiment=Sentiment.HYPE,
        priority_boost=16,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name}'s Masterclass Leads {winner} Past {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=14,
        subheadline_template="{stat_highlight} in {score} victory"
    ),
    HeadlineTemplate(
        template="{player_name} Shines: {winner} {score} {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=10,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name} Too Much for {loser} in {winner} Win",
        sentiment=Sentiment.POSITIVE,
        priority_boost=12,
        subheadline_template="{stat_highlight} leads {winner} to victory"
    ),
    HeadlineTemplate(
        template="{player_name}'s Precision Guides {winner} to {score} Win",
        sentiment=Sentiment.POSITIVE,
        priority_boost=11,
        conditions={"player_position": "QB"},  # QB-specific
        subheadline_template="{stat_highlight} in Week {week} victory"
    ),
    HeadlineTemplate(
        template="{player_name} Runs Wild: {stat_highlight} Leads {winner} Past {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=16,
        subheadline_template="{winner} defeats {loser} {score}"
    ),
    HeadlineTemplate(
        template="{player_name} Can't Be Stopped: {winner} Tops {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=14,
        subheadline_template="{player_name}: {stat_highlight} in {score} win"
    ),
    HeadlineTemplate(
        template="{player_name}'s Big Day Powers {winner} to {score} Victory",
        sentiment=Sentiment.POSITIVE,
        priority_boost=12,
        subheadline_template="{stat_highlight} vs {loser}"
    ),
    HeadlineTemplate(
        template="{player_name} Lights Up {loser}: {winner} Wins {score}",
        sentiment=Sentiment.HYPE,
        priority_boost=15,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name}'s Stellar Performance Lifts {winner} Over {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=13,
        subheadline_template="{stat_highlight} in Week {week}"
    ),
    HeadlineTemplate(
        template="{player_name} Leads the Charge: {winner} Defeats {loser}, {score}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=11,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name} Delivers: {winner} Defeats {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=12,
        subheadline_template="{stat_highlight} powers {winner_city} to {score} win"
    ),
]

# =============================================================================
# DUAL THREAT TEMPLATES (15) - QB-WR Combos, Dynamic Duos
# =============================================================================

DUAL_THREAT_TEMPLATES = [
    HeadlineTemplate(
        template="{player_name} and {player2_name} Combine to Sink {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=18,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="Dynamic Duo: {player_name}, {player2_name} Lead {winner} Past {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=20,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name} to {player2_name}: {winner} Defeats {loser}, {score}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=16,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name}-{player2_name} Connection Too Much for {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name}, {player2_name} Star in {winner}'s {score} Win",
        sentiment=Sentiment.POSITIVE,
        priority_boost=14,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name} and {player2_name} Shine as {winner} Tops {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=13,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="One-Two Punch: {player_name}, {player2_name} Lead {winner} to Victory",
        sentiment=Sentiment.HYPE,
        priority_boost=17,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name}'s {stat_highlight} and {player2_name}'s Heroics Beat {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=16,
        subheadline_template="{player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{winner}'s Star Duo Delivers: {player_name}, {player2_name} Beat {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=14,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name} and {player2_name} Too Much: {winner} {score} {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=13,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="Unstoppable Combo: {player_name}-{player2_name} Lead {winner} Past {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=18,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name} Finds {player2_name} Repeatedly in {winner} Win",
        sentiment=Sentiment.POSITIVE,
        priority_boost=12,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{winner}'s Dynamic Duo Stuns {loser}: {player_name}, {player2_name}",
        sentiment=Sentiment.HYPE,
        priority_boost=16,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name}, {player2_name} Combine for Dominant {winner} Win",
        sentiment=Sentiment.POSITIVE,
        priority_boost=14,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
    HeadlineTemplate(
        template="{player_name}-to-{player2_name}: {winner}'s Winning Formula vs {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=13,
        subheadline_template="{player_name}: {stat_highlight} | {player2_name}: {player2_stat_summary}"
    ),
]

# =============================================================================
# DEFENSIVE SHOWCASE TEMPLATES (15) - Defensive Player Dominates
# =============================================================================

DEFENSIVE_SHOWCASE_TEMPLATES = [
    HeadlineTemplate(
        template="{player_name} Dominates: {winner} Shuts Down {loser}, {score}",
        sentiment=Sentiment.HYPE,
        priority_boost=20,
        subheadline_template="{player_name}: {stat_highlight} in Week {week}"
    ),
    HeadlineTemplate(
        template="{player_name}'s Defense Leads {winner} Past {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=16,
        subheadline_template="{stat_highlight} in {score} victory"
    ),
    HeadlineTemplate(
        template="{player_name} Wreaks Havoc: {winner} Defeats {loser}, {score}",
        sentiment=Sentiment.HYPE,
        priority_boost=18,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name}'s {stat_highlight} Shuts Down {loser} Offense",
        sentiment=Sentiment.HYPE,
        priority_boost=17,
        subheadline_template="{winner} wins {score} in Week {week}"
    ),
    HeadlineTemplate(
        template="{player_name} Unblockable in {winner}'s {score} Win",
        sentiment=Sentiment.HYPE,
        priority_boost=16,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name} Takes Over Defensively: {winner} {score} {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15,
        subheadline_template="{stat_highlight} dominates in Week {week}"
    ),
    HeadlineTemplate(
        template="{player_name} Anchors {winner} Defense in {score} Win Over {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=14,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name}'s Defensive Clinic Stifles {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=17,
        subheadline_template="{stat_highlight} leads {winner} to victory"
    ),
    HeadlineTemplate(
        template="{player_name} Terrorizes {loser}: {stat_highlight} in {winner} Win",
        sentiment=Sentiment.HYPE,
        priority_boost=18,
        subheadline_template="{winner} defeats {loser} {score}"
    ),
    HeadlineTemplate(
        template="{player_name} Leads {winner} Defense to {score} Victory",
        sentiment=Sentiment.POSITIVE,
        priority_boost=13,
        subheadline_template="{player_name}: {stat_highlight} vs {loser}"
    ),
    HeadlineTemplate(
        template="{player_name}'s Big Game on Defense Keys {winner} Win",
        sentiment=Sentiment.POSITIVE,
        priority_boost=14,
        subheadline_template="{stat_highlight} in {score} win over {loser}"
    ),
    HeadlineTemplate(
        template="Defensive Star: {player_name} Dominates in {winner} Win",
        sentiment=Sentiment.HYPE,
        priority_boost=16,
        subheadline_template="{player_name}: {stat_highlight} in Week {week}"
    ),
    HeadlineTemplate(
        template="{player_name} Makes Game-Changing Plays: {winner} Tops {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=13,
        subheadline_template="{stat_highlight} leads {winner} to {score} victory"
    ),
    HeadlineTemplate(
        template="{player_name} Unstoppable on Defense: {winner} {score} {loser}",
        sentiment=Sentiment.HYPE,
        priority_boost=17,
        subheadline_template="{player_name}: {stat_highlight}"
    ),
    HeadlineTemplate(
        template="{player_name}'s Defensive Heroics Lift {winner} Past {loser}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15,
        subheadline_template="{stat_highlight} in Week {week} victory"
    ),
]

# =============================================================================
# INJURY TEMPLATES (25+)
# =============================================================================

INJURY_TEMPLATES = [
    HeadlineTemplate(
        template="{player} Suffers {injury}, Out {duration}",
        sentiment=Sentiment.NEGATIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{team} Loses {player} to {injury}",
        sentiment=Sentiment.NEGATIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Devastating Blow: {player} Out with {injury}",
        conditions={"is_star": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{player} Injured, Expected to Miss {duration}",
        sentiment=Sentiment.NEGATIVE,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="{team}'s {player} Placed on Injured Reserve",
        conditions={"on_ir": True},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Season Over for {player} After {injury}",
        conditions={"is_season_ending": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=30,
        subheadline_template="A crushing blow to {team}'s playoff hopes"
    ),
    HeadlineTemplate(
        template="{player}'s Season Ends with {injury}",
        conditions={"is_season_ending": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{team} Star {player} Done for the Year",
        conditions={"is_season_ending": True, "is_star": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=35
    ),
    HeadlineTemplate(
        template="{player} Leaves Game with {injury}",
        conditions={"in_game": True},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{player} Carted Off with {injury}",
        conditions={"in_game": True, "severity_min": "severe"},
        sentiment=Sentiment.CRITICAL,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Injury Report: {player} Week-to-Week with {injury}",
        sentiment=Sentiment.NEGATIVE,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="{player} to Miss Multiple Games with {injury}",
        conditions={"duration_weeks_min": 2},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{team} Dealing with Rash of Injuries, {player} Latest",
        conditions={"team_has_multiple_injuries": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Good News: {player} Returns from {injury}",
        conditions={"is_return": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Back in Action After {duration} Absence",
        conditions={"is_return": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Gets {player} Back from Injured Reserve",
        conditions={"is_return": True, "off_ir": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Update: {player}'s {injury} Less Serious Than Feared",
        conditions={"is_update": True, "good_news": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Bad News: {player}'s {injury} Worse Than Expected",
        conditions={"is_update": True, "bad_news": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=15
    ),
]

# =============================================================================
# TRADE TEMPLATES (25+)
# =============================================================================

TRADE_TEMPLATES = [
    HeadlineTemplate(
        template="Blockbuster: {acquiring_team} Acquires {player} from {trading_team}",
        conditions={"is_blockbuster": True},
        sentiment=Sentiment.HYPE,
        priority_boost=35,
        subheadline_template="The biggest trade of the season shakes up the league"
    ),
    HeadlineTemplate(
        template="{acquiring_team} Lands {player} in Trade with {trading_team}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Traded to {acquiring_team}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{trading_team} Sends {player} to {acquiring_team}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Done Deal: {player} Heads to {acquiring_city}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{acquiring_team} Adds {player} in Deadline Deal",
        conditions={"is_deadline": True},
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Trade Deadline Shakeup: {player} to {acquiring_team}",
        conditions={"is_deadline": True},
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{acquiring_team} Makes Splash, Acquires {player}",
        conditions={"is_high_value": True},
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{trading_team} Teardown Continues: {player} Traded",
        conditions={"team_is_rebuilding": True},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{acquiring_team} Goes All-In, Trades for {player}",
        conditions={"acquiring_team_contender": True},
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{player} Gets Fresh Start with {acquiring_team}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Blockbuster: {acquiring_team} and {trading_team} Swap Stars",
        conditions={"is_player_swap": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{acquiring_team} Gives Up Haul for {player}",
        conditions={"high_draft_capital": True},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=20,
        subheadline_template="{draft_picks} headed to {trading_city}"
    ),
    HeadlineTemplate(
        template="{trading_team} Stockpiles Picks in {player} Deal",
        conditions={"high_draft_capital": True},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Surprising Move: {player} Dealt to {acquiring_team}",
        conditions={"is_surprising": True},
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{player} Reunites with Former Team {acquiring_team}",
        conditions={"is_reunion": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Multi-Team Deal Sends {player} to {acquiring_team}",
        conditions={"is_multi_team": True},
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
]

# =============================================================================
# SIGNING TEMPLATES (25+)
# =============================================================================

SIGNING_TEMPLATES = [
    HeadlineTemplate(
        template="{player} Signs {years}-Year, ${value}M Deal with {team}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=10,
        subheadline_template="{player} joins {team_city} on a {contract_type} contract"
    ),
    HeadlineTemplate(
        template="{team} Lands {player} in Free Agency",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Inks Deal with {team}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="{team} Signs {player} to ${value}M Contract",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Done Deal: {player} Joins {team}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{team} Makes Splash, Signs {player}",
        conditions={"is_high_value": True},
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Mega Deal: {player} Signs ${value}M Contract with {team}",
        conditions={"is_mega_deal": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{player} Stays Home, Re-Signs with {team}",
        conditions={"is_re_signing": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Brings Back {player} on New Deal",
        conditions={"is_re_signing": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Hometown Discount: {player} Re-Signs with {team}",
        conditions={"is_discount": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Takes Talents to {team_city}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{team} Adds Veteran {player}",
        conditions={"is_veteran": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{team} Signs Undrafted Free Agent {player}",
        conditions={"is_udfa": True},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0
    ),
    HeadlineTemplate(
        template="{player} Returns to NFL, Signs with {team}",
        conditions={"is_comeback": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Locks Up {player} Long-Term",
        conditions={"years_min": 4},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Cashes In, Signs ${value}M Deal with {team}",
        conditions={"is_high_value": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
]

# =============================================================================
# AWARD TEMPLATES (20+)
# =============================================================================

AWARD_TEMPLATES = [
    HeadlineTemplate(
        template="{player} Named {award}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Wins {award}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Takes Home {award} Honors",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Named Week {week} {award}",
        conditions={"is_weekly": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{player} Earns {award} After {stat_line}",
        conditions={"has_stat_line": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Wins MVP",
        conditions={"award_is_mvp": True},
        sentiment=Sentiment.HYPE,
        priority_boost=35,
        subheadline_template="The {team} star caps dominant season"
    ),
    HeadlineTemplate(
        template="{player} Named League MVP",
        conditions={"award_is_mvp": True},
        sentiment=Sentiment.HYPE,
        priority_boost=35
    ),
    HeadlineTemplate(
        template="{player} Crowned Offensive Player of the Year",
        conditions={"award_is_opoy": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{player} Named Defensive Player of the Year",
        conditions={"award_is_dpoy": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{player} Wins Offensive Rookie of the Year",
        conditions={"award_is_oroy": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{player} Named Defensive Rookie of the Year",
        conditions={"award_is_droy": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{player} Repeats as {award}",
        conditions={"is_repeat_winner": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{player} Becomes First {position} to Win {award}",
        conditions={"is_historic": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{player} Selected to Pro Bowl",
        conditions={"award_is_probowl": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Named First-Team All-Pro",
        conditions={"award_is_allpro1": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
]

# =============================================================================
# MILESTONE TEMPLATES (20+)
# =============================================================================

MILESTONE_TEMPLATES = [
    HeadlineTemplate(
        template="{player} Joins Elite Company with {milestone}",
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{player} Reaches {milestone}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Historic: {player} Becomes {ordinal} Player to {achievement}",
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{player} Sets New {record_type} Record",
        conditions={"is_record": True},
        sentiment=Sentiment.HYPE,
        priority_boost=35
    ),
    HeadlineTemplate(
        template="{player} Breaks {previous_holder}'s {record_type} Record",
        conditions={"is_record": True, "has_previous_holder": True},
        sentiment=Sentiment.HYPE,
        priority_boost=35
    ),
    HeadlineTemplate(
        template="{player} Surpasses {count} Career {stat_type}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{player} Passes {legend} on All-Time {stat_type} List",
        conditions={"passes_legend": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{player} Becomes All-Time Leader in {stat_type}",
        conditions={"is_all_time_leader": True},
        sentiment=Sentiment.HYPE,
        priority_boost=40,
        subheadline_template="A historic achievement caps a legendary career"
    ),
    HeadlineTemplate(
        template="{player} Hits {count} {stat_type} This Season",
        conditions={"is_season_milestone": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} First to Reach {count} {stat_type} in a Season",
        conditions={"is_first_ever": True},
        sentiment=Sentiment.HYPE,
        priority_boost=35
    ),
    HeadlineTemplate(
        template="{player} Achieves Rare Feat with {milestone}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{player}'s {count}th Career {stat_type}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{player} Reaches {count} Career {stat_type}",
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
]

# =============================================================================
# RUMOR TEMPLATES (20+)
# =============================================================================

RUMOR_TEMPLATES = [
    HeadlineTemplate(
        template="Sources: {team} Showing Interest in {player}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="Report: {team} Interested in Trading for {player}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{team} Reportedly in Talks for {player}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Sources: {team} Listening to Offers for {player}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{player} Could Be on the Move, Per Sources",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Trade Buzz: {player} Drawing Interest",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Multiple Teams Inquiring About {player}",
        sentiment=Sentiment.HYPE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Expected to Be Active at Trade Deadline",
        conditions={"deadline_approaching": True},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Free Agency Target: {player} on {team}'s Radar",
        conditions={"is_fa_speculation": True},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="{player} Reportedly Unhappy in {team_city}",
        conditions={"is_discontent_rumor": True},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Trade Request? {player} Wants Out of {team_city}",
        conditions={"is_trade_request": True},
        sentiment=Sentiment.HYPE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="Heat Intensifying on {coach} After Another Loss",
        conditions={"is_hot_seat": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{coach}'s Job in Jeopardy as {team} Continues to Struggle",
        conditions={"is_hot_seat": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="Sources: {team} Considering Coaching Change",
        conditions={"is_hot_seat": True, "severe": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{team} Expected to Target {position} in Draft",
        conditions={"is_draft_buzz": True},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=5
    ),
    HeadlineTemplate(
        template="Mock Draft Update: {team} Linked to {player}",
        conditions={"is_draft_buzz": True},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=5
    ),
]

# =============================================================================
# STREAK TEMPLATES (15+)
# =============================================================================

STREAK_TEMPLATES = [
    HeadlineTemplate(
        template="{team} Extends Winning Streak to {count} Games",
        conditions={"streak_type": "winning"},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team}'s Losing Streak Hits {count} Games",
        conditions={"streak_type": "losing"},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Hot Streak: {team} Wins {count}th Straight",
        conditions={"streak_type": "winning"},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Freefall: {team} Drops {count}th Consecutive Game",
        conditions={"streak_type": "losing"},
        sentiment=Sentiment.CRITICAL,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Riding {count}-Game Win Streak Into Week {next_week}",
        conditions={"streak_type": "winning"},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Can Anyone Stop Them? {team} Wins {count} in a Row",
        conditions={"streak_type": "winning", "count_min": 5},
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="Crisis Mode: {team}'s Losing Streak Reaches {count}",
        conditions={"streak_type": "losing", "count_min": 4},
        sentiment=Sentiment.CRITICAL,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{team} Snaps {opponent}'s {count}-Game Win Streak",
        conditions={"is_streak_snap": True},
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{team} Finally Wins, Ends {count}-Game Skid",
        conditions={"is_skid_end": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team}'s Win Streak Alive at {count} Games",
        conditions={"streak_type": "winning"},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="Rolling: {team} Makes It {count} Wins in a Row",
        conditions={"streak_type": "winning"},
        sentiment=Sentiment.HYPE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Drops {count}th Straight, Season Spiraling",
        conditions={"streak_type": "losing", "count_min": 3},
        sentiment=Sentiment.CRITICAL,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="Dominant: {team} Cruising with {count}-Game Win Streak",
        conditions={"streak_type": "winning", "count_min": 3},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Searching for Answers After {count}th Loss",
        conditions={"streak_type": "losing"},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=10
    ),
]


# =============================================================================
# POWER RANKING TEMPLATES (10+)
# =============================================================================

POWER_RANKING_TEMPLATES = [
    HeadlineTemplate(
        template="{team} Rises to No. {rank} in Power Rankings",
        conditions={"is_rising": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{team} Falls to {rank} After Loss",
        conditions={"is_falling": True},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=10
    ),
    HeadlineTemplate(
        template="{team} Holds Steady at No. {rank}",
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0
    ),
    HeadlineTemplate(
        template="New No. 1: {team} Takes Top Spot",
        conditions={"rank": 1, "is_new_top": True},
        sentiment=Sentiment.HYPE,
        priority_boost=25
    ),
    HeadlineTemplate(
        template="{team} Climbs {movement} Spots to {rank}",
        conditions={"is_rising": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Plummets {movement} Spots to {rank}",
        conditions={"is_falling": True, "movement_min": 5},
        sentiment=Sentiment.CRITICAL,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{team} Enters Top 10 at No. {rank}",
        conditions={"rank_max": 10, "was_outside_top10": True},
        sentiment=Sentiment.POSITIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="{team} Drops Out of Top 10",
        conditions={"was_top10": True, "rank_min": 11},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=15
    ),
    HeadlineTemplate(
        template="Biggest Mover: {team} Jumps {movement} Spots",
        conditions={"is_biggest_mover": True},
        sentiment=Sentiment.HYPE,
        priority_boost=20
    ),
    HeadlineTemplate(
        template="{team} Tumbles in Rankings After Upset Loss",
        conditions={"is_falling": True, "lost_upset": True},
        sentiment=Sentiment.NEGATIVE,
        priority_boost=15
    ),
]


# =============================================================================
# PREVIEW TEMPLATES - Upcoming Game Previews (Tollgate 7.8)
# =============================================================================

PREVIEW_TEMPLATES = [
    # Legendary rivalry games (intensity >= 85)
    HeadlineTemplate(
        template="{rivalry_name}: {away_team} at {home_team}",
        conditions={"is_rivalry": True, "rivalry_intensity_min": 85},
        sentiment=Sentiment.HYPE,
        priority_boost=25,
        subheadline_template="Historic rivalry renews in Week {week}"
    ),
    # Intense rivalry games (intensity >= 75)
    HeadlineTemplate(
        template="Rivalry Renewed: {away_team} at {home_team}",
        conditions={"is_rivalry": True, "rivalry_intensity_min": 75},
        sentiment=Sentiment.HYPE,
        priority_boost=20,
        subheadline_template="Division foes clash in heated matchup"
    ),
    # Divisional + playoff implications (most critical)
    HeadlineTemplate(
        template="Must-Win: {away_record} {away_team} at {home_record} {home_team}",
        conditions={"is_divisional": True, "playoff_implications": True},
        sentiment=Sentiment.CRITICAL,
        priority_boost=25,
        subheadline_template="Division showdown with massive playoff implications"
    ),
    # Pure playoff implications
    HeadlineTemplate(
        template="Playoff Push: {away_team} and {home_team} Battle for Positioning",
        conditions={"playoff_implications": True},
        sentiment=Sentiment.HYPE,
        priority_boost=20,
        subheadline_template="Both teams fighting for postseason spot"
    ),
    # Divisional showdowns
    HeadlineTemplate(
        template="Division Showdown: {away_team} vs {home_team}",
        conditions={"is_divisional": True},
        sentiment=Sentiment.HYPE,
        priority_boost=15,
        subheadline_template="Division rivals meet in Week {week}"
    ),
    # Head-to-head streak (team looking to extend dominance)
    HeadlineTemplate(
        template="{streak_team} Look to Extend {streak_count}-Game Win Streak vs {opponent}",
        conditions={"has_streak": True, "streak_count_min": 3},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=10,
        subheadline_template="One team owns the series; can they keep it going?"
    ),
    # Late-season conference games
    HeadlineTemplate(
        template="Conference Clash: {away_team} at {home_team}",
        conditions={"is_conference": True, "week_min": 12},
        sentiment=Sentiment.NEUTRAL,
        priority_boost=5,
        subheadline_template="Late-season conference matchup could determine seeding"
    ),
    # Generic notable game (fallback)
    HeadlineTemplate(
        template="Week {week} Preview: {away_team} at {home_team}",
        conditions={},  # No conditions - fallback
        sentiment=Sentiment.NEUTRAL,
        priority_boost=0,
        subheadline_template="{away_record} {away_team} visit {home_record} {home_team}"
    ),
]


# =============================================================================
# BODY TEXT TEMPLATES FOR GAME RECAPS (Tollgate 4)
# =============================================================================

# Opening paragraph templates - set the scene
OPENING_PARAGRAPH_TEMPLATES = {
    HeadlineType.GAME_RECAP: [
        "The {winner} secured a {margin}-point victory over the {loser} on {day_of_week}, improving their record to {winner_record}. The {score} final showcased {winner_nickname}'s ability to execute in crucial moments.",
        "In a Week {week} matchup, the {winner} defeated the {loser} {score}. The win moves {winner_city} to {winner_record} on the season while {loser_city} falls to {loser_record}.",
        "{winner_city} came out on top in their {venue_type} matchup against the {loser}, winning {score}. The {winner_nickname} now sit at {winner_record} as they look ahead to the rest of the season.",
        "The {winner} picked up a crucial victory over the {loser}, winning {score} in Week {week}. With the win, {winner_city} improves to {winner_record}.",
    ],
    HeadlineType.BLOWOUT: [
        "The {winner} dominated from start to finish, routing the {loser} {score} in a one-sided affair. The {margin}-point victory was never in doubt as {winner_city} controlled all phases of the game.",
        "It was all {winner_city} on {day_of_week} as the {winner_nickname} demolished the {loser} {score}. The lopsided {margin}-point win raises serious questions for {loser_city}.",
        "The {loser} had no answer for the {winner} in a {score} blowout. {winner_city} dominated in all three phases, cruising to a {margin}-point victory.",
        "Complete domination. The {winner} embarrassed the {loser} {score}, with the {margin}-point margin only telling part of the story. {winner_city} improves to {winner_record}.",
    ],
    HeadlineType.UPSET: [
        "In a stunning result, the {winner} knocked off the favored {loser} {score}. The underdog {winner_nickname} came to play and walked away with a statement victory.",
        "The {winner} shocked the football world with a {score} upset over the {loser}. Few gave {winner_city} a chance, but they proved the doubters wrong.",
        "Nobody saw this coming. The {winner} took down the heavily-favored {loser} {score} in one of the biggest upsets of the season.",
        "Upset alert! The {winner} stunned the {loser} with a {score} victory that sent shockwaves through the league standings.",
    ],
    HeadlineType.COMEBACK: [
        "In a game that will be remembered for years, the {winner} erased a {comeback_points}-point deficit to stun the {loser} {score}. The remarkable comeback showcases the {winner_nickname}'s resilience.",
        "Down {comeback_points} points, the {winner} refused to quit. Their {score} comeback victory over the {loser} stands as one of the season's most dramatic moments.",
        "The {winner} mounted an incredible comeback, overcoming a {comeback_points}-point hole to defeat the {loser} {score}. {loser_city} will be left wondering what went wrong.",
        "It looked over for the {winner}, trailing by {comeback_points}. But they stormed back for a {score} victory that left the {loser} stunned.",
    ],
}

# Star players paragraph templates
STAR_PLAYERS_TEMPLATES = [
    "{star_player} led the charge with {stat_line}. {secondary_player_sentence}",
    "Leading the way for {winner_city} was {star_player}, who finished with {stat_line}. {secondary_player_sentence}",
    "{star_player} put on a clinic with {stat_line} in the victory. {secondary_player_sentence}",
    "The {winner_nickname} got a monster performance from {star_player}: {stat_line}. {secondary_player_sentence}",
    "{winner_city}'s {star_player} was dominant, posting {stat_line}. {secondary_player_sentence}",
    "{star_player} stole the show, finishing with {stat_line}. {secondary_player_sentence}",
    "It was {star_player} who made the difference with {stat_line}. {secondary_player_sentence}",
]

# Defensive standout templates (used when top player is defensive)
DEFENSIVE_STAR_TEMPLATES = [
    "The defense was the story, led by {star_player} who recorded {stat_line}. {secondary_player_sentence}",
    "{star_player} anchored a dominant defensive effort with {stat_line}. The {winner_nickname} defense was suffocating all game. {secondary_player_sentence}",
    "It was the {winner_nickname} defense that stole the show. {star_player} finished with {stat_line}, setting the tone for the unit. {secondary_player_sentence}",
    "On a day when the defense dominated, {star_player} stood out with {stat_line}. {secondary_player_sentence}",
    "{winner_city}'s defense was relentless, with {star_player} leading the charge ({stat_line}). {secondary_player_sentence}",
    "The {winner_nickname} defense made life miserable for the opposing offense. {star_player} was everywhere, finishing with {stat_line}. {secondary_player_sentence}",
]

# Templates when defense had a big game (multiple players)
DEFENSIVE_DOMINANCE_SENTENCE = [
    "The defense combined for {total_sacks} sacks and {total_turnovers} turnovers.",
    "The {winner_nickname} defense was stifling, generating {total_sacks} sacks.",
    "It was a total team effort on defense, creating {total_turnovers} turnovers.",
    "The defensive front was dominant, recording {total_sacks} sacks on the day.",
]

# Secondary player sentence templates
SECONDARY_PLAYER_SENTENCES = [
    "{player_name} also contributed with {stat_line}.",
    "On the other side, {player_name} had {stat_line} for the {team_name}.",
    "Also noteworthy was {player_name}'s {stat_line}.",
    "{player_name} added {stat_line} in support.",
    "The {team_name} also got {stat_line} from {player_name}.",
]

# Defensive secondary player sentences
DEFENSIVE_SECONDARY_SENTENCES = [
    "The secondary also came up big, with {player_name} recording {stat_line}.",
    "{player_name} contributed on defense with {stat_line}.",
    "The pass rush was complemented by {player_name}'s {stat_line}.",
    "The defensive effort was a group one, with {player_name} adding {stat_line}.",
]

# Templates for dedicated defensive standouts paragraph
DEFENSIVE_STANDOUTS_TEMPLATES = [
    "Defensively, {winner_defender} stood out with {winner_def_stats}. {loser_defender_sentence}",
    "The defensive battle featured {winner_defender} ({winner_def_stats}). {loser_defender_sentence}",
    "On the defensive side, {winner_defender} was a force with {winner_def_stats}. {loser_defender_sentence}",
    "{winner_defender} led the {winner_nickname} defense with {winner_def_stats}. {loser_defender_sentence}",
    "The {winner_nickname} defense was anchored by {winner_defender}, who finished with {winner_def_stats}. {loser_defender_sentence}",
]

# Templates for loser's defensive player mention
LOSER_DEFENDER_SENTENCE_TEMPLATES = [
    "For {loser_name}, {loser_defender} recorded {loser_def_stats}.",
    "{loser_name}'s {loser_defender} had {loser_def_stats} in the losing effort.",
    "On the other side, {loser_defender} finished with {loser_def_stats}.",
    "Despite the loss, {loser_defender} was active with {loser_def_stats}.",
]

# Postgame quote templates - winner
WINNER_QUOTE_TEMPLATES = [
    '"{quote}" said {player_name} after the victory.',
    '"{quote}" {player_name} said postgame.',
    'After the game, {player_name} said: "{quote}"',
    '{player_name} was thrilled: "{quote}"',
]

# Quote content for winners
WINNER_QUOTE_CONTENT = [
    "We came out and executed our game plan. The guys played hard and it showed.",
    "This is what we've been working for all week. Great team win.",
    "Everyone stepped up today. That's what championship teams do.",
    "We knew it was going to be a battle, but we stayed focused and got the job done.",
    "The preparation paid off. We were ready for everything they threw at us.",
    "I'm proud of how we responded. This team has something special.",
    "We're just getting started. There's more work to do.",
    "The defense played lights out today. They made it easy for us on offense.",
    "Big win for us. Now we reset and focus on next week.",
    "You can feel the momentum building. This team believes in each other.",
    "We played complementary football today. That's when we're at our best.",
    "Credit to the coaches for having us ready. We knew exactly what to expect.",
    "The energy was different today. You could feel it from the opening kickoff.",
    "We didn't panic when things got tight. That's growth from this team.",
    "We're playing our best football right now. Exciting times.",
    "That's the standard we've set for ourselves. Now we have to maintain it.",
    "When you prepare the right way, good things happen on Sunday.",
    "The O-line was dominant today. Those guys don't get enough credit.",
    "We knew they'd come out swinging. We just had to weather the storm.",
    "This team has heart. When it matters, we find a way.",
    "The young guys stepped up big today. The future is bright.",
    "We're a second-half team. We knew we'd make adjustments and come out strong.",
    "That was a total team effort. Offense, defense, special teams - everyone contributed.",
    "We've been close in a lot of games. Today we finished.",
    "The locker room is special right now. Guys genuinely care about each other.",
]

# Quote content for winners after close games
WINNER_CLOSE_GAME_QUOTES = [
    "That was a dogfight. Hats off to them, they played us tough.",
    "Ugly wins still count. We'll take it and move on.",
    "Games like that build character. We found a way.",
    "Not our cleanest performance, but winners find ways to win.",
    "We made it harder than it needed to be, but a W is a W.",
    "Those games teach you a lot about your team.",
]

# Quote content for winners after blowouts
WINNER_BLOWOUT_QUOTES = [
    "We wanted to send a message today. I think we did that.",
    "When we're clicking on all cylinders, we're tough to beat.",
    "We came out with intensity and never let up. That's the mentality.",
    "Dominant performance. That's what we're capable of.",
    "We wanted to be physical and impose our will. Mission accomplished.",
    "That's the blueprint. Now we have to replicate it.",
]

# Postgame quote templates - loser
LOSER_QUOTE_TEMPLATES = [
    '"{quote}" {player_name} admitted after the loss.',
    '"{quote}" said a disappointed {player_name}.',
    '{player_name} reflected on the loss: "{quote}"',
]

# Quote content for losers
LOSER_QUOTE_CONTENT = [
    "We have to go back and watch the film. Too many mistakes today.",
    "Give them credit, they outplayed us. We need to be better.",
    "This one hurts, but we'll bounce back. That's what this team does.",
    "We didn't execute when it mattered. That's on all of us.",
    "Not the result we wanted. We have to regroup and come back stronger.",
    "They made plays and we didn't. Simple as that.",
    "We beat ourselves today. Can't do that against good teams.",
    "The game got away from us. We have to start faster.",
    "It's a long season. We'll learn from this and get better.",
    "We're better than we showed today. We know that.",
    "Frustrating. We had chances and didn't capitalize.",
    "When you don't take care of the ball, this is what happens.",
    "The effort was there. The execution wasn't. That's fixable.",
    "We'll watch the tape and get better. That's all you can do.",
    "Can't spot a good team like that and expect to win.",
    "We're still figuring some things out. Growing pains.",
    "The message doesn't change. We have to keep working.",
    "Individual mistakes killed us. We have to clean that up.",
    "You can't give them extra possessions and expect to win.",
    "We stopped doing what got us here. That's on us.",
    "We'll be back. This league is about how you respond.",
    "Disappointed, but not discouraged. Plenty of season left.",
    "You learn more from losses than wins. We'll use this.",
    "The gameplan was good. We just didn't execute it.",
]

# Quote content for losers after close games
LOSER_CLOSE_GAME_QUOTES = [
    "That one's going to sting. We were right there.",
    "A play here or there and it's a different outcome.",
    "We fought hard. Just came up short in the end.",
    "Moral victories don't count, but we showed something today.",
    "We can build on this. We went toe-to-toe with a good team.",
    "Close doesn't count. We have to find a way to finish.",
]

# Quote content for losers after blowouts
LOSER_BLOWOUT_QUOTES = [
    "We got our butts kicked. No excuses.",
    "That was embarrassing. We owe our fans better than that.",
    "They exposed us. We have a lot of work to do.",
    "Not acceptable. We have to look in the mirror.",
    "We weren't ready to play. That starts with me.",
    "You can't show up like that against anyone in this league.",
    "We got outcoached and outplayed. Period.",
]

# Quote templates for tie games
TIE_QUOTE_TEMPLATES = [
    '"{quote}" said {player_name} after the tie.',
    '"{quote}" {player_name} reflected postgame.',
    '{player_name} summed up the result: "{quote}"',
    'After the draw, {player_name} said: "{quote}"',
]

# Quote content for tie games
TIE_QUOTE_CONTENT = [
    "A tie feels like a loss to both teams. We had chances to win it.",
    "In this league, you have to find ways to win. We didn't do that today.",
    "We'll take the point, but we wanted the W.",
    "Strange feeling. Not a win, not a loss. We have to be better.",
    "Ties are frustrating. We left points on the field.",
    "Can't be satisfied with a tie. We had opportunities.",
    "It's rare, but it happens. We move on to next week.",
    "Neither team could put the other away. Credit to them, but we expected more from ourselves.",
    "A draw on the road isn't the worst result, but we came here to win.",
    "We fought hard, they fought hard. In the end, nobody won.",
    "Overtime and still no winner. That's a tough one to swallow.",
    "We'll look at the film. There were plays to be made that we didn't make.",
]


# =============================================================================
# ANALYST/MEDIA REACTION TEMPLATES (Tollgate 4 Enhancement)
# =============================================================================

ANALYST_REACTION_TEMPLATES = [
    '"{quote}" observed one NFL analyst.',
    'League insiders took note: "{quote}"',
    'Media reaction was swift. "{quote}" noted one observer.',
    '"This {analysis_type}," said one league source.',
    'Around the league, the sentiment was clear: "{quote}"',
    'Analysts were quick to weigh in: "{quote}"',
]

ANALYST_CONTENT = {
    # Contender wins convincingly
    "contender_dominant_win": [
        "They're playing like a team that expects to be in February.",
        "This is exactly what championship teams do - they don't let bad teams hang around.",
        "You have to like where they're headed. That's a complete performance.",
        "If you're looking for Super Bowl contenders, start here.",
        "Everything is clicking at the right time. That's a scary team.",
    ],
    # Contender wins close game
    "contender_close_win": [
        "Good teams find ways to win. That's what separates contenders from pretenders.",
        "Not their best, but they got it done. That's championship DNA.",
        "They'll take the W, but there's tape to clean up.",
        "Winning ugly is still winning. But they need to be sharper in January.",
    ],
    # Contender loses
    "contender_loss": [
        "Concerning loss for a team with Super Bowl aspirations.",
        "They'll need to figure this out before January.",
        "Red flags for a supposed contender. You can't play like that and expect to win in the playoffs.",
        "A reality check. Maybe they're not as good as we thought.",
        "The blueprint to beat them just got exposed.",
    ],
    # Upset winner
    "upset_winner": [
        "Where did that come from? The league should take notice.",
        "A statement win that could change their trajectory.",
        "This is why you play the games. Nobody saw that coming.",
        "Proof that any given Sunday is real. Huge confidence boost.",
        "The upset special. Sometimes the better team doesn't win.",
    ],
    # Blowout winner
    "blowout_dominant": [
        "Complete domination from start to finish. A message game.",
        "They sent a message to the rest of the league.",
        "That's the kind of performance that makes you a believer.",
        "When you're that much better, you're supposed to win by that much.",
        "Ruthless. That's a team playing with supreme confidence.",
    ],
    # Blowout loser
    "blowout_loser": [
        "An embarrassing performance. Hard to find positives there.",
        "That's the kind of loss that can define a season - and not in a good way.",
        "Questions need to be answered. That was not acceptable.",
        "A thorough beating. Changes may be coming.",
    ],
    # Struggling/rebuilding team loses
    "struggling_team_loss": [
        "Serious questions need to be answered in that locker room.",
        "Changes could be coming if this continues.",
        "This franchise is at a crossroads. What's the plan?",
        "Another week, another loss. The frustration has to be mounting.",
        "Patience is running thin. How much longer does this go on?",
    ],
    # Struggling team wins
    "struggling_team_win": [
        "A much-needed win. Maybe there's something to build on.",
        "Finally, a positive result. The question is whether they can sustain it.",
        "The drought is over. Now can they stack wins?",
        "A glimmer of hope for a fan base that needed one.",
    ],
    # Eliminated team
    "eliminated_team": [
        "Playing for pride now. The season is effectively over.",
        "Evaluating for next year at this point.",
        "A lost season. Time to start thinking about the draft.",
        "Nothing to play for but individual stats and building blocks.",
    ],
    # Playoff implications (late season)
    "playoff_implications": [
        "That's a game with playoff implications. Every result matters now.",
        "The playoff picture just got more interesting.",
        "When the stakes are high, you learn who can handle the pressure.",
        "This is when the season separates contenders from pretenders.",
    ],
    # Week 1 specific
    "week_1_take": [
        "It's just Week 1, but first impressions matter.",
        "One game is a small sample, but the early signs are worth noting.",
        "The journey of a thousand miles begins with a single step. Good start.",
        "Way too early to draw conclusions, but it's a data point.",
    ],
    # Season finale
    "season_finale": [
        "The regular season is in the books. Now the real work begins.",
        "A fitting end to their season. The offseason starts now.",
        "They finished the way they wanted. Momentum matters heading into playoffs.",
    ],
}

# Criticism templates (for media criticism angle)
MEDIA_CRITICISM_TEMPLATES = [
    "Critics will point to {criticism_point}.",
    "The talking heads won't be kind about {criticism_point}.",
    "Expect questions about {criticism_point} in the press conferences.",
    "Social media was ruthless about {criticism_point}.",
]

CRITICISM_POINTS = {
    "turnover": [
        "the turnover margin",
        "the careless ball security",
        "the costly giveaways",
    ],
    "third_down": [
        "the third-down struggles",
        "the inability to sustain drives",
        "the offense going three-and-out repeatedly",
    ],
    "defense": [
        "the porous defense",
        "how easily they were gashed",
        "the lack of pass rush",
    ],
    "coaching": [
        "the questionable play-calling",
        "the game management decisions",
        "whether this coaching staff is the answer",
    ],
    "effort": [
        "the apparent lack of effort",
        "whether this team has quit",
        "the disconnect on the sideline",
    ],
}

# Big play description templates
BIG_PLAY_TEMPLATES = [
    "The {play_yards}-yard {play_type} by {player_name} brought the crowd to its feet.",
    "{player_name}'s {play_yards}-yard {play_type} was the play of the game.",
    "A highlight-reel {play_yards}-yard {play_type} from {player_name} swung momentum.",
    "{player_name} broke loose for a {play_yards}-yard {play_type} that electrified the stadium.",
]

# Turning point paragraph templates
TURNING_POINT_TEMPLATES = [
    "The game turned in the {quarter} quarter when {play_description}. From that point on, {winner_city} was in control.",
    "The pivotal moment came {quarter_context} when {play_description}. That play shifted momentum firmly in favor of the {winner_nickname}.",
    "If there was a turning point, it came {quarter_context}: {play_description}. The {loser_nickname} never recovered.",
    "The decisive swing occurred when {play_description}. That {quarter} quarter sequence proved to be the difference.",
]

# Scoring summary templates (fallback when no play grades)
SCORING_SUMMARY_TEMPLATES = [
    "The {winner_nickname} built their lead through {scoring_description}. {quarter_breakdown}",
    "{winner_city} controlled the scoring, {scoring_description}. {quarter_breakdown}",
    "The {winner_nickname}'s scoring attack featured {scoring_description}. {quarter_breakdown}",
]

# Looking ahead paragraph templates
LOOKING_AHEAD_TEMPLATES = {
    "playoff_clinch": [
        "With the victory, the {winner} clinch a playoff berth and will look to build momentum heading into the postseason. The {loser} see their playoff hopes take a significant hit.",
        "The win secures a playoff spot for {winner_city}. They'll look to lock up the best seed possible in their remaining games.",
        "Playoff football is officially on the horizon for {winner_city}. Now it's about seeding and staying healthy heading into January.",
    ],
    "playoff_implications": [
        "The win keeps {winner_city}'s playoff hopes alive as they sit at {winner_record}. Every game from here on out is crucial for the {winner_nickname}.",
        "With {games_remaining} games remaining, the {winner} are firmly in the playoff hunt at {winner_record}. The {loser} ({loser_record}) still have work to do.",
        "The playoff picture gets a little clearer. {winner_city} control their own destiny at {winner_record}, while {loser_city} face an uphill climb.",
    ],
    "division_race": [
        "The division race tightens as {winner_city} moves to {winner_record}. They'll look to continue this momentum in their upcoming matchup.",
        "This win has major division implications. The {winner_nickname} are now in the driver's seat at {winner_record} in the {division}.",
        "Division supremacy is on the line, and {winner_city} just made a statement. The {loser_nickname} will need to bounce back quickly to stay in the race.",
    ],
    "streak": [
        "The victory extends {winner_city}'s winning streak to {streak_count} games. They'll look to keep it going next week.",
        "That's {streak_count} straight wins for the {winner_nickname}, who are hitting their stride at just the right time.",
    ],
    "rivalry": [
        "Another chapter written in this storied rivalry. The {winner} extend their recent dominance over the {loser} and will look to carry this momentum forward.",
        "Bragging rights go to {winner_city} in this rivalry matchup. The {loser} will have to wait for the rematch to settle the score.",
        "In a rivalry that always delivers, {winner_city} came out on top. These teams will meet again, and {loser_city} will be hungry for revenge.",
    ],
    "week_1": [
        "It's only Week 1, but first impressions matter. {winner_city} will like what they saw, while {loser_city} has 17 weeks to find their footing.",
        "The season is young, but {winner_city} sends an early message. For {loser_city}, it's time to regroup before Week 2.",
        "Opening day success for the {winner_nickname}. A long road ahead, but you always want to start with a W.",
    ],
    "season_finale": [
        "The regular season is complete. For {winner_city}, it's time to prepare for the postseason. For {loser_city}, the offseason begins.",
        "A season-ending victory for {winner_city}. The final chapter of the regular season is written; now it's playoff time.",
        "The 18-week marathon is over. {winner_city} finish strong and turn their attention to what's next.",
    ],
    "must_win_winner": [
        "A must-win game, and {winner_city} delivered. Their playoff hopes remain alive heading into the final weeks.",
        "Backs against the wall, and the {winner_nickname} responded. Survive and advance to next week.",
        "{winner_city} keeps their postseason dreams intact. Every game is an elimination game from here on out.",
    ],
    "eliminated_loser": [
        "For {loser_city}, the loss is the final nail in the coffin. Their playoff hopes are mathematically eliminated. Time to evaluate for next year.",
        "A tough end for {loser_city}. The focus now shifts to the draft and building for the future.",
        "Season over for {loser_city}. The difficult conversations about the direction of this franchise begin now.",
    ],
    "default": [
        "The {winner} will look to build on this win in Week {next_week} while the {loser} regroup and prepare for their next challenge.",
        "Both teams now turn their attention to the rest of the season. For {winner_city}, it's about maintaining momentum. For {loser_city}, it's time to regroup.",
        "The {winner_nickname} will carry this confidence into Week {next_week}. The {loser_nickname} must put this one behind them quickly.",
        "Another week in the books. {winner_city} adds to the win column while {loser_city} looks for answers.",
    ],
}


# =============================================================================
# WILD CARD PLAYOFF HEADLINES
# =============================================================================

WILD_CARD_GAME_RECAP = [
    HeadlineTemplate(
        template="{winner} Advances Past Wild Card Round, Defeats {loser} {score}",
        conditions={"playoff_round": "wild_card"},
        sentiment=Sentiment.HYPE,
        priority_boost=30,
        subheadline_template="{winner_city} moves on to divisional round"
    ),
    HeadlineTemplate(
        template="{winner} Survives Wild Card Thriller Against {loser}, {score}",
        conditions={"playoff_round": "wild_card", "margin_max": 7},
        sentiment=Sentiment.HYPE,
        priority_boost=35,
        subheadline_template="Win-or-go-home drama delivers in {winner_city}"
    ),
    HeadlineTemplate(
        template="{winner} Dominates {loser} in Wild Card Rout, {score}",
        conditions={"playoff_round": "wild_card", "margin_min": 21},
        sentiment=Sentiment.POSITIVE,
        priority_boost=32,
        subheadline_template="{winner} makes statement in playoff opener"
    ),
    HeadlineTemplate(
        template="{winner} Edges {loser} in Wild Card Round, {score}",
        conditions={"playoff_round": "wild_card"},
        sentiment=Sentiment.POSITIVE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="Wild Card Victory: {winner} Defeats {loser}, {score}",
        conditions={"playoff_round": "wild_card"},
        sentiment=Sentiment.HYPE,
        priority_boost=31,
        subheadline_template="Playoff push continues for {winner_city}"
    ),
    HeadlineTemplate(
        template="{winner} Takes Care of Business in Wild Card Round, {score}",
        conditions={"playoff_round": "wild_card"},
        sentiment=Sentiment.POSITIVE,
        priority_boost=30
    ),
    HeadlineTemplate(
        template="{winner}'s Playoff Run Continues with Wild Card Win Over {loser}",
        conditions={"playoff_round": "wild_card"},
        sentiment=Sentiment.HYPE,
        priority_boost=31,
        subheadline_template="Divisional round awaits after {score} victory"
    ),
]

WILD_CARD_UPSET = [
    HeadlineTemplate(
        template="{winner} Shocks {loser} in Wild Card Upset, {score}",
        conditions={"playoff_round": "wild_card", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=40,
        subheadline_template="Lower seed {winner} stuns {loser} in playoff stunner"
    ),
    HeadlineTemplate(
        template="Wild Card Shocker: {winner} Stuns Favored {loser}, {score}",
        conditions={"playoff_round": "wild_card", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=41
    ),
    HeadlineTemplate(
        template="{loser} Eliminated in Wild Card Upset by {winner}",
        conditions={"playoff_round": "wild_card", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=39,
        subheadline_template="Underdogs advance with {score} victory"
    ),
    HeadlineTemplate(
        template="{winner} Pulls Off Wild Card Upset Over {loser}, {score}",
        conditions={"playoff_round": "wild_card", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=40
    ),
]

WILD_CARD_COMEBACK = [
    HeadlineTemplate(
        template="{winner} Stages Wild Card Comeback to Shock {loser}, {score}",
        conditions={"playoff_round": "wild_card", "comeback_points_min": 14},
        sentiment=Sentiment.HYPE,
        priority_boost=38,
        subheadline_template="Dramatic rally keeps playoff hopes alive"
    ),
    HeadlineTemplate(
        template="Incredible Rally: {winner} Overcomes {comeback_deficit} to Beat {loser} in Wild Card",
        conditions={"playoff_round": "wild_card", "comeback_points_min": 14},
        sentiment=Sentiment.HYPE,
        priority_boost=39
    ),
    HeadlineTemplate(
        template="{winner} Mounts Epic Wild Card Comeback Against {loser}, {score}",
        conditions={"playoff_round": "wild_card", "comeback_points_min": 14},
        sentiment=Sentiment.HYPE,
        priority_boost=38
    ),
]


# =============================================================================
# DIVISIONAL PLAYOFF HEADLINES
# =============================================================================

DIVISIONAL_GAME_RECAP = [
    HeadlineTemplate(
        template="{winner} One Win Away from Super Bowl After Divisional Victory Over {loser}",
        conditions={"playoff_round": "divisional"},
        sentiment=Sentiment.HYPE,
        priority_boost=35,
        subheadline_template="{winner} advances to {conference} Championship Game"
    ),
    HeadlineTemplate(
        template="{winner} Rolls to Conference Championship with Divisional Win, {score}",
        conditions={"playoff_round": "divisional"},
        sentiment=Sentiment.POSITIVE,
        priority_boost=33
    ),
    HeadlineTemplate(
        template="{winner} Survives {loser} Challenge in Divisional Round, {score}",
        conditions={"playoff_round": "divisional", "margin_max": 7},
        sentiment=Sentiment.HYPE,
        priority_boost=37,
        subheadline_template="Conference championship berth on the line in thriller"
    ),
    HeadlineTemplate(
        template="{winner} Dominates {loser} in Divisional Round, {score}",
        conditions={"playoff_round": "divisional", "margin_min": 21},
        sentiment=Sentiment.POSITIVE,
        priority_boost=34,
        subheadline_template="{winner_city} marches toward Super Bowl"
    ),
    HeadlineTemplate(
        template="Divisional Round Victory: {winner} Defeats {loser}, {score}",
        conditions={"playoff_round": "divisional"},
        sentiment=Sentiment.HYPE,
        priority_boost=33
    ),
    HeadlineTemplate(
        template="{winner} Advances to {conference} Championship Game with Win Over {loser}",
        conditions={"playoff_round": "divisional"},
        sentiment=Sentiment.HYPE,
        priority_boost=34,
        subheadline_template="One step closer to the Super Bowl"
    ),
    HeadlineTemplate(
        template="{winner} Punches Ticket to Conference Championship, {score}",
        conditions={"playoff_round": "divisional"},
        sentiment=Sentiment.HYPE,
        priority_boost=35,
        subheadline_template="{loser} eliminated in divisional round"
    ),
]

DIVISIONAL_UPSET = [
    HeadlineTemplate(
        template="{winner} Shocks {loser} in Divisional Round Upset, {score}",
        conditions={"playoff_round": "divisional", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=42,
        subheadline_template="Lower seed stuns favorites, advances to conference championship"
    ),
    HeadlineTemplate(
        template="Divisional Shocker: {winner} Stuns {loser}, {score}",
        conditions={"playoff_round": "divisional", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=43
    ),
    HeadlineTemplate(
        template="{loser} Stunned in Divisional Round by {winner}",
        conditions={"playoff_round": "divisional", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=41,
        subheadline_template="Underdog advances with {score} upset victory"
    ),
    HeadlineTemplate(
        template="{winner} Pulls Off Divisional Upset, Eliminates {loser} {score}",
        conditions={"playoff_round": "divisional", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=42
    ),
]

DIVISIONAL_COMEBACK = [
    HeadlineTemplate(
        template="{winner} Stages Dramatic Divisional Comeback to Beat {loser}, {score}",
        conditions={"playoff_round": "divisional", "comeback_points_min": 14},
        sentiment=Sentiment.HYPE,
        priority_boost=40,
        subheadline_template="Conference championship berth earned after epic rally"
    ),
    HeadlineTemplate(
        template="Incredible Rally: {winner} Overcomes {comeback_deficit} in Divisional Round",
        conditions={"playoff_round": "divisional", "comeback_points_min": 14},
        sentiment=Sentiment.HYPE,
        priority_boost=41
    ),
    HeadlineTemplate(
        template="{winner} Mounts Epic Comeback Against {loser} in Divisional Round, {score}",
        conditions={"playoff_round": "divisional", "comeback_points_min": 14},
        sentiment=Sentiment.HYPE,
        priority_boost=40
    ),
]


# =============================================================================
# CONFERENCE CHAMPIONSHIP HEADLINES
# =============================================================================

CONFERENCE_CHAMPIONSHIP_GAME_RECAP = [
    HeadlineTemplate(
        template="{winner} Punches Ticket to Super Bowl, Defeats {loser} {score}",
        conditions={"playoff_round": "conference"},
        sentiment=Sentiment.HYPE,
        priority_boost=45,
        subheadline_template="{winner} claims {conference} Championship, heads to Super Bowl"
    ),
    HeadlineTemplate(
        template="{winner} Wins {conference} Championship, Headed to Super Bowl",
        conditions={"playoff_round": "conference"},
        sentiment=Sentiment.HYPE,
        priority_boost=43,
        subheadline_template="{winner} dominates {loser} {score} to earn Super Bowl berth"
    ),
    HeadlineTemplate(
        template="{conference} Champions: {winner} Defeats {loser} to Reach Super Bowl",
        conditions={"playoff_round": "conference"},
        sentiment=Sentiment.HYPE,
        priority_boost=44
    ),
    HeadlineTemplate(
        template="{winner} Survives {conference} Championship Thriller, {score}",
        conditions={"playoff_round": "conference", "margin_max": 7},
        sentiment=Sentiment.HYPE,
        priority_boost=47,
        subheadline_template="Super Bowl berth decided in final seconds"
    ),
    HeadlineTemplate(
        template="{winner} Dominates {conference} Championship, Cruises to Super Bowl",
        conditions={"playoff_round": "conference", "margin_min": 21},
        sentiment=Sentiment.HYPE,
        priority_boost=45,
        subheadline_template="{loser} eliminated in blowout {score} loss"
    ),
    HeadlineTemplate(
        template="{winner} Earns Super Bowl Berth with {conference} Championship Victory",
        conditions={"playoff_round": "conference"},
        sentiment=Sentiment.HYPE,
        priority_boost=44,
        subheadline_template="{winner_city} celebrates conference title"
    ),
    HeadlineTemplate(
        template="Super Bowl Bound: {winner} Defeats {loser} in {conference} Championship",
        conditions={"playoff_round": "conference"},
        sentiment=Sentiment.HYPE,
        priority_boost=45
    ),
]

CONFERENCE_CHAMPIONSHIP_UPSET = [
    HeadlineTemplate(
        template="{winner} Shocks {loser} in {conference} Championship Upset, {score}",
        conditions={"playoff_round": "conference", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=48,
        subheadline_template="Underdog punches ticket to Super Bowl in stunning upset"
    ),
    HeadlineTemplate(
        template="{conference} Championship Shocker: {winner} Stuns {loser}, Reaches Super Bowl",
        conditions={"playoff_round": "conference", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=49
    ),
    HeadlineTemplate(
        template="{loser} Stunned in {conference} Championship by {winner}",
        conditions={"playoff_round": "conference", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=47,
        subheadline_template="Lower seed advances to Super Bowl with {score} upset"
    ),
]


# =============================================================================
# SUPER BOWL HEADLINES (HIGHEST PRIORITY)
# =============================================================================

SUPER_BOWL_CHAMPIONS = [
    HeadlineTemplate(
        template="{winner_caps} WIN SUPER BOWL, Defeat {loser} {score}",
        conditions={"playoff_round": "super_bowl"},
        sentiment=Sentiment.HYPE,
        priority_boost=50,
        subheadline_template="World champions crowned after {winner} victory"
    ),
    HeadlineTemplate(
        template="SUPER BOWL CHAMPIONS: {winner} Defeat {loser}, {score}",
        conditions={"playoff_round": "super_bowl"},
        sentiment=Sentiment.HYPE,
        priority_boost=50,
        subheadline_template="{winner_city} celebrates championship parade"
    ),
    HeadlineTemplate(
        template="{winner} Are Super Bowl Champions After Victory Over {loser}",
        conditions={"playoff_round": "super_bowl"},
        sentiment=Sentiment.HYPE,
        priority_boost=48,
        subheadline_template="{winner} caps championship season with {score} win"
    ),
    HeadlineTemplate(
        template="{winner} Claim Lombardi Trophy with Super Bowl Win Over {loser}, {score}",
        conditions={"playoff_round": "super_bowl"},
        sentiment=Sentiment.HYPE,
        priority_boost=49
    ),
    HeadlineTemplate(
        template="{winner_caps} DOMINATE SUPER BOWL, Rout {loser} {score}",
        conditions={"playoff_round": "super_bowl", "margin_min": 21},
        sentiment=Sentiment.HYPE,
        priority_boost=50,
        subheadline_template="Championship coronation complete in dominant fashion"
    ),
    HeadlineTemplate(
        template="{winner} Win Super Bowl in Thriller, Edge {loser} {score}",
        conditions={"playoff_round": "super_bowl", "margin_max": 7},
        sentiment=Sentiment.HYPE,
        priority_boost=50,
        subheadline_template="Championship decided in final moments"
    ),
    HeadlineTemplate(
        template="{winner} Shock the World, Win Super Bowl Over {loser} {score}",
        conditions={"playoff_round": "super_bowl", "is_upset": True},
        sentiment=Sentiment.HYPE,
        priority_boost=50,
        subheadline_template="Underdogs claim ultimate prize in stunning upset"
    ),
    HeadlineTemplate(
        template="WORLD CHAMPIONS: {winner} Defeat {loser} to Win Super Bowl",
        conditions={"playoff_round": "super_bowl"},
        sentiment=Sentiment.HYPE,
        priority_boost=50,
        subheadline_template="Lombardi Trophy returns to {winner_city}"
    ),
    HeadlineTemplate(
        template="{winner} Complete Championship Run with Super Bowl Victory",
        conditions={"playoff_round": "super_bowl"},
        sentiment=Sentiment.HYPE,
        priority_boost=49,
        subheadline_template="{loser} fall short in {score} loss"
    ),
]


# =============================================================================
# PLAYOFF TEMPLATE COLLECTIONS MAPPING
# =============================================================================

PLAYOFF_TEMPLATES = {
    "wild_card": {
        HeadlineType.GAME_RECAP: WILD_CARD_GAME_RECAP,
        HeadlineType.UPSET: WILD_CARD_UPSET,
        HeadlineType.COMEBACK: WILD_CARD_COMEBACK,
        HeadlineType.BLOWOUT: WILD_CARD_GAME_RECAP,  # Reuse GAME_RECAP with margin conditions
    },
    "divisional": {
        HeadlineType.GAME_RECAP: DIVISIONAL_GAME_RECAP,
        HeadlineType.UPSET: DIVISIONAL_UPSET,
        HeadlineType.COMEBACK: DIVISIONAL_COMEBACK,
        HeadlineType.BLOWOUT: DIVISIONAL_GAME_RECAP,  # Reuse GAME_RECAP with margin conditions
    },
    "conference": {
        HeadlineType.GAME_RECAP: CONFERENCE_CHAMPIONSHIP_GAME_RECAP,
        HeadlineType.UPSET: CONFERENCE_CHAMPIONSHIP_UPSET,
        HeadlineType.COMEBACK: CONFERENCE_CHAMPIONSHIP_GAME_RECAP,  # Reuse GAME_RECAP
        HeadlineType.BLOWOUT: CONFERENCE_CHAMPIONSHIP_GAME_RECAP,  # Reuse GAME_RECAP
    },
    "super_bowl": {
        HeadlineType.GAME_RECAP: SUPER_BOWL_CHAMPIONS,
        HeadlineType.UPSET: SUPER_BOWL_CHAMPIONS,  # All Super Bowl headlines use same high-priority pool
        HeadlineType.COMEBACK: SUPER_BOWL_CHAMPIONS,
        HeadlineType.BLOWOUT: SUPER_BOWL_CHAMPIONS,
    }
}


class HeadlineGenerator:
    """
    Service for generating event-driven headlines.

    Processes events (games, injuries, trades, etc.) and generates
    appropriate headlines with sentiment and priority scoring.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize HeadlineGenerator.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty identifier for isolation
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Initialize database connection
        self._db = GameCycleDatabase(db_path)
        self._media_api = MediaCoverageAPI(self._db)

        # Initialize APIs for body text generation (Tollgate 4)
        self._box_scores_api = BoxScoresAPI(db_path)
        self._standings_api = StandingsAPI(self._db)
        self._rivalry_api = RivalryAPI(self._db)
        self._analytics_api = AnalyticsAPI(db_path)
        self._play_grades_api = PlayGradesAPI(db_path)

        # Load team data for name lookups
        self._teams_data = self._load_teams_data()

        # Cache for player names (loaded on demand)
        self._player_names_cache: Dict[int, str] = {}

        # Template pools by type
        self._templates = {
            HeadlineType.GAME_RECAP: GAME_RECAP_TEMPLATES,
            HeadlineType.BLOWOUT: BLOWOUT_TEMPLATES,
            HeadlineType.UPSET: UPSET_TEMPLATES,
            HeadlineType.COMEBACK: COMEBACK_TEMPLATES,
            # NEW: Player-focused game headlines
            HeadlineType.PLAYER_PERFORMANCE: PLAYER_PERFORMANCE_TEMPLATES,
            HeadlineType.DUAL_THREAT: DUAL_THREAT_TEMPLATES,
            HeadlineType.DEFENSIVE_SHOWCASE: DEFENSIVE_SHOWCASE_TEMPLATES,
            # Existing non-game headlines
            HeadlineType.INJURY: INJURY_TEMPLATES,
            HeadlineType.TRADE: TRADE_TEMPLATES,
            HeadlineType.SIGNING: SIGNING_TEMPLATES,
            HeadlineType.AWARD: AWARD_TEMPLATES,
            HeadlineType.MILESTONE: MILESTONE_TEMPLATES,
            HeadlineType.RUMOR: RUMOR_TEMPLATES,
            HeadlineType.STREAK: STREAK_TEMPLATES,
            HeadlineType.POWER_RANKING: POWER_RANKING_TEMPLATES,
            HeadlineType.PREVIEW: PREVIEW_TEMPLATES,
        }

    def _load_teams_data(self) -> Dict[int, Dict[str, Any]]:
        """Load team information from JSON."""
        teams_file = Path(__file__).parent.parent.parent / "data" / "teams.json"
        try:
            with open(teams_file) as f:
                data = json.load(f)
                return {int(k): v for k, v in data.get("teams", {}).items()}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._logger.warning(f"Could not load teams.json: {e}")
            return {}

    def _get_team_info(self, team_id: int) -> Dict[str, str]:
        """Get team name, city, and nickname as a dict."""
        team = self._teams_data.get(team_id, {})
        return {
            "team": team.get("full_name", f"Team {team_id}"),
            "city": team.get("city", "Unknown"),
            "nickname": team.get("nickname", f"Team {team_id}"),
        }

    def _get_season_context(self, week: int) -> Dict[str, Any]:
        """
        Get season context based on week number.

        Args:
            week: Week number (1-18)

        Returns:
            Dict with 'key', 'label', 'period', 'phrases', 'outlook_phrases'
        """
        if week == 1:
            key = "week_1"
        elif week <= 4:
            key = "early_season"
        elif week <= 12:
            key = "mid_season"
        elif week <= 16:
            key = "late_season"
        else:
            key = "week_17_18"

        context = SEASON_CONTEXT.get(key, SEASON_CONTEXT["mid_season"]).copy()
        context["key"] = key
        context["week"] = week
        context["games_remaining"] = max(0, 18 - week)
        return context

    def _classify_team_status(
        self,
        standing: Any,
        week: int
    ) -> str:
        """
        Classify team as contender, bubble, rebuilding, or eliminated.

        Args:
            standing: Team standing object with wins/losses/playoff_seed
            week: Current week number

        Returns:
            TeamStatus classification string
        """
        if standing is None:
            return TeamStatus.REBUILDING

        wins = getattr(standing, 'wins', 0) or 0
        losses = getattr(standing, 'losses', 0) or 0
        playoff_seed = getattr(standing, 'playoff_seed', None)

        # Has playoff seed = contender
        if playoff_seed:
            return TeamStatus.CONTENDER

        # Calculate win percentage
        games_played = wins + losses
        win_pct = wins / games_played if games_played > 0 else 0.5

        # Late season with bad record = effectively eliminated
        if week >= 14 and losses >= 10:
            return TeamStatus.ELIMINATED

        # Late season with winning record but no seed = bubble
        if week >= 10 and wins >= losses and games_played >= 8:
            return TeamStatus.BUBBLE

        # Winning record = bubble team
        if win_pct >= 0.5 and games_played >= 4:
            return TeamStatus.BUBBLE

        # Default = rebuilding
        return TeamStatus.REBUILDING

    # =========================================================================
    # Main Generation Methods
    # =========================================================================

    def generate_headline(
        self,
        event_type: HeadlineType,
        event_data: Dict[str, Any]
    ) -> Headline:
        """
        Generate a single headline for an event.

        Args:
            event_type: Type of event (GAME_RECAP, INJURY, etc.)
            event_data: Dict containing event-specific data

        Returns:
            Generated Headline object
        """
        # Get matching templates
        templates = self._get_matching_templates(event_type, event_data)

        if not templates:
            # Fallback to any template of this type
            templates = self._templates.get(event_type, [])

        if not templates:
            self._logger.warning(f"No templates found for {event_type}")
            return self._create_fallback_headline(event_type, event_data)

        # Select a random matching template
        template = random.choice(templates)

        # Fill template with data
        headline_text = self._fill_template(template.template, event_data)

        # Generate subheadline if available
        subheadline = None
        if template.subheadline_template:
            try:
                subheadline = self._fill_template(
                    template.subheadline_template, event_data
                )
            except KeyError:
                pass  # Skip subheadline if data not available

        # Calculate priority
        priority = self._calculate_priority(event_type, event_data, template)

        # Create Headline object
        return Headline(
            id=None,
            dynasty_id=self._dynasty_id,
            season=self._season,
            week=event_data.get("week", 1),
            headline_type=event_type.value,
            headline=headline_text,
            subheadline=subheadline,
            body_text=None,
            sentiment=template.sentiment.value,
            priority=priority,
            team_ids=event_data.get("team_ids", []),
            player_ids=event_data.get("player_ids", []),
            game_id=event_data.get("game_id"),
            metadata=event_data.get("metadata", {}),
            created_at=None,
        )

    def generate_game_headline(
        self,
        game_data: Dict[str, Any],
        include_body_text: bool = True
    ) -> Headline:
        """
        Generate appropriate headline for a game result.

        Automatically determines type (GAME_RECAP, BLOWOUT, UPSET, COMEBACK).

        Args:
            game_data: Dict with game result data including:
                - winner_id, loser_id
                - winner_score, loser_score
                - home_team_id, away_team_id
                - is_playoff, is_rivalry, etc.
            include_body_text: Whether to generate 4-paragraph body text
                              (Tollgate 4 feature). Default True.

        Returns:
            Generated Headline with body_text if include_body_text=True
        """
        # Determine headline type based on game characteristics
        event_type = self._classify_game_result(game_data)

        # Enrich data with team info
        enriched_data = self._enrich_game_data(game_data)

        # Generate base headline
        headline = self.generate_headline(event_type, enriched_data)

        # Generate body text if requested (Tollgate 4)
        if include_body_text:
            body_text = self._generate_body_text(enriched_data, event_type)
            if body_text:
                headline = replace(headline, body_text=body_text)

        return headline

    def generate_batch(
        self,
        events: List[Tuple[HeadlineType, Dict[str, Any]]]
    ) -> List[Headline]:
        """
        Generate headlines for multiple events.

        Args:
            events: List of (event_type, event_data) tuples

        Returns:
            List of generated Headlines
        """
        headlines = []
        seen_keys = set()  # Track to avoid duplicates

        for event_type, event_data in events:
            headline = self.generate_headline(event_type, event_data)

            # Avoid duplicate headlines
            headline_key = (headline.headline_type, headline.headline)
            if headline_key not in seen_keys:
                headlines.append(headline)
                seen_keys.add(headline_key)

        # Sort by priority (highest first)
        headlines.sort(key=lambda h: h.priority, reverse=True)

        return headlines

    def save_headline(self, headline: Headline) -> int:
        """
        Save a headline to the database.

        Args:
            headline: Headline to save

        Returns:
            ID of saved headline
        """
        headline_dict = {
            "headline_type": headline.headline_type,
            "headline": headline.headline,
            "subheadline": headline.subheadline,
            "body_text": headline.body_text,
            "sentiment": headline.sentiment,
            "priority": headline.priority,
            "team_ids": headline.team_ids,
            "player_ids": headline.player_ids,
            "game_id": headline.game_id,
            "metadata": headline.metadata,
        }

        return self._media_api.save_headline(
            dynasty_id=self._dynasty_id,
            season=self._season,
            week=headline.week,
            headline_data=headline_dict
        )

    def save_headlines(self, headlines: List[Headline]) -> int:
        """
        Save multiple headlines.

        Args:
            headlines: List of Headlines to save

        Returns:
            Number of headlines saved
        """
        count = 0
        for headline in headlines:
            self.save_headline(headline)
            count += 1
        return count

    # =========================================================================
    # Template Matching
    # =========================================================================

    def _get_matching_templates(
        self,
        event_type: HeadlineType,
        event_data: Dict[str, Any]
    ) -> List[HeadlineTemplate]:
        """Get templates that match the event conditions."""
        # Check if this is a playoff game
        playoff_round = event_data.get("playoff_round")

        if playoff_round and playoff_round in PLAYOFF_TEMPLATES:
            # Use playoff-specific templates first
            playoff_template_pool = PLAYOFF_TEMPLATES[playoff_round].get(event_type, [])

            # Filter by conditions
            matching = []
            for template in playoff_template_pool:
                if self._template_matches(template, event_data):
                    matching.append(template)

            # If we found playoff templates, use those exclusively
            if matching:
                self._logger.debug(f"Using {len(matching)} playoff-specific templates for {playoff_round}")
                return matching

            # Fall through to regular templates if no playoff templates match
            self._logger.debug(f"No playoff templates matched for {playoff_round}, using regular templates")

        # Get base templates for this headline type (regular season)
        all_templates = self._templates.get(event_type, [])
        matching = []

        for template in all_templates:
            if self._template_matches(template, event_data):
                matching.append(template)

        return matching

    def _template_matches(
        self,
        template: HeadlineTemplate,
        event_data: Dict[str, Any]
    ) -> bool:
        """Check if event data matches template conditions."""
        if not template.conditions:
            return True  # No conditions = always matches

        for key, expected in template.conditions.items():
            # Handle range conditions
            if key.endswith("_min"):
                base_key = key[:-4]
                actual = event_data.get(base_key)
                if actual is None or actual < expected:
                    return False
            elif key.endswith("_max"):
                base_key = key[:-4]
                actual = event_data.get(base_key)
                if actual is None or actual > expected:
                    return False
            else:
                # Exact match
                actual = event_data.get(key)
                if actual != expected:
                    return False

        return True

    def _fill_template(
        self,
        template: str,
        event_data: Dict[str, Any]
    ) -> str:
        """Fill template placeholders with data."""
        # Handle missing keys gracefully
        class SafeDict(dict):
            def __missing__(self, key):
                return f"{{{key}}}"

        safe_data = SafeDict(event_data)
        return template.format_map(safe_data)

    # =========================================================================
    # Game Classification
    # =========================================================================

    def _should_use_player_headline(
        self,
        game_data: Dict[str, Any],
        enriched_data: Dict[str, Any]
    ) -> Optional[HeadlineType]:
        """
        Determine if a player-focused headline should be used instead of team-focused.

        Priority order:
        1. DEFENSIVE_SHOWCASE - If defensive player has impact >= 12 (lowered for visibility)
        2. DUAL_THREAT - If top 2 players both have impact >= 12 (lowered for visibility)
        3. PLAYER_PERFORMANCE - If top player has impact >= 15 (lowered for visibility)
        4. None - Use team-focused headline

        Typical impact scores:
        - QB: 300 YDS, 3 TDs = 24 impact
        - QB: 350 YDS, 4 TDs = 30 impact
        - RB: 120 YDS, 2 TDs = 24 impact
        - WR: 120 YDS, 1 TD = 18 impact

        Args:
            game_data: Original game data
            enriched_data: Enriched data with player info

        Returns:
            HeadlineType for player-focused headline, or None for team-focused
        """
        # Check if we have player data
        player_impact = enriched_data.get("player_impact", 0)
        if player_impact == 0:
            self._logger.warning(f"[HEADLINE DEBUG] No player impact data - using team-focused headline")
            return None  # No player data available

        # Position is already in abbreviation format (e.g., "WR", "QB") from enrichment
        player_position = enriched_data.get("player_position", "")
        player2_name = enriched_data.get("player2_name", "None")
        player2_impact = enriched_data.get("player2_impact", 0)
        self._logger.warning(f"[HEADLINE DEBUG] Checking player headline - P1: {player_impact:.2f} ({player_position}), P2: {player2_name} ({player2_impact:.2f})")

        # 1. Check for defensive showcase (defensive player with high impact)
        if player_position in DEFENSIVE_POSITIONS and player_impact >= 12:  # Lowered from 22 to 12
            self._logger.warning(f"[HEADLINE DEBUG] ✓ DEFENSIVE_SHOWCASE triggered (impact {player_impact:.2f} >= 12)")
            return HeadlineType.DEFENSIVE_SHOWCASE

        # 2. Check for dual threat (two stars with significant impact)
        player2_impact = enriched_data.get("player2_impact", 0)
        if player_impact >= 12 and player2_impact >= 12:  # Lowered from 18 to 12
            # Position is already in abbreviation format from enrichment
            player2_position = enriched_data.get("player2_position", "")
            self._logger.warning(f"[HEADLINE DEBUG] Checking DUAL_THREAT - player1: {player_impact:.2f} ({player_position}), player2: {player2_impact:.2f} ({player2_position})")

            # Check if they're a QB-WR/RB combo (common narrative)
            if player_position in QB_POSITIONS:
                if player2_position in RECEIVER_POSITIONS or player2_position in RB_POSITIONS:
                    self._logger.warning(f"[HEADLINE DEBUG] ✓ DUAL_THREAT triggered (QB-{player2_position} combo)")
                    return HeadlineType.DUAL_THREAT
                else:
                    self._logger.warning(f"[HEADLINE DEBUG] ✗ DUAL_THREAT failed: QB paired with {player2_position} (need WR/TE/RB)")
            # Or WR/RB-QB (flip case)
            elif player_position in RECEIVER_POSITIONS or player_position in RB_POSITIONS:
                if player2_position in QB_POSITIONS:
                    self._logger.warning(f"[HEADLINE DEBUG] ✓ DUAL_THREAT triggered ({player_position}-QB combo)")
                    return HeadlineType.DUAL_THREAT
                else:
                    self._logger.warning(f"[HEADLINE DEBUG] ✗ DUAL_THREAT failed: {player_position} paired with {player2_position} (need QB)")
            else:
                self._logger.warning(f"[HEADLINE DEBUG] ✗ DUAL_THREAT failed: Neither player is QB/RB/WR/TE combo")

        # 3. Check for dominant individual performance
        if player_impact >= 15:  # Lowered from 25 to 15
            self._logger.warning(f"[HEADLINE DEBUG] ✓ PLAYER_PERFORMANCE triggered (impact {player_impact:.2f} >= 15)")
            return HeadlineType.PLAYER_PERFORMANCE

        # No player-focused headline needed
        self._logger.warning(f"[HEADLINE DEBUG] ✗ No player headline - impact {player_impact:.2f} below threshold (need 15+)")
        return None

    def _classify_game_result(self, game_data: Dict[str, Any]) -> HeadlineType:
        """
        Determine appropriate headline type for game result.

        Priority:
        1. Player-focused headlines (DEFENSIVE_SHOWCASE, DUAL_THREAT, PLAYER_PERFORMANCE)
        2. COMEBACK (if 14+ point comeback)
        3. UPSET (if significant favorite lost)
        4. BLOWOUT (if 21+ point margin)
        5. GAME_RECAP (default)
        """
        # FIRST: Enrich data to get player info
        enriched_data = self._enrich_game_data(game_data)

        # SECOND: Check for player-focused headline
        player_headline_type = self._should_use_player_headline(game_data, enriched_data)
        if player_headline_type:
            return player_headline_type

        # THIRD: Existing team-focused logic
        margin = abs(
            game_data.get("winner_score", 0) - game_data.get("loser_score", 0)
        )
        comeback_points = game_data.get("comeback_points", 0)
        is_upset = game_data.get("is_upset", False)

        # Check for comeback (14+ points)
        if comeback_points >= 14:
            return HeadlineType.COMEBACK

        # Check for upset
        if is_upset:
            return HeadlineType.UPSET

        # Check for blowout (21+ margin)
        if margin >= 21:
            return HeadlineType.BLOWOUT

        # Default to game recap
        return HeadlineType.GAME_RECAP

    def _create_stat_summary(self, player: Dict[str, Any]) -> str:
        """
        Create brief stat summary for secondary players.

        Args:
            player: Player dict with position and stats

        Returns:
            Brief stat summary like "3 TDs, 250 yards"
        """
        # Convert position to abbreviation (handles database format like "wide_receiver")
        from constants.position_abbreviations import get_position_abbreviation
        pos = get_position_abbreviation(player.get("position", ""))

        if pos in QB_POSITIONS:
            tds = player.get("passing_tds", 0)
            yards = player.get("passing_yards", 0)
            return f"{tds} TD{'s' if tds != 1 else ''}, {yards} YDS"

        elif pos in RB_POSITIONS:
            tds = player.get("rushing_tds", 0)
            yards = player.get("rushing_yards", 0)
            return f"{yards} YDS, {tds} TD{'s' if tds != 1 else ''}"

        elif pos in RECEIVER_POSITIONS:
            rec = player.get("receptions", 0)
            yards = player.get("receiving_yards", 0)
            tds = player.get("receiving_tds", 0)
            if tds > 0:
                return f"{rec} REC, {yards} YDS, {tds} TD{'s' if tds != 1 else ''}"
            else:
                return f"{rec} REC, {yards} YDS"

        elif pos in DEFENSIVE_POSITIONS:
            sacks = player.get("sacks", 0)
            ints = player.get("interceptions", 0)
            tackles = player.get("tackles_total", 0)

            # Position-based prioritization
            is_dl = pos in ["DL", "DE", "DT", "LE", "RE", "EDGE"]  # Defensive line
            is_db = pos in ["CB", "FS", "SS"]  # Defensive backs

            # For defensive linemen: sacks are more significant than INTs
            if is_dl:
                if sacks >= 1.0:  # Prioritize sacks for DL
                    return f"{sacks:.1f} SACK{'S' if sacks != 1 else ''}"
                elif ints > 0:
                    return f"{ints} INT{'s' if ints != 1 else ''}"
                elif tackles >= 5:
                    return f"{tackles} TACKLES"

            # For defensive backs: INTs are more significant than sacks
            elif is_db:
                if ints > 0:  # Prioritize INTs for DBs
                    return f"{ints} INT{'s' if ints != 1 else ''}"
                elif sacks > 0:
                    return f"{sacks:.1f} SACK{'S' if sacks != 1 else ''}"
                elif tackles >= 5:
                    return f"{tackles} TACKLES"

            # For linebackers and other: prefer sacks but show INTs if no sacks
            else:
                if sacks >= 1.0:
                    return f"{sacks:.1f} SACK{'S' if sacks != 1 else ''}"
                elif ints > 0:
                    return f"{ints} INT{'s' if ints != 1 else ''}"
                elif tackles >= 5:
                    return f"{tackles} TACKLES"

            # Fallback: show tackles if nothing else significant
            return f"{tackles} TACKLES" if tackles > 0 else "0 TACKLES"

        return "key contribution"

    def _enrich_game_data(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add team names and computed fields to game data."""
        enriched = dict(game_data)

        # Get winner/loser team info
        winner_id = game_data.get("winner_id")
        loser_id = game_data.get("loser_id")

        if winner_id:
            winner_info = self._get_team_info(winner_id)
            enriched["winner"] = winner_info["team"]
            enriched["winner_city"] = winner_info["city"]
            enriched["winner_nickname"] = winner_info["nickname"]

            # Add uppercase version for emphasis (e.g., "SAN FRANCISCO WIN SUPER BOWL")
            enriched["winner_caps"] = winner_info["team"].upper()

            # Determine conference for playoff headlines
            if winner_id in AFC_TEAM_IDS:
                enriched["conference"] = "AFC"
            elif winner_id in NFC_TEAM_IDS:
                enriched["conference"] = "NFC"
            else:
                enriched["conference"] = "Unknown"

        if loser_id:
            loser_info = self._get_team_info(loser_id)
            enriched["loser"] = loser_info["team"]
            enriched["loser_city"] = loser_info["city"]
            enriched["loser_nickname"] = loser_info["nickname"]

        # Calculate margin
        winner_score = game_data.get("winner_score", 0)
        loser_score = game_data.get("loser_score", 0)
        enriched["margin"] = winner_score - loser_score
        enriched["score"] = f"{winner_score}-{loser_score}"

        # Determine home/away winner
        home_team_id = game_data.get("home_team_id")
        enriched["winner_is_home"] = (winner_id == home_team_id)

        # Set team_ids for headline association
        team_ids = []
        if winner_id:
            team_ids.append(winner_id)
        if loser_id:
            team_ids.append(loser_id)
        enriched["team_ids"] = team_ids

        # Add team records from standings (for subheadlines)
        try:
            from ..database.standings_api import StandingsAPI
            from ..database.connection import GameCycleDatabase

            gc_db = GameCycleDatabase(self._db_path)
            try:
                standings_api = StandingsAPI(gc_db)

                if winner_id:
                    winner_standing = standings_api.get_team_standing(
                        self._dynasty_id, self._season, winner_id
                    )
                    if winner_standing:
                        enriched["winner_record"] = f"{winner_standing.wins}-{winner_standing.losses}"
                    else:
                        enriched["winner_record"] = "1-0"

                if loser_id:
                    loser_standing = standings_api.get_team_standing(
                        self._dynasty_id, self._season, loser_id
                    )
                    if loser_standing:
                        enriched["loser_record"] = f"{loser_standing.wins}-{loser_standing.losses}"
                    else:
                        enriched["loser_record"] = "0-1"
            finally:
                gc_db.close()
        except Exception as e:
            self._logger.warning(f"Could not fetch standings for records: {e}")
            enriched["winner_record"] = "N/A"
            enriched["loser_record"] = "N/A"

        # Add player data for player-focused headlines
        game_id = game_data.get("game_id")
        if game_id and winner_id:
            try:
                top_players = self._get_top_players_by_stats(game_id, winner_id, limit=4)  # Increased from 3 to 4

                # DEBUG: Log player data retrieval
                self._logger.warning(f"[HEADLINE DEBUG] game_id={game_id}, winner_id={winner_id}")
                self._logger.warning(f"[HEADLINE DEBUG] top_players count: {len(top_players)}")
                if top_players:
                    self._logger.warning(f"[HEADLINE DEBUG] Top player: {top_players[0].get('player_name')} (pos: {top_players[0].get('position')}, impact: {top_players[0].get('impact', 0):.2f})")
                    if len(top_players) > 1:
                        self._logger.warning(f"[HEADLINE DEBUG] 2nd player: {top_players[1].get('player_name')} (pos: {top_players[1].get('position')}, impact: {top_players[1].get('impact', 0):.2f})")
                else:
                    self._logger.warning(f"[HEADLINE DEBUG] NO PLAYER DATA - query returned empty list")

                if top_players:
                    # Primary player
                    player = top_players[0]

                    # Convert position to abbreviation (handles database format like "wide_receiver")
                    from constants.position_abbreviations import get_position_abbreviation
                    pos = get_position_abbreviation(player.get("position", ""))

                    enriched["player_name"] = player.get("player_name", "Unknown")
                    enriched["player_position"] = pos  # Store abbreviation instead of raw position
                    enriched["player_impact"] = player.get("impact", 0)

                    # Position-specific stats
                    if pos in QB_POSITIONS:
                        enriched["player_passing_yards"] = player.get("passing_yards", 0)
                        enriched["player_passing_tds"] = player.get("passing_tds", 0)
                        enriched["player_passing_ints"] = player.get("passing_interceptions", 0)
                        enriched["player_completions"] = player.get("passing_completions", 0)
                        enriched["player_attempts"] = player.get("passing_attempts", 0)

                        # Create stat highlight for QB
                        tds = player.get("passing_tds", 0)
                        yards = player.get("passing_yards", 0)
                        ints = player.get("passing_interceptions", 0)
                        if ints > 0:
                            enriched["stat_highlight"] = f"{tds} TD{'s' if tds != 1 else ''}, {yards} YDS, {ints} INT{'s' if ints != 1 else ''}"
                        else:
                            enriched["stat_highlight"] = f"{tds} TD{'s' if tds != 1 else ''}, {yards} YDS"

                    elif pos in RB_POSITIONS:
                        enriched["player_rushing_yards"] = player.get("rushing_yards", 0)
                        enriched["player_rushing_tds"] = player.get("rushing_tds", 0)
                        enriched["player_carries"] = player.get("rushing_attempts", 0)

                        # Create stat highlight for RB
                        yards = player.get("rushing_yards", 0)
                        tds = player.get("rushing_tds", 0)
                        enriched["stat_highlight"] = f"{yards} YDS, {tds} TD{'s' if tds != 1 else ''}"

                    elif pos in RECEIVER_POSITIONS:
                        enriched["player_receiving_yards"] = player.get("receiving_yards", 0)
                        enriched["player_receiving_tds"] = player.get("receiving_tds", 0)
                        enriched["player_receptions"] = player.get("receptions", 0)
                        enriched["player_targets"] = player.get("targets", 0)

                        # Create stat highlight for WR/TE
                        rec = player.get("receptions", 0)
                        yards = player.get("receiving_yards", 0)
                        tds = player.get("receiving_tds", 0)
                        if tds > 0:
                            enriched["stat_highlight"] = f"{rec} REC, {yards} YDS, {tds} TD{'s' if tds != 1 else ''}"
                        else:
                            enriched["stat_highlight"] = f"{rec} REC, {yards} YDS"

                    elif pos in DEFENSIVE_POSITIONS:
                        enriched["player_tackles"] = player.get("tackles_total", 0)
                        enriched["player_sacks"] = player.get("sacks", 0)
                        enriched["player_ints"] = player.get("interceptions", 0)
                        enriched["player_forced_fumbles"] = player.get("forced_fumbles", 0)

                        # Create stat highlight for defensive player (position-aware prioritization)
                        sacks = player.get("sacks", 0)
                        ints = player.get("interceptions", 0)
                        tackles = player.get("tackles_total", 0)

                        # Position-based prioritization
                        is_dl = pos in ["DL", "DE", "DT", "LE", "RE", "EDGE"]
                        is_db = pos in ["CB", "FS", "SS"]

                        if is_dl:
                            # Defensive line: prioritize sacks
                            if sacks >= 1.0:
                                enriched["stat_highlight"] = f"{sacks:.1f} SACK{'S' if sacks != 1 else ''}"
                            elif ints > 0:
                                enriched["stat_highlight"] = f"{ints} INT{'s' if ints != 1 else ''}"
                            else:
                                enriched["stat_highlight"] = f"{tackles} TACKLES"
                        elif is_db:
                            # Defensive backs: prioritize INTs
                            if ints > 0:
                                enriched["stat_highlight"] = f"{ints} INT{'s' if ints != 1 else ''}"
                            elif sacks > 0:
                                enriched["stat_highlight"] = f"{sacks:.1f} SACK{'S' if sacks != 1 else ''}"
                            else:
                                enriched["stat_highlight"] = f"{tackles} TACKLES"
                        else:
                            # Linebackers: prefer sacks
                            if sacks >= 1.0:
                                enriched["stat_highlight"] = f"{sacks:.1f} SACK{'S' if sacks != 1 else ''}"
                            elif ints > 0:
                                enriched["stat_highlight"] = f"{ints} INT{'s' if ints != 1 else ''}"
                            else:
                                enriched["stat_highlight"] = f"{tackles} TACKLES"

                    # Secondary player for DUAL_THREAT
                    if len(top_players) > 1:
                        player2 = top_players[1]
                        pos2 = get_position_abbreviation(player2.get("position", ""))
                        enriched["player2_name"] = player2.get("player_name", "Unknown")
                        enriched["player2_position"] = pos2  # Store abbreviation instead of raw position
                        enriched["player2_impact"] = player2.get("impact", 0)
                        enriched["player2_stat_summary"] = self._create_stat_summary(player2)

                        # For DUAL_THREAT "QB to WR" style headlines, ensure QB is player1
                        # If player1 is WR/RB/TE and player2 is QB, swap them
                        if (pos in RECEIVER_POSITIONS or pos in RB_POSITIONS) and pos2 in QB_POSITIONS:
                            # Swap player1 and player2 so QB comes first (for "X to Y" templates)
                            enriched["player_name"], enriched["player2_name"] = enriched["player2_name"], enriched["player_name"]
                            enriched["player_position"], enriched["player2_position"] = enriched["player2_position"], enriched["player_position"]
                            enriched["player_impact"], enriched["player2_impact"] = enriched["player2_impact"], enriched["player_impact"]
                            # Swap stat summaries - need to regenerate stat_highlight for the new player1 (QB)
                            old_stat_highlight = enriched.get("stat_highlight", "")
                            enriched["stat_highlight"] = enriched["player2_stat_summary"]
                            enriched["player2_stat_summary"] = old_stat_highlight
                            self._logger.warning(f"[HEADLINE DEBUG] Swapped players for QB-first ordering: {enriched['player_name']} (QB) to {enriched['player2_name']}")

            except Exception as e:
                self._logger.debug(f"Could not fetch player data for headline enrichment: {e}")
                # Player data is optional, continue without it

        return enriched

    # =========================================================================
    # Priority Calculation
    # =========================================================================

    def _calculate_priority(
        self,
        event_type: HeadlineType,
        event_data: Dict[str, Any],
        template: HeadlineTemplate
    ) -> int:
        """Calculate headline priority score (1-100)."""
        base = BASE_PRIORITIES.get(event_type, 50)
        modifiers = template.priority_boost

        # Event-specific modifiers
        if event_data.get("is_playoff"):
            modifiers += 20
        if event_data.get("is_rivalry"):
            modifiers += 10
        if event_data.get("is_primetime"):
            modifiers += 5
        if event_data.get("is_record"):
            modifiers += 15

        # Game margin modifiers
        margin = event_data.get("margin")
        if margin and margin >= 28:
            modifiers += 10
        elif margin and margin >= 35:
            modifiers += 15

        # Comeback modifiers
        comeback_points = event_data.get("comeback_points")
        if comeback_points and comeback_points >= 21:
            modifiers += 10
        elif comeback_points and comeback_points >= 28:
            modifiers += 15

        # Star player modifier
        if event_data.get("is_star"):
            modifiers += 10

        # Clinching modifiers
        if event_data.get("clinches_playoff"):
            modifiers += 15
        if event_data.get("clinches_division"):
            modifiers += 20

        return min(100, max(1, base + modifiers))

    # =========================================================================
    # Fallback
    # =========================================================================

    def _create_fallback_headline(
        self,
        event_type: HeadlineType,
        event_data: Dict[str, Any]
    ) -> Headline:
        """Create generic fallback headline when no template matches."""
        headline_text = f"{event_type.value.replace('_', ' ').title()}"

        return Headline(
            id=None,
            dynasty_id=self._dynasty_id,
            season=self._season,
            week=event_data.get("week", 1),
            headline_type=event_type.value,
            headline=headline_text,
            subheadline=None,
            body_text=None,
            sentiment=Sentiment.NEUTRAL.value,
            priority=BASE_PRIORITIES.get(event_type, 50),
            team_ids=event_data.get("team_ids", []),
            player_ids=event_data.get("player_ids", []),
            game_id=event_data.get("game_id"),
            metadata={},
            created_at=None,
        )

    # =========================================================================
    # Body Text Generation (Tollgate 4)
    # =========================================================================

    def _gather_recap_data(
        self,
        game_id: str,
        winner_id: int,
        loser_id: int
    ) -> Dict[str, Any]:
        """
        Gather data from all APIs for body text generation.

        Uses 3-tier fallback strategy:
        1. Full data (FULL sim): PlayGrades + GameGrades + BoxScores
        2. Partial data (Quick sim with box): No PlayGrades
        3. Minimal data (Quick sim basic): Only basic game info

        Args:
            game_id: Game identifier
            winner_id: Winning team ID
            loser_id: Losing team ID

        Returns:
            Dict with all gathered data for body text generation
        """
        recap_data: Dict[str, Any] = {
            "has_box_scores": False,
            "has_game_grades": False,
            "has_play_grades": False,
            "box_scores": [],
            "game_grades": [],
            "play_grades": [],
            "winner_standing": None,
            "loser_standing": None,
            "rivalry": None,
        }

        # Try to get box scores
        try:
            box_scores = self._box_scores_api.get_game_box_scores(
                self._dynasty_id, game_id
            )
            if box_scores:
                recap_data["box_scores"] = box_scores
                recap_data["has_box_scores"] = True
                # Map box scores to teams
                for box in box_scores:
                    if box.team_id == winner_id:
                        recap_data["winner_box"] = box
                    elif box.team_id == loser_id:
                        recap_data["loser_box"] = box
        except Exception as e:
            self._logger.debug(f"Could not get box scores for {game_id}: {e}")

        # Try to get game grades (player performance)
        try:
            game_grades = self._analytics_api.get_game_grades(
                self._dynasty_id, game_id
            )
            if game_grades:
                recap_data["game_grades"] = game_grades
                recap_data["has_game_grades"] = True
                # Separate by team
                recap_data["winner_grades"] = [
                    g for g in game_grades if g.team_id == winner_id
                ]
                recap_data["loser_grades"] = [
                    g for g in game_grades if g.team_id == loser_id
                ]
        except Exception as e:
            self._logger.debug(f"Could not get game grades for {game_id}: {e}")

        # Try to get play grades (for turning point)
        try:
            play_grades = self._play_grades_api.get_game_play_grades(
                self._dynasty_id, game_id
            )
            if play_grades:
                recap_data["play_grades"] = play_grades
                recap_data["has_play_grades"] = True
        except Exception as e:
            self._logger.debug(f"Could not get play grades for {game_id}: {e}")

        # Get standings for playoff implications
        try:
            winner_standing = self._standings_api.get_team_standing(
                self._dynasty_id, self._season, winner_id
            )
            loser_standing = self._standings_api.get_team_standing(
                self._dynasty_id, self._season, loser_id
            )
            recap_data["winner_standing"] = winner_standing
            recap_data["loser_standing"] = loser_standing
        except Exception as e:
            self._logger.debug(f"Could not get standings: {e}")

        # Check for rivalry
        try:
            rivalry = self._rivalry_api.get_rivalry_between_teams(
                self._dynasty_id, winner_id, loser_id
            )
            recap_data["rivalry"] = rivalry
        except Exception as e:
            self._logger.debug(f"Could not get rivalry info: {e}")

        return recap_data

    def _generate_opening_paragraph(
        self,
        game_data: Dict[str, Any],
        headline_type: HeadlineType,
        recap_data: Dict[str, Any]
    ) -> str:
        """
        Generate the opening paragraph of the game recap.

        Args:
            game_data: Enriched game data with team names, scores, etc.
            headline_type: Type of game (GAME_RECAP, BLOWOUT, etc.)
            recap_data: Data gathered from APIs

        Returns:
            Opening paragraph string
        """
        # Get appropriate template list
        templates = OPENING_PARAGRAPH_TEMPLATES.get(
            headline_type,
            OPENING_PARAGRAPH_TEMPLATES[HeadlineType.GAME_RECAP]
        )

        # Select random template
        template = random.choice(templates)

        # Build context for template
        context = dict(game_data)

        # Add additional context
        context["day_of_week"] = "Sunday"  # Could be dynamic
        context["venue_type"] = "home" if game_data.get("winner_is_home") else "road"

        # Add records if we have standings
        if recap_data.get("winner_standing"):
            standing = recap_data["winner_standing"]
            context["winner_record"] = f"{standing.wins}-{standing.losses}"
        else:
            context["winner_record"] = "N/A"

        if recap_data.get("loser_standing"):
            standing = recap_data["loser_standing"]
            context["loser_record"] = f"{standing.wins}-{standing.losses}"
        else:
            context["loser_record"] = "N/A"

        # Ensure comeback_points is present for COMEBACK templates
        if "comeback_points" not in context:
            context["comeback_points"] = game_data.get("comeback_points", 0)

        return self._fill_template(template, context)

    def _format_stat_line(
        self,
        player_stats: Dict[str, Any],
        position: str
    ) -> str:
        """
        Format a player's stats into a readable stat line.

        This method provides backward compatibility with the older key names.
        It maps keys to the format expected by _format_player_stat_line().

        Args:
            player_stats: Dict with player statistics
            position: Player's position (QB, RB, WR, etc.)

        Returns:
            Formatted stat line string (e.g., "312 yards, 3 TDs")
        """
        # Map legacy key names to the format expected by _format_player_stat_line()
        player = dict(player_stats)
        player["position"] = position

        # Map alternative key names
        if "completions" in player_stats:
            player["passing_completions"] = player_stats["completions"]
        if "pass_attempts" in player_stats:
            player["passing_attempts"] = player_stats["pass_attempts"]
        if "carries" in player_stats:
            player["rushing_attempts"] = player_stats["carries"]
        # Map interceptions to passing_interceptions for QB
        # Convert position to abbreviation (handles database format like "wide_receiver")
        from constants.position_abbreviations import get_position_abbreviation
        position_abbr = get_position_abbreviation(position) if position else ""
        if position_abbr in QB_POSITIONS and "interceptions" in player_stats:
            player["passing_interceptions"] = player_stats["interceptions"]

        result = self._format_player_stat_line(player)

        # Handle fallback for overall_grade (not supported in _format_player_stat_line)
        if result == "key contribution":
            overall = player_stats.get("overall_grade", 0)
            if overall:
                return f"a game grade of {overall:.1f}"
            return "a solid performance"

        return result

    def _get_player_name(self, player_id: int) -> str:
        """
        Get player name from player_id.

        Looks up the player in the database and caches the result.

        Args:
            player_id: The player's ID

        Returns:
            Player's full name (first + last), or fallback if not found
        """
        # Check cache first
        if player_id in self._player_names_cache:
            return self._player_names_cache[player_id]

        # Look up in database
        try:
            conn = self._db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT first_name, last_name
                FROM players
                WHERE dynasty_id = ? AND player_id = ?
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            if row:
                first_name = row[0] or ""
                last_name = row[1] or ""
                full_name = f"{first_name} {last_name}".strip()
                if full_name:
                    self._player_names_cache[player_id] = full_name
                    return full_name

            # Player not found, return fallback
            self._logger.debug(f"Player {player_id} not found in database")
            return f"Player #{player_id}"

        except Exception as e:
            self._logger.warning(f"Error looking up player {player_id}: {e}")
            return f"Player #{player_id}"

    def _calculate_player_impact(self, stats: Dict[str, Any]) -> float:
        """
        Calculate impact score from player stats.

        Uses configurable weights from IMPACT_WEIGHTS constant.

        Args:
            stats: Dict with player statistics

        Returns:
            Weighted impact score (higher = more impactful player)
        """
        return sum(
            stats.get(stat, 0) * weight
            for stat, weight in IMPACT_WEIGHTS.items()
        )

    def _get_top_players_by_stats(
        self,
        game_id: str,
        team_id: int,
        limit: int = 4  # Increased from 3 to allow more defensive player visibility
    ) -> List[Dict[str, Any]]:
        """
        Get top performing players for a team in a game based on stats.

        Ranks players by impact: passing yards, rushing yards, receiving yards,
        tackles, sacks, interceptions.

        Args:
            game_id: Game identifier
            team_id: Team to get players for
            limit: Maximum number of players to return

        Returns:
            List of player dicts with name, position, and stats
        """
        try:
            conn = self._db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    player_id,
                    player_name,
                    position,
                    passing_yards,
                    passing_tds,
                    passing_completions,
                    passing_attempts,
                    passing_interceptions,
                    rushing_yards,
                    rushing_tds,
                    rushing_attempts,
                    receiving_yards,
                    receiving_tds,
                    receptions,
                    targets,
                    tackles_total,
                    tackles_for_loss,
                    sacks,
                    interceptions,
                    forced_fumbles,
                    passes_defended
                FROM player_game_stats
                WHERE dynasty_id = ? AND game_id = ? AND team_id = ?
            """, (self._dynasty_id, game_id, team_id))

            rows = cursor.fetchall()
            players = []

            for row in rows:
                player_id = row[0]
                player_name = row[1] or self._get_player_name(int(player_id) if player_id else 0)
                position = row[2] or "Unknown"

                # Build stats dict for impact calculation and output
                player_stats = {
                    "player_id": player_id,
                    "player_name": player_name,
                    "position": position,
                    "passing_yards": row[3] or 0,
                    "passing_tds": row[4] or 0,
                    "passing_completions": row[5] or 0,
                    "passing_attempts": row[6] or 0,
                    "passing_interceptions": row[7] or 0,
                    "rushing_yards": row[8] or 0,
                    "rushing_tds": row[9] or 0,
                    "rushing_attempts": row[10] or 0,
                    "receiving_yards": row[11] or 0,
                    "receiving_tds": row[12] or 0,
                    "receptions": row[13] or 0,
                    "targets": row[14] or 0,
                    "tackles_total": row[15] or 0,
                    "tackles_for_loss": row[16] or 0,
                    "sacks": row[17] or 0,
                    "interceptions": row[18] or 0,
                    "forced_fumbles": row[19] or 0,
                    "passes_defended": row[20] or 0,
                }

                # Calculate impact using configurable weights
                impact = self._calculate_player_impact(player_stats)

                if impact > 0:
                    player_stats["impact"] = impact
                    players.append(player_stats)

            # Sort by impact and return top players
            players.sort(key=lambda p: p["impact"], reverse=True)
            return players[:limit]

        except Exception as e:
            self._logger.warning(f"Error getting player stats: {e}")
            return []

    def _get_top_defensive_player(
        self,
        game_id: str,
        team_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get top defensive player for a team in a game.

        Ranks by defensive impact: interceptions, sacks, forced fumbles,
        tackles, passes defended.

        Args:
            game_id: Game identifier
            team_id: Team ID

        Returns:
            Dict with player name, position, and defensive stats, or None
        """
        try:
            conn = self._db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    player_id,
                    player_name,
                    position,
                    tackles_total,
                    sacks,
                    interceptions,
                    forced_fumbles,
                    passes_defended,
                    tackles_for_loss,
                    qb_hits
                FROM player_game_stats
                WHERE dynasty_id = ? AND game_id = ? AND team_id = ?
                  AND position IN ('LB', 'MLB', 'OLB', 'LOLB', 'ROLB',
                                   'DE', 'DT', 'LE', 'RE', 'EDGE',
                                   'CB', 'FS', 'SS', 'S', 'DB')
                ORDER BY
                    (COALESCE(interceptions, 0) * 5) +
                    (COALESCE(sacks, 0) * 3) +
                    (COALESCE(forced_fumbles, 0) * 3) +
                    (COALESCE(tackles_total, 0) * 0.5) +
                    (COALESCE(passes_defended, 0) * 1) DESC
                LIMIT 1
            """, (self._dynasty_id, game_id, team_id))

            row = cursor.fetchone()
            if row:
                return {
                    "player_name": row[1] or f"Player #{row[0]}",
                    "position": row[2] or "DEF",
                    "tackles_total": row[3] or 0,
                    "sacks": row[4] or 0,
                    "interceptions": row[5] or 0,
                    "forced_fumbles": row[6] or 0,
                    "passes_defended": row[7] or 0,
                    "tackles_for_loss": row[8] or 0,
                    "qb_hits": row[9] or 0,
                }
            return None

        except Exception as e:
            self._logger.warning(f"Error getting top defender: {e}")
            return None

    def _format_player_stat_line(self, player: Dict[str, Any]) -> str:
        """
        Format a player's stats into a readable stat line.

        Args:
            player: Player dict with stats

        Returns:
            Formatted stat line string
        """
        # Convert position to abbreviation (handles database format like "wide_receiver")
        from constants.position_abbreviations import get_position_abbreviation
        position = get_position_abbreviation(player.get("position", ""))

        # QB stat line
        if position in QB_POSITIONS and player.get("passing_yards", 0) > 0:
            comp = player.get("passing_completions", 0)
            att = player.get("passing_attempts", 0)
            yds = player.get("passing_yards", 0)
            tds = player.get("passing_tds", 0)
            ints = player.get("passing_interceptions", 0)
            parts = [f"{comp}/{att} for {yds} yards"]
            if tds > 0:
                parts.append(f"{tds} TD{'s' if tds > 1 else ''}")
            if ints > 0:
                parts.append(f"{ints} INT")
            return ", ".join(parts)

        # RB stat line
        if position in RB_POSITIONS and player.get("rushing_yards", 0) > 0:
            att = player.get("rushing_attempts", 0)
            yds = player.get("rushing_yards", 0)
            tds = player.get("rushing_tds", 0)
            parts = [f"{att} carries for {yds} yards"]
            if tds > 0:
                parts.append(f"{tds} TD{'s' if tds > 1 else ''}")
            # Add receiving if significant
            rec_yds = player.get("receiving_yards", 0)
            if rec_yds >= 20:
                parts.append(f"{player.get('receptions', 0)} catches for {rec_yds} yards")
            return ", ".join(parts)

        # WR/TE stat line
        if position in RECEIVER_POSITIONS and player.get("receiving_yards", 0) > 0:
            rec = player.get("receptions", 0)
            yds = player.get("receiving_yards", 0)
            tds = player.get("receiving_tds", 0)
            parts = [f"{rec} catches for {yds} yards"]
            if tds > 0:
                parts.append(f"{tds} TD{'s' if tds > 1 else ''}")
            return ", ".join(parts)

        # Defensive stat line
        if position in DEFENSIVE_POSITIONS:
            parts = []
            tackles = player.get("tackles_total", 0)
            sacks = player.get("sacks", 0)
            ints = player.get("interceptions", 0)
            pds = player.get("passes_defended", 0)
            ff = player.get("forced_fumbles", 0)

            if tackles > 0:
                parts.append(f"{tackles} tackles")
            if sacks > 0:
                parts.append(f"{sacks:.1f} sack{'s' if sacks > 1 else ''}" if sacks != int(sacks) else f"{int(sacks)} sack{'s' if sacks > 1 else ''}")
            if ints > 0:
                parts.append(f"{ints} INT")
            if pds > 0 and ints == 0:
                parts.append(f"{pds} PD")
            if ff > 0:
                parts.append(f"{ff} FF")

            return ", ".join(parts) if parts else "solid defensive performance"

        # Fallback
        return "key contribution"

    def _generate_star_players_paragraph(
        self,
        game_data: Dict[str, Any],
        recap_data: Dict[str, Any]
    ) -> str:
        """
        Generate paragraph highlighting star performers with actual stats.

        Prioritizes player_game_stats for actual stat lines, falls back to
        game grades or box score data.

        Args:
            game_data: Enriched game data
            recap_data: Data gathered from APIs

        Returns:
            Star players paragraph string
        """
        # Get info
        game_id = game_data.get("game_id")
        winner_id = game_data.get("winner_id")
        loser_id = game_data.get("loser_id")
        winner_city = game_data.get("winner_city", "The winner")
        winner_nickname = game_data.get("winner_nickname", "team")
        loser_name = game_data.get("loser", "the opponent")

        # Defaults
        star_player = "the offense"
        star_stat_line = "an efficient performance"
        secondary_sentence = ""

        # Try to get actual player stats first
        if game_id and winner_id:
            winner_top_players = self._get_top_players_by_stats(game_id, winner_id, limit=2)

            if winner_top_players:
                # Get star player with their stat line
                top_player = winner_top_players[0]
                star_player = top_player.get("player_name", "the offense")
                star_stat_line = self._format_player_stat_line(top_player)

                # Get secondary player if available
                if len(winner_top_players) > 1:
                    second_player = winner_top_players[1]
                    second_name = second_player.get("player_name", "")
                    second_stats = self._format_player_stat_line(second_player)
                    if second_name and second_stats != "key contribution":
                        secondary_sentence = f"{second_name} also contributed with {second_stats}."

            # Try to get a player from losing team for perspective
            if loser_id and not secondary_sentence:
                loser_top_players = self._get_top_players_by_stats(game_id, loser_id, limit=1)
                if loser_top_players:
                    loser_player = loser_top_players[0]
                    loser_name_str = loser_player.get("player_name", "")
                    loser_stats = self._format_player_stat_line(loser_player)
                    if loser_name_str and loser_stats != "key contribution":
                        secondary_template = random.choice(SECONDARY_PLAYER_SENTENCES)
                        secondary_sentence = secondary_template.format(
                            player_name=loser_name_str,
                            stat_line=loser_stats,
                            team_name=loser_name
                        )

        # Fallback to box scores if no player stats found
        if star_player == "the offense" and recap_data.get("has_box_scores"):
            winner_box = recap_data.get("winner_box")
            if winner_box:
                total_yards = winner_box.total_yards
                pass_yards = winner_box.passing_yards
                rush_yards = winner_box.rushing_yards

                if pass_yards > rush_yards:
                    star_player = "the passing game"
                    star_stat_line = f"{pass_yards} passing yards"
                else:
                    star_player = "the ground game"
                    star_stat_line = f"{rush_yards} rushing yards"

                if not secondary_sentence:
                    secondary_sentence = f"The {winner_nickname} totaled {total_yards} yards of offense."

        # Check if top player is defensive to select appropriate template
        is_defensive_star = False
        if game_id and winner_id:
            winner_top_players = self._get_top_players_by_stats(game_id, winner_id, limit=1)
            if winner_top_players:
                # Convert position to abbreviation (handles database format like "wide_receiver")
                from constants.position_abbreviations import get_position_abbreviation
                top_player_pos = get_position_abbreviation(winner_top_players[0].get("position", ""))
                if top_player_pos in DEFENSIVE_POSITIONS:
                    is_defensive_star = True

        # Select and fill template
        if is_defensive_star:
            template = random.choice(DEFENSIVE_STAR_TEMPLATES)
        else:
            template = random.choice(STAR_PLAYERS_TEMPLATES)

        return template.format(
            star_player=star_player,
            stat_line=star_stat_line,
            secondary_player_sentence=secondary_sentence,
            winner_city=winner_city,
            winner_nickname=winner_nickname
        )

    def _generate_defensive_paragraph(
        self,
        game_data: Dict[str, Any],
        recap_data: Dict[str, Any]
    ) -> str:
        """
        Generate paragraph highlighting defensive standouts from both teams.

        Args:
            game_data: Enriched game data
            recap_data: Data gathered from APIs

        Returns:
            Defensive standouts paragraph string, or empty string if no data
        """
        game_id = game_data.get("game_id")
        winner_id = game_data.get("winner_id")
        loser_id = game_data.get("loser_id")
        winner_nickname = game_data.get("winner_nickname", "team")
        loser_name = game_data.get("loser", "the opponent")

        if not game_id:
            return ""

        # Get top defenders from each team
        winner_def = self._get_top_defensive_player(game_id, winner_id) if winner_id else None
        loser_def = self._get_top_defensive_player(game_id, loser_id) if loser_id else None

        # Need at least winner's defender to generate paragraph
        if not winner_def:
            return ""

        winner_defender = winner_def.get("player_name", "the defense")
        winner_def_stats = self._format_player_stat_line(winner_def)

        # Skip if no meaningful stats
        if not winner_def_stats or winner_def_stats == "solid defensive performance":
            return ""

        # Build loser defender sentence if available
        loser_defender_sentence = ""
        if loser_def:
            loser_defender = loser_def.get("player_name", "a defender")
            loser_def_stats = self._format_player_stat_line(loser_def)
            if loser_def_stats and loser_def_stats != "solid defensive performance":
                loser_template = random.choice(LOSER_DEFENDER_SENTENCE_TEMPLATES)
                loser_defender_sentence = loser_template.format(
                    loser_name=loser_name,
                    loser_defender=loser_defender,
                    loser_def_stats=loser_def_stats
                )

        # Select and fill template
        template = random.choice(DEFENSIVE_STANDOUTS_TEMPLATES)
        return template.format(
            winner_defender=winner_defender,
            winner_def_stats=winner_def_stats,
            winner_nickname=winner_nickname,
            loser_defender_sentence=loser_defender_sentence
        )

    def _find_turning_point_play(
        self,
        recap_data: Dict[str, Any],
        winner_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Find the turning point play (highest EPA contribution for winner).

        Args:
            recap_data: Data gathered from APIs
            winner_id: Winning team ID

        Returns:
            Dict with play info, or None if not found
        """
        if not recap_data.get("has_play_grades"):
            return None

        play_grades = recap_data.get("play_grades", [])

        # Filter to winner's plays and find highest EPA
        winner_plays = [
            p for p in play_grades
            if p.team_id == winner_id and p.epa_contribution
        ]

        if not winner_plays:
            return None

        # Sort by EPA contribution (descending)
        winner_plays.sort(key=lambda p: p.epa_contribution or 0, reverse=True)

        top_play = winner_plays[0]

        # Map quarter number to text
        quarter_map = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "overtime"}

        return {
            "quarter": quarter_map.get(top_play.context.quarter if top_play.context else 1, "third"),
            "quarter_context": f"in the {quarter_map.get(top_play.context.quarter if top_play.context else 3, 'third')} quarter",
            "play_type": top_play.context.play_type if top_play.context else "play",
            "epa": top_play.epa_contribution,
            "down": top_play.context.down if top_play.context else 1,
            "distance": top_play.context.distance if top_play.context else 10,
        }

    def _generate_turning_point_paragraph(
        self,
        game_data: Dict[str, Any],
        recap_data: Dict[str, Any]
    ) -> str:
        """
        Generate paragraph describing the game's turning point.

        Uses play grades for specific moments if available,
        falls back to scoring summary from box scores.

        Args:
            game_data: Enriched game data
            recap_data: Data gathered from APIs

        Returns:
            Turning point paragraph string
        """
        winner_id = game_data.get("winner_id")
        winner_city = game_data.get("winner_city", "The winner")
        winner_nickname = game_data.get("winner_nickname", "team")
        loser_nickname = game_data.get("loser_nickname", "opponent")

        # Try to find a specific turning point play
        turning_point = self._find_turning_point_play(recap_data, winner_id)

        if turning_point:
            # Describe the play
            play_type = turning_point.get("play_type", "play")
            down = turning_point.get("down", 3)
            distance = turning_point.get("distance", 5)

            play_descriptions = [
                f"a crucial {play_type} on {down}{'st' if down == 1 else 'nd' if down == 2 else 'rd' if down == 3 else 'th'} and {distance}",
                f"a big {play_type} that swung momentum",
                f"a key {down}{'st' if down == 1 else 'nd' if down == 2 else 'rd' if down == 3 else 'th'}-down conversion",
                f"an explosive {play_type} that changed everything",
            ]

            context = {
                "quarter": turning_point.get("quarter", "third"),
                "quarter_context": turning_point.get("quarter_context", "in the third quarter"),
                "play_description": random.choice(play_descriptions),
                "winner_city": winner_city,
                "winner_nickname": winner_nickname,
                "loser_nickname": loser_nickname,
            }

            template = random.choice(TURNING_POINT_TEMPLATES)
            return self._fill_template(template, context)

        # Fallback to scoring summary if we have box scores
        if recap_data.get("has_box_scores"):
            winner_box = recap_data.get("winner_box")
            if winner_box:
                # Create quarter-by-quarter narrative
                quarters = []
                if winner_box.q1_score > 0:
                    quarters.append(f"{winner_box.q1_score} in Q1")
                if winner_box.q2_score > 0:
                    quarters.append(f"{winner_box.q2_score} in Q2")
                if winner_box.q3_score > 0:
                    quarters.append(f"{winner_box.q3_score} in Q3")
                if winner_box.q4_score > 0:
                    quarters.append(f"{winner_box.q4_score} in Q4")

                quarter_breakdown = "They scored " + ", ".join(quarters) + "." if quarters else ""

                # Describe scoring pattern
                if winner_box.q1_score >= 14:
                    scoring_desc = "a fast start"
                elif winner_box.q3_score + winner_box.q4_score > winner_box.q1_score + winner_box.q2_score:
                    scoring_desc = "a strong second half"
                else:
                    scoring_desc = "balanced scoring throughout"

                template = random.choice(SCORING_SUMMARY_TEMPLATES)
                return template.format(
                    winner_nickname=winner_nickname,
                    winner_city=winner_city,
                    scoring_description=scoring_desc,
                    quarter_breakdown=quarter_breakdown
                )

        # Minimal fallback
        return f"The {winner_nickname} controlled the tempo and made plays when it mattered most."

    def _generate_looking_ahead_paragraph(
        self,
        game_data: Dict[str, Any],
        recap_data: Dict[str, Any]
    ) -> str:
        """
        Generate the looking ahead paragraph with playoff/streak context.

        Args:
            game_data: Enriched game data
            recap_data: Data gathered from APIs

        Returns:
            Looking ahead paragraph string
        """
        winner = game_data.get("winner", "The winner")
        loser = game_data.get("loser", "the opponent")
        winner_city = game_data.get("winner_city", "The winner")
        loser_city = game_data.get("loser_city", "The opponent")
        winner_nickname = game_data.get("winner_nickname", "team")
        loser_nickname = game_data.get("loser_nickname", "opponent")
        week = game_data.get("week", 1)

        context = {
            "winner": winner,
            "loser": loser,
            "winner_city": winner_city,
            "loser_city": loser_city,
            "winner_nickname": winner_nickname,
            "loser_nickname": loser_nickname,
            "next_week": week + 1,
            "week": week,
        }

        # Add records if available
        if recap_data.get("winner_standing"):
            standing = recap_data["winner_standing"]
            context["winner_record"] = f"{standing.wins}-{standing.losses}"
        else:
            context["winner_record"] = "N/A"

        if recap_data.get("loser_standing"):
            standing = recap_data["loser_standing"]
            context["loser_record"] = f"{standing.wins}-{standing.losses}"
        else:
            context["loser_record"] = "N/A"

        # Determine template category based on context
        template_key = "default"

        # Check for rivalry
        if recap_data.get("rivalry"):
            template_key = "rivalry"

        # Check for playoff implications (late season)
        elif week >= 14:
            winner_standing = recap_data.get("winner_standing")
            if winner_standing:
                if winner_standing.playoff_seed:
                    template_key = "playoff_clinch"
                elif winner_standing.wins >= 8:
                    template_key = "playoff_implications"
                    context["games_remaining"] = 18 - week

        # Check for division implications
        if game_data.get("is_divisional"):
            template_key = "division_race"
            context["division"] = "division"  # Could be made dynamic

        # Get templates and select one
        templates = LOOKING_AHEAD_TEMPLATES.get(template_key, LOOKING_AHEAD_TEMPLATES["default"])
        template = random.choice(templates)

        return self._fill_template(template, context)

    def _generate_fallback_body_text(self, game_data: Dict[str, Any]) -> str:
        """
        Generate simple body text when full recap data is unavailable.

        This fallback ensures headlines always have some body text,
        even when API calls fail or data is incomplete.

        Args:
            game_data: Game data dictionary with winner/loser info

        Returns:
            A simple 2-paragraph summary string
        """
        winner_name = game_data.get("winner_name", "The winner")
        loser_name = game_data.get("loser_name", "their opponent")
        winner_score = game_data.get("winner_score", 0)
        loser_score = game_data.get("loser_score", 0)
        margin = winner_score - loser_score

        # Paragraph 1: Basic game result
        para1 = f"{winner_name} defeated {loser_name} by a score of {winner_score}-{loser_score}."

        # Paragraph 2: Context based on margin
        if margin >= 21:
            para2 = (
                f"It was a dominant performance from start to finish, "
                f"with {winner_name} controlling the game throughout."
            )
        elif margin >= 14:
            para2 = (
                f"{winner_name} built a comfortable lead and never looked back "
                f"in this convincing victory."
            )
        elif margin <= 3:
            para2 = (
                f"It was a hard-fought battle that came down to the final moments, "
                f"but {winner_name} emerged victorious."
            )
        elif margin <= 7:
            para2 = (
                f"It was a competitive game throughout, with {winner_name} "
                f"making the plays when it mattered most."
            )
        else:
            para2 = f"{winner_name} put together a solid performance to secure the win."

        return f"{para1}\n\n{para2}"

    def _generate_postgame_quotes_paragraph(
        self,
        game_data: Dict[str, Any],
        recap_data: Dict[str, Any]
    ) -> str:
        """
        Generate a paragraph with postgame player quotes.

        Selects quotes based on game margin:
        - Tie games (margin == 0): use TIE_QUOTE_TEMPLATES/TIE_QUOTE_CONTENT
        - Close games (margin <= 7): use WINNER_CLOSE_GAME_QUOTES/LOSER_CLOSE_GAME_QUOTES
        - Blowouts (margin >= 17): use WINNER_BLOWOUT_QUOTES/LOSER_BLOWOUT_QUOTES
        - Otherwise: use general quote pool

        Args:
            game_data: Enriched game data
            recap_data: Data gathered from APIs

        Returns:
            Postgame quotes paragraph string
        """
        game_id = game_data.get("game_id")
        home_id = game_data.get("home_id")
        away_id = game_data.get("away_id")
        winner_id = game_data.get("winner_id")
        loser_id = game_data.get("loser_id")
        margin = game_data.get("margin", 0)

        # Determine game type for quote selection
        is_tie = margin == 0
        is_close_game = 0 < margin <= 7
        is_blowout = margin >= 17

        quotes = []

        # Handle tie games - get quotes from both teams
        if is_tie:
            team_ids = [t for t in [home_id, away_id] if t]
            for team_id in team_ids[:2]:  # Get up to 2 quotes (one per team)
                if game_id:
                    players = self._get_top_players_by_stats(game_id, team_id, limit=1)
                    if players:
                        player_name = players[0].get("player_name", "a player")
                        quote_template = random.choice(TIE_QUOTE_TEMPLATES)
                        quote_content = random.choice(TIE_QUOTE_CONTENT)
                        tie_quote = quote_template.format(
                            player_name=player_name,
                            quote=quote_content
                        )
                        quotes.append(tie_quote)
            return " ".join(quotes) if quotes else ""

        # Get a winning player for a quote
        if game_id and winner_id:
            winner_players = self._get_top_players_by_stats(game_id, winner_id, limit=1)
            if winner_players:
                player_name = winner_players[0].get("player_name", "the star player")
                quote_template = random.choice(WINNER_QUOTE_TEMPLATES)

                # Select quote content based on game margin
                if is_close_game:
                    quote_content = random.choice(WINNER_CLOSE_GAME_QUOTES)
                elif is_blowout:
                    quote_content = random.choice(WINNER_BLOWOUT_QUOTES)
                else:
                    quote_content = random.choice(WINNER_QUOTE_CONTENT)

                winner_quote = quote_template.format(
                    player_name=player_name,
                    quote=quote_content
                )
                quotes.append(winner_quote)

        # Optionally get a losing player quote
        if game_id and loser_id and random.random() < 0.5:  # 50% chance
            loser_players = self._get_top_players_by_stats(game_id, loser_id, limit=1)
            if loser_players:
                player_name = loser_players[0].get("player_name", "a player")
                quote_template = random.choice(LOSER_QUOTE_TEMPLATES)

                # Select quote content based on game margin
                if is_close_game:
                    quote_content = random.choice(LOSER_CLOSE_GAME_QUOTES)
                elif is_blowout:
                    quote_content = random.choice(LOSER_BLOWOUT_QUOTES)
                else:
                    quote_content = random.choice(LOSER_QUOTE_CONTENT)

                loser_quote = quote_template.format(
                    player_name=player_name,
                    quote=quote_content
                )
                quotes.append(loser_quote)

        return " ".join(quotes) if quotes else ""

    def _generate_media_reaction_paragraph(
        self,
        game_data: Dict[str, Any],
        recap_data: Dict[str, Any],
        winner_status: str,
        loser_status: str,
        headline_type: HeadlineType,
        season_context: Dict[str, Any]
    ) -> str:
        """
        Generate media/analyst reaction paragraph with criticism or praise.

        Provides external perspective on the game based on team status,
        game type (blowout/upset), and season context.

        Args:
            game_data: Enriched game data
            recap_data: Data gathered from APIs
            winner_status: TeamStatus classification for winner
            loser_status: TeamStatus classification for loser
            headline_type: Type of game (BLOWOUT, UPSET, etc.)
            season_context: Season/week context dict

        Returns:
            Media reaction paragraph string
        """
        margin = game_data.get("margin", 0)
        week = game_data.get("week", 1)
        winner_city = game_data.get("winner_city", "The winner")
        loser_city = game_data.get("loser_city", "The loser")

        sentences = []

        # Determine the primary narrative angle
        # Priority: upset > blowout > contender storyline > team status

        # Check for upset
        if headline_type == HeadlineType.UPSET:
            quote = random.choice(ANALYST_CONTENT.get("upset_winner", []))
            template = random.choice(ANALYST_REACTION_TEMPLATES)
            sentences.append(template.format(quote=quote, analysis_type="was a shocker"))

        # Check for blowout (margin >= 21)
        elif headline_type == HeadlineType.BLOWOUT or margin >= 21:
            # Winner perspective
            quote = random.choice(ANALYST_CONTENT.get("blowout_dominant", []))
            template = random.choice(ANALYST_REACTION_TEMPLATES)
            sentences.append(template.format(quote=quote, analysis_type="was total domination"))

            # Loser criticism if struggling
            if loser_status in (TeamStatus.REBUILDING, TeamStatus.ELIMINATED):
                loser_quote = random.choice(ANALYST_CONTENT.get("blowout_loser", []))
                sentences.append(f"For {loser_city}, the assessment is harsher: \"{loser_quote}\"")

        # Contender-specific narratives
        elif winner_status == TeamStatus.CONTENDER:
            if margin >= 10:
                quote = random.choice(ANALYST_CONTENT.get("contender_dominant_win", []))
            else:
                quote = random.choice(ANALYST_CONTENT.get("contender_close_win", []))
            template = random.choice(ANALYST_REACTION_TEMPLATES)
            sentences.append(template.format(quote=quote, analysis_type="was championship caliber"))

        # Contender loses (big story)
        elif loser_status == TeamStatus.CONTENDER:
            quote = random.choice(ANALYST_CONTENT.get("contender_loss", []))
            template = random.choice(ANALYST_REACTION_TEMPLATES)
            sentences.append(template.format(quote=quote, analysis_type="raises questions"))

        # Struggling team wins (feel-good story)
        elif winner_status in (TeamStatus.REBUILDING, TeamStatus.ELIMINATED):
            quote = random.choice(ANALYST_CONTENT.get("struggling_team_win", []))
            template = random.choice(ANALYST_REACTION_TEMPLATES)
            sentences.append(template.format(quote=quote, analysis_type="was unexpected"))

        # Default: struggling team loses
        elif loser_status in (TeamStatus.REBUILDING, TeamStatus.ELIMINATED):
            quote = random.choice(ANALYST_CONTENT.get("struggling_team_loss", []))
            template = random.choice(ANALYST_REACTION_TEMPLATES)
            sentences.append(template.format(quote=quote, analysis_type="raises concerns"))

        # Add week-specific context
        context_key = season_context.get("key", "mid_season")
        if context_key == "week_1":
            week_quote = random.choice(ANALYST_CONTENT.get("week_1_take", []))
            sentences.append(week_quote)
        elif context_key == "week_17_18":
            finale_quote = random.choice(ANALYST_CONTENT.get("season_finale", []))
            sentences.append(finale_quote)
        elif context_key == "late_season" and winner_status == TeamStatus.BUBBLE:
            playoff_quote = random.choice(ANALYST_CONTENT.get("playoff_implications", []))
            sentences.append(playoff_quote)

        # Add criticism for blowout losers (optional, 40% chance)
        if margin >= 17 and random.random() < 0.4:
            criticism_category = random.choice(list(CRITICISM_POINTS.keys()))
            criticism_point = random.choice(CRITICISM_POINTS[criticism_category])
            criticism_template = random.choice(MEDIA_CRITICISM_TEMPLATES)
            sentences.append(criticism_template.format(criticism_point=criticism_point))

        return " ".join(sentences) if sentences else ""

    def _generate_body_text(
        self,
        game_data: Dict[str, Any],
        headline_type: HeadlineType
    ) -> Optional[str]:
        """
        Generate full body text for a game recap.

        Orchestrates the 7-paragraph structure:
        1. Opening - game summary
        2. Star players - top performers
        3. Defensive standouts - top defenders from both teams
        4. Turning point - key moment
        5. Postgame quotes - player reactions
        6. Media reaction - analyst perspective
        7. Looking ahead - implications

        Args:
            game_data: Enriched game data
            headline_type: Type of game headline

        Returns:
            Full body text string, or fallback text if generation fails
        """
        game_id = game_data.get("game_id")
        winner_id = game_data.get("winner_id")
        loser_id = game_data.get("loser_id")
        week = game_data.get("week", 1)

        if not all([game_id, winner_id, loser_id]):
            self._logger.warning("Missing required data for body text generation, using fallback")
            return self._generate_fallback_body_text(game_data)

        # Gather data from APIs
        recap_data = self._gather_recap_data(game_id, winner_id, loser_id)

        # Get season context for week-aware generation
        season_context = self._get_season_context(week)

        # Classify team status for narrative selection
        winner_status = self._classify_team_status(
            recap_data.get("winner_standing"), week
        )
        loser_status = self._classify_team_status(
            recap_data.get("loser_standing"), week
        )

        try:
            # Generate each paragraph (7 paragraphs)
            opening = self._generate_opening_paragraph(
                game_data, headline_type, recap_data
            )
            star_players = self._generate_star_players_paragraph(
                game_data, recap_data
            )
            defensive_standouts = self._generate_defensive_paragraph(
                game_data, recap_data
            )
            turning_point = self._generate_turning_point_paragraph(
                game_data, recap_data
            )
            postgame_quotes = self._generate_postgame_quotes_paragraph(
                game_data, recap_data
            )
            media_reaction = self._generate_media_reaction_paragraph(
                game_data, recap_data, winner_status, loser_status,
                headline_type, season_context
            )
            looking_ahead = self._generate_looking_ahead_paragraph(
                game_data, recap_data
            )

            # Combine paragraphs (up to 7, defensive may be empty)
            paragraphs = [
                opening,
                star_players,
                defensive_standouts,
                turning_point,
                postgame_quotes,
                media_reaction,
                looking_ahead
            ]
            body_text = "\n\n".join(p for p in paragraphs if p)

            # If all paragraphs failed, use fallback
            if not body_text:
                self._logger.warning("All paragraphs empty, using fallback body text")
                return self._generate_fallback_body_text(game_data)

            return body_text

        except Exception as e:
            self._logger.error(f"Error generating body text: {e}, using fallback")
            return self._generate_fallback_body_text(game_data)

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_headlines(
        self,
        week: int,
        headline_type: Optional[HeadlineType] = None
    ) -> List[Headline]:
        """Get saved headlines for a week."""
        type_str = headline_type.value if headline_type else None
        return self._media_api.get_headlines(
            dynasty_id=self._dynasty_id,
            season=self._season,
            week=week,
            headline_type=type_str
        )

    def get_top_headlines(self, week: int, limit: int = 10) -> List[Headline]:
        """Get top headlines by priority for a week."""
        return self._media_api.get_top_headlines(
            dynasty_id=self._dynasty_id,
            season=self._season,
            week=week,
            limit=limit
        )

    # =========================================================================
    # Preview Headline Generation (Tollgate 7.8)
    # =========================================================================

    def _is_same_division(self, team1_id: int, team2_id: int) -> bool:
        """Check if two teams are in the same division."""
        team1 = self._teams_data.get(team1_id, {})
        team2 = self._teams_data.get(team2_id, {})
        if not team1 or not team2:
            return False
        return (
            team1.get("conference") == team2.get("conference") and
            team1.get("division") == team2.get("division")
        )

    def _is_same_conference(self, team1_id: int, team2_id: int) -> bool:
        """Check if two teams are in the same conference."""
        team1 = self._teams_data.get(team1_id, {})
        team2 = self._teams_data.get(team2_id, {})
        if not team1 or not team2:
            return False
        return team1.get("conference") == team2.get("conference")

    def generate_preview_headlines(
        self,
        week: int,
        min_priority_boost: int = 20
    ) -> List[Headline]:
        """
        Generate preview headlines for upcoming games worth covering.

        Only generates headlines for games with sufficient criticality
        (rivalry, divisional, playoff implications, streaks).

        Args:
            week: Week number to generate previews for
            min_priority_boost: Minimum combined priority boost to generate headline
                               (default 20 filters out generic games)

        Returns:
            List of preview headlines for critical/rivalry games
        """
        headlines = []

        # Initialize APIs
        h2h_api = HeadToHeadAPI(self._db)

        # Get unplayed games for the week from events table
        # (The schedule table is empty; games are stored in events table)
        try:
            from src.database.unified_api import UnifiedDatabaseAPI

            # Create UnifiedAPI with the dynasty_id
            unified_api = UnifiedDatabaseAPI(self._db_path, self._dynasty_id)
            games_data = unified_api.events_get_games_by_week(self._season, week)

            # Filter for unplayed games only (home_score is None)
            unplayed_games = [g for g in games_data if g.get('home_score') is None]
            self._logger.info(f"Found {len(unplayed_games)} unplayed games for week {week}")

        except Exception as e:
            self._logger.error(f"Failed to get games for week {week}: {e}")
            return []

        for game_dict in unplayed_games:
            home_team_id = game_dict.get('home_team_id')
            away_team_id = game_dict.get('away_team_id')

            if not home_team_id or not away_team_id:
                continue

            # Create a simple game object with the properties _calculate_game_criticality needs
            class GameInfo:
                def __init__(self, home_id, away_id, is_div, is_conf):
                    self.home_team_id = home_id
                    self.away_team_id = away_id
                    self.is_divisional = is_div
                    self.is_conference = is_conf

            game = GameInfo(
                home_id=home_team_id,
                away_id=away_team_id,
                is_div=self._is_same_division(home_team_id, away_team_id),
                is_conf=self._is_same_conference(home_team_id, away_team_id)
            )

            # Calculate criticality score and build context
            priority_boost, context = self._calculate_game_criticality(
                game, week, h2h_api
            )

            # Only generate if meets threshold
            if priority_boost >= min_priority_boost:
                headline = self._generate_preview_headline(context, priority_boost)
                if headline:
                    headlines.append(headline)

        return headlines

    def _calculate_game_criticality(
        self,
        game,
        week: int,
        h2h_api: HeadToHeadAPI
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate criticality score for a game and build context.

        Args:
            game: ScheduledGame object
            week: Current week number
            h2h_api: HeadToHeadAPI instance for streak lookup

        Returns:
            Tuple of (priority_boost, context_dict)
        """
        priority_boost = 0

        # Get team info
        home_info = self._get_team_info(game.home_team_id)
        away_info = self._get_team_info(game.away_team_id)

        context = {
            "week": week,
            "home_team_id": game.home_team_id,
            "away_team_id": game.away_team_id,
            "home_team": home_info["team"],
            "away_team": away_info["team"],
            "home_city": home_info["city"],
            "away_city": away_info["city"],
            "is_divisional": game.is_divisional,
            "is_conference": game.is_conference,
        }

        # Check rivalry
        try:
            rivalry = self._rivalry_api.get_rivalry_between_teams(
                self._dynasty_id, game.home_team_id, game.away_team_id
            )
            if rivalry:
                context["is_rivalry"] = True
                context["rivalry_name"] = rivalry.rivalry_name
                context["rivalry_intensity"] = rivalry.intensity
                if rivalry.intensity >= 85:
                    priority_boost += 25
                elif rivalry.intensity >= 75:
                    priority_boost += 20
                elif rivalry.intensity >= 50:
                    priority_boost += 10
        except Exception as e:
            self._logger.debug(f"Could not check rivalry: {e}")

        # Check standings proximity (playoff implications)
        try:
            home_standing = self._standings_api.get_team_standing(
                self._dynasty_id, self._season, game.home_team_id
            )
            away_standing = self._standings_api.get_team_standing(
                self._dynasty_id, self._season, game.away_team_id
            )
            if home_standing and away_standing:
                home_wins = getattr(home_standing, 'wins', 0) or 0
                home_losses = getattr(home_standing, 'losses', 0) or 0
                away_wins = getattr(away_standing, 'wins', 0) or 0
                away_losses = getattr(away_standing, 'losses', 0) or 0

                wins_diff = abs(home_wins - away_wins)
                if wins_diff <= 1:
                    context["playoff_implications"] = True
                    priority_boost += 15

                context["home_record"] = f"{home_wins}-{home_losses}"
                context["away_record"] = f"{away_wins}-{away_losses}"
        except Exception as e:
            self._logger.debug(f"Could not check standings: {e}")

        # Divisional bonus
        if game.is_divisional:
            priority_boost += 10

        # Late-season conference games bonus
        if game.is_conference and week >= 12:
            priority_boost += 5

        # Check head-to-head streak
        try:
            h2h = h2h_api.get_record(
                self._dynasty_id, game.home_team_id, game.away_team_id
            )
            if h2h and h2h.current_streak_count >= 3:
                context["has_streak"] = True
                context["streak_count"] = h2h.current_streak_count
                context["streak_team_id"] = h2h.current_streak_team
                # Get team name for streak
                if h2h.current_streak_team:
                    streak_info = self._get_team_info(h2h.current_streak_team)
                    context["streak_team"] = streak_info["team"]
                    # Determine opponent for streak context
                    if h2h.current_streak_team == game.home_team_id:
                        context["streak_opponent"] = away_info["team"]
                    else:
                        context["streak_opponent"] = home_info["team"]
                priority_boost += 10
        except Exception as e:
            self._logger.debug(f"Could not check head-to-head: {e}")

        return priority_boost, context

    def _generate_preview_headline(
        self,
        context: Dict[str, Any],
        priority_boost: int
    ) -> Optional[Headline]:
        """
        Generate a preview headline for a game.

        Args:
            context: Dict with game context (teams, rivalry, standings, etc.)
            priority_boost: Calculated priority boost from criticality

        Returns:
            Headline object or None if generation fails
        """
        # Find matching template based on context
        matching_templates = []

        for template in PREVIEW_TEMPLATES:
            if self._preview_template_matches(template, context):
                matching_templates.append(template)

        if not matching_templates:
            # Fallback to generic preview template
            matching_templates = [t for t in PREVIEW_TEMPLATES if not t.conditions]

        if not matching_templates:
            self._logger.warning("No preview templates found")
            return None

        # Select template (weighted toward higher priority boost)
        template = random.choice(matching_templates)

        # Fill template with context data
        try:
            headline_text = self._fill_template(template.template, context)
        except KeyError as e:
            self._logger.warning(f"Missing context key for preview template: {e}")
            return None

        # Generate subheadline if available
        subheadline = None
        if template.subheadline_template:
            try:
                subheadline = self._fill_template(
                    template.subheadline_template, context
                )
            except KeyError:
                pass

        # Generate body text
        body_text = self._generate_preview_body_text(context)

        # Calculate final priority
        base_priority = BASE_PRIORITIES.get(HeadlineType.PREVIEW, 55)
        final_priority = min(100, base_priority + priority_boost + template.priority_boost)

        return Headline(
            id=None,
            dynasty_id=self._dynasty_id,
            season=self._season,
            week=context.get("week", 0),
            headline_type=HeadlineType.PREVIEW.value,
            headline=headline_text,
            subheadline=subheadline,
            body_text=body_text,
            sentiment=template.sentiment.value,
            priority=final_priority,
            team_ids=[context["home_team_id"], context["away_team_id"]],
            player_ids=[],
            game_id=None,
            metadata={
                "is_rivalry": context.get("is_rivalry", False),
                "is_divisional": context.get("is_divisional", False),
                "playoff_implications": context.get("playoff_implications", False),
                "has_streak": context.get("has_streak", False),
                "priority_boost": priority_boost,
            }
        )

    def _preview_template_matches(
        self,
        template: HeadlineTemplate,
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if a preview template matches the given context.

        Args:
            template: HeadlineTemplate to check
            context: Game context dict

        Returns:
            True if template conditions are satisfied
        """
        for key, value in template.conditions.items():
            # Handle min/max intensity conditions
            if key == "rivalry_intensity_min":
                intensity = context.get("rivalry_intensity", 0)
                if intensity < value:
                    return False
            elif key == "rivalry_intensity_max":
                intensity = context.get("rivalry_intensity", 0)
                if intensity > value:
                    return False
            # Handle boolean conditions
            elif isinstance(value, bool):
                if context.get(key) != value:
                    return False
            # Handle other conditions
            else:
                if context.get(key) != value:
                    return False

        return True

    def _generate_preview_body_text(self, context: Dict[str, Any]) -> str:
        """
        Generate preview body text with game context.

        Args:
            context: Dict with game context

        Returns:
            Multi-paragraph preview body text
        """
        paragraphs = []

        home_team = context.get("home_team", "Home Team")
        away_team = context.get("away_team", "Away Team")
        home_record = context.get("home_record", "")
        away_record = context.get("away_record", "")
        week = context.get("week", "")

        # Opening paragraph
        if home_record and away_record:
            paragraphs.append(
                f"The {away_team} ({away_record}) travel to face the {home_team} "
                f"({home_record}) in Week {week} action."
            )
        else:
            paragraphs.append(
                f"The {away_team} travel to face the {home_team} in Week {week}."
            )

        # Rivalry context
        if context.get("is_rivalry"):
            rivalry_name = context.get("rivalry_name", "this rivalry")
            intensity = context.get("rivalry_intensity", 50)
            if intensity >= 85:
                paragraphs.append(
                    f"This game marks the latest chapter in {rivalry_name}, one of the "
                    f"most storied and intense matchups in the league. Expect emotions "
                    f"to run high as these two teams renew their legendary feud."
                )
            elif intensity >= 75:
                paragraphs.append(
                    f"This game continues the heated rivalry between these two teams. "
                    f"{rivalry_name} has produced memorable moments over the years, "
                    f"and this matchup should be no different."
                )
            else:
                paragraphs.append(
                    f"These teams share a competitive rivalry that adds extra meaning "
                    f"to this Week {week} matchup."
                )

        # Divisional context
        if context.get("is_divisional") and not context.get("is_rivalry"):
            paragraphs.append(
                "As a divisional matchup, this game carries extra weight in the standings "
                "and could prove crucial come playoff time. Division games often have a "
                "different feel, with both teams knowing each other's tendencies well."
            )

        # Playoff implications
        if context.get("playoff_implications"):
            paragraphs.append(
                "With both teams in the thick of the playoff race, this game takes on "
                "added significance. The loser could find themselves on the outside "
                "looking in as the season enters its final stretch."
            )

        # Streak context
        if context.get("has_streak"):
            streak_team = context.get("streak_team", "One team")
            streak_count = context.get("streak_count", 3)
            streak_opponent = context.get("streak_opponent", "their opponent")
            paragraphs.append(
                f"{streak_team} enters this matchup having won {streak_count} straight "
                f"games against {streak_opponent}. They'll look to continue their "
                f"dominance in this series."
            )

        return "\n\n".join(paragraphs)


# =============================================================================
# Template Count Verification
# =============================================================================

def get_template_counts() -> Dict[str, int]:
    """Get count of templates by type (for testing/verification)."""
    return {
        "GAME_RECAP": len(GAME_RECAP_TEMPLATES),
        "BLOWOUT": len(BLOWOUT_TEMPLATES),
        "UPSET": len(UPSET_TEMPLATES),
        "COMEBACK": len(COMEBACK_TEMPLATES),
        "INJURY": len(INJURY_TEMPLATES),
        "TRADE": len(TRADE_TEMPLATES),
        "SIGNING": len(SIGNING_TEMPLATES),
        "AWARD": len(AWARD_TEMPLATES),
        "MILESTONE": len(MILESTONE_TEMPLATES),
        "RUMOR": len(RUMOR_TEMPLATES),
        "STREAK": len(STREAK_TEMPLATES),
        "POWER_RANKING": len(POWER_RANKING_TEMPLATES),
        "TOTAL": (
            len(GAME_RECAP_TEMPLATES) + len(BLOWOUT_TEMPLATES) +
            len(UPSET_TEMPLATES) + len(COMEBACK_TEMPLATES) +
            len(INJURY_TEMPLATES) + len(TRADE_TEMPLATES) +
            len(SIGNING_TEMPLATES) + len(AWARD_TEMPLATES) +
            len(MILESTONE_TEMPLATES) + len(RUMOR_TEMPLATES) +
            len(STREAK_TEMPLATES) + len(POWER_RANKING_TEMPLATES)
        ),
    }
