"""Serve the story-to-comic website and its Gemini backend."""

import base64
import json
import os
import re
import ssl
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def load_local_env():
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if line and not line.lstrip().startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def gemini_request(model, payload):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Gemini API key is not configured on the server.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json", "x-goog-api-key": key,
    }, method="POST")
    try:
        cafile = next((p for p in (os.environ.get("SSL_CERT_FILE"), "/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt") if p and Path(p).is_file()), None)
        with urlopen(request, timeout=90, context=ssl.create_default_context(cafile=cafile)) as response:
            return json.load(response)
    except HTTPError as error:
        try:
            detail = json.load(error).get("error", {}).get("message", "")
        except (ValueError, OSError):
            detail = ""
        raise RuntimeError(f"Gemini returned HTTP {error.code}: {detail[:220]}") from error
    except URLError as error:
        raise RuntimeError("Could not reach Gemini. Check the internet connection.") from error


def first_part(response, kind):
    for candidate in response.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if kind in part:
                return part[kind]
    raise RuntimeError(f"Gemini did not return {kind} content.")


def make_comic(story, count, style):
    schema = {"type": "OBJECT", "properties": {
        "main_character": {"type": "STRING"}, "character_guide": {"type": "STRING"},
        "panels": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "caption": {"type": "STRING"}, "scene": {"type": "STRING"}},
            "required": ["caption", "scene"]}}},
        "required": ["main_character", "character_guide", "panels"]}
    plan_response = gemini_request(os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.5-flash"), {
        "contents": [{"parts": [{"text": (
            f"Turn this short story into exactly {count} comic panels. Preserve events, character details, and order. "
            "Give each panel a short caption and a clear visual scene. Describe the main character's consistent appearance "
            f"in character_guide. Art style: {style}. Story:\n{story}"
        )}]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}})
    plan = json.loads(first_part(plan_response, "text"))
    panels = plan.get("panels", [])[:count]
    if len(panels) != count:
        raise RuntimeError("Gemini returned the wrong number of panels. Please try again.")
    warning = None
    for panel in panels:
        try:
            picture = gemini_request(os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"), {
                "contents": [{"parts": [{"text": (
                    f"Draw one polished comic panel in {style} style. Consistent character: {plan['character_guide']}. "
                    f"Scene: {panel['scene']}. No text, captions, logos, or speech balloons in the image."
                )}]}], "generationConfig": {"responseModalities": ["IMAGE"]}})
            inline = first_part(picture, "inlineData")
            data = inline["data"]
            base64.b64decode(data, validate=True)
            panel["image"] = f"data:{inline.get('mimeType', 'image/png')};base64,{data}"
        except (RuntimeError, ValueError, KeyError) as error:
            warning = str(error)
            break
    return {"panels": panels, "main_character": plan.get("main_character", "Your character"),
            "mode": "gemini-text-only" if warning else "gemini", "warning": warning}


class SiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path not in ("/", "/index.html"):
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path not in ("/", "/index.html"):
            self.send_error(404)
            return
        super().do_HEAD()

    def do_POST(self):
        if self.path != "/api/comic":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 20000:
                self.send_error(413)
                return
            payload = json.loads(self.rfile.read(size))
            story = str(payload.get("story", "")).strip()
            count = max(3, min(6, int(payload.get("count", 4))))
            if len(story) < 20:
                self._json(400, {"error": "Add a little more story first."})
                return
            style = str(payload.get("style", "Storybook color"))[:60]
            if os.environ.get("GEMINI_API_KEY"):
                self._json(200, make_comic(story, count, style))
                return
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", story) if s.strip()]
            panels = []
            for i in range(count):
                start = round(i * len(sentences) / count)
                end = max(start + 1, round((i + 1) * len(sentences) / count))
                caption = " ".join(sentences[start:end])
                panels.append({"caption": caption[:180], "scene": caption[:300]})
            self._json(200, {"panels": panels, "mode": "local-preview"})
        except RuntimeError as error:
            self._json(502, {"error": str(error)})
        except (ValueError, TypeError, json.JSONDecodeError, KeyError):
            self._json(400, {"error": "Please check the story and panel settings."})

    def _json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    load_local_env()
    address = ("127.0.0.1", 8000)
    print(f"Draw Me a Story running at http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, SiteHandler).serve_forever()
