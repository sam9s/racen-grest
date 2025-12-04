/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/chat/:path*',
        destination: 'http://localhost:8080/api/chat/:path*',
      },
      {
        source: '/api/feedback/:path*',
        destination: 'http://localhost:8080/api/feedback/:path*',
      },
      {
        source: '/api/channels/:path*',
        destination: 'http://localhost:8080/api/channels/:path*',
      },
      {
        source: '/webhook/:path*',
        destination: 'http://localhost:8080/webhook/:path*',
      },
      {
        source: '/health',
        destination: 'http://localhost:8080/health',
      },
    ];
  },
};

module.exports = nextConfig;
