const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
});

const withPWA = require("next-pwa")({
  dest: "public",
});

module.exports = withBundleAnalyzer(
  withPWA({
    reactStrictMode: true,
    async rewrites() {
      return [
        {
          source: "/:locale/:workspaceid/rag-chat/:path*",
          destination: "/:locale/:workspaceid/chat/:path*",
        },
      ]
    },
    images: {
      remotePatterns: [
        {
          protocol: "http",
          hostname: "localhost",
        },
        {
          protocol: "http",
          hostname: "127.0.0.1",
        },
        {
          protocol: "https",
          hostname: "**",
        },
      ],
    },
    experimental: {
      serverComponentsExternalPackages: ["sharp", "onnxruntime-node"],
    },
  }) // 🔴 여기 괄호 제대로 닫아야 함
);
