# Updated speaker notes: slides 6–11

## Slide 6 (55 seconds)

We now support nine types of robotic tasks. These include packing, sorting, restocking, exchanging objects, retrieving an item and restoring the scene. We also include navigation and inspection. The distinction matters: some missing information is a user preference, so the robot needs an answer. Other missing information is a world fact that the robot can discover by searching or inspecting. We create cases with complete instructions as well as missing information, separate related layouts into groups, and check feasibility by executing a physical solution.

## Slide 7 (60 seconds)

Here are the three gate-based policies. NoAsk always continues, so the DeepSeek planner must act using the information it already has. LLM-Gate first asks DeepSeek whether a question is needed. Jev-Gate uses the Jev probability with a threshold of one half. Both gates then use the same DeepSeek question or action planner. A user answer updates the public history, while an action changes the physical observation. We also test a fourth baseline, Single-call DeepSeek, which chooses a question, an action or DONE in one request.

## Slide 8 (35 seconds)

This table is our cross-model evaluation setup. Each model will use the same LLM-Gate workflow, serving as both the decision gate and the planner. Only the DeepSeek row is currently measured. Its success rate is one hundred percent in this development pilot, and we normalize its API time and estimated cost to one hundred percent for future comparison. The other rows remain blank until those experiments are completed. We do not infer a ranking from missing results.

## Slide 9 (55 seconds)

This is the completed four-method comparison. NoAsk reached about seventy-eight percent success. LLM-Gate reached one hundred percent, while Jev-Gate and Single-call DeepSeek reached about ninety-six percent. Relative to the separate LLM-Gate, Jev used about thirty percent less API time and forty-six percent lower estimated API cost. Single-call DeepSeek was faster than Jev here, but had a higher estimated cost. No unnecessary questions appeared in the fully specified cases. This is a small development pilot, so it cannot establish that false alarms never occur or that one method is always best.

## Slide 10 (50 seconds)

This is our robot command center. We choose a task, a decision method, and automatic or human replies. Here, I launch four different tasks, each running in its own PyBullet world. The cameras show what each robot is doing. When information is missing, questions appear in the queue on the right. I type my answer here. Only the asking robot pauses; the others keep working. After submission, that robot continues. We can therefore supervise several tasks from one screen, stepping in when needed. The final status comes from physical checks, rather than the model simply claiming success. All four tasks complete in this recorded, time-compressed demonstration.

## Slide 11 (35 seconds)

Our main contribution is a benchmark that tests when robotic agents should ask, continue or gather information themselves. We implemented nine task types, real physical execution, and a shared evaluation system. The Jev gate showed lower observed inference time and estimated cost than the separate LLM gate, with a small success-rate trade-off. Our main limitations are the small development sample, fixed skills and simulated robots. Next, we will expand independent layouts, repeat the comparisons and complete the cross-model evaluation. Thank you.

