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
            cls.PISTOL: {
                Position.QB: 1, Position.RB: 1, Position.WR: 3, Position.TE: 1,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1
            },
            cls.WILDCAT: {
                Position.QB: 0, Position.RB: 2, Position.WR: 3, Position.TE: 1,
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
            cls.TRIPS: {
                Position.QB: 1, Position.RB: 1, Position.WR: 3, Position.TE: 1,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1
            },
            cls.BUNCH: {
                Position.QB: 1, Position.RB: 1, Position.WR: 3, Position.TE: 1,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1
            },
            cls.GOAL_LINE: {
                Position.QB: 1, Position.RB: 1, Position.FB: 1, Position.WR: 1,
                Position.TE: 2, Position.LT: 1, Position.LG: 1, Position.C: 1,
                Position.RG: 1, Position.RT: 1
            },
            cls.SHORT_YARDAGE: {
                Position.QB: 1, Position.RB: 1, Position.FB: 1, Position.WR: 1,
                Position.TE: 2, Position.LT: 1, Position.LG: 1, Position.C: 1,
                Position.RG: 1, Position.RT: 1
            },
            cls.VICTORY: {
                Position.QB: 1, Position.RB: 2, Position.WR: 2, Position.TE: 1,
                Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1
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
        
        # Base personnel requirements
        four_three_personnel = {
            Position.DE: 2, Position.DT: 2, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
            Position.CB: 2, Position.FS: 1, Position.SS: 1
        }
        three_four_personnel = {
            Position.DE: 2, Position.NT: 1, Position.OLB: 2, Position.ILB: 2,
            Position.CB: 2, Position.FS: 1, Position.SS: 1
        }
        four_six_personnel = {
            Position.DE: 2, Position.DT: 2, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
            Position.CB: 2, Position.SS: 2  # Extra SS in box, no FS
        }
        nickel_personnel = {
            Position.DE: 2, Position.DT: 2, Position.MIKE: 1, Position.SAM: 1,
            Position.CB: 2, Position.NCB: 1, Position.FS: 1, Position.SS: 1
        }
        dime_personnel = {
            Position.DE: 2, Position.DT: 2, Position.MIKE: 1,
            Position.CB: 2, Position.NCB: 2, Position.FS: 1, Position.SS: 1
        }
        quarter_personnel = {
            Position.DE: 2, Position.DT: 2, Position.MIKE: 1,
            Position.CB: 3, Position.FS: 2, Position.SS: 1  # 6 DBs
        }
        goal_line_personnel = {
            Position.DE: 2, Position.DT: 3, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
            Position.CB: 1, Position.SS: 2
        }
        prevent_personnel = {
            Position.DE: 2, Position.DT: 2, Position.MIKE: 1,
            Position.CB: 2, Position.FS: 2, Position.SS: 2
        }
        blitz_personnel = {
            Position.DE: 2, Position.DT: 2, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
            Position.CB: 1, Position.FS: 1, Position.SS: 2  # Extra rusher
        }
        fg_block_personnel = {
            Position.DE: 2, Position.DT: 3, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
            Position.CB: 1, Position.SS: 2  # FG block unit
        }
        punt_return_personnel = {
            Position.DE: 2, Position.DT: 1, Position.MIKE: 1, Position.SAM: 1,
            Position.CB: 2, Position.FS: 1, Position.SS: 1, Position.PR: 1,
            Position.WR: 1  # Return specialist
        }
        kick_return_personnel = {
            Position.DE: 1, Position.DT: 1, Position.MIKE: 1, Position.SAM: 1, Position.WILL: 1,
            Position.CB: 2, Position.FS: 1, Position.SS: 1, Position.KR: 1,
            Position.WR: 1  # Return specialist
        }

        # Map both constant names AND alternate string formats used by unified_formations
        requirements = {
            # 4-3 Base (multiple name formats)
            cls.FOUR_THREE: four_three_personnel,
            "4_3_base": four_three_personnel,
            "defensive_4_3_base": four_three_personnel,

            # 3-4 Base (multiple name formats)
            cls.THREE_FOUR: three_four_personnel,
            "3_4_base": three_four_personnel,
            "defensive_3_4_base": three_four_personnel,

            # 4-6 Base
            cls.FOUR_SIX: four_six_personnel,
            "4_6_base": four_six_personnel,

            # Nickel (multiple name formats)
            cls.NICKEL: nickel_personnel,
            "nickel": nickel_personnel,
            "nickel_defense": nickel_personnel,
            "defensive_nickel": nickel_personnel,

            # Dime (multiple name formats)
            cls.DIME: dime_personnel,
            "dime": dime_personnel,
            "dime_defense": dime_personnel,
            "defensive_dime": dime_personnel,

            # Quarter
            cls.QUARTER: quarter_personnel,
            "quarter": quarter_personnel,
            "quarter_defense": quarter_personnel,

            # Goal Line
            cls.GOAL_LINE: goal_line_personnel,
            "goal_line_defense": goal_line_personnel,

            # Prevent
            cls.PREVENT: prevent_personnel,
            "prevent_defense": prevent_personnel,

            # Blitz Package
            cls.BLITZ_PACKAGE: blitz_personnel,
            "blitz_package": blitz_personnel,

            # Field Goal Block (multiple name formats)
            cls.FIELD_GOAL_BLOCK: fg_block_personnel,
            "field_goal_block": fg_block_personnel,
            "defensive_field_goal_block": fg_block_personnel,
            "defensive_fg_block": fg_block_personnel,

            # Punt Return (multiple name formats)
            cls.PUNT_RETURN: punt_return_personnel,
            "punt_return": punt_return_personnel,
            "defensive_punt_return": punt_return_personnel,

            # Kick Return (multiple name formats)
            cls.KICK_RETURN: kick_return_personnel,
            "kick_return": kick_return_personnel,
            "defensive_kick_return": kick_return_personnel,
            "defensive_kickoff_return": kick_return_personnel,
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