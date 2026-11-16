# Draw Me a Story

A Python localhost app for turning a short story into a comic layout. The visual frontend keeps its story-studio design while `server.py` connects to Gemini for panel planning and image generation.

## Run locally

```bash
python3 server.py
```

Open [http://localhost:8000](http://localhost:8000). No third-party packages are needed. Your last 5 stories are saved in browser storage ("My stories"). When Gemini image generation is unavailable (for example on the free tier), panels show scene cards with the setting, mood, characters and dialogue.

Set `GEMINI_API_KEY` in a local `.env` file or the server environment. `.env` is ignored by Git. The defaults are `gemini-3.5-flash` for the story plan and `gemini-3.1-flash-image` for illustrations; override them with `GEMINI_TEXT_MODEL` and `GEMINI_IMAGE_MODEL` if needed. Never place a secret key in `index.html` or commit it to GitHub.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests fake every Gemini call, so they need no API key and make no network requests.
