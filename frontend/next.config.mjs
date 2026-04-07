/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export — produces an `out/` directory of plain HTML/CSS/JS.
  // Required for GitHub Pages and nginx-based Docker serving.
  output: "export",

  // When deployed to GitHub Pages the site lives at /<repo-name>.
  // Set NEXT_PUBLIC_BASE_PATH=/Jack (or leave empty for a custom domain).
  basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? "",
  assetPrefix: process.env.NEXT_PUBLIC_BASE_PATH ?? "",

  // Next.js image optimisation requires a server; disable for static export.
  images: {
    unoptimized: true,
  },

  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;

