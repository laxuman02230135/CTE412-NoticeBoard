# CTE412 assessed lab: Campus Notice Board releases

Student: **Laxu Man Ghalley**
Student ID: **02230135**
Validation date: **14 October 2026**

## 1. Objective

Deploy the Campus Notice Board API to a three-node kind cluster and measure how release choices affect successful requests. Compare Recreate and RollingUpdate, observe a readiness failure and rollback, switch between prepared blue/green releases, and enable pinned-first notice ordering without building another image.

The original student attempts are preserved under `evidence/previous-attempt-20261014/`. They exposed invalid manifest fields and incomplete measurements. The results below use the corrected, assisted validation run in the top-level evidence directory, rather than relabelling unsuccessful earlier attempts as successful.

## 2. Environment

Windows build 26300; Docker Desktop 4.91.0 / Docker Engine 29.8.0; kind 0.33.0; kubectl 1.36.1; cluster Kubernetes 1.37.0; Git 2.55.0.windows.3. The kubectl client is one minor version behind the server. The application uses Python 3.12 on `python:3.12-alpine`, runs as UID 10001 and listens on port 8080. See `t1-software-versions.txt`, `t1-nodes.txt`, `t2-local-images.txt` and `t2-container-user.txt`.

Cluster `cte412-02230135` has one control-plane and two workers. Host loopback port 30090 maps to NodePort 30090. Namespace `nb-02230135` carries the required practical labels and full-name annotation (`t1-namespace.txt`). Its quota is 1 CPU/1Gi requested, 2 CPUs/2Gi limited, 15 Pods and four Services (`t1-quota.txt`). Application images are built once per version from one source tree and loaded directly into kind (`t2-image-load.txt`, `t2-worker-images.txt`). Workload images are Alpine-based and have `imagePullPolicy: Never`; kind's infrastructure node image is provided by kind.

The fresh local-container check demonstrates health 503 before five seconds and 200 after five seconds for the baseline (`t2-baseline-health.txt`). `t2-endpoint-checks.txt` checks all release/flag combinations, including permanently failing health with functioning version/notices endpoints for the broken image.

## 3. Results

| Release | Requests observed | Failed requests | Observed mixed-version window (seconds) | Peak notice-board Pods observed |
|---|---:|---:|---:|---:|
| Recreate 1.0.0 to 1.1.0 | 100 | 25 | 0.000 | 3 |
| RollingUpdate 1.0.0 to 1.1.0 | 144 | 0 | 35.498 | 5 |
| Broken release and rollback | 166 | 0 | 0.000 | 4 |
| Blue/green switch 1: blue to green | 43 | 0 | 0.000 | 6 |
| Blue/green switch 2: green to blue | 43 | 0 | 0.000 | 6 |
| Blue/green switch 3: blue to green | 44 | 0 | 0.000 | 6 |
| Feature flag false to true | 156 | 0 | 0.000 | 8 |

Counts are calculated from saved monitor logs with `scripts/summarise.sh`. Mixed-version windows use the first new-version response through the last subsequently observed old-version response, or zero when no interleaving was observed. This is a sampling estimate, not an exact measure of simultaneous endpoint availability. A zero-failure result applies only to the requests and timeout observed.

Peak counts include terminating application Pods, exclude the monitor and are sampled about once per second. They may miss shorter peaks. Detailed counts and Pod identities are in `t5-*-pod-samples.json`, `t6-monitor-pod-samples.json`, `t7-switchN-pod-samples.json` and `t8-monitor-pod-samples.json`. The RollingUpdate watch provides additional event evidence (`t5-rolling-pod-watch.txt`).

Evidence for table rows: `t5-recreate-summary.txt`, `t5-rolling-summary.txt`, `t6-monitor-summary.txt`, `t7-switch1-summary.txt`, `t7-switch2-summary.txt`, `t7-switch3-summary.txt` and `t8-monitor-summary.txt`. `t9-results.json` records the capture boundaries and derived values. Each Task 5 window includes more than ten seconds before apply and after rollout completion. Each blue/green switch has its own window and event timestamps, avoiding a misleading mixed-window calculation across three opposite-direction switches.

The one-minute at-rest check is in `t4-at-rest-log.txt`, `t4-at-rest-first10.txt` and `t4-at-rest-summary.txt`. The final baseline was rechecked on stable green 1.1.0 after the releases because the initial new-monitor capture began before its first output and contained less than a minute of actual samples. The same monitor Pod remained running during Tasks 4-8 (`t4-monitor-uid.txt`, `t8-monitor-continuity.txt`). Its complete session is `t9-monitor-full.log`. The mandatory Task 7 preparation removes the single Deployment before starting both colours; that setup outage is retained in the full log but excluded from the three switch windows.

