# 🚀 SmartPlex Deployment Checklist

## ✅ Code Changes (Completed)
- [x] Fixed Railway buildCommand conflict (removed from railway.json)
- [x] Added pydantic-settings dependency
- [x] Made CORS origins configurable via environment variables
- [x] Fixed Plex auth to create Supabase auth users (with fallback)
- [x] Added proper session expiration (24 hours)
- [x] Added FRONTEND_URL configuration

## 📋 Railway Environment Variables (Required)
Set these in Railway dashboard → Settings → Variables:

```bash
SMARTPLEX_ENV=production
SUPABASE_URL=https://lecunkywsfuqumqzddol.supabase.co
SUPABASE_SERVICE_KEY=<your-supabase-service-role-key>
FRONTEND_URL=https://smartplex-ecru.vercel.app
```

**Do NOT set PORT** - Railway provides this automatically

## 📋 Vercel Environment Variables (Required)
Set these in Vercel dashboard → Settings → Environment Variables:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://qqqyzrvwysxuevg8ww.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>
NEXT_PUBLIC_API_URL=https://smartplex-production.up.railway.app
```

## 🗄️ Supabase Database Setup (Required)
Execute these SQL files in order in Supabase SQL Editor:

1. **First**: Execute `packages/db/schema.sql`
   - Creates 9 tables (users, servers, integrations, media_items, etc.)
   - Sets up enums, constraints, indexes, triggers

2. **Second**: Execute `packages/db/rls.sql`
   - Enables Row Level Security on all tables
   - Creates 35+ security policies
   - Sets up helper functions (get_user_by_email, create_user_profile, etc.)
   - Grants proper permissions

## 🔐 Supabase Authentication Settings
Configure in Supabase Dashboard → Authentication:

1. **Email Provider**: Enable
2. **Site URL**: `https://smartplex-ecru.vercel.app`
3. **Redirect URLs**: Add:
   - `https://smartplex-ecru.vercel.app/auth/callback`
   - `http://localhost:3000/auth/callback`
4. **Email Confirmations**: Disable (optional for testing)

## 🔄 Post-Deployment Testing

### 1. Verify Railway API Deployment
```bash
curl https://smartplex-production.up.railway.app/
# Expected: {"message":"SmartPlex API","version":"0.1.0","docs":"/docs","status":"🚀 Running"}
```

### 2. Test Plex OAuth Flow
1. Visit `https://smartplex-ecru.vercel.app`
2. Click "Sign in with Plex"
3. Verify PIN appears
4. Authorize in Plex window
5. Should redirect to `/dashboard`
6. Check browser localStorage for `smartplex_user` and `smartplex_session`

### 3. Verify Database Connection
```bash
# In Supabase SQL Editor
SELECT * FROM users LIMIT 1;
# Should show your newly created user
```

## ⚠️ Known Limitations (To Fix Later)

1. **No /setup/connect-plex Page**
   - Email signup redirects to non-existent page
   - Workaround: Use Plex login only for now

2. **Session Management**
   - Sessions stored in localStorage (not secure for production)
   - No refresh token flow
   - TODO: Implement proper JWT handling

3. **HTTPBearer Security**
   - All protected endpoints require auth
   - No public endpoints
   - TODO: Add optional auth dependency

4. **Error Handling**
   - Generic error messages
   - TODO: Add detailed error responses

## 🎉 Success Criteria
- ✅ Railway API returns 200 on GET /
- ✅ Plex OAuth login creates user in database
- ✅ Frontend can fetch from API without CORS errors
- ✅ User can login and see dashboard
- ✅ Database has proper RLS policies enabled

## 📝 Next Steps After Successful Deployment
1. Create `/setup/connect-plex` page for email users
2. Implement proper JWT refresh token flow
3. Add comprehensive error handling
4. Set up monitoring/logging (Sentry, LogTail, etc.)
5. Add rate limiting
6. Set up CI/CD pipeline
7. Add automated tests
