/** @type {import('next').NextConfig} */
const nextConfig = {
  // DEBUGGING: Disable minification to see actual errors
  productionBrowserSourceMaps: true,
  // Force fresh build - cache buster v5
  generateBuildId: async () => {
    return 'build-' + Date.now() + '-v5-' + Math.random().toString(36).substring(7)
  },
  compiler: {
    // Remove console logs in production (but keep errors)
    removeConsole: false,
  },
  // Disable webpack cache completely and force different chunk names
  webpack: (config, { isServer, dev }) => {
    // Disable webpack persistent cache
    config.cache = false
    
    // CRITICAL: Disable minification to see actual error messages
    if (!dev) {
      config.optimization.minimize = false
    }
    
    // Enable source maps
    config.devtool = 'source-map'
    
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
