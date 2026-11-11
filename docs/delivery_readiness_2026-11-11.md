# When2Ask — tonight's delivery status (2026-11-11)

The local engineering prototype is ready to demonstrate with documented limits. Core implementation is no longer the main gap. Remaining research/submission work must be distinguished from the tested local demo; no arbitrary completion percentage is claimed.

## Verified and deliverable now

| Deliverable | Actual state / evidence |
|---|---|
| Real robotics | Panda tabletop skills and three-room Husky navigation, real PyBullet bodies/contacts and independent evaluators; DIRECT render/step/disconnect rerun in delivery audit |
| Task diversity |9 task templates in the HTML catalogue; extra tasks have their own public goals/DAGs/evaluators, not merely colour changes |
| Live control | Local controller + HTTP execution workers, three independent physics processes, panoramic camera wall, task dispatch and method selection |
| Human interaction | Auto simulator or manual finite/text answers, unified question queue, preserved drafts/routing, ASK freezes that world's physics |
| Three methods | NoAsk, LLM-Gate, Jev-Gate with shared DeepSeek Planner and physical evaluation; no fabricated scores or hidden answers in model input |
| Reliable selected demo flow | v6 fixed observed loop cases; v7 compact Gate input now asks before buffer selection, opens then asks during retrieval, and senses without asking during occlusion in the new small study |
| Research data | Original formal2-template dataset:32 Dev/8 groups,128 Test/16 groups, group-isolated; existing real physical oracle160/160 |
| Evidence | Historical Phase2/3 results retained, plus independent later Dev studies with per-attempt usage, raw trajectories, actual physical videos and failure records |
| Presentation assets | Existing synchronized HTML replay, GIF/MP4, two-slide milestone PPT and speaker notes remain available; source-frame/flow mapping was previously verified |
| Tests / integrity |350 offline tests passed; final browser checks and actual model/physics controls; private GitHub, ignored0600 environment file, secret scan and historical/source hash verification |

## Clear remaining work

1. **Formal held-out model evaluation has not run.** `configs/frozen_test.yaml` still says `FROZEN_NOT_RUN`:128 samples×3 methods=384 fresh episodes under the original frozen protocol. All160 physical oracle passes establish executability, not model success. This turn did not authorize or consume that formal Test budget. New v7 must be frozen as its own protocol before any formal adoption; its small Dev results cannot be presented as held-out Test results.
2. **Two-computer VPN operation is not tested.** Local HTTP controller/worker separation and concurrency work. A real second-device network/environment rehearsal remains if a distributed deployment claim is required. Present it as implemented architecture/local validation until then.
3. **Final course submission requirements are not available here.** The user-modified milestone PPT was deliberately preserved; its Phase3 figures remain historical. This audit does not claim an updated final report/deck or rubric-specific submission is complete. A final presentation should identify dates/protocols, use current evidence accurately and disclose the small Dev scope.

Thus tonight's finish line can be a working local course-project demo plus a reproducible engineering report. A full held-out research conclusion and verified remote deployment remain separate measurable milestones.

## Suggested concise demonstration sequence

- **Retrieve & Restore / Jev / Gate Dev v7:** known opening first; p0.13 CONTINUE, then p0.83 ASK; answer selects the item; real retrieve and cover; model DONE. This illustrates useful progress before interruption.
- **Buffer / same Jev / v6 versus v7:** identical initial full public input and threshold0.5. Original p0.39 skips ASK and guesses wrong; compact view p0.56 asks then succeeds. Three physical moves in both cases distinguish clarification failure from motor-control failure.
- **Reveal & Inspect / Jev / Gate Dev v7:** move the opaque screen, perform real line-of-sight/range inspection, report measured code and finish with no question. This guards against an "ask more" explanation.

Use the recorded actual episodes at http://127.0.0.1:8898/ for a bounded presentation; live launches are available in the main console http://127.0.0.1:8877/. Choosing Human never forces ASK; it only changes who answers an actual question. For live v7 use one of its three supported templates, then explicitly select **Gate Dev v7**. Original default behaviour is retained for the broader catalogue.

## Reproducibility / file entry points

- [Latest diagnostic interpretation](gate_diagnostics_dev_v7.md), [machine-derived report](../outputs/gate_diagnostics_dev_v7/report.md), [all six videos](../presentation/gate_dev_v7/README.md).
- [Original formal Dev report](phase3/dev_report.md), [frozen Test configuration](../configs/frozen_test.yaml).
- [Existing synchronized milestone replay/PPT](../presentation/milestone/README.md); do not combine its historical Phase3 table with the newer tiny Dev results as one experiment.
- Actual readiness checks: [delivery_readiness.json](../outputs/gate_diagnostics_dev_v7/delivery_readiness.json), [test/browser evidence](../outputs/gate_diagnostics_dev_v7/test_validation.json).

The normal local launch is `.venv/bin/python console.py --live`. A fresh checkout needs the documented editable Python3.11 install and locally configured ignored credentials; credentials are never supplied through Git or report files. All work in this turn ran automatically, with no user terminal/configuration steps.
