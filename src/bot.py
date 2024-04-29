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
import time

HOVER_IDLE_HEIGHT = 2000
HOVER_IDLE_Y = 1000
HOVER_MAX_HEIGHT = 1800
HOVER_MAX_SIDE = 3900
HOVER_TARGET_Y = 5000
GET_TO_DISTANCE = 1000 # farthest you can be to get to the ball
CHECKING_TIME = 6000 # needs to be adjusted; is the time (in miliseconds) needed to elapse to check ball movement

starting_time = time.time()
list_of_ball_positions = [] # in vectors (?)

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

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.info.read_packet(packet)
        if self.car is None:
            # Inits car and stuff
            self.car = self.info.cars[self.index]
            self.hover = GetToAirPoint(self.car, self.info)
            self.kickoff = Kickoff(self.car, self.info)

        if packet.game_info.is_kickoff_pause and dist(self.info.ball.position, self.car.position) < 4000:
            # Starts kickoff
            self.kickoff.step(self.info.time_delta)
            self.controls = self.kickoff.controls
            
            return self.controls
        
        time_now = time.time()
        time_elapsed = time_now - starting_time
        
        # Gets the ball prediction and converts it to a vector
        ball_prediction = self.get_ball_prediction_struct()
        go_to_balls_y = self.get_vec3_ball(ball_prediction, time_elapsed)
        
        target = go_to_balls_y 
        
        # Render target and ball prediction
        polyline = [ball_prediction.slices[i].physics.location for i in range(0, 100, 5)]
        self.renderer.draw_polyline_3d(polyline, self.renderer.yellow())
        self.renderer.draw_rect_3d(target, 10, 10, True, self.renderer.cyan())
        self.renderer.draw_line_3d(self.car.position, target, self.renderer.lime())

        # update controls
        self.hover.target = target
        self.hover.step(self.info.time_delta)
        self.controls = self.hover.controls

        return self.controls

    def get_vec3_ball(self, ball_prediction, time_elapsed):
        global list_of_ball_positions, starting_time
        
        for step in ball_prediction.slices[:ball_prediction.num_slices]:
            pos = step.physics.location
            
            if len(list_of_ball_positions) <= 1 and time_elapsed >= CHECKING_TIME:
                list_of_ball_positions.append(self.info.ball.position)

            elif len(list_of_ball_positions) >= 2: # realistically, this should never go over 2
                distance_from_ball = dist(list_of_ball_positions[0], list_of_ball_positions[1])
                movement_vector = vec3(pos.x, 0, pos.z if pos.z > self.hover_min_height else self.hover_min_height)
                hover_vector = vec3(0, 0, self.hover_min_height)

                # return movement_vector if distance_from_ball != abs(distance_from_ball) 
                if (self.team == 0 and distance_from_ball != abs(distance_from_ball)) or \
                    (self.team != 0 and distance_from_ball != abs(distance_from_ball) and self.info.ball.position[1] >= 0):
                    list_of_ball_positions = []
                    starting_time = time.time()
                    return movement_vector
                
                elif (self.team == 0 and distance_from_ball == abs(distance_from_ball) and self.info.ball.position[1] <= 0) or \
                    (self.team != 0 and distance_from_ball == abs(distance_from_ball)):
                    list_of_ball_positions = []
                    starting_time = time.time()
                    return hover_vector
