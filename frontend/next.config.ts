// frontend/next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
        port: '',
        pathname: '/a/**', // For Google avatars
      },
      { // ***** ADD THIS OBJECT FOR YOUR BACKEND *****
        protocol: 'http', // Your backend is on http for localhost
        hostname: 'localhost',
        port: '8000',     // The port your backend runs on
        pathname: '/static/avatars/**', // Path pattern for your avatar images
      },
    ],
  },
};

export default nextConfig;