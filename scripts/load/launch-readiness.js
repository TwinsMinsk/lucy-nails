import crypto from "k6/crypto";
import http from "k6/http";
import { check, fail, sleep } from "k6";
import { SharedArray } from "k6/data";

const apiBase = (__ENV.API_BASE_URL || "").replace(/\/$/, "");
const courseId = __ENV.COURSE_ID || "default";
const coursePrice = __ENV.COURSE_PRICE || "0";
const prodamusSecret = __ENV.PRODAMUS_SECRET_KEY || "";
const profile = __ENV.LOAD_PROFILE || "acceptance";
const learners = new SharedArray("learners", () => __ENV.LEARNERS_FILE ? JSON.parse(open(__ENV.LEARNERS_FILE)) : []);

if (__ENV.ALLOW_STAGING_LOAD !== "true") {
  throw new Error("Set ALLOW_STAGING_LOAD=true after confirming the target is an isolated staging environment");
}
const targetHost = /^https?:\/\/([^/:]+)/.exec(apiBase)?.[1]?.toLowerCase();
if (!targetHost || !(targetHost === "127.0.0.1" || targetHost === "localhost" || targetHost === "host.docker.internal" || /^([a-z0-9]+-)*staging([.-][a-z0-9-]+)+$/.test(targetHost) || /^([a-z0-9-]+\.)*staging\.[a-z0-9.-]+$/.test(targetHost))) {
  throw new Error("API_BASE_URL must point to staging or localhost; production load is blocked by this script");
}
if (!["acceptance", "smoke"].includes(profile)) throw new Error("Unknown LOAD_PROFILE");
if (profile === "acceptance" && learners.length < 100) throw new Error("Acceptance requires 100 separate verified staging learner accounts in LEARNERS_FILE");
if (learners.length && (learners.some(learner => !learner.access_token) || new Set(learners.map(learner => learner.access_token)).size !== learners.length)) throw new Error("Learner fixtures must contain distinct preauthenticated session-bound access tokens");
if (!prodamusSecret || coursePrice === "0") {
  throw new Error("PRODAMUS_SECRET_KEY and COURSE_PRICE are required for the signed webhook scenario");
}

export const options = {
  scenarios: {
    public_reads: {
      executor: "ramping-vus",
      exec: "learnerRead",
      startVUs: profile === "smoke" ? 5 : 50,
      stages: profile === "smoke" ? [{duration: "60s", target: 5}] : [{duration: "15m", target: 50}, {duration: "1s", target: 100}, {duration: "5m", target: 100}],
      gracefulRampDown: "10s",
    },
    checkout_burst: {
      executor: "per-vu-iterations",
      exec: "createCheckout",
      vus: 10,
      iterations: 1,
      maxDuration: "30s",
      startTime: "5s",
    },
    webhook_burst: {
      executor: "constant-arrival-rate",
      exec: "repeatWebhook",
      rate: 5,
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
    checks: ["rate>0.99"],
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
    offer_accepted: true,
    personal_data_consent: true,
  }), { headers: { "Content-Type": "application/json" }, tags: { operation: "checkout" } });
}

export function setup() {
  const email = `load-webhook-${Date.now()}@example.com`;
  const response = guestCheckout(email);
  if (!check(response, { "setup checkout created": (item) => item.status === 200 })) {
    fail(`Unable to prepare load order: HTTP ${response.status}`);
  }
  const order = response.json();
  return { orderId: order.order_id, email };
}

export function learnerRead() {
  const learner = learners[(__VU - 1) % learners.length];
  const headers = learner ? {Authorization: `Bearer ${learner.access_token}`} : {};
  const path = learner ? `/courses/${courseId}/my-progress` : `/courses/${courseId}`;
  const response = http.get(`${apiBase}${path}`, {headers, tags: {operation: "course"}});
  check(response, {"course API successful": r => r.status === 200});
  if (learner?.lesson_id) {
    const lessonId = learner.lesson_ids?.[__ITER % learner.lesson_ids.length] || learner.lesson_id;
    const lesson = http.get(`${apiBase}/lessons/${lessonId}`, {headers, tags: {operation: "lesson"}});
    check(lesson, {"paid lesson accessible": r => r.status === 200});
  }
  sleep(90 + Math.random() * 30);
}

export function createCheckout() {
  const email = `load-checkout-${__VU}-${Date.now()}@example.com`;
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
