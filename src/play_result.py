class PlayResult:
    """Data object representing the result of a simulated play"""
    
    def __init__(self, outcome="incomplete", yards=0):
        self.outcome = outcome
        self.yards = yards
    
    def __str__(self):
        return f"PlayResult(outcome='{self.outcome}', yards={self.yards})"
    
    def __repr__(self):
        return self.__str__()