# Campus Notice Board release strategies

Student ID: 02230135
Student name: Laxu Man Ghalley

## Purpose

Deploy the Campus Notice Board API on Kubernetes and measure availability
during Recreate, RollingUpdate, failed releases, blue/green switches and
feature-flag updates.

## Environment

- Operating system: Windows
- Docker version: TO BE RECORDED
- kind version: TO BE RECORDED
- kubectl version: TO BE RECORDED
- Cluster Kubernetes version: TO BE RECORDED
- Application language and Alpine base image: TO BE RECORDED
- Application language: Python 3.12
- Base image: python:3.12-alpine
- Application port: 8080
- Runtime user UID: 10001

### Deploy the baseline application

```powershell
kubectl --context kind-cte412-02230135 apply -f manifests/rolling/00-deployment.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/rolling/01-service.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/rolling/02-service-external.yaml

kubectl --context kind-cte412-02230135 -n nb-02230135 rollout status deployment/notice-board --timeout=180s
```

Host endpoint: http://127.0.0.1:30090/version

kubectl --context kind-cte412-02230135 apply -f manifests/base/03-monitor-code.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/base/04-monitor-pod.yaml
kubectl --context kind-cte412-02230135 -n nb-02230135 wait --for=condition=Ready pod/monitor --timeout=120s

Image: notice-board:02230135-1.1.0
Strategy: RollingUpdate
maxUnavailable: 0
maxSurge: 1
minReadySeconds: 5
progressDeadlineSeconds: 60