## 4. Analysis

### A1. Rank strategies by failed requests and explain the mechanism

Recreate had 25 failed requests out of 100, the highest measured count. Old replicas were removed before the new replicas became ready; the readiness probe then withheld the new Pods during warm-up. Failed monitor lines and the transition from old to new responses are in `t5-recreate-log.txt`. No old/new response interleaving was observed.

RollingUpdate had 0 failures out of 144. It retained available old replicas while adding one replacement at a time, waiting for readiness and the extra five-second minimum ready interval. Its measured mixed-version interval was 35.498 seconds (`t5-rolling-log.txt`, `t5-rolling-mixed-window.txt`, `t5-rolling-pod-watch.txt`).

The broken release/rollback, all three prepared blue/green switches and the feature-flag rollout tied at zero observed failures. The broken Pod never became a ready endpoint; production stayed on healthy 1.1.0 Pods. Blue/green changed Service selection between already-ready groups rather than waiting for an image to start. The flag rollout reused RollingUpdate's availability protection. See the corresponding logs/summaries listed in Section 3, plus `t6-failed-pods.txt` and `t7-preview-comparison.txt`.

### A2. Broken-release protection and predictions for default fields

`readinessProbe.httpGet.path: /healthz` excludes the broken Pod from ready endpoints. `strategy.type: RollingUpdate`, `maxUnavailable: 0` and `maxSurge: 1` preserve three old ready replicas and allow one unready candidate. `minReadySeconds: 5` requires sustained readiness. `progressDeadlineSeconds: 60` reports the stalled rollout; it does not automatically roll it back. Kubernetes reported **Progressing=False, reason=ProgressDeadlineExceeded** (`t6-conditions.txt`, `t6-failed-rollout.txt`). The recorded manual rollback restored the previous revision, and `kubectl diff` returned zero after the repository was reconciled (`t6-rollback.txt`, `t6-manifest-diff.txt`).

The liveness probe checks `/version`, not `/healthz`: this keeps the deliberately unready process running for diagnosis. `imagePullPolicy: Never` prevents registry access. Explicit resources leave room for the surge candidate. A two-second `preStop` delay keeps the process serving while endpoint removal propagates; `terminationGracePeriodSeconds: 10` allows it to finish. These settings are in `manifests/rolling/00-deployment.yaml` and `t6-broken-manifest.yaml`.

Predictions when individual fields are omitted:

- Deployment strategy defaults to RollingUpdate. Its 25% unavailable rounds down to zero for three replicas; 25% surge rounds up to one. For this particular replica count, those defaults give the same numerical availability allowance. Zero failures would still be expected in this controlled broken-readiness experiment, rather than an assumed outage.
- Without readiness probing, the broken release can receive traffic. However, this monitor checks `/version`, which the broken image deliberately still serves successfully. It could therefore still record zero failures while missing the health defect. Zero request failures alone do not prove correct readiness isolation.
- `minReadySeconds` defaults to zero. The five-second health warm-up still applies, but there is no additional stability interval. Zero failures remain plausible in this application, with less protection against a Pod failing immediately after becoming ready.
- The progress deadline defaults to 600 seconds. Failure detection would take longer; healthy old Pods could continue serving and the monitor could still see zero failures.
- No liveness probe means Kubernetes performs no liveness-based restart. It would not inherently break `/version` in this example. Using `/healthz` for liveness instead would repeatedly restart the deliberately broken image.
- For this non-latest image tag, omitted pull policy defaults to IfNotPresent. Loaded images could still work, but a missing local image could trigger a forbidden registry pull. Resource omissions would use the namespace's LimitRange defaults, changing the budget rather than proving a request outage.

These are predictions from documented defaults and the application's endpoint behaviour, not extra experiments. See References [1], [2] and [5].

### A3. RollingUpdate versus blue/green

RollingUpdate's measured mixed window was 35.498 seconds. The three blue/green windows were 0.000, 0.000 and 0.000 seconds. Selection changes can propagate asynchronously, so even a zero observed window is not a guarantee of atomic switching (`t7-switchN-log.txt` and `t7-switch-events.txt`).

