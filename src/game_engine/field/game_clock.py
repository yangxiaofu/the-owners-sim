from dataclasses import dataclass

@dataclass
class GameClock:
    """Manages game time and quarter progression"""
    
    def __init__(self, is_playoff_game: bool = False):
        self.quarter = 1
        self.clock = 900  # 15 minutes per quarter in seconds
        self.play_clock = 40  # play clock in seconds
        self.is_playoff_game = is_playoff_game
        # TODO: Add timeouts, two-minute warning
    
    def is_game_over(self) -> bool:
        """Check if the game is over"""
        # During regulation (Q1-Q4)
        if self.quarter < 4:
            return False
        elif self.quarter == 4 and self.clock > 0:
            return False
        elif self.quarter == 4 and self.clock <= 0:
            # End of Q4 - game continues to overtime
            return False
        
        # Overtime logic (Q5+)
        if self.is_playoff_game:
            return False  # Playoffs never end in ties - continue until winner
        else:
            # Regular season: game ends after one overtime period (Q5)
            return self.quarter > 5 or (self.quarter == 5 and self.clock <= 0)
    
    def advance_quarter(self):
        """Advance to the next quarter"""
        if self.clock <= 0:
            if self.quarter < 4:
                # Regular quarters
                self.quarter += 1
                self.clock = 900
                # TODO: Switch possession for start of quarter
            elif self.quarter == 4:
                # Start overtime
                self.quarter = 5
                if self.is_playoff_game:
                    self.clock = 900  # 15-minute playoff overtime periods
                else:
                    self.clock = 600  # 10-minute regular season overtime
                # TODO: Switch possession for start of overtime
            elif self.quarter >= 5 and self.is_playoff_game:
                # Continue playoff overtime
                self.quarter += 1
                self.clock = 900  # 15-minute playoff overtime periods
                # TODO: Switch possession for start of overtime period
    
    def run_time(self, seconds: int):
        """Run time off the clock"""
        self.clock = max(0, self.clock - seconds)
        
        # Auto-advance quarter if clock expires
        if self.clock <= 0:
            self.advance_quarter()
    
    def stop_clock(self):
        """Stop the clock (incomplete pass, out of bounds, etc.)"""
        # Clock management will be more complex in the future
        pass
    
    def get_time_remaining_text(self) -> str:
        """Get human-readable time remaining"""
        minutes = self.clock // 60
        seconds = self.clock % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def is_two_minute_warning(self) -> bool:
        """Check if it's close to two-minute warning"""
        # Two-minute warning applies to end of 2nd and 4th quarters
        # and end of 2nd overtime period in playoffs (based on NFL rules)
        if self.quarter in [2, 4] and self.clock <= 120:
            return True
        # In playoffs, two-minute warning applies to 2nd overtime period (Q6)
        if self.is_playoff_game and self.quarter == 6 and self.clock <= 120:
            return True
        return False
    
    def is_final_minute(self) -> bool:
        """Check if it's the final minute of any quarter"""
        return self.clock <= 60