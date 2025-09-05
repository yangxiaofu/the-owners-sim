class OffensiveFormation:
    """Offensive formation constants and personnel requirements"""
    
    # Standard formations
    I_FORMATION = "i_formation"
    SHOTGUN = "shotgun"
    SINGLEBACK = "singleback"
    PISTOL = "pistol"
    WILDCAT = "wildcat"
    
    # Passing formations
    FOUR_WIDE = "four_wide"
    FIVE_WIDE = "five_wide"
    TRIPS = "trips"
    BUNCH = "bunch"
    
    # Running formations
    GOAL_LINE = "goal_line"
    SHORT_YARDAGE = "short_yardage"
    
    # Special situations
    FIELD_GOAL = "field_goal"
    PUNT = "punt"
    KICKOFF = "kickoff"
    VICTORY = "victory"
    
    @classmethod
    def get_personnel_requirements(cls, formation):
        """Get the required personnel for a specific formation"""
        from team_management.players.player import Position
        
        requirements = {
            cls.I_FORMATION: {
                Position.QB: 1, Position.RB: 1, Position.FB: 1, Position.WR: 2,
                Position.TE: 1, Position.LT: 1, Position.LG: 1, Position.C: 1,
                Position.RG: 1, Position.RT: 1
            },
            cls.SHOTGUN: {
                Position.QB: 1, Position.RB: 1, Position.WR: 3, Position.TE: 1,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1
            },
            cls.SINGLEBACK: {
                Position.QB: 1, Position.RB: 1, Position.WR: 3, Position.TE: 1,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1
            },
            cls.FOUR_WIDE: {
                Position.QB: 1, Position.RB: 1, Position.WR: 4, Position.TE: 0,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1
            },
            cls.FIVE_WIDE: {
                Position.QB: 1, Position.RB: 0, Position.WR: 5, Position.TE: 0,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1
            },
            cls.GOAL_LINE: {
                Position.QB: 1, Position.RB: 1, Position.FB: 1, Position.WR: 1,
                Position.TE: 2, Position.LT: 1, Position.LG: 1, Position.C: 1,
                Position.RG: 1, Position.RT: 1
            },
            cls.FIELD_GOAL: {
                Position.K: 1, Position.H: 1, Position.LS: 1, Position.WR: 2,
                Position.TE: 2, Position.LT: 1, Position.LG: 1, Position.RG: 1, Position.RT: 1
            },
            cls.PUNT: {
                Position.P: 1, Position.LS: 1, Position.WR: 2, Position.TE: 1,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1,
                Position.RT: 1, Position.FB: 1
            },
            cls.KICKOFF: {
                Position.K: 1, Position.WR: 4, Position.TE: 2, Position.OLB: 2,
                Position.CB: 1, Position.SS: 1  # Coverage specialists
            }
        }
        
        return requirements.get(formation, {})


class DefensiveFormation:
    """Defensive formation constants and personnel requirements"""
    
    # Base defenses
    FOUR_THREE = "4_3_base"
    THREE_FOUR = "3_4_base"
    FOUR_SIX = "4_6_base"
    
    # Nickel/Dime packages
    NICKEL = "nickel"
    DIME = "dime"
    QUARTER = "quarter"
    
    # Situational defenses
    GOAL_LINE = "goal_line_defense"
    PREVENT = "prevent_defense"
    BLITZ_PACKAGE = "blitz_package"
    
    # Special teams defense
    PUNT_RETURN = "punt_return"
    KICK_RETURN = "kick_return"
    FIELD_GOAL_BLOCK = "field_goal_block"
    
    @classmethod
    def get_personnel_requirements(cls, formation):
        """Get the required personnel for a specific defensive formation"""
        from team_management.players.player import Position
        
        requirements = {
            cls.FOUR_THREE: {
                Position.DE: 2, Position.DT: 2, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
                Position.CB: 2, Position.FS: 1, Position.SS: 1
            },
            cls.THREE_FOUR: {
                Position.DE: 2, Position.NT: 1, Position.OLB: 2, Position.ILB: 2,
                Position.CB: 2, Position.FS: 1, Position.SS: 1
            },
            cls.NICKEL: {
                Position.DE: 2, Position.DT: 2, Position.MIKE: 1, Position.SAM: 1,
                Position.CB: 2, Position.NCB: 1, Position.FS: 1, Position.SS: 1
            },
            cls.DIME: {
                Position.DE: 2, Position.DT: 2, Position.MIKE: 1,
                Position.CB: 2, Position.NCB: 2, Position.FS: 1, Position.SS: 1
            },
            cls.GOAL_LINE: {
                Position.DE: 2, Position.DT: 3, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
                Position.CB: 1, Position.SS: 2
            },
            cls.PREVENT: {
                Position.DE: 2, Position.DT: 2, Position.MIKE: 1,
                Position.CB: 2, Position.FS: 2, Position.SS: 2
            },
            cls.BLITZ_PACKAGE: {
                Position.DE: 2, Position.DT: 2, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
                Position.CB: 1, Position.FS: 1, Position.SS: 2  # Extra rusher
            },
            cls.PUNT_RETURN: {
                Position.DE: 2, Position.DT: 1, Position.MIKE: 1, Position.SAM: 1,
                Position.CB: 2, Position.FS: 1, Position.SS: 1, Position.PR: 1,
                Position.WR: 1  # Return specialist
            },
            cls.KICK_RETURN: {
                Position.DE: 1, Position.DT: 1, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
                Position.CB: 2, Position.FS: 1, Position.SS: 1, Position.KR: 1,
                Position.WR: 1  # Return specialist
            }
        }
        
        return requirements.get(formation, {})


