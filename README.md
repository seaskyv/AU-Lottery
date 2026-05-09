# AU-Lottery

A small two-tier app that generates Australian lottery numbers (OZ Lotto, Powerball, Lotto) for fun.

- **`API/`** — Python (FastAPI + Uvicorn) backend that generates the numbers. Default port `9000`.
- **`UI/`** — Node.js (Express + EJS) frontend that calls the API. Default port `8080` in containers / `3300` in local dev.

The repo-root `VERSION` file is the single source of truth for the image tag used by CI and k8s.

---

## Repository layout

```
.
├── API/                     # FastAPI service (Python)
│   ├── main.py
│   ├── lotteryGenerator.py
│   ├── mylogger.py
│   ├── config.yaml
│   ├── requirements.txt
│   └── Dockerfile
├── UI/                      # Express service (Node.js)
│   ├── app.js
│   ├── bin/www
│   ├── routes/
│   ├── views/
│   ├── public/
│   ├── config.js
│   ├── config.json
│   ├── package.json
│   └── Dockerfile
├── k8s/                     # Kubernetes manifests (namespace: au-lottery)
│   ├── namespace.yaml
│   ├── api.yaml
│   └── ui.yaml
├── .github/workflows/       # GitHub Actions: per-component image build & push
│   ├── api.yml
│   └── ui.yml
└── VERSION                  # image tag, e.g. 0.1.0
```

---

## 1. Local host deployment (no containers)

Run the API and UI directly on your machine. You will need **Python 3.10+** and **Node.js 18+**.

### 1.1 Start the API

```bash
cd API
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The API listens on `http://localhost:9000` by default (configured in `API/config.yaml`).
Override the port with the `PORT` env var:

```bash
PORT=9000 python main.py
```

Interactive OpenAPI docs are at `http://localhost:9000/docs`.

Quick smoke test:

```bash
curl "http://localhost:9000/api?game=OZLotto&magic=12345&num=2&system=7"
```

### 1.2 Start the UI

In a second terminal:

```bash
cd UI
npm install
# Point the UI at the local API (UI/config.js reads these envs):
export backendhost=localhost
export backendport=9000
export node_port=3300
npm start
```

Open `http://localhost:3300`.

> The default `UI/config.json` has `API_location: http://localhost:9090`. The
> `backendhost`/`backendport` env vars override that at runtime, so you don't
> need to edit the JSON.

---

## 2. Two-container deployment (Docker)

Build and run each component as its own container. Both images are also published to Docker Hub by CI:

- `seaskyv/au-lottery-api:<version>`
- `seaskyv/au-lottery-ui:<version>`

### 2.1 Build locally (optional)

```bash
# from repo root
docker build -t seaskyv/au-lottery-api:dev ./API
docker build -t seaskyv/au-lottery-ui:dev  ./UI
```

Or pull the published images:

```bash
docker pull seaskyv/au-lottery-api:latest
docker pull seaskyv/au-lottery-ui:latest
```

### 2.2 Run

Create a user-defined network so the UI can resolve the API by name:

```bash
docker network create au-lottery-net
```

**Run the API** (internal port `9000`, no need to publish unless you want to hit it directly):

```bash
docker run -d \
  --name au-lottery-api \
  --network au-lottery-net \
  -p 9000:9000 \
  seaskyv/au-lottery-api:latest
```

**Run the UI** and point it at the API container by name:

```bash
docker run -d \
  --name au-lottery-ui \
  --network au-lottery-net \
  -e NODE_ENV=production \
  -e backendhost=au-lottery-api \
  -e backendport=9000 \
  -e node_port=8080 \
  -p 8080:8080 \
  seaskyv/au-lottery-ui:latest
```

### 2.3 Exposing the UI port

The UI listens on container port `8080`. Use the `-p` flag to publish it on the host:

| Goal                                  | Flag                | Visit                     |
| ------------------------------------- | ------------------- | ------------------------- |
| Expose on host port **8080**          | `-p 8080:8080`      | `http://localhost:8080`   |
| Expose on host port **80** (default)  | `-p 80:8080`        | `http://localhost`        |
| Expose on a custom host port (e.g. 3000) | `-p 3000:8080`   | `http://localhost:3000`   |
| Bind only to localhost                | `-p 127.0.0.1:8080:8080` | `http://localhost:8080` |
| Listen on all interfaces (LAN)        | `-p 0.0.0.0:8080:8080`   | `http://<host-ip>:8080` |

The format is `-p <HOST_PORT>:<CONTAINER_PORT>`. The container port is fixed at `8080` (set by `EXPOSE 8080` and the `node_port` env in `UI/Dockerfile`); change the **left** side to choose the host port.

