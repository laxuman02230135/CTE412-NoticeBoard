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