from typing import List
from random import randint
from dataclasses import dataclass

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState, BOT_CONFIG_AGENT_HEADER
from rlbot.parsing.custom_config import ConfigObject
from rlbot.utils.structures.game_data_struct import GameTickPacket


from rlutilities.simulation import Game
from rlutilities.linear_algebra import vec3, norm, normalize, clip

from get_to_air_point import GetToAirPoint
from kickoff import Kickoff
from random import randint

HOVER_IDLE_HEIGHT = 2000
HOVER_IDLE_Y = 1000
HOVER_MAX_HEIGHT = 1800
HOVER_MAX_SIDE = 3900
HOVER_TARGET_Y = 5000

# Team Blue is 0, Team Orange is 1

def sign(x):
    return 1 if x >= 0 else -1

def dist(a, b):
    return norm(a - b)

class MyBot(BaseAgent):
    @staticmethod
    def create_agent_configurations(config: ConfigObject):
        params = config.get_header(BOT_CONFIG_AGENT_HEADER)
        params.add_value("hover_min_height", int, default=1022)

    def load_config(self, config_header):        
        self.hover_min_height = config_header.getint("hover_min_height")

    def initialize_agent(self):
        self.controls = SimpleControllerState()

        self.info = Game()
        self.info.set_mode("soccar")
        self.info.read_field_info(self.get_field_info())
        self.velocity_list = []

        self.car = None
        self.hover = None
        self.kickoff = None

        self.sign = 2 * self.team - 1  # 1 if orange, else -1
        self.xHoverPos = 3000 if randint(0, 1) == 0 else -3000

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState: 
        self.ball = packet.game_ball
        self.info.read_packet(packet)
        if self.car is None:
            self.car = self.info.cars[self.index]
            self.hover = GetToAirPoint(self.car, self.info)
            self.kickoff = Kickoff(self.car, self.info)

        if packet.game_info.is_kickoff_pause and dist(self.info.ball.position, self.car.position) < 4000:
            self.kickoff.step(self.info.time_delta)
            self.controls = self.kickoff.controls
            
            return self.controls
        

        ball_prediction = self.get_ball_prediction_struct()
        go_to_balls_y = self.get_vec3_ball(ball_prediction)
        # if future_goal and not packet.game_info.is_kickoff_pause:
        #     target = future_goal

        #     # the ball prediction is slightly wrong, the ball will be closer to the center of the goal
        #     target[0] *= 0.9
        #     target[2] *= 0.8

        #     target[2] += 50
        # else:
        self.is_seeking_our_goal = sign(self.info.ball.velocity[1]) == sign(self.car.position[1])
        # even if the ball prediction didn't end up in our goal, move to the side of the ball to be ready
        # idle_x = clip(self.info.ball.position[0], 0, 0) if is_seeking_our_goal else 0
        target = go_to_balls_y #vec3(0, HOVER_IDLE_Y, HOVER_IDLE_HEIGHT)

        # render target and ball prediction
        # polyline = [ball_prediction.slices[i].physics.location for i in range(0, 100, 5)]
        # self.renderer.draw_polyline_3d(polyline, self.renderer.yellow() if not future_goal else self.renderer.cyan())
        self.renderer.draw_rect_3d(target, 10, 10, True, self.renderer.cyan())
        self.renderer.draw_line_3d(self.car.position, target, self.renderer.lime())

        # update controls
        self.hover.target = target
        self.hover.step(self.info.time_delta)
        self.controls = self.hover.controls

        return self.controls

    def get_vec3_ball(self, ball_prediction):
        for step in ball_prediction.slices[:ball_prediction.num_slices]:
            pos = step.physics.location

            
            if self.ball.latest_touch.team == self.team and self.info.ball.position[0] > 0 and self.xHoverPos == 3000:
                return vec3(pos.x, 0, pos.z if pos.z > self.hover_min_height else self.hover_min_height)
            elif self.ball.latest_touch.team == self.team and self.info.ball.position[0] < 0 and self.xHoverPos == -3000:
                return vec3(pos.x, 0, pos.z if pos.z > self.hover_min_height else self.hover_min_height)
            else:
                return vec3(self.xHoverPos, 0, self.hover_min_height)

            # if self.team == 0:
            #     if (pos.y < 0 and pos.z >= 400) and (self.is_seeking_our_goal != True or dist(self.info.ball.position, self.car.position) < 400): # On our side and is able to hit
            #         return vec3(pos.x, 0, pos.z if pos.z > self.hover_min_height else self.hover_min_height)
            #     else:
            #         return vec3(0, 0, self.hover_min_height)
                
            # else:
            #     if pos.y > 0 and pos.z >= 400 and self.is_seeking_our_goal != True: # On our side and is able to hit
            #         return vec3(pos.x, 0, pos.z if pos.z > self.hover_min_height else self.hover_min_height)
            #     else:
            #         return vec3(0, 0, self.hover_min_height)
                
    def find_future_goal(self, ball_prediction):
        
        for step in ball_prediction.slices[:ball_prediction.num_slices]:
            pos = step.physics.location
            if sign(pos.y) == self.sign:
                continue
            if abs(pos.y) > HOVER_TARGET_Y and abs(pos.x) < HOVER_MAX_SIDE and pos.z < HOVER_MAX_HEIGHT:
                return vec3(pos.x, pos.y, pos.z if pos.z > self.hover_min_height else self.hover_min_height)
        return None

