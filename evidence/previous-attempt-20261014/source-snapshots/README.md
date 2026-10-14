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

# Create the cluster.
kind create cluster --name cte412-02230135 --config cluster/kind-cluster.yaml

# Configure the namespace and its resource budget.
kubectl --context kind-cte412-02230135 apply -f manifests/base/00-namespace.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/base/01-resourcequota.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/base/02-limitrange.yaml

kubectl config use-context kind-cte412-02230135
kubectl config set-context kind-cte412-02230135 --namespace=nb-02230135

# Build all three release images.
docker build --build-arg APP_VERSION=1.0.0 --build-arg STUDENT_ID=02230135 -t notice-board:02230135-1.0.0 ./app
docker build --build-arg APP_VERSION=1.1.0 --build-arg STUDENT_ID=02230135 -t notice-board:02230135-1.1.0 ./app
docker build --build-arg APP_VERSION=1.2.0-broken --build-arg STUDENT_ID=02230135 -t notice-board:02230135-1.2.0-broken ./app

# Load the images without an application registry.
kind load docker-image notice-board:02230135-1.0.0 notice-board:02230135-1.1.0 notice-board:02230135-1.2.0-broken --name cte412-02230135

# Restore the final Task 8 configuration.
kubectl --context kind-cte412-02230135 apply -f manifests/bluegreen/04-feature-flags.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/bluegreen/00-blue-deployment.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/bluegreen/01-green-deployment.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/bluegreen/02-production-services.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/bluegreen/03-preview-service.yaml

kubectl --context kind-cte412-02230135 -n nb-02230135 rollout status deployment/notice-board-blue --timeout=180s
kubectl --context kind-cte412-02230135 -n nb-02230135 rollout status deployment/notice-board-green --timeout=180s

# Start monitoring after production is ready.
kubectl --context kind-cte412-02230135 apply -f manifests/base/03-monitor-code.yaml
kubectl --context kind-cte412-02230135 apply -f manifests/base/04-monitor-pod.yaml

kubectl --context kind-cte412-02230135 -n nb-02230135 wait --for=condition=Ready pod/monitor --timeout=120s

# Verify the final application.
kubectl --context kind-cte412-02230135 -n nb-02230135 get deployments,pods,services
curl.exe --noproxy "*" --fail -sS http://127.0.0.1:30090/version
curl.exe --noproxy "*" --fail -sS http://127.0.0.1:30090/notices