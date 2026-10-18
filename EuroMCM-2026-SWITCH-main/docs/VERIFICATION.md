# Verification record

Completed on 18 October 2026.

## Original work

The original results were **not reproduced**. The remote repository was empty and the referenced simulation file was missing. The new code is a reconstruction with documented missing-detail choices, not recovery of the original implementation.

## Executed experiments

- 30 independent synthetic seed streams, 450 training and 1,200 test requests per stream.
- Nine policies, including the requested four adaptive ablations, two fixed-effort controls and three simple baselines.
- 21 one-at-a-time sensitivity and operational scenarios, each across all 30 streams and both SWITCH and the large-model comparator.
- Observed-response replay on 1,307 eligible paired GSM8K rows after 12 source contamination exclusions, with 30 saved train/validation/test splits and six comparators. Those splits overlap and are not independent model runs.
- Saved every numerical output, benchmark prediction, split assignment, scenario configuration, and synthetic workload needed to inspect the results. No model APIs or electricity meters were used.

## Checks actually run

Seven integrity tests passed. They check pinned source bytes, 30-seed and nine-policy coverage, an independent numerical calculus optimum, independently recomputed multi-call cost/energy/delay/carbon, split separation, exclusion of test labels from score construction, and per-row benchmark outcomes and call costs.

The full pipeline was executed again with `scripts/reproduce.py --verify`. All 19 pre-existing numerical result CSV/JSON files matched byte for byte. The receipt is `results/reproduction_check.json`. Plot layout was subsequently refined without altering the numerical results. This establishes repeatability of these computations, not empirical validity of their assumptions.

Every final PDF page was rendered and inspected. Mechanical checks cover page count, PDF size, a one-page summary and memo, a separate final one-page AI report, control-number/page headers, body text size, and absence of team-identifying text. `results/pdf_check.json` records the current counts and incomplete submission items. The PDF uses 12 TeX point body text (approximately 11.96 PDF points). Mathematical scripts are naturally smaller. Final plots use enlarged labels to remain readable at their printed size.

## Limits and remaining actions

The benchmark does not validate the synthetic reasoning benefit, confidence distributions, electricity values, queues, carbon scenarios or public-service quality curves. The simple real-response cascade fails its selected test-quality target in many splits. These failures are retained in the paper.

The actual nine-digit team control number is unknown and remains `000000000`. The AI report is clearly marked for the team to complete accurately; the draft is not submission-ready until those items and the filename are finalized. This work does not submit anything to EuroMCM.

Authenticated GitHub push was unavailable: a non-mutating push check returned `fatal: unable to get password from user`. GitHub Desktop UI access also timed out. Local commits and a portable repository bundle preserve the completed work; no successful remote push is claimed.
