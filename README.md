# Draw Me a Story

A Python localhost app that turns a short story into a comic storyboard. `index.html` is the story-studio frontend; `server.py` is a standard-library HTTP server that asks Gemini to break the story into panels and, when available, to draw each panel.

## Run locally

Requires Python 3.9+. No third-party packages are needed.

```bash
python3 server.py
```

Open [http://localhost:8000](http://localhost:8000), write a story, pick a panel count (3–6) and a style, and click **Make my comic**.

- **My stories** keeps your last 5 stories (with their panels) in browser storage and lets you reload any of them.
- **Download** saves the comic as an HTML page; **Download storyboard (JSON)** saves the full storyboard.

## Configuration

Put settings in a local `.env` file (ignored by Git) or in the server environment:

```bash
GEMINI_API_KEY=your-key-here
GEMINI_IMAGES=off
```

| Setting | Default | What it does |
| --- | --- | --- |
| `GEMINI_API_KEY` | none | Gemini API key. Without it the server runs in **local preview** mode and splits the story into panels by sentences, with no AI. |
| `GEMINI_IMAGES` | `on` | Set to `off` (or `false`, `0`, `no`) to skip all image requests. Panels are then shown as scene cards. |
| `GEMINI_TEXT_MODEL` | `gemini-3.5-flash` | Model used for the story plan. |
| `GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image` | Model used for panel images. |

Never put the key in `index.html` or commit it to GitHub.

### Gemini free tier: no images

Gemini's free tier has no quota for image generation, so image requests return HTTP 429. Without billing, **text-only mode is expected**: the story plan works, and each panel is shown as a scene card with its setting, mood, characters and dialogue bubbles. Set `GEMINI_IMAGES=off` to skip the image request entirely. If image requests are left on and Gemini returns 429, the server stops requesting more images for that comic. Other image errors only skip the affected panel.

## Storyboard format

`POST /api/comic` with `{"story": "...", "count": 4, "style": "Storybook color"}` returns:

```json
{
  "title": "Milo and the Moon Rabbit",
  "main_character": "Milo",
  "character_guide": "A small orange fox with a green scarf.",
  "characters": [
    {"id": "milo", "name": "Milo", "appearance": "small orange fox, green scarf"}
  ],
  "panels": [
    {
      "panel_number": 1,
      "setting": "Old apple tree at dusk",
      "mood": "curious",
      "scene": "Milo kneels beside a tiny door in the roots.",
      "caption": "Milo found a tiny door.",
      "character_ids": ["milo"],
      "dialogue": [{"speaker_id": "milo", "text": "Is anyone in there?"}],
      "image": "data:image/png;base64,... (only when an image was generated)"
    }
  ],
  "mode": "gemini-text-only",
  "warning": null
}
```

`mode` is one of `gemini` (all images), `gemini-partial` (some images), `gemini-text-only` (no images) or `local-preview` (no API key). In local preview, `characters` and each panel's `dialogue`/`character_ids` are empty.

The server checks every Gemini plan with `validate_plan()`. It verifies the panel count, panel numbering 1..N, non-empty scenes, unique lowercase character ids, that panel characters and dialogue speakers exist and appear in the panel, at most 2 dialogue lines per panel, and reasonable text lengths. An invalid plan is requested once more; if it is still invalid, the API returns a clear error.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests fake every Gemini call, so they need no API key and make no network requests.
