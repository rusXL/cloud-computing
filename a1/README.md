# A1 Report

You can also write your report on the Gitlab (or write a PDF).

The submission should be in `a1` folder in your repository. Put all your kubernetes manifest files in `a1/manifests`, and the Collector service source code files in `a1/collector`. Do not forget to include a `Dockerfile` for the Collector service.

### Useful commands

#### Docker (local dev):

Start camera:

```bash
curl -X POST http://localhost:31100/stream \
 -H "Content-Type: application/json" \
 -d '{"destination": "http://collector/frame", "max-frames": 1}'
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
