#!/usr/bin/env sh
set -eu

container_name=${N8N_CONTAINER:-n8n}
remote_dir=/tmp/n8n-nim-evaluation
local_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

docker exec "$container_name" mkdir -p "$remote_dir"
docker cp "$local_dir/fixtures.json" "$container_name:$remote_dir/fixtures.json"
docker cp "$local_dir/run_eval.mjs" "$container_name:$remote_dir/run_eval.mjs"
probe=no
for arg do
  if [ "$arg" = --probe ]; then probe=yes; fi
done
runner_status=0
docker exec "$container_name" node "$remote_dir/run_eval.mjs" "$@" --output "$remote_dir/results.json" || runner_status=$?
if [ "$probe" = no ]; then
  docker cp "$container_name:$remote_dir/results.json" "$local_dir/results.json"
fi
exit "$runner_status"
