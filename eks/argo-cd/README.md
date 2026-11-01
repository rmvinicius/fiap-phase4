# Argo CD Installation Guide

This folder contains the Helm values file to install Argo CD on an EKS cluster.

## Prerequisites

- AWS CLI configured with appropriate IAM permissions
- kubectl configured to access the EKS cluster
- Helm (>= 3.0) installed
- EKS cluster running
- Argo CD Helm chart repository added

## Installation Steps

### 1. Add the Argo CD Helm chart repository

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
```

### 2. Install Argo CD using the values file

```bash
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --values values.yaml
```

### 3. Verify the installation

```bash
kubectl get pods -n argocd
```

### 4. Access the Argo CD UI

Port-forward to access the Argo CD server locally:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:80
```

Then open http://localhost:8080 in your browser.

### 5. Login

- **Username**: `admin`
- **Password**: Retrieve with:

```bash
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d
```

## Configuration

Edit `values.yaml` to customize the deployment:

- **Server**: Replicas, service type (LoadBalancer/ClusterIP/NodePort), ingress
- **Repo Server**: Resource limits and replicas
- **Application Controller**: Replicas and resources
- **Redis**: Enable/disable built-in Redis
- **Notifications**: Enable/disable Argo CD notifications
- **ConfigMaps**: RBAC policies, timeout settings, URL configuration

## Uninstall

```bash
helm uninstall argocd -n argocd
```

## CI/CD

A GitHub Actions workflow (`../.github/workflows/argo-cd-install.yml`) is provided to install Argo CD on the EKS cluster. It triggers on:

- Push to `develop`, `staging`, `main` branches (when `eks/argo-cd/**` changes)
- Pull requests to those branches
- Manual `workflow_dispatch` with environment selection (DEV/STG/PRD)

The workflow:
1. Configures AWS credentials using environment-specific secrets
2. Configures kubectl against the EKS cluster
3. Creates the `argocd` namespace
4. Adds the Argo CD Helm chart repository
5. Installs Argo CD using this `values.yaml`

Required GitHub secrets:
- `AWS_ACCESS_KEY_ID_{DEV|STG|PRD}`
- `AWS_SECRET_ACCESS_KEY_{DEV|STG|PRD}`
- `AWS_SESSION_TOKEN_{DEV|STG|PRD}`
- `EKS_CLUSTER_NAME_{DEV|STG|PRD}`