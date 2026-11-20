# Stage demo photos (Puri)

Made by `scripts/make_stage_photos.py` from the photos in `../photos`. Only the EXIF is changed: GPS of a
building that Copernicus EMS graded "Destroyed" inside the Cyclone Fani flood map (Puri), and the time
the script was run. Credits and licenses: `../photos/ATTRIBUTION.md` (CC BY / CC BY-SA, GODL-India).

**On demo day:** rerun the script so the capture time is fresh, then restart with `.\start-all.ps1`.
Upload each photo only once: a second upload of the same photo is (correctly) flagged as a duplicate.
For the cleanest result, block location access for the app in the browser, so the photo's own GPS is used.
