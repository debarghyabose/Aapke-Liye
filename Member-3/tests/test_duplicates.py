from app.duplicates import DuplicateIndex


def test_same_photo_is_duplicate(photo_factory):
    idx = DuplicateIndex()
    photo = photo_factory(seed=1)
    idx.add("claim-a", "9000000001", 22.57, 88.36, [photo])
    assert idx.find_photo(photo) == "claim-a"


def test_different_photo_is_not_duplicate(photo_factory):
    idx = DuplicateIndex()
    idx.add("claim-a", "9000000001", 22.57, 88.36, [photo_factory(seed=1)])
    assert idx.find_photo(photo_factory(seed=7)) is None


def test_same_phone_same_place_is_duplicate_claim():
    idx = DuplicateIndex()
    idx._claims.append(("9000000001", 22.5700, 88.3600, "claim-a"))
    assert idx.find_claim("9000000001", 22.5701, 88.3601) == "claim-a"  # ~15 m away
    assert idx.find_claim("9000000001", 22.6000, 88.4000) is None  # km away
    assert idx.find_claim("9000000002", 22.5701, 88.3601) is None  # other phone
