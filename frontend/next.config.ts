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

// Yandex Metrika hosts (counter, Webvisor, its websocket transport) for the
// audience regions; full list: yandex.ru/support/metrica/code/install-counter-csp
const metrikaOrigins = [
  "https://mc.yandex.ru",
  "https://mc.yandex.by",
  "https://mc.yandex.kz",
  "https://mc.yandex.com",
  "https://mc.webvisor.com",
  "https://mc.webvisor.org",
];
const metrikaSockets = metrikaOrigins.map((origin) => origin.replace("https://", "wss://"));
// Metrika opens the site in a frame to replay Webvisor sessions and click maps.
const metrikaFrameAncestors = [
  "https://metrika.yandex.ru",
  "https://metrika.yandex.by",
  "https://metrika.yandex.kz",
  "https://metrika.yandex.com",
  "https://metrica.yandex.ru",
  "https://metrica.yandex.by",
  "https://metrica.yandex.com",
  "https://metrika.ya.ru",
  "https://metrica.ya.ru",
  "https://metr.yandex.ru",
  "https://analytics.yandex.ru",
  "https://analytics.yandex.by",
  "https://analytics.yandex.com",
];

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
                `connect-src 'self' ${apiOrigin} https://kinescope.io https://*.kinescope.io https://cloudflareinsights.com https://static.cloudflareinsights.com ${metrikaOrigins.join(" ")} ${metrikaSockets.join(" ")}`,
                "font-src 'self' data:",
                "form-action 'self'",
                `frame-ancestors ${metrikaFrameAncestors.join(" ")}`,
                `frame-src 'self' https://kinescope.io https://*.kinescope.io https://www.youtube.com https://*.youtube.com ${metrikaOrigins.join(" ")}`,
                `img-src 'self' data: blob: https: ${apiOrigin}`,
                // Ad reels in the admin play from the API host by signed link.
                `media-src 'self' blob: ${apiOrigin} https://kinescope.io https://*.kinescope.io`,
                "object-src 'none'",
                `script-src 'self' 'unsafe-inline' 'unsafe-eval' https://static.cloudflareinsights.com ${metrikaOrigins.join(" ")} https://yastatic.net`,
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
          ...(process.env.NODE_ENV === "production"
            ? [
                {
                  key: "Strict-Transport-Security",
                  value: "max-age=31536000; includeSubDomains",
                },
              ]
            : []),
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
