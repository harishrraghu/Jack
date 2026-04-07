/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produces a self-contained server bundle in .next/standalone
  // so the Docker image only needs `node server.js` to run.
  output: "standalone",
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;

