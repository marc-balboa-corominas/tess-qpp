# Manuscript 1.4 — Gate 5 referee attack test

STATUS: **PASS — all mandatory referee attacks answered only from frozen claims and limitations.**

This audit is adversarial by design. It does not add scientific claims, calculations, sources, or defenses. Each response is bounded to the frozen M1.1 claim/limitation architecture and the frozen M1.2/M1.3 evidence chain. A PASS means the manuscript can answer the attack without exceeding those boundaries; it does not mean the underlying limitation disappears.

## Machine-readable attack register

| Attack | Verdict | Claims | Limitations | Evidence planes | Sources |
|---|---|---|---|---|---|
| M14R01 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C006;M1C007 | M1L008 | M1EP04 | M1S030;M1S035;M1S036;M1S037;M1S038 |
| M14R02 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C005;M1C008;M1C010 | M1L008;M1L009 | M1EP04 | M1S030;M1S031;M1S032;M1S035;M1S036;M1S037;M1S038 |
| M14R03 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C015;M1C016 | M1L013 | M1EP05 | M1S042;M1S045;M1S046 |
| M14R04 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C013;M1C014 | M1L012 | M1EP05 | M1S039;M1S041;M1S042;M1S046 |
| M14R05 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C002;M1C012;M1C020;M1C025 | M1L003;M1L014 | M1EP02;M1EP05 | M1S004;M1S005;M1S008;M1S010;M1S015;M1S039;M1S042;M1S043;M1S045;M1S046;M1S047;M1S048 |
| M14R06 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C019;M1C020;M1C023 | M1L014 | M1EP05 | M1S043;M1S045;M1S046;M1S047;M1S048 |
| M14R07 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C021;M1C022;M1C014 | M1L015;M1L012 | M1EP05 | M1S042;M1S044;M1S045;M1S046 |
| M14R08 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C003;M1C011 | M1L004;M1L010 | M1EP02;M1EP04 | M1S006;M1S007;M1S011;M1S012;M1S015;M1S033;M1S036;M1S038 |
| M14R09 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C017;M1C018 | M1L016 | M1EP05 | M1S040;M1S041;M1S047 |
| M14R10 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C012;M1C017;M1C018 | M1L016;M1L017 | M1EP05 | M1S039;M1S040;M1S041;M1S042;M1S047;M1S048 |
| M14R11 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C028 | M1L018 | M1EP04;M1EP05;M1EP06 | M1S026;M1S027;M1S028;M1S029;M1S036;M1S046 |
| M14R12 | PASS_BOUNDED_BY_FROZEN_CLAIMS | M1C028 | M1L007;M1L018 | M1EP04;M1EP05;M1EP06 | M1S026;M1S027;M1S028;M1S029;M1S036;M1S046 |

## M14R01 — Why do 51/61 QPP references mismatch?

**Referee attack.** Why do 51/61 QPP references mismatch?

**Bounded response.** Within the frozen F3A design, 51 of 61 published-QPP references are baseline reproduction mismatches under W00/P00/seed0. The cause remains UNRESOLVED_WITHIN_F3A, so the result is treated as a reproduction limitation rather than as evidence that 51 published QPPs are physically false.

**Frozen claim mapping:** `M1C006;M1C007`  
**Frozen limitation mapping:** `M1L008`  
**Evidence planes:** `M1EP04`  
**Source IDs:** `M1S030;M1S035;M1S036;M1S037;M1S038`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R02 — Does this undermine the observational robustness result?

**Referee attack.** Does this undermine the observational robustness result?

**Bounded response.** It narrows the admissible scope of the observational robustness result. F3A perturbation claims are conditioned on baseline-concordant references, and reference-state transitions are not interpreted as observational accuracy, sensitivity, specificity, or FPR. The mismatch therefore limits which references can enter the transition analysis without converting the remaining robustness result into a physical-validation claim.

