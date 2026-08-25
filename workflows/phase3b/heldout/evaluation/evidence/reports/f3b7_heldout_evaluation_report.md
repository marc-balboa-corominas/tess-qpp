# Phase 3B.7 — Single-use HELDOUT baseline evaluation

## 1. Single-use boundary

Phase 3B.7 is the first and only stage in which the frozen HELDOUT blind decisions are joined to the independently generated synthetic ground truth. The classification outputs were already frozen in Phase 3B.6 before any truth inspection. This evaluation does not execute AFINO, regenerate simulations, search candidate rules, modify thresholds, refit the decision rule, or reopen DEVELOPMENT for tuning. The HELDOUT dataset is consumed as a single-use validation set at the moment the authorized truth join is performed. Any future method change would require a new independent validation dataset and a new prospective freeze.

The inference rule remains the frozen AFINO 0.5 baseline: `delta_BIC01 > 10 AND delta_BIC21 > 10`, with strict greater-than semantics and thresholds t01=t21=10. The candidate developed in DEVELOPMENT was not promoted; consequently the HELDOUT branch is BASELINE_ONLY and no candidate-versus-baseline test is performed.

## 2. Evaluator regression before unblinding

Before opening HELDOUT truth, the final evaluator was exercised against the frozen DEVELOPMENT products. It reproduced the DEVELOPMENT confusion matrix TP=143, FN=1657, TN=1799 and FP=1; sensitivity, specificity, FPR and balanced accuracy; all Wilson 95% intervals; the 156-row empirical selection-function representation with nine STRUCTURAL_NO_EXPOSURE cells; and the 143 selected-true-positive period-recovery rows. The regression therefore demonstrated that the metric implementation was not being used for the first time on HELDOUT. The evaluator, input binding, authorization, validator and tests were then frozen in a dedicated Git commit before the truth join.

## 3. Truth join

The authorized join accounts for all 4,320 HELDOUT synthetic series. Exactly 3,600 belong to the primary CONTIGUOUS_ALL_GOOD classifier plane, split prospectively into 1,800 SYNTHETIC_QPP_PRESENT and 1,800 SYNTHETIC_QPP_ABSENT series. Each of those primary eligible series has exactly one frozen BASELINE seed-0 decision. The remaining 720 series belong to the INPUT_ADMISSIBILITY challenge plane and have no classifier decision by design. They are audited separately and are never converted into false negatives or true negatives. Missing truth rows, duplicated simulation identifiers, unexpected challenge decisions and missing primary decisions are all prohibited by the evaluation gate.

## 4. Baseline HELDOUT confusion matrix

The prospective HELDOUT confusion matrix of the frozen baseline is TP=152, FN=1648, TN=1800 and FP=0. These counts sum to 1,800 synthetic-positive and 1,800 synthetic-null primary observations exactly. The result is a synthetic-ground-truth characterization of the frozen classifier in the preregistered simulation domain. It is not an observational sensitivity or specificity estimate, and it does not establish physical truth for the earlier observational catalogue labels.

## 5. Sensitivity, specificity and false-positive rate

HELDOUT sensitivity is 0.084444444444444447, specificity is 1, FPR is 0, and balanced accuracy is 0.54222222222222227. Sensitivity, specificity and FPR each report their numerator, denominator, point estimate and a separately calculated closed-form 95% Wilson score interval. Balanced accuracy is retained as the arithmetic mean of sensitivity and specificity and is not assigned a Wilson interval because it is not a single binomial proportion. Poor or strong performance cannot change the formal success branch: the preregistration explicitly treats baseline performance as a scientific result rather than an execution threshold.

## 6. End-to-end behavior and inadmissibility

Input admissibility remains separate from classifier performance. The end-to-end table reports the primary input-admissibility fraction, positive recovery fraction and null selection fraction with explicit denominators, and separately records admissibility for the 720 challenge series and their frozen gap-quality regimes. Challenge rows are not prevalence-weighted as observational frequencies. Any aggregate across the synthetic design is labelled SYNTHETIC_DESIGN_MIXTURE and NOT_OBSERVATIONAL_PREVALENCE. Numerical equality between conditional and end-to-end primary quantities can occur when all primary series are eligible, but their meanings remain distinct.

## 7. HELDOUT selection function

The primary selection function preserves the preregistered STRATIFIED_EMPIRICAL representation. It contains 36 positive base strata over n_samples, red_noise_alpha and qpp_fraction; 108 positive period-expanded strata using the frozen P40_63, P63_106 and P106_300 bins; and 12 null strata pooled only across the paired qpp_fraction label as prospectively specified. The resulting table therefore contains exactly 156 rows. Structural impossibility is retained explicitly: 9 cells are marked STRUCTURAL_NO_EXPOSURE rather than being fabricated as zero rates. Every exposed empirical proportion records its numerator and denominator and uses a 95% Wilson interval. No probabilistic selection model is fitted and no predictor, bin or pooling rule is changed after HELDOUT inspection.

## 8. Period recovery

Period recovery is computed only for eligible SYNTHETIC_QPP_PRESENT series that were selected by the frozen baseline and have a finite in-support formal M1 period estimate. The coverage numerator is 152 out of 1,800 eligible positive injections. Non-selected M1 centers are not imputed as recovered periods. For the finite selected true positives, absolute period error, relative period error and log period ratio are reported row by row; their summaries use the median and the 16th and 84th empirical percentiles under numpy.quantile with the frozen linear method. No within-X-percent recovery threshold is introduced.

## 9. HELDOUT validation gate

The predetermined branch is BASELINE_ONLY. Its success requirements are complete HELDOUT baseline characterization under the frozen metrics contract and absence of DEVELOPMENT retuning after HELDOUT generation. The evaluation records the formal state `HELDOUT_BASELINE_CHARACTERIZATION_SUCCESS` and the correction claim `NOT_ESTABLISHED`. This conclusion does not depend on whether the numerical sensitivity is high or low. There is no HELDOUT candidate comparison because `candidate_rule_promoted=false`.

## 10. Limitations

These results apply to the synthetic family and parameter domain fixed prospectively in F3B.1. The positive and null proportions are controlled experimental allocations, not observational prevalence. The empirical selection function describes the sampled synthetic domain and its frozen strata; it is not a fitted population model. The input-admissibility challenges diagnose pipeline eligibility separately from classifier discrimination. Period recovery is conditional on true-positive selection and finite M1 period availability. Numerical optimizer stability is not rerun in HELDOUT: the extra-seed stability study remains a DEVELOPMENT-only diagnostic by design.

A second limitation concerns interpretation across controlled strata. The experiment deliberately balances positive and null allocations and samples nuisance parameters according to the frozen simulation plan; therefore the unconditional mixture in this report has no direct population-frequency meaning. Stratum-specific differences may nevertheless be scientifically informative within the simulated domain, especially where cadence length, red-noise slope, QPP fraction or period support alter eligibility or selection. Those differences should be carried forward descriptively into the final Phase 3B synthesis, without using the consumed HELDOUT outcomes to redesign thresholds, merge strata, introduce new predictors or choose a different representation.

## 11. Continuing prohibitions

The consumed HELDOUT set cannot be reused to invent or tune a new classification rule. No threshold tweak, feature addition, alternate candidate search, additional optimizer seeds, new AFINO execution, generator execution or DEVELOPMENT retuning is authorized. A revised method would require a new independent validation dataset and a new prospective freeze. Phase 3B.7 therefore closes with a frozen prospective baseline characterization, not with a claim that an observational correction has been established. The broader DEVELOPMENT-to-HELDOUT synthesis and final claim matrix belong to Phase 3B.8 rather than this report.
