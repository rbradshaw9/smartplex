-- Sample data for SmartPlex development and testing
-- This file provides realistic test data for local development

-- IMPORTANT: Default admin user
-- Email: rbradshaw@gmail.com
-- If user already exists from Plex login, this will promote them to admin role

-- Sample users (passwords would be handled by Supabase Auth)
-- Using INSERT ... ON CONFLICT to handle existing users
INSERT INTO users (id, email, display_name, role, plex_username, preferences) VALUES
  ('00000000-0000-0000-0000-000000000001', 'rbradshaw@gmail.com', 'Ryan Bradshaw', 'admin', 'rbradshaw', '{"theme": "dark", "notifications": {"email": true, "push": true, "storage_alerts": true, "cleanup_reports": true}}'),
  ('550e8400-e29b-41d4-a716-446655440000', 'admin@smartplex.dev', 'SmartPlex Admin', 'admin', 'admin_user', '{"theme": "dark", "notifications": true}'),
  ('550e8400-e29b-41d4-a716-446655440001', 'john@example.com', 'John Doe', 'user', 'john_plex', '{"theme": "light", "autoplay": true}'),
  ('550e8400-e29b-41d4-a716-446655440002', 'jane@example.com', 'Jane Smith', 'user', 'jane_plex', '{"theme": "dark", "language": "en"}'),
  ('550e8400-e29b-41d4-a716-446655440003', 'moderator@smartplex.dev', 'Mod User', 'moderator', 'mod_user', '{"notifications": true}')
ON CONFLICT (email) DO UPDATE SET 
  role = EXCLUDED.role,
  display_name = COALESCE(EXCLUDED.display_name, users.display_name);

-- If rbradshaw@gmail.com already exists with a different ID, promote that user
UPDATE users 
SET role = 'admin'
WHERE email = 'rbradshaw@gmail.com' AND role != 'admin';

-- Sample Plex servers
INSERT INTO servers (id, user_id, name, url, machine_id, platform, version, status) VALUES
  ('660e8400-e29b-41d4-a716-446655440000', '550e8400-e29b-41d4-a716-446655440001', 'Johns Main Server', 'http://192.168.1.100:32400', 'machine-123-abc', 'Linux', '1.32.8.7639', 'online'),
  ('660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002', 'Janes Home Server', 'http://192.168.1.200:32400', 'machine-456-def', 'Windows', '1.32.8.7639', 'online'),
  ('660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440001', 'Johns Backup Server', 'http://192.168.1.150:32400', 'machine-789-ghi', 'Linux', '1.30.2.6563', 'offline');

-- Sample integrations
INSERT INTO integrations (user_id, server_id, service, name, url, status) VALUES
  ('550e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440000', 'tautulli', 'Tautulli Analytics', 'http://192.168.1.100:8181', 'active'),
  ('550e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440000', 'overseerr', 'Overseerr Requests', 'http://192.168.1.100:5055', 'active'),
  ('550e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', 'sonarr', 'Sonarr TV', 'http://192.168.1.200:8989', 'active'),
  ('550e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', 'radarr', 'Radarr Movies', 'http://192.168.1.200:7878', 'inactive');

-- Sample media items
INSERT INTO media_items (server_id, plex_id, type, title, year, imdb_id, tmdb_id, library_section, file_size_bytes, duration_ms) VALUES
  ('660e8400-e29b-41d4-a716-446655440000', 'plex_1001', 'movie', 'The Batman', 2022, 'tt1877830', 414906, 'Movies', 9123456789, 10680000),
  ('660e8400-e29b-41d4-a716-446655440000', 'plex_1002', 'movie', 'Dune: Part One', 2021, 'tt1160419', 438631, 'Movies', 12345678901, 9360000),
  ('660e8400-e29b-41d4-a716-446655440000', 'plex_1003', 'movie', 'Top Gun: Maverick', 2022, 'tt1745960', 361743, 'Movies', 8765432109, 7800000),
  ('660e8400-e29b-41d4-a716-446655440000', 'plex_2001', 'show', 'House of the Dragon', 2022, 'tt11198330', 94997, 'TV Shows', NULL, NULL),
  ('660e8400-e29b-41d4-a716-446655440000', 'plex_2002', 'show', 'The Last of Us', 2023, 'tt3581920', 100088, 'TV Shows', NULL, NULL),
  ('660e8400-e29b-41d4-a716-446655440001', 'plex_1004', 'movie', 'Oppenheimer', 2023, 'tt15398776', 872585, 'Movies', 15678901234, 10800000),
  ('660e8400-e29b-41d4-a716-446655440001', 'plex_1005', 'movie', 'Everything Everywhere All at Once', 2022, 'tt6710474', 545611, 'Movies', 7890123456, 8520000);

