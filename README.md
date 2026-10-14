# Campus Notice Board release strategies

Student ID: **02230135**
Student name: **Laxu Man Ghalley**

## Purpose

Measure request availability during Recreate, RollingUpdate, a failed release and rollback, blue/green production switches, and a feature-flag update. The assessed report is [report/p06-report.md](report/p06-report.md). Evidence is real command output and monitor logs under [evidence/](evidence/).

## Environment and prerequisites

The original session used Windows build 26300, Docker Desktop 4.91.0 / Engine 29.8.0, kind 0.33.0, kubectl 1.36.1, Kubernetes 1.37.0, and Git 2.55.0.windows.3. The final validation records its actual versions in `evidence/t1-software-versions.txt`; use that file if a locally installed version changes. kubectl must remain within one minor version of the cluster.

On a fresh Windows machine, install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/), [kind](https://kind.sigs.k8s.io/docs/user/quick-start/), [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/), [Git](https://git-scm.com/downloads/win), and PowerShell. Follow the Docker installer requirements for WSL 2/virtualization and restart Windows if requested. Start Docker Desktop. Allow enough Docker memory for three kind nodes and the workload; port 30090 must be free. Internet access is needed to obtain the tools and initial base/node images. No application registry is used. The application image is `python:3.12-alpine`, listens on port 8080 and runs as UID 10001. Image tags and `/version` responses contain student ID 02230135.

Clone this repository and enter it:

```powershell
git clone https://github.com/laxuman02230135/CTE412-NoticeBoard.git
Set-Location CTE412-NoticeBoard
```

## Rebuild the final state from an empty cluster

Run from the repository root. `-CreateCluster` creates exactly `cte412-02230135`; do not use that switch if it already exists. `-BuildImages` builds all three application versions from `app/`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/rebuild-final.ps1 -CreateCluster -BuildImages
```

The script is the executable command sequence: it creates the namespace/quota/LimitRange, builds and loads images, applies the true-valued flag before the green Deployment, applies both colours and production/preview Services, waits for both rollouts, creates the monitor, and verifies production `1.1.0` with pinned notice 2 first. It checks every native command's exit code. All Kubernetes operations explicitly target the lab context; unrelated clusters are not used. The script configures the lab context's default namespace without changing which unrelated context is current.

For the Task 9 namespace-only rehearsal, retain the cluster and its loaded images, namespace, quota and LimitRange, then use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/rebuild-final.ps1
```

Final objects:

- Namespace `nb-02230135`, quota and LimitRange.
- Blue Deployment: three replicas of `1.0.0`.
- Green Deployment: three replicas of `1.1.0`, `FEATURE_PINNED=true` from the ConfigMap.
- `notice-board` and `notice-board-ext`: select green; external NodePort 30090.
- `notice-board-preview`: always selects green.
- Monitor ConfigMap and Pod; monitor requests production `/version` every 0.5 seconds.

## Inspect and summarise

```powershell
kubectl --context kind-cte412-02230135 -n nb-02230135 get deployments,pods,services
curl.exe --noproxy "*" --fail -sS http://127.0.0.1:30090/version
curl.exe --noproxy "*" --fail -sS http://127.0.0.1:30090/notices

$labRoot = (Get-Location).Path
docker run --rm --mount "type=bind,source=$labRoot,target=/lab,readonly" notice-board:02230135-1.0.0 sh /lab/scripts/summarise.sh /lab/evidence/t5-rolling-log.txt
```

The shell summariser takes one log path and requires Python 3 inside its environment. Running it in the existing Alpine application image supplies both `sh` and Python. Shell scripts use LF endings via `.gitattributes`.

## Task sequence and evidence

1. Cluster, namespace, quota and limits: `t1-*`.
2. Build three releases and demonstrate warm-up/non-root execution: `t2-*`.
3. Three-replica baseline and Services: `t3-*`.
4. Continuous monitor and one-minute baseline: `t4-*`.
5. Recreate, restore baseline, RollingUpdate: `t5-*`.
6. Broken readiness, failed progress condition, imperative rollback and declarative reconciliation: `t6-*`.
7. Remove the single Deployment; start both colours; switch blue/green/blue/green: `t7-*`.
8. False flag, ConfigMap-only change, replacement green Pods: `t8-*`.
9. Preserve full log, namespace-only rebuild and cluster cleanup: `t9-*`.

`evidence/previous-attempt-20261014/` preserves the student's original attempts unchanged. The canonical top-level evidence is the corrected validation run. Do not combine counts from these different sessions. The Task 7 preparation gap is preserved in the full log but excluded from the three switch measurements. Peak Pod counts include terminating Pods and exclude the monitor; sampled counts can miss very brief peaks.

The optional `scripts/repeat-lab.py` repeats Tasks 1-8 with assertions and measurement capture. It requires Python 3.12 and an absent lab cluster, edits and applies repository manifests, and restores the final manifest files at exit. Run only when intentionally collecting a new session; archive current evidence first. It does not touch `dso202` or other cluster names. It leaves the lab cluster running for Task 9. It is a measurement helper, not the final-state rebuild script.

## Validate the saved submission evidence

After a complete measurement run and report generation, this offline check compares log counts, failure conditions, flag responses, report headings and rebuild evidence:

```powershell
python scripts/audit-evidence.py
```

The corrective validation is assisted work recorded separately from the original student attempts. Review the report, especially the analysis and reflection, before submitting it.

## Cleanup

Save all logs before running these commands. Cleanup deletes the lab cluster and its workloads; source and evidence files remain on disk.

```powershell
kubectl config set-context kind-cte412-02230135 --namespace=default
kind delete cluster --name cte412-02230135
kind get clusters
```

Commit and push after each task. Finally review the report and evidence and submit the GitHub repository URL on the VLE before the lecturer's deadline. VLE submission is manual.
