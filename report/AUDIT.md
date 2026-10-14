# Final validation audit - student 02230135

Validated on 14 October 2026. This corrective validation was assisted by Codex.

| Task | Validation | What was checked | Evidence in `evidence/` |
|---|---|---|---|
| 1 | PASS | Three Ready nodes, correct namespace identity and quota | t1-nodes.txt; t1-namespace.txt; t1-quota.txt; t1-context.txt |
| 2 | PASS | Three local/worker images, real warm-up and non-root endpoint checks | t2-local-images.txt; t2-worker-images.txt; t2-baseline-health.txt; t2-endpoint-checks.txt |
| 3 | PASS | Three replicas, three endpoints and host requests across multiple Pods | t3-workloads.txt; t3-endpointslices.txt; t3-host-version-responses.txt |
| 4 | PASS | Continuous monitor, 60.996-second stable recheck and shell summary | t4-at-rest-first10.txt; t4-at-rest-summary.txt; t8-monitor-continuity.txt |
| 5 | PASS | Recreate and real rolling release, history, Pod watch and mixed windows | t5-recreate-summary.txt; t5-rolling-summary.txt; t5-rollout-history.txt; t5-rolling-pod-watch.txt |
| 6 | PASS | Real deadline failure, zero-failure rollback, diff exit code zero | t6-conditions.txt; t6-failed-pods.txt; t6-monitor-summary.txt; t6-manifest-diff.txt |
| 7 | PASS | Preview and production comparison, three separately measured switches, quota | t7-preview-comparison.txt; t7-switch1-summary.txt; t7-switch2-summary.txt; t7-switch3-summary.txt; t7-quota.txt |
| 8 | PASS | False before/after ConfigMap-only update; true after replacement; zero failures | t8-existing-pod-flags.txt; t8-notices-before.txt; t8-notices-after.txt; t8-monitor-summary.txt |
| 9 | PASS | Preserved session, actual README rebuild and lab-only cleanup | t9-monitor-full.log; t9-rebuild.txt; t9-cluster-deleted.txt |

## Corrections made

- Fixed the rolling manifest's misspelled progress deadline and incorrectly nested minimum ready time.
- Replaced the namespace name placeholder with Laxu Man Ghalley.
- Corrected blue's version label to 1.0.0 and stale flag/Service comments.
- Added a short preStop delay and explicit termination grace period to application Deployments.
- Preserved the original evidence and relevant source snapshots under `evidence/previous-attempt-20261014/` before replacing canonical evidence with measured reruns.
- Repeated the warm-up, deployment, release, rollback, blue/green and feature-flag experiments. No failed old log was edited to make it pass.
- Rechecked a full minute at rest after the initial new-monitor capture contained fewer than sixty seconds of emitted samples. The corrected report states this ordering explicitly.
- Added a fail-fast final-state rebuild script, offline evidence audit, application checks and a measured report with A1-A5.
- Normalized inherited supplemental text outputs to UTF-8; their original bytes remain archived.

## Measurement limits and submission actions

Pod counts are sampled and include terminating application Pods, so they can exceed the non-terminating surge allowance. A zero failure count applies to this monitor's observed requests, not all possible clients. Full-session failures during intentional Recreate/restoration/blue-green setup remain in the full log; the individual experiment windows are stated separately.

The old Git history has no separately named Task 4 commit. Its historical timing cannot be repaired by inventing commits. Existing commits are retained, and this later corrective work is recorded separately. Submission timing and assessor interpretation remain outside the technical validation.

Review `p06-report.md`, especially its analysis/reflection and assisted-run provenance. Push the local finalization commit to GitHub and submit the repository URL on the VLE yourself. The local lab cluster is deleted; `dso202` was left running.

Run `python scripts/audit-evidence.py` to repeat the offline evidence checks. The saved successful output is `evidence/t9-final-audit.txt`.
