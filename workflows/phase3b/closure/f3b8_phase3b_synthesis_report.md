# F3B.8 — Phase 3B synthesis and closure report

## 1. Closure purpose and evidence boundary

Phase 3B is closed as a controlled synthetic-ground-truth validation programme for the frozen AFINO 0.5 decision rule. F3B.8 does not create a new scientific experiment. It binds and synthesizes the already frozen F3B.1–F3B.7 evidence, translates that evidence into an explicit claim boundary, and prepares the synthetic-validation component for Manuscript 1. No AFINO execution, generator execution, stochastic draw, candidate search, threshold mutation, rule refit, DEVELOPMENT retuning, pooling of DEVELOPMENT with HELDOUT, or new inferential test occurs in this closure.

This distinction matters because HELDOUT was deliberately single-use. F3B.6 froze blinded decisions before truth access, and F3B.7 then consumed the set for the authorized truth join and baseline evaluation. F3B.8 therefore treats F3B.7 outputs as final validation evidence rather than material for another development cycle. The original F3B.5 truth ledger is not reopened. Closure uses the frozen F3B.7 truth-join audit, evaluation tables, metrics, gate and single-use audit.

## 2. DEVELOPMENT baseline characterization

The frozen baseline in DEVELOPMENT was `delta_BIC01 > 10 AND delta_BIC21 > 10`, with strict greater-than comparisons. On 3,600 primary DEVELOPMENT series, equally divided between 1,800 synthetic positives and 1,800 synthetic nulls, the confusion matrix was 143 TP, 1,657 FN, 1,799 TN and 1 FP. Sensitivity was 0.07944444444444444, specificity 0.9994444444444445, FPR 0.0005555555555555556, and balanced accuracy 0.5394444444444445.

These figures established a clear operating profile inside the frozen simulation domain: low sensitivity and extremely high specificity. They are synthetic-domain quantities, not observational performance estimates. The Wilson intervals frozen in F3B.4 remain the relevant finite-sample uncertainty summaries, and F3B.8 neither recomputes them as new inference nor transports them to real TESS populations.

## 3. DEVELOPMENT candidate gate and final-rule decision

DEVELOPMENT contained the prospectively authorized two-threshold candidate search. The optimum had t01=-7.517054630023225 and t21=-4.4514075428899105, with balanced accuracy 0.635. It increased DEVELOPMENT sensitivity, but promotion required all four frozen criteria. Criterion C4, the lower confidence bound on candidate-minus-baseline specificity being greater than -0.025, failed: the frozen lower bound was -0.3933333333333333. Three criteria passed and four were required.

The candidate was therefore not promoted. There was no runner-up rescue or alternate candidate search. The final-rule freeze retained the untouched AFINO 0.5 baseline at t01=t21=10. This does not establish global optimality over arbitrary classifiers; it is the correct consequence of the preregistered candidate family and gate. HELDOUT played no role in threshold choice.

## 4. Blind HELDOUT and single-use truth evaluation

The independent HELDOUT used a stronger separation than exploratory validation. AFINO outputs and 3,600 classifier decisions were frozen while truth remained blinded. Only after the pre-unblinding procedure was committed and verified was truth joined. F3B.7 accounts for 4,320 HELDOUT series: 3,600 primary classifier-plane cases, comprising 1,800 synthetic QPP-present and 1,800 synthetic QPP-absent cases, plus 720 input-admissibility challenges whose classifier decisions were absent by design.

The final HELDOUT confusion matrix was 152 TP, 1,648 FN, 1,800 TN and 0 FP. Sensitivity was 0.08444444444444445 with Wilson 95% interval [0.07246744846806605, 0.0981913737445873]. Specificity was 1.0 with interval [0.997870401081032, 1.0]. Observed FPR was 0.0 with interval [2.168404344971009e-19, 0.002129598918967953]. Balanced accuracy was 0.5422222222222223.

The observed 0/1,800 false selections must not be converted into a statement that a population FPR is exactly zero. The finite-sample Wilson upper bound is nonzero. Likewise these are HELDOUT synthetic-ground-truth operating characteristics, not observational sensitivity, specificity, FPR, PPV or prevalence estimates for real TESS flare populations.

## 5. DEVELOPMENT to HELDOUT synthesis

`f3b8_development_heldout_comparison.csv` keeps the two splits separate. No pooled confusion matrix, pooled rate, equivalence test or hypothesis test is introduced. Descriptively, both splits show the same qualitative operating profile in the preregistered synthetic domain: low sensitivity and extremely high specificity. DEVELOPMENT sensitivity was 0.07944444444444444 and HELDOUT sensitivity 0.08444444444444445; DEVELOPMENT specificity was 0.9994444444444445 and HELDOUT specificity 1.0; balanced accuracy was 0.5394444444444445 and 0.5422222222222223.

The permitted conclusion is qualitative consistency of operating profile under an independent single-use split. Closure does not claim statistical equivalence. Nor does it use HELDOUT to reopen the candidate gate. The frozen rule and rejected candidate decision remain unchanged.

## 6. Final synthetic selection function

The final selection surface for Manuscript 1 is `f3b8_final_selection_function.csv`. It contains exactly 156 rows and derives only from the F3B.7 HELDOUT selection table. Every original numerical and categorical field is reproduced exactly; F3B.8 adds only closure metadata identifying `HELDOUT_PRIMARY_FINAL` and the source artifact/SHA.

The representation remains `STRATIFIED_EMPIRICAL`. There is no smoothed surface, new probabilistic model or DEVELOPMENT-plus-HELDOUT pooling. The table preserves 9 `STRUCTURAL_NO_EXPOSURE` cells so structurally impossible exposure is not represented as empirical zero selection. The interpretation is domain-conditional: selection depends on frozen experimental conditions rather than one universal sensitivity scalar. Observational use would require explicit transport assumptions linking the synthetic design to the real TESS population.

