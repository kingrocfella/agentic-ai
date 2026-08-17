#!/bin/sh
# Restore an RDB snapshot into the Compose Redis instance. Destructive: the
# snapshot replaces the entire keyspace, including every user account.
#
#   ./scripts/restore-db.sh /absolute/path/backup.rdb --confirm
#
# Redis loads dump.rdb only at startup, so the file is written into the stopped
# container's volume and Redis is started afterwards. Writing it while Redis is
# running would be overwritten by its own snapshot on shutdown.
set -eu

if [ "$#" -ne 2 ] || [ "$2" != '--confirm' ]; then
  printf '%s\n' 'Usage: restore-db.sh /absolute/path/backup.rdb --confirm' >&2
  exit 2
fi

backup=$1
case "$backup" in
  /*) ;;
  *) printf '%s\n' 'Backup path must be absolute.' >&2; exit 2 ;;
esac
if [ ! -f "$backup" ]; then
  printf '%s\n' 'Backup file does not exist.' >&2
  exit 2
fi
if [ "$(dd if="$backup" bs=1 count=5 2>/dev/null)" != 'REDIS' ]; then
  printf '%s\n' 'Refusing to restore: file does not carry the RDB magic.' >&2
  exit 2
fi

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

# Stop the application first so nothing writes between the stop and the swap.
docker compose --project-directory "$repo_dir" stop app redis >/dev/null

# `docker compose cp` works against a stopped container, which is the point:
# the file has to be in place before Redis starts and reads it.
docker compose --project-directory "$repo_dir" cp "$backup" redis:/data/dump.rdb

docker compose --project-directory "$repo_dir" start redis >/dev/null
docker compose --project-directory "$repo_dir" start app >/dev/null

printf '%s\n' 'Restored. Verify with: docker compose exec redis redis-cli dbsize'
