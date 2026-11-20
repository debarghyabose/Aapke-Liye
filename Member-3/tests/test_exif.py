from datetime import datetime

from app.exif_check import gps_in_zone, read_exif, timestamp_valid


def test_reads_gps_and_time(photo_factory):
    photo = photo_factory(lat=22.57, lon=88.36, taken_at=datetime(2026, 11, 5, 10, 0, 0))
    info = read_exif(photo)
    assert abs(info["lat"] - 22.57) < 0.001
    assert abs(info["lon"] - 88.36) < 0.001
    assert info["taken_at"] == datetime(2026, 11, 5, 10, 0, 0)


def test_missing_exif_returns_none(photo_factory):
    info = read_exif(photo_factory())
    assert info == {"lat": None, "lon": None, "taken_at": None}


def test_zone_check():
    assert gps_in_zone(22.60, 88.40) is True  # Kolkata, inside demo zone
    assert gps_in_zone(28.61, 77.20) is False  # Delhi, outside
    assert gps_in_zone(None, None) is None


def test_timestamp_check():
    now = datetime(2026, 11, 20)
    assert timestamp_valid(datetime(2026, 11, 5), now) is True
    assert timestamp_valid(datetime(2026, 10, 1), now) is False  # before the disaster
    assert timestamp_valid(datetime(2026, 12, 1), now) is False  # in the future