## 7. Period recovery and selection conditioning

DEVELOPMENT contains 143 period-recovery rows and HELDOUT 152. HELDOUT period-estimate coverage is 152/1800=0.08444444444444445. Among selected true positives with finite recovered period, the frozen HELDOUT median absolute period error is 0.728071354085948 s, median relative error 0.011820556706242477, and median log-period ratio 0.0032587212754156855.

This conditioning matters. A method can estimate periods accurately for the small subset of synthetic QPP signals it selects while missing most injected positives. Conditional period accuracy therefore does not imply high detection completeness. Manuscript 1 must keep period-recovery quality and selection coverage separate.

## 8. Input admissibility and numerical scope

The 720 challenge series remain an input-admissibility plane rather than classifier truth cases. They are not converted into false negatives or true negatives, and their designed frequency is not a population prevalence estimate. This prevents pipeline-input robustness from being conflated with classifier performance.

Numerical stability evidence also remains bounded. Extra-seed stability was a DEVELOPMENT diagnostic; HELDOUT optimizer stability was not rerun by design. The evidence can support statements about the tested numerical subset but does not establish a unique global optimizer solution. Scientific execution is also bound to AFINO 0.5 and the frozen implementation/environment; different versions require separate evidence.

## 9. Claim matrix and limitations

The claim matrix classifies manuscript-facing statements as `SUPPORTED_NOW`, `SUPPORTED_WITH_EXPLICIT_LIMITATION`, `REQUIRES_F4_PLUS` or `PROHIBITED`. Supported claims include controlled synthetic-ground-truth characterization, HELDOUT sensitivity 152/1,800, observed absence of false selections in 1,800 synthetic nulls, rejection of the DEVELOPMENT candidate, retention of the 10/10 baseline, independent HELDOUT selection behavior and conditional period-recovery results.

Claims requiring explicit limitation include the specificity point estimate of 1.0 because finite-sample uncertainty must accompany it; the domain-conditional selection surface; and period accuracy conditional on selection. Claims requiring F4+ include real-TESS prevalence, observational PPV/sensitivity/specificity/FPR and population correction. Unqualified observational validation of AFINO and reuse of the consumed HELDOUT for new threshold development are prohibited.

The limitations register also preserves the synthetic nature of truth, frozen signal family, 40–300 s period support, discrete design grid, nonrepresentative challenge plane, incomplete observational null model, low HELDOUT sensitivity, finite uncertainty around 0/1,800 FP, selection-domain restriction, conditional period analysis, DEVELOPMENT-only extra-seed stability, optimizer nonuniqueness, AFINO version binding, restricted candidate family, rejected candidate, lack of external comparator execution, consumed HELDOUT, absent transport calibration, absent physical inference and evidence-plane separation.

A further limitation is the relationship between the synthetic design distribution and any future observational target population. The simulation programme deliberately fixes class balance, signal amplitudes, red-noise slopes, period support and duration/sample-count combinations to obtain controlled coverage of the experimental domain. Those allocations are design choices, not estimates of how frequently the corresponding conditions occur in TESS flare data. Consequently, neither the raw confusion matrix nor the empirical selection strata should be prevalence-weighted into an observational occurrence correction inside Phase 3B. Any later transport step must state how real events are mapped onto the frozen synthetic coordinates, how unsupported or weakly supported regions are handled, and how uncertainty in that mapping propagates into corrected population quantities.

The closure also preserves a distinction between reproducibility and generalizability. The F3B evidence is strongly reproducible because the generator, software environment, plans, blinded decisions, truth join, checksums and Git/OSF freezes are all bound. That reproducibility does not by itself establish that the synthetic family spans every astrophysically relevant flare morphology, noise process, cadence artifact or nonstationary background encountered in observations. Manuscript 1 should therefore present Phase 3B as a controlled validation layer that constrains what the frozen baseline does under specified conditions, while reserving broader observational validity, transport and population correction for later evidence planes.

## 10. Evidence-plane separation for Manuscript 1

The handoff explicitly separates F0 observational reproduction, F1 synthetic/numerical benchmark evidence, F2 observational pilot robustness, F3A catalogue-scale observational robustness and F3B synthetic ground-truth validation. F3B.8 does not re-audit F0–F3A and therefore does not invent new detailed claims for them; source-phase freezes remain authoritative.

This architecture prevents the word “validation” from obscuring different truth conditions. Synthetic ground truth measures controlled classification performance because labels are known by construction. Observational robustness can test reproducibility and analysis sensitivity without automatically providing physical truth. Catalogue-scale behavior can demonstrate operational consistency without yielding injection-recovery sensitivity. Manuscript 1 should preserve those distinctions in methods, results and discussion.

## 11. Formal Phase 3B decision

Phase 3B concludes with `HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS` and `CORRECTION CLAIM: NOT_ESTABLISHED`. The candidate was not promoted; the final rule is the preregistered AFINO 0.5 baseline at 10/10; the synthetic selection function has been characterized on independent HELDOUT; and the single-use HELDOUT is consumed.

The formal status is `PHASE3B_COMPLETE_HELDOUT_BASELINE_CHARACTERIZED_CORRECTION_NOT_ESTABLISHED_PROCEED_TO_MANUSCRIPT1`. This means the synthetic-validation component needed for Manuscript 1 is complete. It does not mean AFINO has been observationally validated, that a real-TESS selection function has been established, or that a population correction is ready. Those remain later transport and physical-inference problems.

After independent validation of this closure and its Git/OSF freeze, the next activity is Manuscript 1 evidence→claim→section architecture. There is no F3B.9 development cycle, and the consumed HELDOUT remains permanently closed to further rule tuning.
