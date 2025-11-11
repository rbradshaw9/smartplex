import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring.
  // Adjust this value in production
  tracesSampleRate: 1.0,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Filter out sensitive data
  beforeSend(event) {
    // Don't send events if no DSN is configured
    if (!process.env.NEXT_PUBLIC_SENTRY_DSN) {
      return null;
    }
    
    // Remove API keys and tokens from request data
    if (event.request?.headers) {
      delete event.request.headers['Authorization'];
      delete event.request.headers['authorization'];
      delete event.request.headers['cookie'];
    }
    
    return event;
  },
});
