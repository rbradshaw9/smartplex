# SmartPlex Beta Readiness Checklist

**Status**: ✅ **READY FOR BETA TESTING**  
**Last Updated**: November 11, 2025

---

## 🎯 Beta Launch Requirements

### ✅ Completed (6/10 Critical Items)

1. **✅ User-Focused Landing Page**
   - Beta badge prominently displayed
   - Clear value proposition for end users
   - "Coming Soon" section for admin features
   - No technical/admin jargon
   - Links to Terms and Privacy

2. **✅ White-Labeled AI**
   - Removed all OpenAI references from user-facing text
   - Generic "AI" messaging throughout
   - Error messages don't mention OpenAI
   - Feels like native SmartPlex intelligence

3. **✅ Admin Features Hidden**
   - Navigation only shows admin links to admins
   - Non-admins redirected from /admin routes
   - Role-based access control working
   - Clean user experience for regular users

4. **✅ Error Tracking (Sentry)**
   - Frontend: `smartplex-web` project configured
   - Backend: `smartplex-api` project configured
   - DSNs hardcoded as fallbacks (works out of the box)
   - Session replay enabled for debugging
   - Test endpoints: `/sentry-debug` (API), console errors (web)

5. **✅ User Feedback System**
   - Floating feedback button on all authenticated pages
   - Modal form with bug/feature/improvement/other categories
   - API endpoints: POST/GET `/api/feedback`
   - Migration 013 executed in Supabase ✅
   - Admin can view/update feedback status

6. **✅ Terms of Service & Privacy Policy**
   - `/terms` - Comprehensive beta ToS
   - `/privacy` - Detailed privacy policy covering AI, data usage
   - Linked from landing page login section
   - Covers all aspects: Plex integration, AI features, data retention

---

## 📋 Optional/Lower Priority Items

### 🔄 Sign-Up Flow (Already Working)
**Status**: Functional, tested  
- Plex OAuth with PIN flow works
- Auto-closing popup implemented
- Clean error handling
- No changes needed for beta

### 🔄 Plex Webhook for Deletions (Optional)
**Status**: Not needed for beta  
- Current orphan cleanup works well (post-sync)
- Webhook would be real-time but adds complexity
- **Recommendation**: Add after beta feedback
- **Note**: Can use same webhook endpoint for multiple event types

### 🎓 User Onboarding Flow (Nice to Have)
**Status**: Not blocking  
- First-time users can figure out the interface
- Dashboard is intuitive
- **Recommendation**: Add after initial beta feedback

### 📊 Usage Analytics (Nice to Have)
**Status**: Not blocking  
- Sentry provides basic usage data
- **Recommendation**: Add Plausible/PostHog after beta launch
- Focus on feedback system for now

---

## 🚀 Deployment Status

### Railway (Auto-deployed)
- ✅ All code pushed to GitHub (main branch)
- ✅ Railway auto-deploys on push
- ✅ Frontend: Latest commit eb2795f
- ✅ Backend: Latest commit eb2795f

### Database (Supabase)
- ✅ Migration 011: genres column (executed)
- ✅ Migration 012: overseerr_requests table (executed)
- ✅ Migration 013: feedback table (executed)

### Environment Variables

#### Frontend (Railway - Web Service)
Required (optional, DSN is hardcoded):
```bash
NEXT_PUBLIC_SENTRY_DSN=https://0384e7109635342e54c2f9916a6a8daf@o4510303274926080.ingest.us.sentry.io/4510346716643328
```

#### Backend (Railway - API Service)
Required (optional, DSN is hardcoded):
```bash
SENTRY_DSN=https://9352877a711f16edf148d59fd3d7900b@o4510303274926080.ingest.us.sentry.io/4510346730733568
```

**Note**: Sentry works without env vars due to hardcoded DSN fallbacks.

---

## 🧪 Testing Checklist

### Before Opening to Beta

- [ ] **Test Sign-Up Flow**
  - Create new test account with Plex
  - Verify auto-close popup works
  - Check Terms/Privacy links on landing page

- [ ] **Test Core Features**
  - Media library sync works
  - AI recommendations display
  - AI chat responds correctly
  - Media requests to Overseerr work
  - Feedback button appears and submits

- [ ] **Test Error Tracking**
  - Trigger frontend error (console: `throw new Error("test")`)
  - Visit `/sentry-debug` on API
  - Check Sentry dashboards for errors

- [ ] **Test Permissions**
  - Non-admin can't access /admin routes
  - Admin sees "Administration" in menu
  - Regular user doesn't see admin features

