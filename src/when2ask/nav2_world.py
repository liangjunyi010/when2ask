"""Reuse v1 geometry/sensing/evaluation; vary real motor speed, not playback speed."""
import math

from PIL import ImageDraw

from .navigation_world import NavigationWorld


class World(NavigationWorld):
    def __init__(self,sample):
        self.speed_factor=sample.speed_factor
        super().__init__(sample)

    def motors(self,v,w):
        super().motors(v*self.speed_factor,w*self.speed_factor)

    def drive(self,waypoint,max_steps=4000,final_yaw=None):
        return super().drive(waypoint,max_steps=math.ceil(max_steps/self.speed_factor),final_yaw=final_yaw)

    def render(self,width=960,height=540):
        image=super().render(width,height)
        draw=ImageDraw.Draw(image)
        draw.rectangle((0,0,width,37),fill=(10,25,42))
        draw.text((12,8),f'Navigation Dev v2 | wheel speed factor {self.speed_factor:g} | LOCAL sensing',fill='white')
        return image
