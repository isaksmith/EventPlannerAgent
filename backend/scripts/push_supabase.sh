#!/usr/bin/env bash
# Option B: link remote Supabase project and push migrations.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! supabase projects list >/dev/null 2>&1; then
  echo "Not logged in. Run: supabase login"
  exit 1
fi

supabase link --project-ref kvktyffgvyehjxqwnfjk
supabase db push --yes

echo "Done. Verify in Dashboard → Table Editor → registrations"
