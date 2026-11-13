#!/usr/bin/env bash
# Deploy only this account-service project into its pre-provisioned teaching namespace.
set -euo pipefail
cd "$(dirname "$0")/.."
NAMESPACE=sn-labs-u241983
IMAGE=us.icr.io/sn-labs-u241983/accounts:1.0
mkdir -p evidence
case "${1:-}" in
  image)
    docker build -t "$IMAGE" . 2>&1 | tee evidence/docker-build.txt
    docker image ls --no-trunc --format 'Name={{.Repository}} Tag={{.Tag}} ID={{.ID}} Created={{.CreatedAt}} Size={{.Size}}' "$IMAGE" | tee evidence/kube-images.txt
    docker push "$IMAGE" 2>&1 | tee evidence/docker-push.txt
    ;;
  kubernetes)
    # The course's OpenShift template provides a compatible image and generated database Secret.
    if ! oc -n "$NAMESPACE" get service postgresql >/dev/null 2>&1; then
      oc -n "$NAMESPACE" new-app postgresql-ephemeral
    fi
    sed "s|IMAGE_NAME_HERE|$IMAGE|g" deploy/deployment.yaml | kubectl -n "$NAMESPACE" apply -f -
    kubectl -n "$NAMESPACE" rollout status deployment/accounts --timeout=180s
    kubectl -n "$NAMESPACE" get deployment/accounts -o wide | tee evidence/kube-deploy-accounts.txt
    kubectl -n "$NAMESPACE" get pods,replicasets,services -l app=accounts -o wide | tee -a evidence/kube-deploy-accounts.txt
    ;;
  pipeline)
    # Existing lab service-account and buildah ClusterTask are prerequisites; never create broad permissions.
    kubectl -n "$NAMESPACE" get serviceaccount pipeline >/dev/null
    kubectl get clustertask buildah >/dev/null
    kubectl get clustertask openshift-client >/dev/null
    kubectl -n "$NAMESPACE" apply -f tekton/pvc.yaml
    kubectl -n "$NAMESPACE" apply -f tekton/tasks.yaml
    kubectl -n "$NAMESPACE" apply -f tekton/pipeline.yaml
    kubectl -n "$NAMESPACE" create -f tekton/pipelinerun.yaml -o name | tee evidence/pipelinerun-name.txt
    ;;
  *) printf 'Usage: bash bin/lab-deploy-accounts.sh image|kubernetes|pipeline\n' >&2; exit 2 ;;
esac
