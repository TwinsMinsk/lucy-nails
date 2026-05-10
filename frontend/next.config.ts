import type { NextConfig } from "next";

const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://localhost:8000/api"
    : "https://api.lucysmirnova.ru/api");
const apiOrigin = (() => {
  try {
    return new URL(apiUrl).origin;
  } catch {
    return "'self'";
  }
})();

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              [
                "default-src 'self'",
                "base-uri 'self'",
                `connect-src 'self' ${apiOrigin} https://kinescope.io https://*.kinescope.io https://cloudflareinsights.com https://static.cloudflareinsights.com`,
                "font-src 'self' data:",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "frame-src 'self' https://kinescope.io https://*.kinescope.io https://www.youtube.com https://*.youtube.com",
                "img-src 'self' data: blob: https:",
                "media-src 'self' blob: https://kinescope.io https://*.kinescope.io",
                "object-src 'none'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://static.cloudflareinsights.com",
                "style-src 'self' 'unsafe-inline'",
              ].join("; "),
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.kinescope.io',
      },
      {
        protocol: 'https',
        hostname: 'kinescope.io',
      },
      {
        protocol: 'https',
        hostname: '*.up.railway.app',
      },
      {
        protocol: 'https',
        hostname: 'lucysmirnova.ru',
      },
      {
        protocol: 'https',
        hostname: 'www.lucysmirnova.ru',
      },
      {
        protocol: 'https',
        hostname: 'api.lucysmirnova.ru',
        pathname: '/uploads/**',
      },
    ],
  },
};

export default nextConfig;
