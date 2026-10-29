"""
Metrikalar xizmati bo'yicha testlar.
"""
from app.services.system_metrics import collect_metrics, format_uptime, get_history


def test_collect_metrics_shape():
    data = collect_metrics()
    assert isinstance(data, dict)
    assert "timestamp" in data
    assert "hostname" in data
    assert "platform" in data
    assert "cpu_percent" in data
    assert "memory" in data
    assert "disk" in data
    assert "uptime_seconds" in data
    assert data["data_source"] == "local"

    # Memory structure
    mem = data["memory"]
    assert "used_percent" in mem
    assert "total_bytes" in mem

    # Disk structure
    disk = data["disk"]
    assert "used_percent" in disk
    assert "free_bytes" in disk


def test_format_uptime():
    assert "0 daqiqa" in format_uptime(10)
    assert "2 daqiqa" in format_uptime(120)
    assert "1 soat" in format_uptime(3600)
    assert "1 kun" in format_uptime(86400)


def test_history_recording():
    hist = get_history()
    assert isinstance(hist, list)
    assert len(hist) > 0
    latest = hist[-1]
    assert "timestamp" in latest
    assert "cpu_percent" in latest
    assert "memory_percent" in latest
