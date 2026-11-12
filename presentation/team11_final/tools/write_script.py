"""Team 11 narration, aligned with the four presentation requirements."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
OLD=BASE.parent/'final_benchmark_cost/speaker_script.json'
old=json.loads(OLD.read_text())['slides']
slides=[
('When2Ask',15,
'''Hi everyone. We are Team Eleven, Liang Junyi and Yang Haocheng. Our project, When2Ask, benchmarks when a robot should ask for clarification and when it can continue.''',
'Team number and names supplied directly by the team.','title'),
('Problem & Motivation',65,
'''As we learned in class, conversational large language models have strong zero-shot capabilities, making it easy to build agents for new tasks. However, response speed and inference cost are important factors when we call these models repeatedly. Our project brings that trade-off into robotic clarification. Consider this instruction: open the box, bring my chosen item, and replace the lid. If the user never specified the item, even a strong model cannot know the preference. Guessing risks a wrong choice. Asking immediately can interrupt useful work, because opening the box is already allowed. We therefore benchmark whether a specialized judgment model can decide when to ask, while keeping task reliability and reducing decision overhead.''',
old[0]['evidence']+' Classroom connection paraphrases the user-supplied lecture description; no invented quotation or slide attribution.','problem'),
('Approach & Implementation',60,
'''This diagram shows the implemented execution loop. The public state contains the instruction, current observation and public history. A gate chooses ASK or CONTINUE before the planner runs. On the orange branch, DeepSeek generates a question. The simulator, or a human in the HTML console, answers it, and the answer updates public history. The physical world stays paused. On the blue branch, the shared DeepSeek planner selects a robot skill. Panda executes it using inverse kinematics and our documented near-range constraint grasp, then observes the result. Only the action planner can return DONE. The independent evaluator checks the actual world and task order. Hidden preferences stay outside the gate and planner.''',
old[4]['evidence']+' Same-source implementation: research_runner, public protocol, user simulator, skills and physical evaluator. The frozen benchmark uses simulator answers; HTML supports human answers separately.','approach'),
('Benchmark Task Design',65,
'''The benchmark creates three different clarification situations. Buffer exchange requires swapping two occupied slots through a temporary pad. If the permitted pad is unknown, the first move needs a user preference. Retrieve and restore allows useful progress first: open the box, ask which item to deliver, retrieve it, and reclose the box. Occlusion inspection tests a different kind of uncertainty. The robot must move the screen, inspect a label and report the measured code. That is an observable world fact, so asking the user should not replace the required inspection. Public task dependencies define the order in every case. Fully disclosed controls test whether gates avoid unnecessary questions. These structures test when to ask, rather than simply whether a robot can ask.''',
old[2]['evidence'],'approach'),
('Dataset Construction & Physical Validation',70,
'''Each generated sample combines a layout, instruction, public dependency graph and private preference. We split by base physical layout, so preference changes and wording variants cannot cross Development and Test. This version has twenty-four Development samples from six groups, and twelve Test samples from twelve independent groups, four per task. Both partitions balance zero and one initially unknown slot. We also balance correct-choice candidate order and exclude previously debugged layouts from Test. Before online evaluation, a deterministic oracle executes every sample using the real robot skills. An independent evaluator checks footprints, support, stability, release and required task order. All thirty-six feasibility executions passed. The oracle can access private preferences to check feasibility, but the models never receive its actions or evaluation labels.''',
old[3]['evidence'],'approach'),
('Three Methods, One Shared Planner',50,
'''We compare three methods under the same task and execution conditions. LLM-NoAsk skips the gate and never asks. DeepSeek must act from public information and may guess. LLM-Gate uses DeepSeek to generate an ASK-or-CONTINUE decision. Jev-Gate uses a Noul probability with a frozen threshold of zero point five. Jev returns typed probabilities instead of autoregressive answer text, motivating faster decisions. Both gates receive the same compact public state. All methods share the DeepSeek action planner, skills, evaluator and budgets. Both asking methods share the question planner and simulator. We froze models, prompts and threshold before Test, and reset the environment independently for every method.''',
old[4]['evidence'],'approach'),
('Results: Success & Clarification Burden',60,
'''We evaluated twelve held-out layout groups across three methods: thirty-six real API and PyBullet episodes. NoAsk succeeded in ten out of twelve, while both gates succeeded in all twelve. Its two failures came from guessing the wrong buffer or requested item. The evaluator used the same physical criteria for every method; skipping questions did not automatically count as failure. Burden counts distinct requested preference slots, charging repeated questions again. Both gates requested four slots in total, or one third per episode. Success and burden alone cannot tell us whether a question came too early, which is why we also inspect the saved execution order. These are observed results from a small study, not proof of general superiority.''',
old[6]['evidence'],'results'),
('Results: Speed & Estimated API Cost',65,
'''Speed has two scopes here. Mean gate API response was eight hundred and fifteen milliseconds for DeepSeek and two hundred and ninety-five for Jev, about two point eight times faster. These calls follow different trajectories, not identical test inputs. Across twelve episodes per method, cumulative API latency was fifty-eight seconds for NoAsk, one hundred and five for LLM-Gate, and seventy-nine for Jev-Gate. That excludes robot execution time. Estimated total API cost was about one point one cents, one point eight five cents, and one point seven eight cents, respectively. We apply current public rates to actual usage, including cache hits. These are estimates, not invoices. Jev's estimated total saving over LLM-Gate is only three point seven percent. NoAsk remains fastest and cheapest, with lower observed reliability.''',
old[7]['evidence'],'results'),
('Results & Demonstration: Real Execution',75,
'''Timing can differ even when success and burden match. On two retrieval tasks with an undisclosed item, LLM-Gate asked before opening, while Jev opened first and then asked. This is exploratory trace analysis. Here is one actual Jev episode. A score of zero point eleven leads to CONTINUE and the robot opens the box. The score then becomes zero point sixty-two. It asks which item to retrieve, and the simulator selects the block. The robot delivers it and replaces the lid. The replay retains a rejected lid move before the correct cover action repairs it. Both motion and flow highlights follow the same recorded frames.''',
old[8]['evidence'],'results'),
('Discussion & Conclusions',45,
'''Our benchmark separates asking first, progressing before asking, and inspecting instead of asking. We combine layout isolation, physical validation and shared planning. In this small study, both gates improved observed reliability over guessing. Jev reduced gate response time, while its estimated total cost advantage was modest. Limitations include twelve Test groups, binary choices, assisted grasping and sensitivity to prompts, thresholds and API conditions. Next, we will expand independent layouts, pre-register timing metrics and repeat the comparisons. The takeaway is that clarification should depend on what information blocks useful progress. Thank you.''',
old[9]['evidence'],'discussion')]
data={'language':'English','team_number':11,'members':['Liang Junyi','Yang Haocheng'],
      'target_minutes':10,'target_seconds':570,'replay_seconds':22.2,
      'slides':[dict(slide=i+1,title=t,target_seconds=sec,script=s,evidence=e,section=section,
                     spoken_words=len(s.split()))for i,(t,sec,s,e,section)in enumerate(slides)]}
(BASE/'speaker_script.json').write_text(json.dumps(data,indent=2)+'\n')
out=['# Team 11 — When2Ask speaker notes\n','Liang Junyi and Yang Haocheng\n',
     f"English script: {sum(x['spoken_words']for x in data['slides'])} words. Slide schedule: 9:30, including a separate 22.2-second recorded demo. The remaining 30 seconds are a buffer.\n",
     'Evidence paragraphs are not spoken. Start the video on slide 9 and let it finish; its duration is already included.\n']
elapsed=0
for s in data['slides']:
    fmt=lambda v:f'{v//60}:{v%60:02d}'
    out.append(f"## Slide {s['slide']} — {s['title']}\n\n{fmt(elapsed)}–{fmt(elapsed+s['target_seconds'])} ({s['target_seconds']} seconds)\n\n{s['script']}\n")
    if s['slide']==9:out.append('**Demo cue:** allow the full 22.2-second clip. A separate playback hold fits inside this slide’s 75 seconds.\n')
    out.append(f"<details><summary>Evidence and cautions (not spoken)</summary>\n\n{s['evidence']}\n\n</details>\n")
    elapsed+=s['target_seconds']
(BASE/'speaker_notes.md').write_text('\n'.join(out))
print(json.dumps({'slides':len(slides),'words':sum(s['spoken_words']for s in data['slides']),'seconds':elapsed,
                  'wpm_including_separate_video_hold':[round(s['spoken_words']*60/(s['target_seconds']-(22.2 if s['slide']==9 else 0)),1)for s in data['slides']]}))
