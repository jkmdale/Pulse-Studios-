# Assets

This directory holds binary assets that must be sourced separately.

## lullaby_template.mp3 (required for production)

A royalty-free piano track used as the base for the custom lullaby.

**Specifications:**
- Format: MP3, stereo, 44.1 kHz, 128+ kbps
- Target tempo: 60–80 BPM (slower than baby's heartbeat — will be time-stretched to match)
- Duration: minimum 3 minutes (the lullaby_composer will loop if shorter, but longer is better)
- License: royalty-free, suitable for commercial use

**Recommended sources:**
- [Musopen](https://musopen.org) — public domain classical piano recordings
- [Free Music Archive](https://freemusicarchive.org) — search "piano lullaby"
- [Pixabay Music](https://pixabay.com/music) — filter by "lullaby"

**Development / CI placeholder:**
`lullaby_composer.py` automatically generates a sine-wave placeholder tone when
`lullaby_template.mp3` is absent. This is sufficient for running tests and verifying
the pipeline end-to-end, but the output will not be musically pleasant.

## fonts/ (required for print PDF)

Lato font files are required for proper TTF embedding in the print PDF.
Standard PDF fonts (Helvetica, Times) are NOT embedded by reportlab by default
and will be rejected by professional print services.

Download from [Google Fonts — Lato](https://fonts.google.com/specimen/Lato):
- `fonts/Lato-Regular.ttf`
- `fonts/Lato-Light.ttf`

These files are not committed to the repository to keep the repo size small.
Add them to `assets/fonts/` before running the PDF generator in production.