To **change the container's listening port**, override `node_port`:

```bash
docker run -d --name au-lottery-ui \
  --network au-lottery-net \
  -e node_port=9000 \
  -p 9000:9000 \
  seaskyv/au-lottery-ui:latest
```

### 2.4 Stop / clean up

```bash
docker rm -f au-lottery-ui au-lottery-api
docker network rm au-lottery-net
```

---

## 3. Kubernetes deployment

Manifests live in `k8s/`. Everything is deployed into the **`au-lottery`** namespace as two Deployments + two Services.

### 3.1 Apply

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/ui.yaml
```

### 3.2 Pin to the current VERSION

The manifests default to the `:latest` tag. For real deployments, pin to the value in `VERSION` (which is what CI tags the images with):

```bash
V=$(cat VERSION | tr -d '[:space:]')
kubectl -n au-lottery set image deploy/au-lottery-api api=seaskyv/au-lottery-api:$V
kubectl -n au-lottery set image deploy/au-lottery-ui  ui=seaskyv/au-lottery-ui:$V
```

### 3.3 Internal service wiring

The UI Pod is configured (via env vars in `k8s/ui.yaml`) to reach the API at:

```
http://au-lottery-api.au-lottery.svc.cluster.local:9000
```

### 3.4 Verify

```bash
kubectl -n au-lottery get pods,svc
kubectl -n au-lottery logs deploy/au-lottery-api
kubectl -n au-lottery logs deploy/au-lottery-ui
```

Quick port-forward to test from your laptop:

```bash
kubectl -n au-lottery port-forward svc/au-lottery-ui 8080:80
# then open http://localhost:8080
```

### 3.5 Exposing the UI externally

`au-lottery-ui` is a `ClusterIP` Service by default. Pick one of:

- **LoadBalancer** — edit `k8s/ui.yaml` and change `spec.type` to `LoadBalancer`, then `kubectl apply -f k8s/ui.yaml`. Cloud providers will allocate an external IP.
- **NodePort** — set `spec.type: NodePort` and (optionally) `spec.ports[0].nodePort: 30080`.
- **Ingress** — keep `ClusterIP` and add an Ingress that routes a hostname to `au-lottery-ui:80`.

### 3.6 Clean up

```bash
kubectl delete -f k8s/ui.yaml
kubectl delete -f k8s/api.yaml
kubectl delete -f k8s/namespace.yaml
```

---

## 4. CI / CD

Two GitHub Actions workflows in `.github/workflows/`:

- **`api.yml`** — runs only when files under `API/**` (or `VERSION`) change. Builds and pushes `seaskyv/au-lottery-api`.
- **`ui.yml`** — runs only when files under `UI/**` (or `VERSION`) change. Builds and pushes `seaskyv/au-lottery-ui`.

Each image is tagged with `:<VERSION>`, `:<git-sha>`, and `:latest` for `linux/amd64` and `linux/arm64`.

### Required GitHub repository secrets

| Secret               | Value                                                |
| -------------------- | ---------------------------------------------------- |
| `DOCKERHUB_USERNAME` | `seaskyv`                                            |
| `DOCKERHUB_TOKEN`    | A Docker Hub access token with **Read & Write** scope |

### Releasing a new version

1. Bump `VERSION` (e.g. `0.1.0` → `0.1.1`).
2. Commit & push to `main`/`master`.
3. Both workflows run (because `VERSION` changed) and publish images tagged `:0.1.1`.
4. Roll the cluster forward:

   ```bash
   V=$(cat VERSION | tr -d '[:space:]')
   kubectl -n au-lottery set image deploy/au-lottery-api api=seaskyv/au-lottery-api:$V
   kubectl -n au-lottery set image deploy/au-lottery-ui  ui=seaskyv/au-lottery-ui:$V
   ```

If you only touch one component, only that component's image is rebuilt.

---

## 5. API reference (quick)

`GET /api?game=<OZLotto|Powerball|lotto>&magic=<int>&num=<int>&system=<int>`

| Query param | Type | Description                                     |
| ----------- | ---- | ----------------------------------------------- |
| `game`      | str  | One of `OZLotto`, `Powerball`, `lotto`          |
| `magic`     | int  | Seed value mixed into the RNG                   |
| `num`       | int  | Number of game lines to generate                |
| `system`    | int  | Numbers per line (e.g. system 7, 8, ...)        |

Example:

```bash
curl "http://localhost:9000/api?game=Powerball&magic=42&num=3&system=7"
```

---

## License

See `LICENSE`.
