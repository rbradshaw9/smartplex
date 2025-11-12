#!/usr/bin/env python3
"""
Script to identify and optionally fix media items with invalid plex_id values.

Invalid plex_ids are non-numeric strings (e.g., 'Mr. Deeds_2002' instead of '12345').
These cause deletion failures when trying to call Plex API.

Usage:
    # List invalid items only (dry run):
    python fix_invalid_plex_ids.py

    # Delete invalid items from database:
    python fix_invalid_plex_ids.py --delete

    # Re-sync invalid items from Plex (requires plex token):
    python fix_invalid_plex_ids.py --resync --plex-token YOUR_TOKEN
"""
import os
import sys
import argparse
from supabase import create_client, Client

# Get Supabase credentials from environment
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def is_valid_plex_id(plex_id: str) -> bool:
    """Check if plex_id is a valid numeric string."""
    if not plex_id:
        return False
    try:
        int(plex_id)
        return True
    except (ValueError, TypeError):
        return False


def find_invalid_items():
    """Find all media items with invalid plex_id values."""
    print("🔍 Scanning media_items table for invalid plex_ids...")
    
    # Get all media items
    result = supabase.table("media_items")\
        .select("id, title, plex_id, type, server_id")\
        .execute()
    
    invalid_items = []
    total_count = len(result.data)
    
    for item in result.data:
        if not is_valid_plex_id(item.get('plex_id')):
            invalid_items.append(item)
    
    print(f"✅ Scanned {total_count} items, found {len(invalid_items)} with invalid plex_ids\n")
    
    return invalid_items


def display_invalid_items(items):
    """Display invalid items in a readable format."""
    if not items:
        print("✨ No invalid plex_ids found!")
        return
    
    print("📋 Invalid plex_id items:\n")
    print(f"{'Title':<50} {'Type':<10} {'Invalid plex_id':<30} {'ID'}")
    print("-" * 120)
    
    for item in items:
        title = (item.get('title', 'Unknown')[:47] + '...') if len(item.get('title', '')) > 50 else item.get('title', 'Unknown')
        print(f"{title:<50} {item.get('type', 'N/A'):<10} {str(item.get('plex_id', 'N/A')):<30} {item.get('id')}")


def delete_invalid_items(items):
    """Delete items with invalid plex_ids from the database."""
    if not items:
        return
    
    print(f"\n⚠️  About to delete {len(items)} items from database...")
    confirm = input("Type 'DELETE' to confirm: ")
    
    if confirm != "DELETE":
        print("❌ Deletion cancelled")
        return
    
    deleted_count = 0
    failed_count = 0
    
    for item in items:
        try:
            supabase.table("media_items")\
                .delete()\
                .eq("id", item['id'])\
                .execute()
            print(f"✅ Deleted: {item.get('title')}")
            deleted_count += 1
        except Exception as e:
            print(f"❌ Failed to delete {item.get('title')}: {e}")
            failed_count += 1
    
    print(f"\n✅ Deletion complete: {deleted_count} deleted, {failed_count} failed")


def main():
    parser = argparse.ArgumentParser(description="Find and fix media items with invalid plex_id values")
    parser.add_argument('--delete', action='store_true', help='Delete items with invalid plex_ids')
    parser.add_argument('--resync', action='store_true', help='Re-sync items from Plex (requires --plex-token)')
    parser.add_argument('--plex-token', type=str, help='Plex authentication token')
    
    args = parser.parse_args()
    
    # Find invalid items
    invalid_items = find_invalid_items()
    display_invalid_items(invalid_items)
    
    if not invalid_items:
        return
    
    # Handle actions
    if args.delete:
        delete_invalid_items(invalid_items)
    elif args.resync:
        if not args.plex_token:
            print("❌ Error: --plex-token required for --resync")
            sys.exit(1)
        print("\n⚠️  Re-sync functionality not yet implemented")
        print("For now, use --delete to remove invalid items, then re-run Plex sync")
    else:
        print("\n💡 Actions:")
        print("  - To delete these items: python fix_invalid_plex_ids.py --delete")
        print("  - To re-sync from Plex: python fix_invalid_plex_ids.py --resync --plex-token YOUR_TOKEN")


if __name__ == "__main__":
    main()
