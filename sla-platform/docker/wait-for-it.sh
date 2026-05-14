#!/bin/sh
# wait-for-it.sh - wait for a TCP host:port to be available
# Used for container dependency ordering

set -e

host="$1"
shift
port="$1"
shift

until nc -z "$host" "$port"; do
  >&2 echo "Waiting for $host:$port..."
  sleep 1
done

>&2 echo "$host:$port is available"
exec "$@"
