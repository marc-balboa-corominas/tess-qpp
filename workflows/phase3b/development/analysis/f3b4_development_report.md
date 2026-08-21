# Phase 3B.4 DEVELOPMENT characterization and final-rule freeze

## Scope and interpretation

Phase 3B.4 characterizes AFINO 0.5 on the preregistered synthetic DEVELOPMENT domain and freezes the only rule that may later be carried into HELDOUT. All performance quantities in this report are **DEVELOPMENT synthetic-ground-truth performance**. They are not observational estimates, they are not evidence about the prevalence of QPPs in real TESS flares, and they are not final held-out validation. No new AFINO executions or synthetic-series generation were performed during closure. The scientific inputs are the already frozen F3B.2 truth/materialization records and the already frozen F3B.3 AFINO DEVELOPMENT outputs. HELDOUT remained ungenerated and inaccessible throughout F3B.4.

The primary classifier population contains exactly 3,600 eligible, contiguous, all-good, seed-0 BASELINE decisions: 1,800 synthetic QPP-positive series and 1,800 paired synthetic-null series. The 720 challenge series belong to the input-admissibility plane and do not enter sensitivity, specificity or FPR. Likewise, the 648 numerical-stability extra-seed decisions are diagnostic repeats rather than independent classifier observations. Truth is used as a target or evaluation axis where required to score DEVELOPMENT performance, but the inference rule itself receives only the two BIC differences.

## Synthetic baseline classification performance

Under the original AFINO 0.5 decision rule, `delta_BIC01 > 10 AND delta_BIC21 > 10`, with strict greater-than semantics, the DEVELOPMENT confusion matrix is TP=143, FN=1,657, TN=1,799 and FP=1. Sensitivity is 0.07944444444444444, specificity is 0.9994444444444445, FPR is 0.0005555555555555556 and balanced accuracy is 0.5394444444444445. Standard closed-form 95% Wilson intervals are attached to the binomial metrics in the frozen baseline metrics artifact and are independently reconstructed by the permanent validator.

The result describes a conservative baseline on this specific synthetic domain: false positive selection is extremely rare, while most injected positive signals are not selected by the strict baseline rule. That trade-off is precisely why a DEVELOPMENT-only candidate threshold optimization was permitted by the preregistered design. These values must not be interpreted as an observational detection efficiency, because the synthetic family, noise distributions, cadence, duration grid and QPP fractions were deliberately controlled experimental factors.

## Input admissibility and end-to-end behavior

Classifier performance and end-to-end behavior remain separate quantities. For the 3,600 primary series, input admissibility is 1.0 because every primary payload is eligible for AFINO. End-to-end positive recovery is 143/1,800 and null selection is 1/1,800. For the 720 challenge series, input admissibility is zero by construction: the challenge masks test conditions that violate the frozen AFINO input contract. Their positive and null end-to-end selection numerators are consequently zero, but these observations are not converted into false negatives or true negatives.

Across the complete planned synthetic mixture of 4,320 series, the input-admissibility fraction is 3,600/4,320. This mixture is a design-weighted synthetic summary, not an observational prevalence-weighted estimate. Maintaining these distinctions prevents input rejection from being mistaken for classifier failure and prevents challenge cases from artificially changing sensitivity or specificity.

## Empirical selection function

The primary selection-function representation is `STRATIFIED_EMPIRICAL`; no probabilistic selection model was fitted. The frozen table contains 156 rows: 36 positive base strata, 108 positive period-expanded strata and 12 pooled null strata. The positive design is stratified by sample count, red-noise exponent and injected QPP fraction. Period-expanded positive strata additionally use the three preregistered period bins. Null rows pool the paired QPP-fraction dimension rather than attempting to parse a nonexistent numeric null fraction.

Nine period-expanded cells are marked `STRUCTURAL_NO_EXPOSURE`. They are exactly the n=15, longest-period-bin combinations across the three red-noise exponents and three positive QPP fractions. Those cells have zero exposure and deliberately contain no fabricated point estimates. Positive base exposure totals 1,800 with 143 selections; the period-expanded view also totals 1,800 exposures and 143 selections; the pooled null view totals 1,800 exposures and one selection. Challenge rows are absent from this selection function.

## Period recovery

Period-recovery summaries are conditional on baseline true-positive selection. Of the 1,800 eligible positive injections, 143 are baseline true positives and all 143 have a finite recovered selected M1 period; none of the 1,657 false negatives receives an imputed period-recovery error. The median absolute period error is 0.8555459988347351 seconds, with P16=0.23207739153627158 seconds and P84=2.0874258904619793 seconds. Median relative error is 0.014847583385661523, with P16=0.0038890402253348583 and P84=0.02965191669760797.

