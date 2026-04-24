# healthcabinet Helm chart

Single-chart deployment of HealthCabinet (backend, worker, frontend) with
managed Postgres, Redis and MinIO datastores and Kubernetes Gateway API
routing. Primary target: **k3s local cluster with kgateway**.

---

## Prerequisites

These are cluster-scoped concerns — install them **once per cluster**, not per chart release.

### 1. Gateway API CRDs

The upstream Gateway API v1 CRDs are not shipped by k3s out of the box.

```sh
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml
```

### 2. kgateway controller

```sh
helm install --create-namespace -n kgateway-system \
  kgateway-crds oci://cr.kgateway.dev/kgateway-dev/charts/kgateway-crds
helm install --create-namespace -n kgateway-system \
  kgateway oci://cr.kgateway.dev/kgateway-dev/charts/kgateway
```

Verify the GatewayClass exists:

```sh
kubectl get gatewayclass kgateway
```

### 3. cert-manager (only if you set `gateway.tls.enabled=true`)

```sh
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true
```

Create a ClusterIssuer (Let's Encrypt, self-signed, or whatever you need) — the chart
references it by name via `gateway.tls.certManager.issuerName` / `issuerKind`.

### 4. Local DNS

Add to `/etc/hosts` (adjust the IP to your k3s node):

```
127.0.0.1  healthcabinet.local api.healthcabinet.local
```

---

## Install

```sh
cd healthcabinet/chart
helm dependency update
# Helm 4 currently leaves OCI sub-charts as .tgz files. Extract them so
# `helm template` / `helm install` can read them:
( cd charts && for t in *.tgz; do tar -xzf "$t"; done )
```

Dev install on k3s (generates fresh app secrets):

```sh
helm upgrade --install healthcabinet . \
  --namespace healthcabinet --create-namespace \
  -f values.yaml -f values-dev.yaml \
  --set appSecrets.data.SECRET_KEY="$(openssl rand -hex 32)" \
  --set appSecrets.data.ENCRYPTION_KEY="$(python -c 'import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())')"
```

Render without installing:

```sh
helm template test . -f values.yaml -f values-dev.yaml
```

---

## Values reference (abridged)

| Key                                 | Default                                  | Meaning                                         |
|-------------------------------------|------------------------------------------|-------------------------------------------------|
| `image.registry`                    | `ghcr.io`                                | Registry prefix for backend + frontend          |
| `image.backend.repository`          | `vladtara/healthcabinet-backend`         | Backend image repo                              |
| `image.frontend.repository`         | `vladtara/healthcabinet-frontend`        | Frontend image repo                             |
| `image.backend.tag` / `.frontend.tag` | `""` (→ `.Chart.AppVersion`)           | Image tag override                              |
| `imagePullSecret.create`            | `false`                                  | Create a ghcr dockerconfigjson secret           |
| `backend.autoscaling.enabled`       | `false`                                  | Toggle HPA                                      |
| `worker.command`                    | `["arq", "app.processing.worker..."]`    | Override ARQ entrypoint                         |
| `frontend.env.PUBLIC_API_URL`       | `https://api.healthcabinet.local`        | Browser-facing API URL                          |
| `appSecrets.create`                 | `true`                                   | Generate Opaque secret from `.data`             |
| `appSecrets.existingSecret`         | `""`                                     | Reference out-of-band secret instead            |
| `gateway.enabled`                   | `true`                                   | Render Gateway + HTTPRoute                      |
| `gateway.className`                 | `kgateway`                               | GatewayClass (kgateway / traefik / cilium ...)  |
| `gateway.tls.enabled`               | `false`                                  | Issue cert-manager Certificate + HTTPS listener |
| `postgres.auth.password`            | `healthcabinet`                          | **Override in prod** via `auth.existingSecret`  |
| `minio.auth.rootPassword`           | `minioadmin`                             | **Override in prod** via `auth.existingSecret`  |
| `minio.defaultBuckets`              | `healthcabinet`                          | Buckets created by the chart at init            |
| `redis.auth.enabled`                | `false`                                  | Matches docker-compose parity                   |

Sub-chart values (`postgres.*`, `redis.*`, `minio.*`) pass through to the
CloudPirates charts — see their docs for the full surface:
<https://github.com/CloudPirates-io/helm-charts>.

---

## Uninstall

```sh
helm uninstall healthcabinet -n healthcabinet
# PVCs survive helm uninstall. Remove them explicitly:
kubectl -n healthcabinet delete pvc -l app.kubernetes.io/instance=healthcabinet
```

---

## Production notes

1. Override `postgres.auth.existingSecret` and `minio.auth.existingSecret` with
   SOPS-managed secrets — avoid plaintext passwords in values.yaml.
2. Set `appSecrets.existingSecret` to a secret produced by your secret controller
   (SOPS, External Secrets, Vault) instead of embedding data in values.
3. Flip `gateway.tls.enabled=true` and point `certManager.issuerName` at a real
   ClusterIssuer (Let's Encrypt).
4. Multi-replica rollouts: today the backend entrypoint runs `alembic upgrade head`
   at every pod start. For rolling upgrades under load, convert to a pre-upgrade
   Helm hook Job and flip `RUN_DB_MIGRATIONS_ON_STARTUP=false`.
