#!/bin/bash
set -ex

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/

kubectl wait --for=condition=ready pod -l app=directory -n cloud-storage --timeout=120s
kubectl wait --for=condition=ready pod -l app=bucket -n cloud-storage --timeout=120s

kubectl get pods -n cloud-storage