-- Sample user stats (watch history)
INSERT INTO user_stats (user_id, media_item_id, play_count, total_duration_ms, last_played_at, completion_percentage, rating) VALUES
  ('550e8400-e29b-41d4-a716-446655440001', (SELECT id FROM media_items WHERE title = 'The Batman'), 2, 21360000, '2024-01-15 19:30:00+00', 100, 8.5),
  ('550e8400-e29b-41d4-a716-446655440001', (SELECT id FROM media_items WHERE title = 'Dune: Part One'), 1, 9360000, '2024-01-10 20:00:00+00', 100, 9.2),
  ('550e8400-e29b-41d4-a716-446655440001', (SELECT id FROM media_items WHERE title = 'Top Gun: Maverick'), 1, 7800000, '2024-01-08 21:15:00+00', 100, 8.8),
  ('550e8400-e29b-41d4-a716-446655440002', (SELECT id FROM media_items WHERE title = 'Oppenheimer'), 1, 10800000, '2024-01-12 18:00:00+00', 100, 9.5),
  ('550e8400-e29b-41d4-a716-446655440002', (SELECT id FROM media_items WHERE title = 'Everything Everywhere All at Once'), 3, 25560000, '2024-01-14 20:30:00+00', 100, 9.8);

-- Sample sync history
INSERT INTO sync_history (user_id, server_id, sync_type, status, items_processed, items_added, items_updated, started_at, completed_at) VALUES
  ('550e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440000', 'scheduled', 'completed', 1247, 23, 8, '2024-01-01 02:00:00+00', '2024-01-01 02:05:32+00'),
  ('550e8400-e29b-41d4-a716-446655440001', '660e8400-e29b-41d4-a716-446655440000', 'manual', 'completed', 1224, 0, 15, '2023-12-31 12:00:00+00', '2023-12-31 12:03:45+00'),
  ('550e8400-e29b-41d4-a716-446655440002', '660e8400-e29b-41d4-a716-446655440001', 'scheduled', 'completed', 892, 12, 5, '2024-01-01 02:30:00+00', '2024-01-01 02:33:12+00');

-- Sample chat history
INSERT INTO chat_history (user_id, message, response, model_used, tokens_used) VALUES
  ('550e8400-e29b-41d4-a716-446655440001', 'What should I watch next?', 'Based on your recent viewing of action movies like "The Batman", I recommend "Top Gun: Maverick" if you haven''t seen it yet. It has excellent reviews and matches your preference for high-quality action films.', 'gpt-3.5-turbo', 145),
  ('550e8400-e29b-41d4-a716-446655440001', 'Show me my watch stats', 'You''ve watched 156 total items this year, spending 248 hours watching content. Your favorite genre is Action, and you prefer recent releases (2020+). Would you like recommendations based on these preferences?', 'gpt-3.5-turbo', 132),
  ('550e8400-e29b-41d4-a716-446655440002', 'Any sci-fi recommendations?', 'Given your love for "Everything Everywhere All at Once", you might enjoy "Dune: Part One" for epic sci-fi storytelling, or "The Matrix" series if you haven''t seen it. Both offer mind-bending concepts and excellent visuals.', 'gpt-3.5-turbo', 158);

-- Sample cleanup log
INSERT INTO cleanup_log (server_id, action, file_path, file_size_bytes, reason, performed_by) VALUES
  ('660e8400-e29b-41d4-a716-446655440000', 'deleted', '/data/movies/Old_Movie_2019.mkv', 8589934592, 'File not accessed for 180+ days, low rating (3.2/10)', 'agent-main-server'),
  ('660e8400-e29b-41d4-a716-446655440000', 'quarantined', '/data/movies/Corrupt_File.mp4', 5368709120, 'Failed integrity check, unplayable', 'agent-main-server'),
  ('660e8400-e29b-41d4-a716-446655440001', 'moved', '/data/old/Backup_Copy.mkv', 12884901888, 'Duplicate file found, moved to archive', 'user-manual-cleanup');

