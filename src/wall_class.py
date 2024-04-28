# velocity orange to blue is negatives, and velocity blue to orange is positives

class Wall:
    def __init__(self, team, ball_velocity, player_last_hit: bool):
        self.self = self
        self.team = "orange" if team == 1 else "blue"
        self.velocity = ball_velocity
        self.player_hit = player_last_hit

    def last_hit(self):
        if self.team == "orange" and self.velocity <= -2500 and self.player_hit == True:
            return True
        else:
            return False