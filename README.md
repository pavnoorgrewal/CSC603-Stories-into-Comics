# Draw Me a Story

A Python and Streamlit prototype for turning a short story into illustrated comic panels. It has a local preview mode and can use OpenAI for story breakdown and image generation when an API key is configured.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

To enable generated text and artwork, set `OPENAI_API_KEY` in your shell before starting Streamlit. Optional model overrides: `OPENAI_TEXT_MODEL` and `OPENAI_IMAGE_MODEL`.

Without a key, the app creates a local illustrated preview from the story text so the interface can be explored without making API requests.
