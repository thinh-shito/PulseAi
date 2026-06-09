/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output for production Docker image (smaller, faster startup)
  output: process.env.NODE_ENV === "production" ? "standalone" : undefined,
};

export default nextConfig;
