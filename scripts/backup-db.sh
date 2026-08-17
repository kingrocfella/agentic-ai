#!/bin/sh
# Create one validated, mode-0600 RDB snapshot of the Compose Redis instance,
# then prune the backup directory down to the newest BACKUP_RETENTION snapshots
# (default 2). Pruning runs only after the new snapshot has been written and
# verified, so a failed backup never destroys the copies that already exist.
#
#   ./scripts/backup-db.sh [backup_dir]
#   BACKUP_RETENTION=5 ./scripts/backup-db.sh
#
# Redis is not a cache here — it is this app's ONLY durable store. The
# `user:<email>` records written by app/routes/auth.py carry no TTL, so losing
# this volume loses every account. That is why an app with no SQL database
# still has a backup script.
#
# `redis-cli --rdb` asks the server for a fresh point-in-time dump and streams
# it out, rather than copying dump.rdb off disk mid-write.
#
# Local files are not disaster recovery: copy each snapshot off-host and apply
# retention there too.
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
backup_dir=${1:-"$repo_dir/backups"}
retention=${BACKUP_RETENTION:-2}
timestamp=$(date -u '+%Y%m%dT%H%M%SZ')
output="$backup_dir/agentic-ai-$timestamp.rdb"
temporary="$output.incomplete"

case "$retention" in
  '' | *[!0-9]*)
    printf '%s\n' "BACKUP_RETENTION must be a whole number, got '$retention'." >&2
    exit 2
    ;;
  0)
    printf '%s\n' 'BACKUP_RETENTION must be at least 1.' >&2
    exit 2
    ;;
esac

umask 077
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
trap 'rm -f "$temporary"' EXIT HUP INT TERM

docker compose --project-directory "$repo_dir" exec -T redis \
  redis-cli --no-auth-warning --rdb - >"$temporary"

# Every RDB file begins with the ASCII magic "REDIS" followed by a 4-digit
# version. Checking it catches the case where redis-cli wrote an error message
# to stdout and still exited 0.
if [ ! -s "$temporary" ] || [ "$(dd if="$temporary" bs=1 count=5 2>/dev/null)" != 'REDIS' ]; then
  printf '%s\n' 'Snapshot failed validation: not an RDB file.' >&2
  exit 1
fi

mv "$temporary" "$output"
trap - EXIT HUP INT TERM
chmod 600 "$output"

# Snapshot names carry a UTC basic-format timestamp, so a reverse lexicographic
# sort is newest-first regardless of mtime — which a copy, rsync, or restore
# rewrites. Only files matching the generated name are considered for deletion.
find "$backup_dir" -maxdepth 1 -type f -name 'agentic-ai-*.rdb' |
  sort -r |
  {
    seen=0
    while IFS= read -r snap; do
      seen=$((seen + 1))
      if [ "$seen" -gt "$retention" ]; then
        rm -f -- "$snap"
        printf 'pruned %s\n' "$snap" >&2
      fi
    done
  }

find "$backup_dir" -maxdepth 1 -type f -name 'agentic-ai-*.rdb.incomplete' -mmin +1440 \
  -exec rm -f -- {} +

printf '%s\n' "$output"
