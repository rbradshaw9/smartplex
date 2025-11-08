import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SmartPlex | AI-Powered Plex Ecosystem',
  description: 'The autonomous, AI-powered Plex server ecosystem that intelligently manages your media.',
  keywords: ['Plex', 'AI', 'Media Server', 'Automation', 'SmartPlex'],
  other: {
    'build-version': '2.1.0', // Cache buster
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  )
}