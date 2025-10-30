# IN PROGRESS... - NOT FOR ASSESMENT

# A1 Report

You can also write your report on the Gitlab (or write a PDF).

The submission should be in `a1` folder in your repository. Put all your kubernetes manifest files in `a1/manifests`, and the Collector service source code files in `a1/collector`. Do not forget to include a `Dockerfile` for the Collector service.

### Useful commands

Ingress

```bash
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80
```

Metrics

```bash
watch -n 1 "kubectl top pods -n a1-app"
```

Build, tag, push

```bash
docker build -t collector:latest collector/
docker tag collector:latest rusxl/collector:latest
docker push rusxl/collector:latest
```

Delete everything from manifests

```bash
kubectl delete all --all -n a1-app
kubectl delete pvc --all -n a1-app
kubectl delete configmap --all -n a1-app
kubectl delete secret --all -n a1-app
```

Start camera

```bash
curl -X POST http://localhost:8080/camera/stream \
 -H "Content-Type: application/json" \
 -d '{"destination": "http://collector/frame", "delay": 1, "max-frames": 1}'
```

Get from sections

```bash
curl -X GET "http://localhost:8080/section/persons?from=2010-10-14T11:19:18&to=2025-10-25T10:00:00&aggregate=count" \
 -H "Content-Type: application/json"
```

Debugging

```bash
kubectl get pods -n a1-app
kubectl logs section-666df4bbdf-w86jw -c FIXME_CONTAINER -n a1-app -f
```

```bash
kubectl describe pod FIXME_POD -n a1-app
```

```bash
kubectl get pv
```

Restart docker containers

```bash
docker-compose down && docker-compose build && docker-compose up
```

Install new python package

```bash
pip install FIXME && pip freeze -> collector/requirements.txt
```
