import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 py-16">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-8 md:p-12">
          {/* Header */}
          <div className="mb-8">
            <Link 
              href="/"
              className="text-blue-400 hover:text-blue-300 text-sm mb-4 inline-block"
            >
              ← Back to Home
            </Link>
            <h1 className="text-4xl font-bold text-white mb-2">Privacy Policy</h1>
            <p className="text-slate-400">Beta Program - Last Updated: November 11, 2025</p>
          </div>

          {/* Content */}
          <div className="prose prose-invert prose-slate max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">1. Information We Collect</h2>
              
              <h3 className="text-xl font-semibold text-white mb-3 mt-6">Account Information</h3>
              <p className="text-slate-300 mb-4">
                When you sign in with Plex, we collect:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Your Plex username and email address</li>
                <li>Your Plex user ID and authentication token</li>
                <li>Your Plex server information (if you grant access)</li>
              </ul>

              <h3 className="text-xl font-semibold text-white mb-3 mt-6">Media Library Data</h3>
              <p className="text-slate-300 mb-4">
                To provide recommendations and management features, we collect:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>List of media in your Plex library (titles, genres, metadata)</li>
                <li>Your viewing history and watch progress</li>
                <li>Your ratings and preferences</li>
                <li>Media request history through Overseerr/Jellyseerr</li>
              </ul>

              <h3 className="text-xl font-semibold text-white mb-3 mt-6">Usage Data</h3>
              <p className="text-slate-300 mb-4">
                We automatically collect:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Pages you visit and features you use</li>
                <li>Browser type and device information</li>
                <li>Error logs and performance data via Sentry</li>
                <li>IP addresses for security purposes</li>
              </ul>

              <h3 className="text-xl font-semibold text-white mb-3 mt-6">Feedback and Communications</h3>
              <p className="text-slate-300 mb-4">
                When you submit feedback:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Feedback content and bug reports</li>
                <li>Screenshots you voluntarily provide</li>
                <li>Page URLs where issues occurred</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">2. How We Use Your Information</h2>
              <p className="text-slate-300 mb-4">
                We use your information to:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Provide personalized recommendations using AI</li>
                <li>Manage and sync your media library</li>
                <li>Process media requests through integrations</li>
                <li>Improve the service based on usage patterns</li>
                <li>Debug issues and monitor performance</li>
                <li>Communicate about service updates</li>
                <li>Ensure security and prevent abuse</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">3. AI and Machine Learning</h2>
              <p className="text-slate-300 mb-4">
                SmartPlex uses AI to enhance your experience:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Your viewing history trains recommendation algorithms</li>
                <li>Chat conversations may be analyzed to improve AI responses</li>
                <li>We use third-party AI services (OpenAI) to power features</li>
                <li>No personal data is sold to third parties</li>
                <li>AI processing happens in secure, encrypted environments</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">4. Data Sharing</h2>
              <p className="text-slate-300 mb-4">
                We share data only in these situations:
              </p>
              
              <h3 className="text-xl font-semibold text-white mb-3 mt-6">Service Providers</h3>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li><strong>Supabase:</strong> Database and authentication hosting</li>
                <li><strong>Railway:</strong> Application hosting and deployment</li>
                <li><strong>Sentry:</strong> Error tracking and performance monitoring</li>
                <li><strong>OpenAI:</strong> AI chat and recommendation processing</li>
              </ul>

              <h3 className="text-xl font-semibold text-white mb-3 mt-6">Plex Integration</h3>
              <p className="text-slate-300 mb-4">
                We access your Plex server using your authorization. We never:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Share your Plex credentials with anyone</li>
                <li>Access media you haven't shared with SmartPlex</li>
                <li>Modify your Plex server settings without permission</li>
              </ul>

              <h3 className="text-xl font-semibold text-white mb-3 mt-6">Legal Requirements</h3>
              <p className="text-slate-300 mb-4">
                We may disclose information if required by law or to protect our rights.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">5. Data Storage and Security</h2>
              <p className="text-slate-300 mb-4">
                We take security seriously:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>All data is encrypted in transit (HTTPS/TLS)</li>
                <li>Passwords are never stored (Plex OAuth only)</li>
                <li>Database access is restricted and monitored</li>
                <li>Regular security audits during development</li>
                <li>Data is stored in secure US data centers</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">6. Data Retention</h2>
              <p className="text-slate-300 mb-4">
                During the beta program:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Account data is retained while your account is active</li>
                <li>Viewing history is kept to provide recommendations</li>
                <li>Feedback submissions are retained indefinitely for product improvement</li>
                <li>Error logs are retained for 90 days</li>
                <li>You can request account deletion at any time</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">7. Your Rights</h2>
              <p className="text-slate-300 mb-4">
                You have the right to:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Access your personal data</li>
                <li>Request correction of inaccurate data</li>
                <li>Request deletion of your account and data</li>
                <li>Revoke Plex access at any time</li>
                <li>Opt out of AI features (with reduced functionality)</li>
                <li>Export your data in a readable format</li>
              </ul>
              <p className="text-slate-300 mt-4">
                To exercise these rights, use the feedback button or contact us through your Plex account email.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">8. Cookies and Tracking</h2>
              <p className="text-slate-300 mb-4">
                SmartPlex uses minimal cookies:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Essential cookies for authentication (required)</li>
                <li>Session cookies to maintain your login state</li>
                <li>No third-party advertising cookies</li>
                <li>No behavioral tracking across other websites</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">9. Children's Privacy</h2>
              <p className="text-slate-300">
                SmartPlex is not intended for users under 18. We do not knowingly collect 
                information from children. If you believe we have collected data from a minor, 
                please contact us immediately.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">10. Beta Program Notice</h2>
              <p className="text-slate-300 mb-4">
                During the beta period:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>This privacy policy may be updated frequently</li>
                <li>We'll notify you of significant changes</li>
                <li>Your continued use indicates acceptance of updates</li>
                <li>You can review policy changes in your account settings</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">11. Contact Us</h2>
              <p className="text-slate-300">
                Questions about privacy? Use the feedback button in the app to reach us. 
                We'll respond to privacy inquiries within 48 hours during beta testing.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">12. International Users</h2>
              <p className="text-slate-300">
                SmartPlex is hosted in the United States. If you're accessing from outside the US, 
                your data will be transferred to and processed in the US. By using SmartPlex, you 
                consent to this transfer.
              </p>
            </section>
          </div>

          {/* Footer Links */}
          <div className="mt-12 pt-8 border-t border-slate-700 flex flex-col sm:flex-row gap-4 justify-between items-center">
            <Link 
              href="/terms"
              className="text-blue-400 hover:text-blue-300"
            >
              Terms of Service →
            </Link>
            <Link 
              href="/"
              className="text-slate-400 hover:text-white"
            >
              Back to SmartPlex
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
