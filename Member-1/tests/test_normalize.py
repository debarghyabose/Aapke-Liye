import pytest

from app.normalize import native_digits_to_ascii, normalize_text


@pytest.mark.parametrize("text,amount", [
    ("do lakh ka nuksaan", 200000),
    ("do lakh pachas hazaar", 250000),
    ("dedh lakh rupaye", 150000),
    ("₹50,000 ka", 50000),
    ("1.5 lakh", 150000),
    ("2lakh", 200000),
    ("about 3 lakh rupees", 300000),
    ("forty thousand", 40000),
    ("दो लाख का नुकसान", 200000),
    ("पचास हज़ार", 50000),
    ("ढाई लाख", 250000),
    ("एक लाख रुपयांचे", 100000),          # Marathi
    ("पन्नास हजार रुपयांचे", 50000),       # Marathi
    ("প্রায় এক লাখ টাকার", 100000),       # Bengali
    ("চল্লিশ হাজার টাকা", 40000),          # Bengali
    ("రెండు లక్షల రూపాయల", 200000),        # Telugu
    ("ముప్పై వేల రూపాయలు", 30000),         # Telugu
    ("ஒரு லட்சம் ரூபாய்", 100000),         # Tamil
    ("२ लाख", 200000),                     # Devanagari digits
    ("৫০ হাজার", 50000),                   # Bengali digits
])
def test_amounts(text, amount):
    assert amount in normalize_text(text).amounts


def test_phone_and_year_are_not_amounts():
    n = normalize_text("mera number 9876543210 hai, saal 2026")
    assert n.amounts == []
    assert "9876543210" in n.text


def test_dates_survive():
    assert "14/08/2026" in normalize_text("on 14/08/2026 the flood").text


def test_plain_words_untouched():
    n = normalize_text("I do not know")
    assert n.text == "I do not know"
    assert n.amounts == []


def test_native_digits():
    assert native_digits_to_ascii("९८७६ ৫৪৩ ౨౧ ௦") == "9876 543 21 0"


def test_piped_ffmpeg_wav_sizes_are_fixed():
    """ffmpeg writing WAV to a pipe leaves placeholder sizes; duration must use real bytes."""
    import io
    import wave

    from app.audio import _fix_wav_sizes, _wav_duration

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000 * 2)          # 2 seconds
    wav = bytearray(buf.getvalue())
    wav[4:8] = b"\xff\xff\xff\xff"                       # what ffmpeg writes to a pipe
    wav[40:44] = b"\xff\xff\xff\xff"
    assert round(_wav_duration(_fix_wav_sizes(bytes(wav))), 2) == 2.0
