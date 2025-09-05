"""
NFL Team ID Constants

Provides readable constants for numerical team IDs to improve code clarity.
Instead of using magic numbers, developers can use descriptive constants.

Example:
    # Instead of:
    lions_roster = TeamRosterGenerator.generate_sample_roster(22)
    
    # Use:
    lions_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.DETROIT_LIONS)
"""


class TeamIDs:
    """Constants for NFL team numerical IDs"""
    
    # AFC East
    BUFFALO_BILLS = 1
    MIAMI_DOLPHINS = 2
    NEW_ENGLAND_PATRIOTS = 3
    NEW_YORK_JETS = 4
    
    # AFC North
    BALTIMORE_RAVENS = 5
    CINCINNATI_BENGALS = 6
    CLEVELAND_BROWNS = 7
    PITTSBURGH_STEELERS = 8
    
    # AFC South
    HOUSTON_TEXANS = 9
    INDIANAPOLIS_COLTS = 10
    JACKSONVILLE_JAGUARS = 11
    TENNESSEE_TITANS = 12
    
    # AFC West
    DENVER_BRONCOS = 13
    KANSAS_CITY_CHIEFS = 14
    LAS_VEGAS_RAIDERS = 15
    LOS_ANGELES_CHARGERS = 16
    
    # NFC East
    DALLAS_COWBOYS = 17
    NEW_YORK_GIANTS = 18
    PHILADELPHIA_EAGLES = 19
    WASHINGTON_COMMANDERS = 20
    
    # NFC North
    CHICAGO_BEARS = 21
    DETROIT_LIONS = 22
    GREEN_BAY_PACKERS = 23
    MINNESOTA_VIKINGS = 24
    
    # NFC South
    ATLANTA_FALCONS = 25
    CAROLINA_PANTHERS = 26
    NEW_ORLEANS_SAINTS = 27
    TAMPA_BAY_BUCCANEERS = 28
    
    # NFC West
    ARIZONA_CARDINALS = 29
    LOS_ANGELES_RAMS = 30
    SAN_FRANCISCO_49ERS = 31
    SEATTLE_SEAHAWKS = 32
    
    @classmethod
    def get_all_team_ids(cls) -> list[int]:
        """Get list of all valid team IDs"""
        return [getattr(cls, attr) for attr in dir(cls) 
                if isinstance(getattr(cls, attr), int)]
    
    @classmethod
    def get_division_teams(cls, division_name: str) -> list[int]:
        """
        Get team IDs for a specific division
        
        Args:
            division_name: Division name like "AFC_EAST", "NFC_NORTH", etc.
            
        Returns:
            List of team IDs in that division
        """
        divisions = {
            "AFC_EAST": [cls.BUFFALO_BILLS, cls.MIAMI_DOLPHINS, cls.NEW_ENGLAND_PATRIOTS, cls.NEW_YORK_JETS],
            "AFC_NORTH": [cls.BALTIMORE_RAVENS, cls.CINCINNATI_BENGALS, cls.CLEVELAND_BROWNS, cls.PITTSBURGH_STEELERS],
            "AFC_SOUTH": [cls.HOUSTON_TEXANS, cls.INDIANAPOLIS_COLTS, cls.JACKSONVILLE_JAGUARS, cls.TENNESSEE_TITANS],
            "AFC_WEST": [cls.DENVER_BRONCOS, cls.KANSAS_CITY_CHIEFS, cls.LAS_VEGAS_RAIDERS, cls.LOS_ANGELES_CHARGERS],
            "NFC_EAST": [cls.DALLAS_COWBOYS, cls.NEW_YORK_GIANTS, cls.PHILADELPHIA_EAGLES, cls.WASHINGTON_COMMANDERS],
            "NFC_NORTH": [cls.CHICAGO_BEARS, cls.DETROIT_LIONS, cls.GREEN_BAY_PACKERS, cls.MINNESOTA_VIKINGS],
            "NFC_SOUTH": [cls.ATLANTA_FALCONS, cls.CAROLINA_PANTHERS, cls.NEW_ORLEANS_SAINTS, cls.TAMPA_BAY_BUCCANEERS],
            "NFC_WEST": [cls.ARIZONA_CARDINALS, cls.LOS_ANGELES_RAMS, cls.SAN_FRANCISCO_49ERS, cls.SEATTLE_SEAHAWKS]
        }
        return divisions.get(division_name.upper(), [])
    
    @classmethod
    def get_conference_teams(cls, conference: str) -> list[int]:
        """
        Get team IDs for a conference (AFC or NFC)
        
        Args:
            conference: "AFC" or "NFC"
            
        Returns:
            List of team IDs in that conference
        """
        if conference.upper() == "AFC":
            return (cls.get_division_teams("AFC_EAST") + 
                   cls.get_division_teams("AFC_NORTH") + 
                   cls.get_division_teams("AFC_SOUTH") + 
                   cls.get_division_teams("AFC_WEST"))
        elif conference.upper() == "NFC":
            return (cls.get_division_teams("NFC_EAST") + 
                   cls.get_division_teams("NFC_NORTH") + 
                   cls.get_division_teams("NFC_SOUTH") + 
                   cls.get_division_teams("NFC_WEST"))
        else:
            return []


# Convenience aliases for popular teams
class PopularTeams:
    """Aliases for frequently used teams"""
    LIONS = TeamIDs.DETROIT_LIONS
    COMMANDERS = TeamIDs.WASHINGTON_COMMANDERS
    COWBOYS = TeamIDs.DALLAS_COWBOYS
    PACKERS = TeamIDs.GREEN_BAY_PACKERS
    PATRIOTS = TeamIDs.NEW_ENGLAND_PATRIOTS
    STEELERS = TeamIDs.PITTSBURGH_STEELERS
    CHIEFS = TeamIDs.KANSAS_CITY_CHIEFS
    RAMS = TeamIDs.LOS_ANGELES_RAMS
    BILLS = TeamIDs.BUFFALO_BILLS
    BENGALS = TeamIDs.CINCINNATI_BENGALS


# Example usage demonstration
if __name__ == "__main__":
    print("NFL Team ID Constants Demo")
    print("=" * 40)
    
    print(f"Detroit Lions ID: {TeamIDs.DETROIT_LIONS}")
    print(f"Washington Commanders ID: {TeamIDs.WASHINGTON_COMMANDERS}")
    print()
    
    print("NFC North Teams:")
    nfc_north = TeamIDs.get_division_teams("NFC_NORTH")
    for team_id in nfc_north:
        print(f"  Team ID: {team_id}")
    print()
    
    print("AFC Conference Teams:")
    afc_teams = TeamIDs.get_conference_teams("AFC")
    print(f"  AFC has {len(afc_teams)} teams: {afc_teams}")
    print()
    
    print("Popular Team Aliases:")
    print(f"  Lions: {PopularTeams.LIONS}")
    print(f"  Commanders: {PopularTeams.COMMANDERS}")
    print(f"  Chiefs: {PopularTeams.CHIEFS}")