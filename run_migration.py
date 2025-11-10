#!/usr/bin/env python3
"""Run database migration using Supabase API"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

from app.core.supabase import get_supabase_client

def run_migration():
    """Run the webhook migration"""
    # Read migration file
    migration_path = os.path.join(os.path.dirname(__file__), 'packages', 'db', 'migrations', '005_add_webhooks_and_sync_schedule.sql')
    
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Execute migration via Supabase REST API
    # Note: This requires direct database access via psql or Supabase dashboard
    print("⚠️  Migration SQL generated. Please run it via Supabase SQL Editor:")
    print("\n1. Go to: https://supabase.com/dashboard/project/lecunkywsfuqumqzddol/sql/new")
    print("2. Copy and paste the migration SQL below:")
    print("\n" + "="*80)
    print(migration_sql)
    print("="*80 + "\n")
    
    print("✅ Once run, the webhook_log and sync_schedule tables will be created")

if __name__ == "__main__":
    run_migration()
