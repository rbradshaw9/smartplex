/** @type {import('next').NextConfig} */
const nextConfig = {
  // Force fresh build - cache buster
  generateBuildId: async () => {
    return 'build-' + Date.now() + '-v2'
  },
  // Output standalone for better caching control
  output: 'standalone',
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

module.exports = nextConfig