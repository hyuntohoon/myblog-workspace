#!/usr/bin/env bash
# Exposure guard (TRIAL.md §2): read-only count of album_research rows for the four
# round-manifest-v1 confirmation albums. Writes exposure/<UTC stamp>.txt with the SQL and output.
# DATABASE_URL is read from SSM and never printed.
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"
SQL="select a.id, a.title, (select count(*) from album_research r where r.album_id = a.id) as research_rows
from albums a where a.id in ('eb1817f0-2468-4e14-9926-a3af404b6547','50d820b4-b4d6-412d-a45e-dc326c7f6796',
'9de8820b-bab2-4648-9957-44dabf5b223c','7eb56967-085e-4b55-9427-db7dc0ebc2eb') order by a.title;"
URL=$(aws ssm get-parameter --name /myblog/backend --with-decryption --query Parameter.Value --output text \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1))")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT=$(PGCONNECT_TIMEOUT=30 PGOPTIONS='-c default_transaction_read_only=on' psql "$URL" -v ON_ERROR_STOP=1 -At -F ' | ' -c "$SQL" 2>&1 \
  | sed -E 's#postgres(ql)?://[^ ]*#[masked]#g')
printf -- '-- %s\n%s\n\n%s\n' "$STAMP" "$SQL" "$OUT" > "$H/exposure/$STAMP.txt"
cat "$H/exposure/$STAMP.txt"
