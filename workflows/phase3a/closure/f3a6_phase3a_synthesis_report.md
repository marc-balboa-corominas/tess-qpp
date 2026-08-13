# F3A.6 — Phase 3A synthesis and closure

## 1. Scientific role of Phase 3A

Phase 3A was designed as a catalogue-scale extension of the observational robustness question established in the Phase-2 pilot. Its purpose was not to decide whether AFINO is physically correct, nor to convert published QPP labels into ground truth. The defensible question is procedural: when an observational reference state is frozen in advance, how often does the binary classification remain the same under prospectively specified changes of temporal window and processing, which inputs become structurally inadmissible, what numerical stability is observed across optimizer seeds, and how stable is the recovered period when selection itself survives? The closure therefore keeps reference reproduction, input admissibility, classification robustness, numerical behavior and conditional period robustness as separate evidence planes.

F2 and F3A answer related questions at different scales. F2 was a ten-event pilot with five pairs. F3A expands the experiment to 122 observational reference events divided symmetrically into 61 published-QPP references and 61 not-selected references. This larger scope supports a stronger statement about the existence of procedural classification sensitivity at catalogue scale, but it does not create an observational validation dataset. The labels remain observational reference states, repeated perturbations remain nested within events, and no physical truth class is established.

## 2. Continuity from the F2 pilot

The strongest continuity is in design. F2 froze thirteen temporal windows and six processing profiles, creating 780 planned variants across ten events. F3A inherited the same 78-cell perturbation structure and applied it to 122 events, yielding 9,516 planned variants. Both phases kept inadmissible inputs visible rather than silently converting them into negative classifications. In F2, 514 variants were eligible and 266 inadmissible. In F3A, 6,422 were eligible and 3,094 inadmissible. These denominators are not poolable, but the methodological principle is identical: inadmissibility is part of the outcome of the stress test.

F2 also established the qualitative pattern that motivated scaling. Its ten W00/P00 baseline classifications reproduced the frozen baseline without classification mismatch. Relative to those baselines, the pilot recorded 140 selected-retained variants, 136 selection losses, 238 not-selected-retained variants and no baseline-relative selection gains, with 266 inadmissible variants kept separate. The correct interpretation was already narrow: published classifications could change under frozen methodological perturbations, while the matched not-selected role did not gain selection against the global baseline in that pilot. F2 explicitly prohibited reading these transitions as false negatives, true negatives or an observational false-positive rate.

## 3. Catalogue-scale baseline reproduction

The largest material change from F2 appears before the perturbation analysis itself. At F3A baseline, only 65 of 122 events reproduce their frozen observational reference state. Fifty-one are `REFERENCE_BASELINE_MISMATCH`, six are `INPUT_INADMISSIBLE`, and none is numerically incomplete. The role split is essential. Among the 61 `PUBLISHED_QPP_REFERENCE` events, only eight are baseline concordant, 51 are baseline mismatches and two are baseline-input inadmissible. Among the 61 `PUBLISHED_NOT_SELECTED_REFERENCE` events, 57 are concordant, none is a baseline mismatch and four are inadmissible.

All 51 baseline mismatches therefore arise in the published-QPP reference role. This is the central new limitation exposed by catalogue scale. It is not evidence that 51 published detections are physically false. It says that, under the frozen F3A W00/P00/seed0 implementation and input contract, those 51 events do not reproduce the frozen observational reference state. The cause is `UNRESOLVED_WITHIN_F3A`; the closure does not invent a mechanistic explanation. This limitation means that F3A cannot be presented as a simple replication of the F2 pilot, whose ten baseline states were reproduced.

## 4. Input admissibility

Input admissibility remains an independent methodological result. F3A preserves the full denominator of 9,516 planned variants even though 3,094 are inadmissible. The remaining 6,422 variants provide executable primary decisions. The distinction matters because an inadmissible input contains no valid negative decision and cannot be used as a zero in a selection fraction. The same principle was already present in F2, but catalogue scale reveals a substantially larger absolute burden and a broader set of structural reasons.

The closure therefore treats admissibility as part of the procedure's operating domain rather than as a nuisance to remove. This has direct implications for F3B: injection–recovery should represent relevant gap, quality and cadence regimes prospectively where scientifically appropriate, while preserving an explicit policy for cases that violate the input contract. It must not learn a correction by reclassifying F3A inadmissible rows after the fact.

## 5. Classification robustness

F3A transition claims are calculated only when the event baseline is `REFERENCE_CONCORDANT`. Within that restricted, transition-eligible scope, the catalogue-scale matrix contains 295 `SELECTED_RETAINED` transitions, 171 `SELECTION_LOST` transitions, 3,178 `NOT_SELECTED_RETAINED` transitions and no `SELECTION_GAINED` transitions. Every transition row satisfies the concordant-baseline gate.

The QPP-reference result reproduces the qualitative procedural-sensitivity pattern seen in F2: retained selections and selection losses coexist under prospectively frozen perturbations. This supports the statement that methodological choices can alter binary QPP classification among references whose baseline state is reproduced. It does not support a false-negative rate, because the QPP-reference label is not physical ground truth and the transition rows are repeated perturbations within a restricted subset.

Likewise, zero `SELECTION_GAINED` transitions in the not-selected reference scope is not an observational false-positive rate of zero. The denominator is a set of repeated perturbations of baseline-concordant observational references, not an independently labeled negative population. F2 made the same interpretive distinction, and F3A preserves it at larger scale.

## 6. Numerical stability

