import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Header } from '@/components/layout/header'
import { Footer } from '@/components/layout/footer'
import { createServerComponentClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { Database } from '@smartplex/db/types'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SmartPlex | AI-Powered Plex Ecosystem',
  description: 'The autonomous, AI-powered Plex server ecosystem that intelligently manages your media.',
  keywords: ['Plex', 'AI', 'Media Server', 'Automation', 'SmartPlex'],
  icons: {
    icon: '/favicon.svg',
  },
  other: {
    'build-version': '3.0.1', // Static version - no Date.now() to avoid SSR mismatch
  },
}

// Force dynamic rendering - no static optimization
export const dynamic = 'force-dynamic'
export const revalidate = 0

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const supabase = createServerComponentClient<Database>({ cookies })
  const { data: { user } } = await supabase.auth.getUser()

  return (
    <html lang="en">
      <body className={`${inter.className} flex flex-col min-h-screen bg-slate-900`}>
        <Header user={user} />
        <main className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  )
}