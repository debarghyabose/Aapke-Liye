# Sample recordings

Record each script in `../golden/cases.json` and save it as `<language>/<id>.wav`,
for example `hi/hi_house.wav`. Any format works if ffmpeg is installed; otherwise
use 16 kHz mono WAV.

- Ask native speakers to read the script once, then say it again in their own words.
  Save the second take as `<id>_free.wav`.
- Record 1 clip per language with background noise (fan, traffic, rain).
- Run `python eval.py --audio` to score transcripts + extraction together.

Recordings are git-ignored. Share them through the team drive instead.
