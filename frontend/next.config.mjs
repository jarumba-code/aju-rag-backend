/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required for the single-container image: produces a self-contained
  // standalone server (server.js + minimal node_modules) so the final
  // image does not need the full Next.js dev toolchain at runtime.
  output: "standalone",
};

export default nextConfig;