The rolling measurement observed 4 non-terminating application Pods and 5 total including terminating Pods. Four application Pods plus the monitor budget 210m CPU/272Mi requested and 450m CPU/576Mi limited; the observed five-Pod total plus monitor budgets 260m/336Mi requested and 550m/704Mi limited. Six application Pods plus the monitor require 310m/400Mi requested and 650m/832Mi limited; both colours therefore use more steady resources but remain below the quota. During the flag rollout, a seventh application Pod fits at 360m/464Mi requested and 750m/960Mi limited. The flag measurement observed 8 total application Pods including terminating ones: eight application Pods plus monitor budget 410m/528Mi requested and 850m/1088Mi limited, also below quota. Terminating Pods can briefly add resource use beyond the active surge count. `t7-quota.txt` and the per-experiment Pod samples show the observed state.

The failed-release rollback command through completed rollback took 0.293 seconds in this run; it was unusually quick because the old replicas were still serving. Blue/green's reverse switch reused the ready blue replicas; the first sampled blue response appeared 0.476 seconds after its apply began. These are different timing boundaries, so they are not an exact speed benchmark. A normal rolling rollback after all old Pods have been removed may need replacements to warm up. See `t6-monitor-events.txt` and `t7-switch2-events.txt`.

### A4. When Recreate is appropriate

Recreate can be appropriate when old and new versions cannot safely run together, for example a single-writer maintenance service using an incompatible on-disk data format. Stopping the old writer before the new one starts avoids conflicting access. A planned maintenance window, backups and a verified migration/rollback plan would be needed. The trade-off is the measured service gap illustrated by `t5-recreate-log.txt`; this lab does not itself implement such a migration.

### A5. What the feature flag changed and did not avoid

The flag changed notice ordering so that pinned notice 2 appeared first, and changed `pinnedFirst` from false to true, without a new image (`t8-notices-before.txt`, `t8-notices-after.txt`). Changing the ConfigMap alone left the existing Pods' environment values false and the response unchanged (`t8-existing-pod-flags.txt`, `t8-notices-after-configmap-only.txt`). Changing `spec.template.metadata.annotations.cte412/flag-revision` caused replacement green Pods to read true (`t8-new-pod-flags.txt`). It avoided an image rebuild but did not avoid a Pod rollout. `/version` remained 1.1.0 throughout, so an image-version mixed window of zero does not imply every Pod used the same flag during replacement. See Reference [3].

## 5. Reflection

The original run's `t6-manifest-diff.txt`, preserved under `previous-attempt-20261014/`, reported unknown `spec.postgressDeadlineSeconds` and incorrectly nested `spec.strategy.minReadySeconds`, followed by diff exit code 1. Those messages revealed that the intended rollout settings were not applied. The fix used `spec.progressDeadlineSeconds` and placed `minReadySeconds` directly under `spec`, followed by a fresh broken-release experiment requiring the actual failure condition and diff exit code zero. Similarly, earlier flag evidence already had true in the supposed before state; the corrected experiment explicitly verifies false before changing only the ConfigMap. Original outputs were retained rather than edited into passing evidence.

One remaining uncertainty is how much very brief routing overlap or failure the 0.5-second request sampling and approximately one-second Pod sampling miss. The measured zero-failure results do not resolve that uncertainty; denser monitoring and repeated trials would be needed.

The README's final-state sequence was exercised after removing the namespace workloads while retaining the namespace, quota and LimitRange. `t9-rebuild.txt` records recreation and final endpoint checks. `t9-cluster-deleted.txt` records cleanup of only `cte412-02230135`; the unrelated cluster was retained. The report and evidence must be reviewed before submission. Earlier commits preserve the student's task progression; this assisted validation is a later corrective run.

## 6. References

Documentation consulted during validation; accessed **14 October 2026**.

1. Kubernetes, [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — strategies, readiness intervals, deadline conditions, rollback and terminating Pods.
2. Kubernetes, [Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/) — traffic eligibility versus container restarts.
3. Kubernetes, [Updating Configuration via a ConfigMap](https://kubernetes.io/docs/tutorials/configuration/updating-configuration-via-a-configmap/) — existing environment variables and replacement Pods.
4. kind, [Quick Start](https://kind.sigs.k8s.io/docs/user/quick-start/) and [Configuration](https://kind.sigs.k8s.io/docs/user/configuration/) — local image loading and host port mapping.
5. Kubernetes, [Images](https://kubernetes.io/docs/concepts/containers/images/) — local images and pull-policy defaults.
6. Docker, [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) — build arguments and non-root USER.
