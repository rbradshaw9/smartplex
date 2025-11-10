-- Promote rbradshaw@gmail.com to admin role
-- Run this in Supabase SQL Editor

-- Update existing user to admin role
UPDATE users 
SET 
  role = 'admin',
  display_name = COALESCE(display_name, 'Ryan Bradshaw')
WHERE email = 'rbradshaw@gmail.com';

-- Insert welcome notification if user exists
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

-- Verify the update
SELECT id, email, role, display_name, created_at 
FROM users 
WHERE email = 'rbradshaw@gmail.com';
