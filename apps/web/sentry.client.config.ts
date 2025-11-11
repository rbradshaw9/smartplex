import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "https://0384e7109635342e54c2f9916a6a8daf@o4510303274926080.ingest.us.sentry.io/4510346716643328",
  
  // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring.
  // Adjust this value in production
  tracesSampleRate: 1.0,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Replay settings for session recording (optional)
  replaysOnErrorSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,

  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
    Sentry.browserTracingIntegration(),
  ],
  
  // CORS configuration for distributed tracing
  tracePropagationTargets: ["localhost", /^https:\/\/smartplexapi-production\.up\.railway\.app/],

  // Filter out sensitive data
  beforeSend(event) {
    // Remove sensitive data from breadcrumbs
    if (event.breadcrumbs) {
      event.breadcrumbs = event.breadcrumbs.filter(breadcrumb => {
        return !breadcrumb.message?.includes('password') && 
               !breadcrumb.message?.includes('token');
      });
    }
    
    return event;
  },
});