class FormationMapper:
    """Maps play types to appropriate formations"""
    
    @classmethod
    def get_offensive_formation_for_play(cls, play_type):
        """Get the most appropriate offensive formation for a play type"""
        from ..play_types.offensive_types import OffensivePlayType
        
        formation_map = {
            OffensivePlayType.RUN: OffensiveFormation.I_FORMATION,
            OffensivePlayType.PASS: OffensiveFormation.SHOTGUN,
            OffensivePlayType.PLAY_ACTION_PASS: OffensiveFormation.SINGLEBACK,
            OffensivePlayType.SCREEN_PASS: OffensiveFormation.SHOTGUN,
            OffensivePlayType.QUICK_SLANT: OffensiveFormation.SHOTGUN,
            OffensivePlayType.DEEP_BALL: OffensiveFormation.FOUR_WIDE,
            OffensivePlayType.FIELD_GOAL: OffensiveFormation.FIELD_GOAL,
            OffensivePlayType.PUNT: OffensiveFormation.PUNT,
            OffensivePlayType.KICKOFF: OffensiveFormation.KICKOFF,
            OffensivePlayType.TWO_POINT_CONVERSION: OffensiveFormation.GOAL_LINE,
            OffensivePlayType.KNEEL_DOWN: OffensiveFormation.VICTORY,
            OffensivePlayType.SPIKE: OffensiveFormation.SHOTGUN
        }
        
        return formation_map.get(play_type, OffensiveFormation.SINGLEBACK)
    
    @classmethod
    def get_defensive_formation_for_play(cls, play_type):
        """Get the most appropriate defensive formation for a play type"""
        from ..play_types.defensive_types import DefensivePlayType
        
        formation_map = {
            DefensivePlayType.COVER_0: DefensiveFormation.BLITZ_PACKAGE,
            DefensivePlayType.COVER_1: DefensiveFormation.FOUR_THREE,
            DefensivePlayType.COVER_2: DefensiveFormation.FOUR_THREE,
            DefensivePlayType.COVER_3: DefensiveFormation.FOUR_THREE,
            DefensivePlayType.MAN_COVERAGE: DefensiveFormation.FOUR_THREE,
            DefensivePlayType.ZONE_COVERAGE: DefensiveFormation.FOUR_THREE,
            DefensivePlayType.FOUR_MAN_RUSH: DefensiveFormation.FOUR_THREE,
            DefensivePlayType.BLITZ: DefensiveFormation.BLITZ_PACKAGE,
            DefensivePlayType.CORNER_BLITZ: DefensiveFormation.BLITZ_PACKAGE,
            DefensivePlayType.SAFETY_BLITZ: DefensiveFormation.BLITZ_PACKAGE,
            DefensivePlayType.NICKEL_DEFENSE: DefensiveFormation.NICKEL,
            DefensivePlayType.DIME_DEFENSE: DefensiveFormation.DIME,
            DefensivePlayType.GOAL_LINE_DEFENSE: DefensiveFormation.GOAL_LINE,
            DefensivePlayType.PREVENT_DEFENSE: DefensiveFormation.PREVENT,
            DefensivePlayType.RUN_STUFF: DefensiveFormation.FOUR_SIX
        }
        
        return formation_map.get(play_type, DefensiveFormation.FOUR_THREE)