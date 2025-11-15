# Maestro Kubernetes Deployment Guide

This guide provides comprehensive instructions for deploying the Maestro AI Assistant stack to Kubernetes using Kustomize and Flux CD.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Backend Image Build](#backend-image-build)
4. [Configuration](#configuration)
5. [Manual Deployment with Kustomize](#manual-deployment-with-kustomize)
6. [FluxCD GitOps Setup](#fluxcd-gitops-setup)
7. [Traefik Ingress Configuration](#traefik-ingress-configuration)
8. [Verification and Testing](#verification-and-testing)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance and Updates](#maintenance-and-updates)

---

## Prerequisites

### Required Software

1. **Kubernetes Cluster** (v1.34.1 or compatible)
   - kubeadm-based cluster
   - Minimum: 3 nodes (1 control plane, 2 workers)
   - Minimum resources per worker: 4 CPU, 8GB RAM

2. **kubectl** (v1.34.x or compatible)
   ```bash
   # Verify installation
   kubectl version --client
   ```

3. **Kustomize** (v5.0.0 or later)
   ```bash
   # Install kustomize
   curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
   sudo mv kustomize /usr/local/bin/

   # Verify installation
   kustomize version
   ```

4. **Flux CLI** (v2.0.0 or later) - For GitOps deployment
   ```bash
   # Install Flux CLI
   curl -s https://fluxcd.io/install.sh | sudo bash

   # Verify installation
   flux --version
   ```

5. **Docker or Podman** - For building the backend image
   ```bash
   # Verify Docker installation
   docker --version

   # Or Podman
   podman --version
   ```

### Optional Tools

- **Helm** (v3.x) - For Traefik installation if not already present
- **cert-manager** - For automatic TLS certificate management
- **k9s** - Terminal UI for easier cluster management

---

## Architecture Overview

The Maestro stack consists of the following components:

### Services

| Service | Type | Purpose | Exposure |
|---------|------|---------|----------|
| **PostgreSQL** | Database | Data persistence | Internal (ClusterIP) |
| **Redis** | Cache | Session & data caching | Internal (ClusterIP) |
| **MCPO** | MCP Server | Model Context Protocol server | Internal (ClusterIP) |
| **Backend** | API | Python FastAPI backend | Internal (ClusterIP) |
| **OpenWebUI** | Frontend | Web interface | External (IngressRoute) |

### Storage Requirements

| PVC Name | Size | Purpose |
|----------|------|---------|
| postgres-data | 10Gi | PostgreSQL database |
| redis-data | 5Gi | Redis persistence |
| openwebui-data | 10Gi | OpenWebUI data |
| mcpo-sandbox | 5Gi | MCPO sandbox environment |

### Network Architecture

```
Internet
    ↓
Traefik IngressRoute (maestro.example.com)
    ↓
OpenWebUI Service (ClusterIP:8080)
    ↓
┌─────────────┐
│  OpenWebUI  │
│  Container  │
└──────┬──────┘
       │
       ├─→ Backend Service (ClusterIP:8001)
       │       ↓
       │   Backend Container
       │       ↓
       ├─→ PostgreSQL Service (ClusterIP:5432)
       │       ↓
       │   PostgreSQL Container
       │       ↓
       ├─→ Redis Service (ClusterIP:6379)
       │       ↓
       │   Redis Container
       │       ↓
       └─→ MCPO Service (ClusterIP:8002)
               ↓
           MCPO Container
```

---

## Backend Image Build

The `backend` service requires a pre-built Docker image since it uses a local build context.

### Building the Backend Image

1. **Navigate to the backend directory:**
   ```bash
   cd /home/user/Maestro/backend
   ```

2. **Build the Docker image:**
   ```bash
   # Using Docker
   docker build -t maestro-backend:latest -f ../infra/docker/backend/Dockerfile .

   # Or using Podman
   podman build -t maestro-backend:latest -f ../infra/docker/backend/Dockerfile .
   ```

3. **Tag the image for your registry (if using a private registry):**
   ```bash
   # Example for Docker Hub
   docker tag maestro-backend:latest your-dockerhub-username/maestro-backend:latest

   # Example for private registry
   docker tag maestro-backend:latest registry.example.com/maestro/backend:latest
   ```

4. **Push the image to your registry:**
   ```bash
   # For Docker Hub
   docker login
   docker push your-dockerhub-username/maestro-backend:latest

   # For private registry
   docker login registry.example.com
   docker push registry.example.com/maestro/backend:latest
   ```

5. **Update the image reference in the deployment:**

   If using a custom registry, edit `k8s/base/deployment-backend.yaml`:
   ```yaml
   spec:
     containers:
     - name: backend
       image: registry.example.com/maestro/backend:latest  # Update this line
   ```

   Or use Kustomize image transformation in `k8s/base/kustomization.yaml`:
   ```yaml
   images:
     - name: maestro-backend
       newName: registry.example.com/maestro/backend
       newTag: latest
   ```

### Alternative: Load Image Directly (Development/Testing)

For development or testing on a local cluster (kind, minikube, k3s):

```bash
# For kind
kind load docker-image maestro-backend:latest --name your-cluster-name

# For minikube
minikube image load maestro-backend:latest

# For k3s (import to containerd directly)
docker save maestro-backend:latest | sudo k3s ctr images import -
```

---

## Configuration

### 1. Update Secrets

**CRITICAL:** Before deploying, update all secret values in `k8s/base/secrets.yaml`.

```bash
# Generate secure secrets
openssl rand -hex 32  # For WEBUI_SECRET_KEY
openssl rand -hex 32  # For JWT_SECRET
```

Edit `k8s/base/secrets.yaml` and replace all placeholder values:
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `MCPO_API_KEY`
- `WEBUI_SECRET_KEY`
- `JWT_SECRET`
- API keys (ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc.)

### 2. Update ConfigMaps

Edit `k8s/base/configmaps.yaml` to customize non-sensitive configuration:
- `DATABASE_URL` - Update if you changed database credentials
- `OLLAMA_HOST` - Update if using external Ollama
- `WEBUI_NAME` - Customize your application name
- Feature flags and other settings

### 3. Configure Storage

Edit `k8s/base/pvcs.yaml` to adjust storage sizes or add storage class:

```yaml
spec:
  storageClassName: your-storage-class  # e.g., "fast-ssd", "nfs-client"
  resources:
    requests:
      storage: 20Gi  # Adjust size as needed
```

### 4. Configure Ingress

Edit `k8s/base/ingressroute-openwebui.yaml`:

**Update the domain name:**
```yaml
spec:
  routes:
  - match: Host(`maestro.yourdomain.com`)  # Change this
```

**For HTTPS with cert-manager:**
```yaml
spec:
  tls:
    certResolver: letsencrypt
    # Or use a secret:
    # secretName: maestro-tls-cert
```

### 5. Volume Mounts for Backend

The backend service needs access to:
- Obsidian vault (if applicable)
- Google credentials (if using Google Cloud)

Choose one of these strategies:

**Option A: HostPath (Development only)**
```yaml
volumes:
- name: vault-data
  hostPath:
    path: /path/to/obsidian/vault
    type: Directory
```

**Option B: NFS (Recommended for production)**
```yaml
volumes:
- name: vault-data
  nfs:
    server: your-nfs-server.example.com
    path: /exports/obsidian-vault
```

**Option C: PVC with ReadWriteMany**
```yaml
volumes:
- name: vault-data
  persistentVolumeClaim:
    claimName: obsidian-vault
```

Update `k8s/base/deployment-backend.yaml` accordingly.

---

## Manual Deployment with Kustomize

### 1. Validate the Configuration

```bash
# Validate Kustomize build
cd /home/user/Maestro
kustomize build k8s/ > /tmp/maestro-manifests.yaml

# Review the generated manifests
less /tmp/maestro-manifests.yaml

# Validate with kubectl
kubectl apply --dry-run=client -f /tmp/maestro-manifests.yaml
```

### 2. Deploy to Kubernetes

```bash
# Apply the manifests
kubectl apply -k k8s/

# Or use the generated file
kubectl apply -f /tmp/maestro-manifests.yaml
```

### 3. Monitor the Deployment

```bash
# Watch namespace resources
kubectl get all -n maestro -w

# Check pod status
kubectl get pods -n maestro

# View logs for specific pod
kubectl logs -n maestro -f deployment/backend
kubectl logs -n maestro -f deployment/openwebui
kubectl logs -n maestro -f deployment/postgres

# Check persistent volume claims
kubectl get pvc -n maestro

# Check ingress route
kubectl get ingressroute -n maestro
```

### 4. Verify Services are Running

```bash
# Check all deployments are ready
kubectl get deployments -n maestro

# Expected output:
# NAME        READY   UP-TO-DATE   AVAILABLE
# backend     1/1     1            1
# mcpo        1/1     1            1
# openwebui   1/1     1            1
# postgres    1/1     1            1
# redis       1/1     1            1
```

---

## FluxCD GitOps Setup

### 1. Install Flux on Your Cluster

```bash
# Check prerequisites
flux check --pre

# Bootstrap Flux (GitHub example)
flux bootstrap github \
  --owner=your-github-username \
  --repository=maestro-config \
  --branch=main \
  --path=clusters/production \
  --personal
```

### 2. Create a GitRepository Resource

Create `flux/gitrepository.yaml`:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: maestro
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/your-org/maestro
  ref:
    branch: main
  # For private repositories:
  # secretRef:
  #   name: maestro-git-credentials
```

Apply it:
```bash
kubectl apply -f flux/gitrepository.yaml
```

### 3. Create a Kustomization Resource

Create `flux/kustomization.yaml`:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: maestro
  namespace: flux-system
spec:
  interval: 5m
  path: ./k8s
  prune: true
  sourceRef:
    kind: GitRepository
    name: maestro
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: postgres
      namespace: maestro
    - apiVersion: apps/v1
      kind: Deployment
      name: backend
      namespace: maestro
    - apiVersion: apps/v1
      kind: Deployment
      name: openwebui
      namespace: maestro
  timeout: 10m
  # Handle dependencies
  dependsOn:
    - name: traefik  # If Traefik is managed by Flux
```

Apply it:
```bash
kubectl apply -f flux/kustomization.yaml
```

### 4. Monitor Flux Reconciliation

```bash
# Watch Flux resources
flux get sources git
flux get kustomizations

# Check reconciliation status
flux reconcile source git maestro
flux reconcile kustomization maestro

# View logs
flux logs --follow --all-namespaces
```

### 5. Sealed Secrets (For Production)

For production, use Sealed Secrets instead of plain secrets in Git:

```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Install kubeseal CLI
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar xfz kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal

# Create a sealed secret
kubectl create secret generic maestro-secrets \
  --from-literal=POSTGRES_PASSWORD=your-password \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > k8s/base/sealed-secrets.yaml

# Replace secrets.yaml with sealed-secrets.yaml in kustomization
```

---

## Traefik Ingress Configuration

### 1. Install Traefik (if not already installed)

#### Option A: Using Helm

```bash
# Add Traefik Helm repository
helm repo add traefik https://traefik.github.io/charts
helm repo update

# Install Traefik
helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  --set ports.web.expose=true \
  --set ports.websecure.expose=true \
  --set ports.websecure.tls.enabled=true
```

#### Option B: Using Flux

Create `flux/traefik-helmrelease.yaml`:

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: traefik
  namespace: traefik
spec:
  interval: 5m
  chart:
    spec:
      chart: traefik
      version: '25.0.0'
      sourceRef:
        kind: HelmRepository
        name: traefik
        namespace: flux-system
  values:
    ports:
      web:
        expose: true
      websecure:
        expose: true
        tls:
          enabled: true
```

### 2. Verify Traefik Installation

```bash
# Check Traefik pods
kubectl get pods -n traefik

# Check Traefik service
kubectl get svc -n traefik

# Get Traefik external IP
kubectl get svc traefik -n traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### 3. Configure DNS

Point your domain to the Traefik LoadBalancer IP:

```bash
# Get the external IP
TRAEFIK_IP=$(kubectl get svc traefik -n traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Create DNS A record
# maestro.example.com -> $TRAEFIK_IP
```

### 4. Install cert-manager (for automatic TLS)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: traefik
EOF
```

### 5. Update IngressRoute for TLS

Edit `k8s/base/ingressroute-openwebui.yaml`:

```yaml
spec:
  tls:
    certResolver: letsencrypt-prod
```

---

## Verification and Testing

### 1. Check Pod Status

```bash
# All pods should be Running
kubectl get pods -n maestro

# Check pod events if any issues
kubectl describe pod -n maestro <pod-name>
```

### 2. Test Internal Connectivity

```bash
# Test from OpenWebUI pod to backend
kubectl exec -n maestro deployment/openwebui -- curl -s http://backend:8001/health

# Test from backend to postgres
kubectl exec -n maestro deployment/backend -- pg_isready -h postgres -p 5432

# Test from backend to redis
kubectl exec -n maestro deployment/backend -- redis-cli -h redis -p 6379 ping
```

### 3. Check Logs

```bash
# Backend logs
kubectl logs -n maestro -f deployment/backend

# OpenWebUI logs
kubectl logs -n maestro -f deployment/openwebui

# PostgreSQL logs
kubectl logs -n maestro -f deployment/postgres

# Check for errors
kubectl logs -n maestro deployment/backend | grep -i error
```

### 4. Test External Access

```bash
# Test HTTP access
curl http://maestro.example.com

# Test HTTPS access
curl https://maestro.example.com

# Check TLS certificate
openssl s_client -connect maestro.example.com:443 -servername maestro.example.com
```

### 5. Access the Application

Open your browser and navigate to:
- HTTP: `http://maestro.example.com`
- HTTPS: `https://maestro.example.com`

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Pods in CrashLoopBackOff

```bash
# Check pod logs
kubectl logs -n maestro <pod-name> --previous

# Check events
kubectl describe pod -n maestro <pod-name>

# Common causes:
# - Missing secrets or config
# - Database not ready (check init containers)
# - Image pull errors
```

#### 2. Backend Cannot Connect to Database

```bash
# Verify database is running
kubectl get pod -n maestro -l app=postgres

# Check database logs
kubectl logs -n maestro deployment/postgres

# Verify secret values
kubectl get secret -n maestro maestro-secrets -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d

# Test connection manually
kubectl exec -n maestro deployment/postgres -- psql -U maestro -d maestro -c "SELECT 1"
```

#### 3. Image Pull Errors

```bash
# Check image pull secrets
kubectl get pods -n maestro -o jsonpath='{.items[*].spec.imagePullSecrets}'

# For private registries, create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your-email@example.com \
  -n maestro

# Add to deployment
# spec:
#   imagePullSecrets:
#   - name: regcred
```

#### 4. PVC Not Binding

```bash
# Check PVC status
kubectl get pvc -n maestro

# Check PV availability
kubectl get pv

# Check storage classes
kubectl get storageclass

# Describe PVC for events
kubectl describe pvc -n maestro postgres-data

# Solution: Specify correct storageClassName in pvcs.yaml
```

#### 5. Ingress Not Working

```bash
# Check IngressRoute status
kubectl get ingressroute -n maestro

# Check Traefik logs
kubectl logs -n traefik deployment/traefik

# Verify Traefik can see the IngressRoute
kubectl get ingressroute -n maestro -o yaml

# Check middleware
kubectl get middleware -n maestro
```

#### 6. Service Not Accessible

```bash
# Check service endpoints
kubectl get endpoints -n maestro

# Verify label selectors match
kubectl get pods -n maestro --show-labels
kubectl get svc -n maestro openwebui -o yaml | grep selector -A 3

# Test service from another pod
kubectl run -it --rm debug --image=alpine --restart=Never -- sh
# Inside the pod:
# wget -O- http://openwebui.maestro.svc.cluster.local:8080
```

### Debug Commands Reference

```bash
# Get all resources in namespace
kubectl get all -n maestro

# Describe all resources
kubectl describe all -n maestro

# Get events sorted by time
kubectl get events -n maestro --sort-by='.lastTimestamp'

# Port forward for local testing
kubectl port-forward -n maestro svc/openwebui 8080:8080
# Then access http://localhost:8080

# Execute shell in pod
kubectl exec -it -n maestro deployment/backend -- /bin/bash

# Copy files from/to pod
kubectl cp maestro/backend-pod:/app/logs/app.log ./local-app.log

# Check resource usage
kubectl top pods -n maestro
kubectl top nodes
```

---

## Maintenance and Updates

### Updating Application Images

#### Manual Update

```bash
# Update image in deployment
kubectl set image deployment/backend backend=maestro-backend:v2.0.0 -n maestro

# Or patch the deployment
kubectl patch deployment backend -n maestro -p '{"spec":{"template":{"spec":{"containers":[{"name":"backend","image":"maestro-backend:v2.0.0"}]}}}}'

# Restart deployment
kubectl rollout restart deployment/backend -n maestro
```

#### With Kustomize

Update `k8s/base/kustomization.yaml`:
```yaml
images:
  - name: maestro-backend
    newName: registry.example.com/maestro/backend
    newTag: v2.0.0
```

Apply:
```bash
kubectl apply -k k8s/
```

#### With Flux (GitOps)

Commit and push changes to your Git repository. Flux will automatically apply them:
```bash
git add k8s/base/kustomization.yaml
git commit -m "Update backend image to v2.0.0"
git push origin main

# Force immediate reconciliation
flux reconcile source git maestro
flux reconcile kustomization maestro
```

### Scaling Services

```bash
# Scale OpenWebUI for high availability
kubectl scale deployment openwebui --replicas=3 -n maestro

# Scale backend
kubectl scale deployment backend --replicas=2 -n maestro

# View current replicas
kubectl get deployment -n maestro
```

### Backup and Restore

#### PostgreSQL Backup

```bash
# Create backup
kubectl exec -n maestro deployment/postgres -- pg_dump -U maestro maestro > maestro-backup-$(date +%Y%m%d).sql

# Or use a CronJob for automated backups
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: maestro
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:16-alpine
            command:
            - /bin/sh
            - -c
            - pg_dump -h postgres -U \$POSTGRES_USER \$POSTGRES_DB > /backup/maestro-\$(date +%Y%m%d-%H%M%S).sql
            env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: maestro-secrets
                  key: POSTGRES_USER
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: maestro-secrets
                  key: POSTGRES_DB
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: maestro-secrets
                  key: POSTGRES_PASSWORD
            volumeMounts:
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: postgres-backup
EOF
```

#### PostgreSQL Restore

```bash
# Restore from backup
kubectl cp maestro-backup-20250101.sql maestro/postgres-pod:/tmp/backup.sql
kubectl exec -n maestro deployment/postgres -- psql -U maestro maestro < /tmp/backup.sql
```

### Monitoring

#### Install Prometheus and Grafana (Optional)

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Username: admin, Password: prom-operator
```

### Uninstalling

```bash
# Delete all resources
kubectl delete -k k8s/

# Or delete namespace (which deletes all resources)
kubectl delete namespace maestro

# Delete PVCs (if needed)
kubectl delete pvc -n maestro --all

# Note: This will DELETE ALL DATA
```

---

## Security Best Practices

1. **Always use secrets management:**
   - Use Sealed Secrets or external secrets operators
   - Never commit plain secrets to Git

2. **Enable network policies:**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: maestro-network-policy
     namespace: maestro
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: maestro
   ```

3. **Use resource limits:**
   - Already configured in deployments
   - Adjust based on your workload

4. **Enable Pod Security Standards:**
   ```bash
   kubectl label namespace maestro pod-security.kubernetes.io/enforce=baseline
   ```

5. **Regular updates:**
   - Keep images up to date
   - Monitor for security vulnerabilities
   - Use image scanning tools

---

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Flux CD Documentation](https://fluxcd.io/docs/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [PostgreSQL on Kubernetes](https://www.postgresql.org/docs/)

---

## Support and Contributing

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review pod logs and events
3. Open an issue in the project repository

---

**Last Updated:** 2025-11-15
**Version:** 1.0.0