**Frozen claim mapping:** `M1C005;M1C008;M1C010`  
**Frozen limitation mapping:** `M1L008;M1L009`  
**Evidence planes:** `M1EP04`  
**Source IDs:** `M1S030;M1S031;M1S032;M1S035;M1S036;M1S037;M1S038`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R03 — Can 0/1800 null selections be called zero FPR?

**Referee attack.** Can 0/1800 null selections be called zero FPR?

**Bounded response.** No. Zero false selections were observed among 1800 HELDOUT synthetic nulls, but the finite-sample Wilson interval retains a non-zero upper bound. The result is a synthetic-domain observation and does not establish an underlying population FPR of zero.

**Frozen claim mapping:** `M1C015;M1C016`  
**Frozen limitation mapping:** `M1L013`  
**Evidence planes:** `M1EP05`  
**Source IDs:** `M1S042;M1S045;M1S046`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R04 — Why is 8.44% HELDOUT sensitivity scientifically useful?

**Referee attack.** Why is 8.44% HELDOUT sensitivity scientifically useful?

**Bounded response.** Its value is diagnostic rather than promotional: it quantifies that the frozen 10/10 baseline selects only 152 of 1800 synthetic positives in the preregistered HELDOUT domain. Together with the separately reported null result, it identifies a low-sensitivity, extremely-high-specificity synthetic operating profile and prevents a high-specificity point estimate from being mistaken for broadly effective detection.

**Frozen claim mapping:** `M1C013;M1C014`  
**Frozen limitation mapping:** `M1L012`  
**Evidence planes:** `M1EP05`  
**Source IDs:** `M1S039;M1S041;M1S042;M1S046`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R05 — Is the generator realistic enough to transport to TESS?

**Referee attack.** Is the generator realistic enough to transport to TESS?

**Bounded response.** The frozen evidence does not establish that transport. F1/F3B known-truth performance is conditional on the designed synthetic signal, noise, sampling, and stratification domain. The F3B selection surface is therefore synthetic-domain evidence, not an observational population correction; population transport requires explicit assumptions and independent later evidence.

**Frozen claim mapping:** `M1C002;M1C012;M1C020;M1C025`  
**Frozen limitation mapping:** `M1L003;M1L014`  
**Evidence planes:** `M1EP02;M1EP05`  
**Source IDs:** `M1S004;M1S005;M1S008;M1S010;M1S015;M1S039;M1S042;M1S043;M1S045;M1S046;M1S047;M1S048`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R06 — Why call this a selection function if no population correction is established?

**Referee attack.** Why call this a selection function if no population correction is established?

**Bounded response.** The term refers to the 156-row stratified empirical HELDOUT selection surface within the frozen synthetic domain: it records observed selection behavior over the preregistered strata without DEVELOPMENT pooling, smoothing, interpolation, regression, or observational transport. That bounded empirical selection function is useful as synthetic-domain characterization while correction remains NOT_ESTABLISHED.

**Frozen claim mapping:** `M1C019;M1C020;M1C023`  
**Frozen limitation mapping:** `M1L014`  
**Evidence planes:** `M1EP05`  
**Source IDs:** `M1S043;M1S045;M1S046;M1S047;M1S048`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R07 — Does conditional period accuracy hide low completeness?

**Referee attack.** Does conditional period accuracy hide low completeness?

**Bounded response.** No, provided the conditioning and coverage are reported together. Period recovery is summarized only for selected true positives with finite recovered periods, whereas overall positive selection coverage is low (152/1800 in HELDOUT). Accurate recovered periods among selected positives therefore do not imply high detection completeness.

**Frozen claim mapping:** `M1C021;M1C022;M1C014`  
**Frozen limitation mapping:** `M1L015;M1L012`  
**Evidence planes:** `M1EP05`  
**Source IDs:** `M1S042;M1S044;M1S045;M1S046`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R08 — Could optimizer multiplicity invalidate the classifier?

**Referee attack.** Could optimizer multiplicity invalidate the classifier?