-- Sample agent heartbeats
INSERT INTO agent_heartbeats (agent_id, server_id, status, system_metrics, last_heartbeat) VALUES
  ('agent-main-server', '660e8400-e29b-41d4-a716-446655440000', 'healthy', '{"cpu": 15.2, "memory": 68.5, "disk": 78.3}', NOW() - INTERVAL '2 minutes'),
  ('agent-home-server', '660e8400-e29b-41d4-a716-446655440001', 'healthy', '{"cpu": 8.7, "memory": 45.2, "disk": 85.1}', NOW() - INTERVAL '1 minute'),
  ('agent-backup-server', '660e8400-e29b-41d4-a716-446655440002', 'offline', '{}', NOW() - INTERVAL '2 hours');

-- Insert default system settings
INSERT INTO system_settings (key, value, description, category, is_secret) VALUES
  ('cache.watch_history_ttl_seconds', '900', 'Watch history cache TTL (15 minutes)', 'cache', FALSE),
  ('cache.full_sync_ttl_seconds', '21600', 'Full library sync TTL (6 hours)', 'cache', FALSE),
  ('cache.max_size_mb', '500', 'Maximum cache size in megabytes', 'cache', FALSE),
  ('cleanup.enabled', 'false', 'Enable automated cleanup operations', 'cleanup', FALSE),
  ('cleanup.dry_run', 'true', 'Test mode - no actual deletion', 'cleanup', FALSE),
  ('cleanup.min_age_days', '90', 'Minimum age for cleanup candidates', 'cleanup', FALSE),
  ('cleanup.min_size_mb', '100', 'Minimum file size for cleanup', 'cleanup', FALSE),
  ('cleanup.schedule', '"0 2 * * *"', 'Cron schedule for cleanup (2 AM daily)', 'cleanup', FALSE),
  ('cleanup.storage_warning_threshold', '85', 'Storage warning threshold (%)', 'cleanup', FALSE),
  ('cleanup.storage_critical_threshold', '95', 'Storage critical threshold (%)', 'cleanup', FALSE),
  ('ai.provider', '"openai"', 'AI provider (openai, anthropic, local)', 'ai', FALSE),
  ('ai.model', '"gpt-4o-mini"', 'AI model to use', 'ai', FALSE),
  ('ai.temperature', '0.7', 'AI temperature (0-1)', 'ai', FALSE),
  ('ai.max_tokens', '500', 'Maximum tokens per AI response', 'ai', FALSE),
  ('notifications.email_enabled', 'true', 'Enable email notifications', 'notifications', FALSE),
  ('notifications.discord_webhook', '""', 'Discord webhook URL', 'notifications', TRUE),
  ('notifications.slack_webhook', '""', 'Slack webhook URL', 'notifications', TRUE),
  ('integrations.sync_interval_hours', '6', 'Hours between integration syncs', 'integrations', FALSE),
  ('integrations.timeout_seconds', '30', 'API request timeout', 'integrations', FALSE)
ON CONFLICT (key) DO NOTHING;

-- Insert welcome notification for admin user (using their actual user_id)
INSERT INTO notifications (user_id, type, title, message, severity, data)
SELECT 
  id,
  'system',
  'Admin Access Granted',
  'You now have admin access to SmartPlex. Visit the Admin section to configure integrations and manage your library.',
  'success',
  '{"action": "setup", "url": "/admin/integrations"}'::jsonb
FROM users 
WHERE email = 'rbradshaw@gmail.com'
ON CONFLICT DO NOTHING;

-- Insert audit log for seed operation (using actual user_id)
INSERT INTO audit_log (user_id, action, resource_type, resource_id, changes)
SELECT 
  id,
  'seed',
  'system',
  'database',
  '{"operation": "initial_seed", "admin_role_granted": true}'::jsonb
FROM users 
WHERE email = 'rbradshaw@gmail.com'
LIMIT 1;

-- Update last_active_at for users to simulate recent activity
UPDATE users SET last_active_at = NOW() - (random() * INTERVAL '7 days') WHERE role != 'guest';