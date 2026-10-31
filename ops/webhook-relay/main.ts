// Provider webhook relay for Deno Deploy.
//
// Russian data centres, where Prodamus runs, cannot complete TLS to Railway,
// so provider callbacks are sent here and forwarded unchanged. The backend
// still verifies the Prodamus Sign header and the Kinescope Basic auth: this
// relay trusts nothing and adds nothing.

// RELAY_UPSTREAM is only for local testing against a dev backend.
const UPSTREAM = Deno.env.get("RELAY_UPSTREAM") ?? "https://api.lucysmirnova.ru";

// Only endpoints that authenticate the caller themselves may be relayed.
const RELAYED_PATHS = new Set([
  "/api/payments/webhook",
  "/api/integrations/kinescope/drm/authorize",
]);

const MAX_BODY_BYTES = 64 * 1024;

// Hop-by-hop headers and ones fetch() sets itself.
const DROPPED_REQUEST_HEADERS = new Set([
  "host",
  "connection",
  "content-length",
  "transfer-encoding",
  "keep-alive",
  "upgrade",
  "te",
  "trailer",
  "proxy-authorization",
  "proxy-connection",
]);

// fetch() already decoded the body, so the original encoding headers are stale.
const DROPPED_RESPONSE_HEADERS = new Set([
  "content-encoding",
  "content-length",
  "transfer-encoding",
  "connection",
]);

Deno.serve(async (request) => {
  const url = new URL(request.url);
  if (url.pathname === "/healthz") {
    return new Response("ok");
  }
  if (!RELAYED_PATHS.has(url.pathname)) {
    return new Response("Not Found", { status: 404 });
  }

  let body: ArrayBuffer | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    body = await request.arrayBuffer();
    if (body.byteLength > MAX_BODY_BYTES) {
      return new Response("Payload Too Large", { status: 413 });
    }
  }

  const headers = new Headers();
  for (const [name, value] of request.headers) {
    if (!DROPPED_REQUEST_HEADERS.has(name.toLowerCase())) {
      headers.set(name, value);
    }
  }

  try {
    const upstream = await fetch(UPSTREAM + url.pathname + url.search, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
      signal: AbortSignal.timeout(20_000),
    });
    const responseHeaders = new Headers();
    for (const [name, value] of upstream.headers) {
      if (!DROPPED_RESPONSE_HEADERS.has(name.toLowerCase())) {
        responseHeaders.set(name, value);
      }
    }
    console.log(`${request.method} ${url.pathname} -> ${upstream.status}`);
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error(`${request.method} ${url.pathname} -> upstream error`, error);
    return new Response("Bad Gateway", { status: 502 });
  }
});
