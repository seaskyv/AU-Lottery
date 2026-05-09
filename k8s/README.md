# AU-Lottery — Kubernetes Manifests

Namespace: `au-lottery`. Two services: `au-lottery-api` and `au-lottery-ui`.

## Apply

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/ui.yaml
```

## Pin to a specific version (recommended)

The manifests use the `:latest` tag for convenience. For real deployments, pin to
the value in the repo-root `VERSION` file (which is what the GitHub Actions
workflows tag the images with):

```bash
VERSION=$(cat VERSION | tr -d '[:space:]')
kubectl -n au-lottery set image deploy/au-lottery-api api=seaskyv/au-lottery-api:${VERSION}
kubectl -n au-lottery set image deploy/au-lottery-ui  ui=seaskyv/au-lottery-ui:${VERSION}
```

## Internal wiring

The UI is configured (via `backendhost` / `backendport` env vars consumed by
`UI/config.js`) to call the API at:

```
http://au-lottery-api.au-lottery.svc.cluster.local:9000
```

## External access

The UI Service is `ClusterIP`. To expose it, either:

- change `k8s/ui.yaml` Service `type` to `LoadBalancer` / `NodePort`, or
- add an Ingress resource for your cluster's ingress controller.
