from dataclasses import dataclass

@dataclass
class GameClock:
    """Manages game time and quarter progression"""
    
    def __init__(self):
        self.quarter = 1
        self.clock = 900  # 15 minutes per quarter in seconds
        self.play_clock = 40  # play clock in seconds
        # TODO: Add timeouts, two-minute warning, overtime
    
    def is_game_over(self) -> bool:
        """Check if the game is over"""
        return self.quarter > 4 or (self.quarter == 4 and self.clock <= 0)
    
    def advance_quarter(self):
        """Advance to the next quarter"""
        if self.clock <= 0 and self.quarter < 4:
            self.quarter += 1
            self.clock = 900
            # TODO: Switch possession for start of quarter
    
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
        return self.quarter in [2, 4] and self.clock <= 120
    
    def is_final_minute(self) -> bool:
        """Check if it's the final minute of any quarter"""
        return self.clock <= 60