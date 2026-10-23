"""GIF frames are rendered from the live Bullet world in DIRECT or GUI mode."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .environment import Environment


class Recorder:
    def __init__(self, env: Environment, stride=24):
        self.env, self.stride = env, stride
        self.label = "OBSERVE scene"
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []
        self.frame_log: list[dict] = []

    def on_step(self):
        if self.env.step_count % self.stride == 0:
            self.capture()

    def capture(self, duration_ms=None):
        frame = self.env.render()
        draw = ImageDraw.Draw(frame)
        draw.rectangle((0, 0, 640, 35), fill=(22, 28, 38))
        draw.text((10, 4), f"When2Ask  {self.label}", fill="white")
        draw.text((10, 20), f"PyBullet TinyRenderer  step {self.env.step_count}  grasp_mode=constraint",
                  fill=(205, 215, 229))
        self.frames.append(frame.quantize(colors=256))
        duration = duration_ms or round(1000 * self.stride * self.env.DT)
        self.durations.append(duration)
        self.frame_log.append(dict(simulation_step=self.env.step_count, label=self.label,
                                   duration_ms=duration))

    def save(self, path: Path):
        encoded_count = 0
        if self.frames:
            self.frames[0].save(path, save_all=True, append_images=self.frames[1:],
                                duration=self.durations, loop=0, optimize=False, disposal=2)
            with Image.open(path) as encoded:
                encoded_count = encoded.n_frames
        return dict(renderer="PyBullet ER_TINY_RENDERER", path=str(path.name),
                    frame_count=len(self.frames), encoded_frame_count=encoded_count,
                    stride=self.stride, frames=self.frame_log)
