#!/usr/bin/env bash
# Read-only inspection of the isolated course account namespace.
set -u
cd "$(dirname "$0")/.."
mkdir -p evidence
exec > >(tee evidence/lab-discovery.txt) 2>&1
run() { printf '\n$'; printf ' %q' "$@"; printf '\n'; "$@"; printf 'exit=%s\n' "$?"; }
run git status --short
run git log -1 --oneline
run python --version
run docker version --format '{{.Server.Version}}'
run kubectl config current-context
run kubectl get deployments,pods,services -n sn-labs-u241983
run kubectl get tasks -n sn-labs-u241983
run kubectl get clustertasks
run kubectl get serviceaccounts -n sn-labs-u241983
run kubectl get storageclasses
run kubectl get pvc -n sn-labs-u241983
run kubectl auth can-i create deployments -n sn-labs-u241983
run kubectl auth can-i create pipelineruns.tekton.dev -n sn-labs-u241983
run command -v tkn