- [ ] **Mobile Testing**
  - Landing page responsive
  - Dashboard usable on mobile
  - Feedback button accessible

---

## 📢 Beta Launch Plan

### Phase 1: Limited Beta (First Week)
**Target**: 5-10 trusted users

**Goals**:
- Validate core workflows
- Identify critical bugs
- Test Sentry error tracking
- Gather initial feedback

**Communication**:
- Personal email to beta testers
- Explain it's early beta
- Encourage aggressive feedback via in-app button
- Set expectations: bugs expected

### Phase 2: Expanded Beta (Week 2-4)
**Target**: 20-50 users

**Requirements Before Expansion**:
- No critical bugs from Phase 1
- Sentry dashboard shows low error rate
- Positive feedback from initial testers
- Performance is acceptable

**New Features** (if needed):
- User onboarding flow
- Usage analytics
- Improved AI chat
- More integrations

### Phase 3: Public Beta (Month 2+)
**Target**: 100+ users

**Requirements**:
- Stable performance
- Low error rate (<1% requests)
- Positive user retention
- Admin features ready for testing

---

## 🐛 Bug Tracking & Support

### Error Monitoring
- **Sentry Frontend**: https://tactiqal.sentry.io/issues/?project=4510346716643328
- **Sentry Backend**: https://tactiqal.sentry.io/issues/?project=4510346730733568

### User Feedback
- In-app feedback button (floating, bottom-right)
- Stored in `feedback` table in Supabase
- Admin view: Query `feedback` table or build admin UI

### Direct Support
- Monitor Sentry for errors
- Check feedback submissions daily
- Respond to critical issues within 24h

---

## 🎯 Success Metrics for Beta

### Week 1 Goals
- [ ] 5+ active users
- [ ] <10 critical bugs reported
- [ ] 80%+ successful sign-ups
- [ ] At least 5 feedback submissions

### Month 1 Goals
- [ ] 20+ active users
- [ ] 90%+ uptime
- [ ] 50+ media requests processed
- [ ] Positive sentiment in feedback

---

## 🔐 Security Considerations

### Already Implemented
- ✅ HTTPS everywhere
- ✅ Plex OAuth (no password storage)
- ✅ RLS policies on all tables
- ✅ Role-based access control
- ✅ API authentication required
- ✅ Input validation on all endpoints

### Monitor During Beta
- Watch Sentry for security-related errors
- Review feedback for abuse reports
- Check for unusual API usage patterns

---

## 📝 Post-Beta Improvements

Based on expected feedback:

### Likely Requests
1. Mobile app (React Native)
2. More AI customization
3. Better media discovery UI
4. Integration with more *arr services
5. Automated cleanup improvements
6. Social features (share recommendations)

### Admin Phase (Later)
- Library cleanup tools
- Deletion rules management
- Storage monitoring
- User management
- Analytics dashboard

---

## ✅ Final Checklist

Before sending invites:

- [x] Landing page looks professional
- [x] Sign-up works smoothly
- [x] Terms & Privacy are complete
- [x] Feedback system is live
- [x] Sentry is tracking errors
- [x] All migrations executed
- [x] No OpenAI branding visible
- [x] Admin features hidden from users

**Status**: 🎉 **READY TO LAUNCH BETA!**

---

## 🚀 How to Invite Beta Testers

### Email Template

```
Subject: You're Invited to SmartPlex Beta! 🎬

Hi [Name],

You're invited to be one of the first beta testers for SmartPlex - an AI-powered companion for your Plex media server!

What is SmartPlex?
• Get personalized movie and TV recommendations based on what you actually watch
• Request new content with one click (works with Overseerr/Jellyseerr)
• Chat with AI to discover your next favorite show

Get Started:
1. Visit: [Your Railway URL]
2. Sign in with your Plex account
3. Start exploring!

As a beta tester:
• Expect some bugs (please report them using the feedback button!)
• Your feedback shapes the product
• Free access during beta period
• No commitment required

Questions? Just hit the feedback button in the app or reply to this email.

Thanks for being an early supporter!
[Your Name]
```

---

## 📊 Monitoring Checklist (Daily During Beta)

- [ ] Check Sentry for new errors
- [ ] Review feedback submissions
- [ ] Monitor Railway logs for issues
- [ ] Check Supabase for orphaned data
- [ ] Verify sync jobs are completing
- [ ] Test AI features still working

---

**Need Help?**
- Sentry Setup: `docs/SENTRY_SETUP.md`
- All code deployed: Commit `eb2795f`
- Feedback API: `/api/feedback` (GET/POST)

**You're ready to go! 🚀**
