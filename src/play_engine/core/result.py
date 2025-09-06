class PlayResult:
    """Data object representing the result of a simulated play"""
    
    def __init__(self, outcome="incomplete", yards=0, points=0, time_elapsed=0.0, player_stats_summary=None):
        self.outcome = outcome
        self.yards = yards
        self.points = points
        self.time_elapsed = time_elapsed
        self.player_stats_summary = player_stats_summary
    
    def __str__(self):
        if self.points > 0:
            return f"PlayResult(outcome='{self.outcome}', yards={self.yards}, points={self.points}, time={self.time_elapsed}s)"
        return f"PlayResult(outcome='{self.outcome}', yards={self.yards}, time={self.time_elapsed}s)"
    
    def __repr__(self):
        return self.__str__()
    
    def has_player_stats(self):
        """Check if player stats are available"""
        return self.player_stats_summary is not None
    
    def get_key_players(self):
        """Extract key players based on play type - returns formatted string"""
        if not self.has_player_stats():
            return ""
        
        players = []
        
        # Ball carrier for run plays
        rushing_leader = self.player_stats_summary.get_rushing_leader()
        if rushing_leader:
            runner_name = self._extract_last_name(rushing_leader.player_name)
            players.append(runner_name)
        
        # Passer and receiver for pass plays  
        passing_leader = self.player_stats_summary.get_passing_leader()
        receiving_leader = self.player_stats_summary.get_receiving_leader()
        if passing_leader and receiving_leader:
            passer_name = self._extract_last_name(passing_leader.player_name)
            receiver_name = self._extract_last_name(receiving_leader.player_name)
            players.append(f"{passer_name} to {receiver_name}")
        elif passing_leader:
            passer_name = self._extract_last_name(passing_leader.player_name)
            players.append(passer_name)
        
        # Leading tackler for defense
        leading_tackler = self.player_stats_summary.get_leading_tackler()
        if leading_tackler:
            tackler_name = self._extract_last_name(leading_tackler.player_name)
            players.append(f"tackled by {tackler_name}")
        
        # Kicker for field goals
        kicker_stats = self.player_stats_summary.get_kicker_stats()
        if kicker_stats:
            kicker_name = self._extract_last_name(kicker_stats.player_name)
            players.append(kicker_name)
        
        return ", ".join(players)
    
    def _extract_last_name(self, full_name):
        """Extract last name from full player name for concise display"""
        # Handle names like "Cleveland Starting QB" -> "QB"
        # or "Deshaun Watson" -> "Watson"
        if "Starting" in full_name or "Backup" in full_name:
            # For generated names like "Cleveland Starting QB"
            return full_name.split()[-1]  # Return position (QB, RB, etc.)
        else:
            # For real names, return last word
            return full_name.split()[-1]