import Link from 'next/link'

export default function TermsPage() {
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
            <h1 className="text-4xl font-bold text-white mb-2">Terms of Service</h1>
            <p className="text-slate-400">Beta Program - Last Updated: November 11, 2025</p>
          </div>

          {/* Content */}
          <div className="prose prose-invert prose-slate max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">1. Beta Program Participation</h2>
              <p className="text-slate-300 mb-4">
                SmartPlex is currently in beta testing. By using this service, you acknowledge that:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>The service is provided "as-is" during the beta period</li>
                <li>Features may change, be removed, or have bugs</li>
                <li>Service availability is not guaranteed</li>
                <li>Your account and data may be reset during beta updates</li>
                <li>The service is free during the beta period</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">2. Account Requirements</h2>
              <p className="text-slate-300 mb-4">
                To use SmartPlex, you must:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Have a valid Plex account</li>
                <li>Be at least 18 years old or have parental consent</li>
                <li>Provide accurate information when creating your account</li>
                <li>Keep your login credentials secure</li>
                <li>Not share your account with others</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">3. Acceptable Use</h2>
              <p className="text-slate-300 mb-4">
                You agree not to:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Use the service for any illegal purpose</li>
                <li>Attempt to gain unauthorized access to our systems</li>
                <li>Reverse engineer, decompile, or disassemble the service</li>
                <li>Submit false or misleading feedback</li>
                <li>Abuse or overload our systems</li>
                <li>Violate any applicable laws or regulations</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">4. Content and Media</h2>
              <p className="text-slate-300 mb-4">
                SmartPlex integrates with your Plex media server. You are responsible for:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Ensuring you have proper rights to all media in your library</li>
                <li>Complying with copyright laws in your jurisdiction</li>
                <li>Any content shared through your Plex server</li>
              </ul>
              <p className="text-slate-300 mt-4">
                SmartPlex does not host, store, or provide any media content. We only provide 
                tools to manage and discover content in your existing Plex library.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">5. AI Features</h2>
              <p className="text-slate-300 mb-4">
                SmartPlex uses AI to provide recommendations and chat features. Please note:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>AI recommendations are suggestions, not guarantees</li>
                <li>AI may occasionally provide incorrect information</li>
                <li>Your viewing data is used to improve recommendations</li>
                <li>Chat conversations may be reviewed to improve AI quality</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">6. Feedback and Bug Reports</h2>
              <p className="text-slate-300 mb-4">
                As a beta tester, we encourage you to provide feedback. By submitting feedback, you grant us:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>The right to use your feedback to improve the service</li>
                <li>No obligation to compensate you for feedback</li>
                <li>No confidentiality obligations regarding your feedback</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">7. Service Modifications</h2>
              <p className="text-slate-300 mb-4">
                We reserve the right to:
              </p>
              <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                <li>Modify or discontinue features at any time</li>
                <li>Change these terms with reasonable notice</li>
                <li>Suspend or terminate accounts that violate these terms</li>
                <li>End the beta program at any time</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">8. Disclaimer of Warranties</h2>
              <p className="text-slate-300 mb-4">
                THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND. WE DISCLAIM ALL 
                WARRANTIES, EXPRESS OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR 
                PURPOSE, AND NON-INFRINGEMENT.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">9. Limitation of Liability</h2>
              <p className="text-slate-300 mb-4">
                TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE SHALL NOT BE LIABLE FOR ANY INDIRECT, 
                INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING FROM YOUR USE OF 
                THE SERVICE.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">10. Contact</h2>
              <p className="text-slate-300">
                Questions about these terms? Use the feedback button in the app or contact us at 
                the email address in your Plex account confirmation.
              </p>
            </section>
          </div>

          {/* Footer Links */}
          <div className="mt-12 pt-8 border-t border-slate-700 flex flex-col sm:flex-row gap-4 justify-between items-center">
            <Link 
              href="/privacy"
              className="text-blue-400 hover:text-blue-300"
            >
              Privacy Policy →
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
