"""Convert existing evidence to browser resources. Offline and non-destructive."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from when2ask.replay import convert_episode


def main():
    output=ROOT/"presentation/milestone/web"
    output.mkdir(parents=True,exist_ok=True)
    sources=[("jev_pack", "outputs/phase2_live/paired_v2/validation_002/jev_gate"),
             ("llm_containers", "outputs/phase3_live/dev/v3_dev_016__llm_gate")]
    episodes=[convert_episode(ROOT/ref,output,key,repository_root=ROOT) for key,ref in sources]
    manifest=dict(schema_version=1,default_episode="jev_pack",episodes=episodes,
                  clock="One display clock selects a frame and its flow state atomically.",
                  highlight=dict(action_speed=6,holds_ms=dict(gate_result=500,question=1400,user_answer=1600,evaluation=1000)))
    (output/"timeline.json").write_text(json.dumps(manifest,separators=(",",":"))+"\n")
    print(json.dumps([dict(episode=e["episode_key"],frames=len(e["frames"]),duration_ms=e["duration_ms"]) for e in episodes]))


if __name__=="__main__":
    main()