The optimizer stability plane contains 116 W00/P00 input-eligible events and 1,160 decisions across seeds zero through nine. All 116 events preserve their binary classification across the frozen seed grid; no event is seed-discordant. This is strong evidence that the binary decision is stable to the external optimizer seed within this specific stability scope.

At the same time, every event has ten distinct parameter payloads for each of M0, M1 and M2. Convergence remains `NOT_AUDITABLE`, and M2 continues to show substantial warnings and bound contacts. These facts make the correct numerical conclusion explicit: stable classification is not the same as a unique numerical solution. F3A therefore strengthens confidence in seed stability of the binary output without establishing unique optimizer convergence or a single privileged parameter solution.

## 7. Conditional period robustness

The period plane remains conditioned on retained selection. F3A contains 295 comparable rows for which the baseline is concordant and selected, the perturbed variant is selected, and both recovered M1 periods are finite. Within this restricted population, the absolute period change has a median of approximately 0.216363 s and a maximum of approximately 2.714694 s.

This result is consistent in form with F2, which contained 140 selected-to-selected comparisons with a median absolute change of 0.244031 s and a maximum of 2.714694 s. The two denominators must not be pooled and the similarity of the maxima is not interpreted inferentially. The scientifically defensible claim is simply that conditional period robustness remains observable when classification survives. Lost selections and inadmissible inputs remain outside the recovered-period denominator, and no “true period” is established.

## 8. What F3A reproduces from F2

F3A reproduces several qualitative features of the pilot. The same prospectively frozen 13×6 stress-test logic remains operational at much larger scale. Input inadmissibility remains scientifically relevant and distinct from non-selection. QPP-reference classifications can be retained or lost under frozen methodological perturbations. Baseline-relative gains are absent in the respective not-selected reference scopes. Binary classification remains stable across the frozen optimizer-seed grid while numerical parameter payloads vary. Period robustness remains conditional on retained selection.

These points support continuity of the methodological robustness story. They do not mean that F3A “proves F2.” The phases use different observational populations, different denominators and, most importantly, different baseline-reproduction behavior. The synthesis is therefore documentary and qualitative, not a pooled statistical analysis.

## 9. What materially changes from F2

The decisive change is the baseline gate. F2 entered robustness with ten of ten frozen baseline classifications reproduced. F3A instead finds only 65 concordant baseline events, alongside 51 mismatches and six inadmissible baselines. The mismatch is entirely concentrated in the published-QPP reference role, where only eight of 61 references are concordant. This makes the catalogue-scale QPP transition denominator far narrower than the published-QPP reference set itself.

That limitation changes the emphasis of the project. F3A still demonstrates catalogue-scale procedural sensitivity within reproduced baselines, but the more important methodological lesson is that baseline reproduction itself cannot be assumed when scaling. The closure therefore treats baseline reproduction as a first-class gate rather than as an administrative precondition.

## 10. Interpretation boundaries

Phase 3A does not establish observational ground truth, physical QPP truth, AFINO observational validation, sensitivity, specificity or observational FPR. It introduces no formal hypothesis test and no post-hoc robustness threshold. It does not establish a correction claim or a selection function. Candidate discovery remains outside scope. The absence of selection gains cannot be promoted into a performance metric, and the 51 QPP-reference mismatches cannot be promoted into false-detection counts.

Warnings, bounds and parameter multiplicity are numerical diagnostics, not demonstrated causes of classification change. Similarly, catalogue scale alone does not transform observational-reference labels into validated classes. These boundaries are not weaknesses to hide; they define exactly what evidence F3A supplies and what evidence must be created elsewhere.

## 11. Manuscript 1 implications

The robustness component of Manuscript 1 remains supported. A methods-and-results narrative can document the frozen perturbation design, explicit inadmissibility, baseline-gated transitions, seed stability, numerical multiplicity and conditional period behavior. The new catalogue-scale baseline limitation should be central rather than buried: 51 of 61 published-QPP references fail to reproduce their frozen reference state under the F3A baseline, while 57 of 61 not-selected references are concordant.

The validation/correction component is not complete. Manuscript wording must therefore separate “robustness characterization” from “validated performance.” F3A can support claims about procedural sensitivity and operating-domain limitations; it cannot support claims about true-positive or false-positive behavior.

## 12. Why F3B remains necessary

F3B is required to move from observational robustness to performance under known truth. The next program must freeze a realistic injection–recovery domain, separate development from held-out validation, define classification metrics prospectively, keep period recovery separate from classification, retain AFINO 0.5 as the baseline, and resolve deferred comparator decisions before execution. Any correction or selection function must be frozen before held-out access.

Published observational labels must not be used as physical truth, and the F2/F3A events that motivated the analysis must not be reused as independent held-out confirmation. Numerical stability remains a separate evidence plane. Candidate discovery remains outside the initial validation program.

## 13. Phase 3A closure decision

The evidence supports `PHASE3A_COMPLETE_PROCEED_TO_F3B_WITH_LIMITATIONS`. Phase 3A has completed its catalogue-scale robustness objective: it shows at catalogue scale that frozen methodological perturbations can alter retained QPP-reference classifications among baseline-reproduced references, while also revealing a material baseline-reproduction limitation in the published-QPP reference set. It does not complete observational validation or correction.

The next task is F3B.1: preregister the injection–recovery program, freeze the development/held-out split and validation architecture, define success criteria and metrics, and resolve comparator policy before generating a single injection. Phase 3A closes with a supported robustness component, explicit limitations and a clearly bounded handoff to validation under known ground truth.
