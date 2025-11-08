/** @type {import('next').NextConfig} */
const nextConfig = {
  // Force fresh build - cache buster v4
  generateBuildId: async () => {
    return 'build-' + Date.now() + '-v4-' + Math.random().toString(36).substring(7)
  },
  // Disable webpack cache completely
  webpack: (config, { isServer }) => {
    // Disable webpack persistent cache
    config.cache = false
    return config
  },
  images: {
    domains: [
      'localhost',
      'image.tmdb.org', // TMDB images
      'assets.fanart.tv', // Fanart images
    ],
  },
  async headers() {
    return [
      {
        // Apply CORS headers to API routes
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version' },
        ],
      },
    ]
  },
}

module.exports = nextConfig// Build version 1762639217
