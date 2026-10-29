"""
Diagnostika va tahlil qoidalari bo'yicha testlar.
"""
import pytest
from app.services.network_diagnostics import validate_target
from app.services.diagnostic_rules import analyze_metrics, get_system_summary_status


def test_validate_target_valid():
    assert validate_target("8.8.8.8") == "8.8.8.8"
    assert validate_target("google.com") == "google.com"
    assert validate_target("sub.domain-test.uz") == "sub.domain-test.uz"


def test_validate_target_invalid():
    with pytest.raises(ValueError):
        validate_target("")

    with pytest.raises(ValueError):
        validate_target("bad;rm -rf /")

    with pytest.raises(ValueError):
        validate_target("http://google.com")


def test_analyze_metrics_rules():
    # Test high CPU & RAM
    dummy_metrics = {
        "cpu_percent": 95.0,
        "memory": {"used_percent": 92.0, "total_bytes": 16000000000},
        "disk": {"used_percent": 95.0, "total_bytes": 100000000000, "free_bytes": 5000000000}  # 5% free -> Critical
    }
    findings = analyze_metrics(dummy_metrics)
    levels = [f["level"] for f in findings]
    assert "Muhim" in levels

    summary = get_system_summary_status(findings)
    assert summary["status"] == "critical"


def test_analyze_metrics_normal():
    dummy_metrics = {
        "cpu_percent": 25.0,
        "memory": {"used_percent": 45.0, "total_bytes": 16000000000},
        "disk": {"used_percent": 30.0, "total_bytes": 100000000000, "free_bytes": 70000000000}
    }
    findings = analyze_metrics(dummy_metrics)
    levels = [f["level"] for f in findings]
    assert "Muhim" not in levels
    assert "Diqqat" not in levels

    summary = get_system_summary_status(findings)
    assert summary["status"] == "good"
