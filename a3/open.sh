#!/bin/bash
set -ex

kubectl port-forward svc/directory 8888:8000 -n cloud-storage
