import crypto from "k6/crypto";
import http from "k6/http";
import { check, fail } from "k6";

const apiBase = (__ENV.API_BASE_URL || "").replace(/\/$/, "");
const courseId = __ENV.COURSE_ID || "default";
const coursePrice = __ENV.COURSE_PRICE || "0";
const prodamusSecret = __ENV.PRODAMUS_SECRET_KEY || "";

if (__ENV.ALLOW_STAGING_LOAD !== "true") {
  throw new Error("Set ALLOW_STAGING_LOAD=true after confirming the target is an isolated staging environment");
}
if (!apiBase || (!apiBase.includes("staging") && !apiBase.includes("127.0.0.1") && !apiBase.includes("localhost"))) {
  throw new Error("API_BASE_URL must point to staging or localhost; production load is blocked by this script");
}
if (!prodamusSecret || coursePrice === "0") {
  throw new Error("PRODAMUS_SECRET_KEY and COURSE_PRICE are required for the signed webhook scenario");
}

export const options = {
  scenarios: {
    public_reads: {
      executor: "constant-vus",
      exec: "publicRead",
      vus: 100,
      duration: "60s",
    },
    checkout_burst: {
      executor: "per-vu-iterations",
      exec: "createCheckout",
      vus: 20,
      iterations: 1,
      maxDuration: "30s",
      startTime: "5s",
    },
    webhook_burst: {
      executor: "constant-arrival-rate",
      exec: "repeatWebhook",
      rate: 10,
      timeUnit: "1s",
      duration: "10s",
      preAllocatedVUs: 10,
      maxVUs: 30,
      startTime: "15s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

function stringifyValues(value) {
  if (Array.isArray(value)) return value.map(stringifyValues);
  if (value && typeof value === "object") {
    return Object.keys(value).sort().reduce((result, key) => {
      result[key] = stringifyValues(value[key]);
      return result;
    }, {});
  }
  return String(value);
}

function sign(payload) {
  const canonical = JSON.stringify(stringifyValues(payload)).replace(/\//g, "\\/");
  return crypto.hmac("sha256", prodamusSecret, canonical, "hex");
}

function guestCheckout(email) {
  return http.post(`${apiBase}/payments/guest-link`, JSON.stringify({
    course_id: courseId,
    tariff: "self",
    customer_email: email,
  }), { headers: { "Content-Type": "application/json" }, tags: { operation: "checkout" } });
}

export function setup() {
  const email = `load-webhook-${Date.now()}@example.test`;
  const response = guestCheckout(email);
  if (!check(response, { "setup checkout created": (item) => item.status === 200 })) {
    fail(`Unable to prepare load order: HTTP ${response.status}`);
  }
  const order = response.json();
  return { orderId: order.order_id, email };
}

export function publicRead() {
  const response = http.get(`${apiBase.replace(/\/api$/, "")}/health`, { tags: { operation: "health" } });
  check(response, { "health is successful": (item) => item.status === 200 });
}

export function createCheckout() {
  const email = `load-checkout-${__VU}-${Date.now()}@example.test`;
  const response = guestCheckout(email);
  check(response, { "checkout is created": (item) => item.status === 200 });
}

export function repeatWebhook(data) {
  const payload = {
    order_id: data.orderId,
    customer_email: data.email,
    sum: coursePrice,
    currency: "rub",
    payment_status: "success",
    payment_id: `load-${data.orderId}`,
  };
  const response = http.post(`${apiBase}/payments/webhook`, JSON.stringify(payload), {
    headers: { "Content-Type": "application/json", Sign: sign(payload) },
    tags: { operation: "webhook" },
  });
  check(response, { "webhook is idempotently accepted": (item) => item.status === 200 });
}