**Bounded response.** The frozen evidence separates numerical multiplicity from binary decisions. Multiple numerical solutions, warnings, and bounds prevent any claim of a unique global optimum, but all 116 input-eligible F3A W00/P00 events preserve binary classification across the frozen seed grid. Thus the examined binary output is seed-stable in scope, while optimizer uniqueness remains unestablished.

**Frozen claim mapping:** `M1C003;M1C011`  
**Frozen limitation mapping:** `M1L004;M1L010`  
**Evidence planes:** `M1EP02;M1EP04`  
**Source IDs:** `M1S006;M1S007;M1S011;M1S012;M1S015;M1S033;M1S036;M1S038`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R09 — Why was the DEVELOPMENT candidate rejected?

**Referee attack.** Why was the DEVELOPMENT candidate rejected?

**Bounded response.** The preregistered DEVELOPMENT candidate failed the specificity-preservation criterion, so it was not promoted. The protocol allowed no runner-up rescue, alternate post-hoc search, or HELDOUT-based retuning; consequently the independent HELDOUT target remained the untouched AFINO 0.5 10/10 baseline.

**Frozen claim mapping:** `M1C017;M1C018`  
**Frozen limitation mapping:** `M1L016`  
**Evidence planes:** `M1EP05`  
**Source IDs:** `M1S040;M1S041;M1S047`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R10 — Was HELDOUT truly untouched before the final-rule freeze?

**Referee attack.** Was HELDOUT truly untouched before the final-rule freeze?

**Bounded response.** Within the frozen programme record, yes: threshold exploration was confined to DEVELOPMENT, the final HELDOUT target remained the strict 10/10 baseline after the candidate failed promotion, and the HELDOUT split was single-use and unavailable for later threshold development. The claim is a governance/provenance statement about the frozen workflow, not a re-analysis of HELDOUT.

**Frozen claim mapping:** `M1C012;M1C017;M1C018`  
**Frozen limitation mapping:** `M1L016;M1L017`  
**Evidence planes:** `M1EP05`  
**Source IDs:** `M1S039;M1S040;M1S041;M1S042;M1S047;M1S048`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R11 — Why were external comparators not executed?

**Referee attack.** Why were external comparators not executed?

**Bounded response.** Head-to-head comparator execution was outside the frozen F3A/F3B scientific programmes. BAII was used to constrain positioning and comparator claims, and the manuscript therefore makes no empirical method-superiority claim. Comparator disposition is documented as a limitation rather than replaced by an unexecuted benchmark.

**Frozen claim mapping:** `M1C028`  
**Frozen limitation mapping:** `M1L018`  
**Evidence planes:** `M1EP04;M1EP05;M1EP06`  
**Source IDs:** `M1S026;M1S027;M1S028;M1S029;M1S036;M1S046`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## M14R12 — What is actually new given prior TESS/QPP work?

**Referee attack.** What is actually new given prior TESS/QPP work?

**Bounded response.** The contribution is deliberately not framed as an unqualified first-ever TESS or QPP claim. Within the bounded frozen BAII corpus, the manuscript positions the work around the combined prospective architecture: a fixed public AFINO implementation followed from observational reproduction through preregistered robustness experiments to an independently held-out synthetic-ground-truth evaluation with explicit promotion gates and evidence-plane firewalls. BAII is bounded and cannot prove global novelty.

**Frozen claim mapping:** `M1C028`  
**Frozen limitation mapping:** `M1L007;M1L018`  
**Evidence planes:** `M1EP04;M1EP05;M1EP06`  
**Source IDs:** `M1S026;M1S027;M1S028;M1S029;M1S036;M1S046`  
**Verdict:** `PASS_BOUNDED_BY_FROZEN_CLAIMS`

## Gate 5 conclusion

All twelve mandatory attacks are answerable without new evidence or stronger wording. The answers preserve the central firewalls: observational reference states are not physical ground truth; synthetic HELDOUT metrics are not observational performance; 0/1800 is not population FPR=0; the selection surface is not a population correction; conditional period recovery is not completeness; optimizer stability is not unique convergence; and priority/comparator claims remain bounded by frozen BAII.
