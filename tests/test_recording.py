from PIL import Image

from when2ask.recording import Recorder


def test_headless_live_frames_and_question_hold_do_not_step_physics(env, tmp_path):
    recorder = Recorder(env, stride=12)
    env.frame_callback = recorder.on_step
    recorder.capture()
    env.step(24)
    before = env.snapshot()
    recorder.label = "ASK block_choice"
    recorder.capture(duration_ms=1200)
    assert env.snapshot() == before
    metadata = recorder.save(tmp_path / "real.gif")
    assert metadata["frame_count"] == 4
    assert metadata["frames"][-1]["simulation_step"] == before["simulation_step"]
    with Image.open(tmp_path / "real.gif") as gif:
        assert gif.format == "GIF" and gif.n_frames >= 2
