import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "https://0384e7109635342e54c2f9916a6a8daf@o4510303274926080.ingest.us.sentry.io/4510346716643328",

  // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring.
  // Adjust this value in production
  tracesSampleRate: 1.0,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,
  
  // Environment
  environment: process.env.VERCEL_ENV || process.env.NODE_ENV || "development",
});
