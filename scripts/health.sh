#!/usr/bin/env bash
# scripts/health.sh — prod alias_fill / post_metrics 신선도 quick probe.
#
# 3 SQL 출력:
#   1) artists.aliases 가 빈 배열인 비율 (BUG-15 cross-check 후 alias 미충전 비율)
#   2) artists.musicbrainz_id = 'not_found' sentinel 비율 (BUG-18 eviction 누적 곡선)
#   3) post_metrics.updated_at 의 마지막 갱신 시각 + ago(분)
#
# Usage:
#   DATABASE_URL=postgresql+psycopg://USER:PASS@HOST/DB ./scripts/health.sh
#
# DATABASE_URL 출처 (SSM Parameter Store SecureString — Secrets Manager는 비워짐, CHORE-secrets-ssm-migration):
#   aws ssm get-parameter --name /myblog/backend --with-decryption \
#     --query Parameter.Value --output text | jq -r .DATABASE_URL
#
# psql 가 postgresql+psycopg:// scheme 을 못 받으므로 자동 변환 (reference-database-url-psql).
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  cat >&2 <<'EOF'
DATABASE_URL 미설정. SSM Parameter Store 에서 가져와 export 후 재실행:

  export DATABASE_URL="$(aws ssm get-parameter --name /myblog/backend \
      --with-decryption --query Parameter.Value --output text \
      | jq -r .DATABASE_URL)"
EOF
  exit 2
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql not found. brew install postgresql 또는 PATH 에 추가." >&2
  exit 2
fi

PSQL_URL="${DATABASE_URL/postgresql+psycopg:/postgresql:}"

run_sql() {
  local title="$1"
  local sql="$2"
  echo "── $title"
  psql "$PSQL_URL" -At -F $'\t' -c "$sql"
  echo
}

run_sql "aliases 빈배열 비율 (artists)" \
  "SELECT
     count(*) AS total_rows,
     count(*) FILTER (WHERE aliases = '[]'::jsonb) AS empty_alias_rows,
     round(100.0 * count(*) FILTER (WHERE aliases = '[]'::jsonb)
                 / NULLIF(count(*), 0), 2) AS pct_empty
   FROM artists;"

run_sql "MBID not-found sentinel 비율 (artists)" \
  "SELECT
     count(*) FILTER (WHERE musicbrainz_id = 'not_found') AS sentinel_rows,
     count(*) FILTER (WHERE musicbrainz_id IS NULL)        AS null_rows,
     round(100.0 * count(*) FILTER (WHERE musicbrainz_id = 'not_found')
                 / NULLIF(count(*), 0), 2) AS pct_sentinel
   FROM artists;"

run_sql "post_metrics 최신성" \
  "SELECT
     to_char(MAX(updated_at), 'YYYY-MM-DD HH24:MI:SS') AS last_update,
     round(EXTRACT(EPOCH FROM (now() - MAX(updated_at))) / 60, 1) AS minutes_ago,
     count(*) AS rows_total
   FROM post_metrics;"
