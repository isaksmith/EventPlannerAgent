#!/usr/bin/env python3
"""Apply Supabase SQL migrations when CLI login is unavailable."""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from app.config import get_settings

MIGRATION = Path(__file__).resolve().parent.parent / "supabase/migrations/20250621000000_create_registrations.sql"
PROJECT_REF = "kvktyffgvyehjxqwnfjk"


def _candidate_urls(settings) -> list[str]:
    urls: list[str] = []
    if settings.supabase_db_url:
        urls.append(settings.supabase_db_url)

    password = settings.supabase_db_password or settings.supabase_service_role_key
    if password:
        hosts = [
            f"db.{PROJECT_REF}.supabase.co",
            f"aws-0-us-west-1.pooler.supabase.com",
            f"aws-0-us-east-1.pooler.supabase.com",
            f"aws-1-us-east-1.pooler.supabase.com",
        ]
        for host in hosts:
            if "pooler" in host:
                user = f"postgres.{PROJECT_REF}"
                port = 6543
            else:
                user = "postgres"
                port = 5432
            urls.append(
                f"postgresql://{user}:{password}@{host}:{port}/postgres?sslmode=require"
            )
    return urls


def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    sql = MIGRATION.read_text(encoding="utf-8")

    last_error: Exception | None = None
    for url in _candidate_urls(settings):
        try:
            with psycopg.connect(url, connect_timeout=8) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
            print("Migration applied successfully.")
            return 0
        except Exception as exc:
            last_error = exc

    print("Could not apply migration automatically.", file=sys.stderr)
    if last_error:
        print(f"Last error: {last_error}", file=sys.stderr)
    print(
        "Add SUPABASE_DB_URL from Dashboard → Connect → URI, then rerun:\n"
        "  python scripts/apply_supabase_migration.py",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
