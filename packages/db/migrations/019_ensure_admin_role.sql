-- Migration 019: Ensure Admin Role
-- Purpose: Fix role field to ensure admin access works correctly
-- This ensures rbradshaw@gmail.com has admin role for testing

-- Update user to have admin role
UPDATE users 
SET role = 'admin'
WHERE email = 'rbradshaw@gmail.com';

-- Verify
SELECT id, email, role, display_name 
FROM users 
WHERE email = 'rbradshaw@gmail.com';
