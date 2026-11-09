"""Check that the site opens from Russian home and mobile networks.

Russian ISPs have blocked Railway's network before (see ops/proxy). A monitor in the US or EU
cannot see such a block, so this script asks Globalping probes on Russian eyeball networks to
load the site and the API, and checks that the site certificates are not about to expire.

Exit code 1 means visitors in Russia are likely affected. A Globalping outage or rate limit
is reported as a warning and exits 0, so it does not raise a false alarm.

Optional environment: GLOBALPING_TOKEN (higher rate limit), RU_PROBES (default 10),
MIN_SUCCESS_RATIO (default 0.7), MIN_CERT_DAYS (default 14).
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

API = "https://api.globalping.io/v1/measurements"
TARGETS = (
    ("lucysmirnova.ru", "/", {200}),
    ("api.lucysmirnova.ru", "/health", {200}),
)
CERT_HOSTS = ("lucysmirnova.ru", "www.lucysmirnova.ru", "api.lucysmirnova.ru")


class ProbeServiceUnavailable(RuntimeError):
    """Globalping could not run the measurement; says nothing about the site."""


@dataclass
class Verdict:
    host: str
    ok: int
    total: int
    failures: list[str]

    def passed(self, min_ratio: float) -> bool:
        return self.total > 0 and self.ok / self.total >= min_ratio


def evaluate(host: str, results: list[dict], expected: set[int]) -> Verdict:
    ok = 0
    failures = []
    for item in results:
        result = item.get("result") or {}
        probe = item.get("probe") or {}
        if result.get("statusCode") in expected:
            ok += 1
            continue
        reason = result.get("statusCode") or (result.get("rawOutput") or result.get("status") or "?").splitlines()[0]
        failures.append(f"{probe.get('city', '?')} / {probe.get('network', '?')}: {reason}")
    return Verdict(host, ok, len(results), failures)


def _request(method: str, url: str, body: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json", "User-Agent": "lucy-nails-reachability"}
    token = os.getenv("GLOBALPING_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data, headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 429 or exc.code >= 500:
            raise ProbeServiceUnavailable(f"Globalping HTTP {exc.code}") from exc
        raise
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProbeServiceUnavailable(f"Globalping unreachable: {exc}") from exc


def measure(host: str, path: str, probes: int) -> list[dict]:
    body = {
        "type": "http",
        "target": host,
        "locations": [{"magic": "RU+eyeball-network", "limit": probes}],
        "measurementOptions": {"protocol": "HTTPS", "request": {"method": "GET", "path": path}},
    }
    measurement_id = _request("POST", API, body)["id"]
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        time.sleep(5)
        measurement = _request("GET", f"{API}/{measurement_id}")
        if measurement.get("status") != "in-progress":
            return measurement.get("results") or []
    raise ProbeServiceUnavailable(f"measurement {measurement_id} did not finish")


def cert_days_left(host: str) -> int:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    with socket.create_connection((host, 443), timeout=15) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls:
            not_after = tls.getpeercert()["notAfter"]
    expires = datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), tz=timezone.utc)
    return (expires - datetime.now(timezone.utc)).days


def main() -> int:
    probes = int(os.getenv("RU_PROBES", "10"))
    min_ratio = float(os.getenv("MIN_SUCCESS_RATIO", "0.7"))
    min_cert_days = int(os.getenv("MIN_CERT_DAYS", "14"))
    problems: list[str] = []
    report: list[str] = []

    for host, path, expected in TARGETS:
        try:
            verdict = evaluate(host, measure(host, path, probes), expected)
        except ProbeServiceUnavailable as exc:
            print(f"::warning::Russia check for {host} skipped: {exc}")
            report.append(f"- `{host}{path}`: skipped ({exc})")
            continue
        report.append(f"- `{host}{path}`: {verdict.ok}/{verdict.total} Russian home/mobile probes OK")
        for failure in verdict.failures:
            report.append(f"  - {failure}")
        if not verdict.passed(min_ratio):
            problems.append(f"{host}{path} opened for {verdict.ok}/{verdict.total} probes in Russia")

    for host in CERT_HOSTS:
        try:
            days = cert_days_left(host)
        except (OSError, ssl.SSLError) as exc:
            problems.append(f"TLS check for {host} failed: {exc}")
            report.append(f"- certificate `{host}`: error {exc}")
            continue
        report.append(f"- certificate `{host}`: {days} days left")
        if days < min_cert_days:
            problems.append(f"certificate for {host} expires in {days} days")

    text = "\n".join(report)
    print(text)
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## Reachability from Russia\n\n" + text + "\n")
    for problem in problems:
        print(f"::error::{problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
