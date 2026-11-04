from scripts.ops.check_russia_reachability import evaluate


def _probe(status_code=None, raw_output="", city="Moscow", network="MTS"):
    return {
        "probe": {"city": city, "network": network},
        "result": {"status": "finished" if status_code else "failed", "statusCode": status_code, "rawOutput": raw_output},
    }


def test_evaluate_counts_expected_status_codes():
    verdict = evaluate("lucysmirnova.ru", [_probe(200), _probe(200), _probe(502)], {200})

    assert (verdict.ok, verdict.total) == (2, 3)
    assert verdict.failures == ["Moscow / MTS: 502"]


def test_evaluate_reports_first_line_of_timeout():
    verdict = evaluate(
        "lucysmirnova.ru",
        [_probe(raw_output="Request timed out during the TLS handshake.\nmore", network="Rostelecom")],
        {200},
    )

    assert verdict.failures == ["Moscow / Rostelecom: Request timed out during the TLS handshake."]


def test_passed_uses_ratio_and_rejects_empty_results():
    assert evaluate("h", [_probe(200)] * 7 + [_probe(502)] * 3, {200}).passed(0.7)
    assert not evaluate("h", [_probe(200)] * 6 + [_probe(502)] * 4, {200}).passed(0.7)
    assert not evaluate("h", [], {200}).passed(0.7)
