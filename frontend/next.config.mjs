/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emits a self-contained server bundle so the Docker image can run without node_modules.
  output: "standalone",
};

export default nextConfig;