These error summaries therefore describe accuracy conditional on successful baseline detection. The overall coverage is only 143/1,800 and must be reported alongside the error distribution. Formal M1 centers from non-selected cases are not treated as recovered periods, no missing errors are imputed, and no post-hoc “within X percent” success threshold is introduced.

## Numerical stability

The numerical-stability audit covers 72 preregistered series over ten optimizer seeds each, for 720 decisions total. Seed 0 is the baseline decision and seeds 1–9 provide 648 extra diagnostic decisions. Classification is stable for all 72 series: there are zero series with a classification state discordant from seed 0, and only two seed-0 stability-series selections.

This does not establish a unique optimizer optimum. Every stability series/model combination exhibits ten distinct parameter payloads across the ten seeds. Convergence status is `NOT_AUDITABLE` because the underlying AFINO output does not provide an auditable convergence flag. M0 produced zero warning calls and five bound calls; M1 produced zero warning calls and 400 bound calls; M2 produced 296 warning calls, 3,158 warnings and 311 bound calls. The appropriate conclusion is classification stability under the tested optimizer seeds, not parameter or optimum uniqueness.

## Candidate optimization and paired bootstrap

The candidate family was frozen to the strict conjunction `delta_BIC01 > t01 AND delta_BIC21 > t21`. The only allowed rule features were `delta_BIC01` and `delta_BIC21`. Truth was available only to score candidate outcomes in DEVELOPMENT; true period, QPP fraction, red-noise exponent and numerical-stability diagnostics were not rule features. Each threshold axis contained 7,200 finite values after frozen unique-value, midpoint and baseline-10 construction. The one-shot search therefore represented 51,840,000 full axis pairs and 12,960,000 selection-equivalent state pairs.

The single DEVELOPMENT optimum was t01=-7.517054630023225 and t21=-4.4514075428899105. It yielded TP=1,171, FN=629, TN=1,115 and FP=685, giving sensitivity 0.6505555555555556, specificity 0.6194444444444445, FPR 0.38055555555555554 and balanced accuracy 0.635. The point balanced-accuracy improvement over baseline was 0.0955555555555555. No runner-up row was written and runner-up rescue was forbidden.

Uncertainty was evaluated using the frozen paired-background bootstrap: 10,000 PCG64 replicates, 36 strata, 50 backgrounds per stratum and the `background_realization_id` as sampling unit. Positive and null members of each background travelled together. The permanent validator exactly replays all 10,000 RNG replicates and recovers the frozen global draw-stream SHA-256 `6e37f0c99c8dbc018d9be25e7530cf1aa4c6c1cf3edc0df9e6075214232cac2c`.

## Promotion gate and frozen final rule

The candidate had to pass all four preregistered criteria. Criterion 1 passed because the point balanced-accuracy gain exceeded 0.025. Criterion 2 passed because the lower 95% paired-bootstrap bound for the balanced-accuracy difference was positive; its interval was approximately [0.08611111111111114, 0.10472222222222227]. Criterion 3 passed because the lower sensitivity-difference bound was greater than -0.025; its interval was approximately [0.5533333333333333, 0.5894444444444444]. Criterion 4 (C4) failed: the specificity-difference interval was approximately [-0.3933333333333333, -0.3672222222222222], so its lower bound was far below the required -0.025 limit.

The promotion result is therefore 3/4, not 4/4. The candidate is not promoted. No alternate candidate may be searched and no runner-up may be rescued. The final frozen rule is consequently the unmodified AFINO 0.5 baseline, `delta_BIC01 > 10 AND delta_BIC21 > 10`, using strict greater-than comparisons. The correction claim is `NOT_ESTABLISHED`. Threshold mutation after freeze is forbidden.

## Final HELDOUT target and limitations

The frozen baseline rule is now the sole target intended for eventual single-use HELDOUT evaluation, but F3B.4 closure itself contains no HELDOUT results. Before any HELDOUT stochastic byte may be materialized, the complete F3B.4 closure must be independently validated, committed, tagged `phase3b-final-rule-v1`, pushed and remotely verified. HELDOUT must not be used to choose thresholds, rescue the DEVELOPMENT candidate, create new bins or modify the comparator.

The study remains limited to the preregistered synthetic family and its controlled design domain. Primary injections use the frozen stationary envelope-modulated sinusoid construction, and challenge masks test admissibility rather than classifier accuracy. Period-recovery accuracy is conditional on the small detected subset. Numerical-stability testing demonstrates classification invariance across the tested seeds but not unique parameter convergence. Finally, none of these DEVELOPMENT synthetic-ground-truth quantities is an observational validation of AFINO on real TESS flares. That distinction remains mandatory until the separately frozen HELDOUT workflow and any later observational analysis are completed.
