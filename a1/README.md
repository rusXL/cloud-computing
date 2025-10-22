# IN PROGRESS... - NOT FOR ASSESMENT

# A1 Report

You can also write your report on the Gitlab (or write a PDF).

The submission should be in `a1` folder in your repository. Put all your kubernetes manifest files in `a1/manifests`, and the Collector service source code files in `a1/collector`. Do not forget to include a `Dockerfile` for the Collector service.

### Useful commands

#### Docker (local dev):

Build, tag, push

```bash
docker build -t collector:latest collector/
docker tag collector:latest rusxl/collector:latest
docker push rusxl/collector:latest
```

Start camera:

```bash
curl -X POST http://localhost:32100/stream \
 -H "Content-Type: application/json" \
 -d '{"destination": "http://collector/frame", "delay": 1, "max-frames": 1}'
```

```bash
kubectl get pods -n a1-app
kubectl logs face-recognition-57db79755b-6zmm2 -n a1-app -f
```

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Restart containers:

```bash
docker-compose down && docker-compose build && docker-compose up
```

Install new python package:

```bash
pip install FIXME && pip freeze -> collector/requirements.txt
```

#### Kubernetes (local prod)
