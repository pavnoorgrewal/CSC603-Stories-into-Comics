"""Draw Me a Story: turn a short story into a comic strip."""

from __future__ import annotations

import base64
import html
import json
import os
import textwrap
from io import BytesIO

import streamlit as st
from PIL import Image, ImageDraw, ImageFont


st.set_page_config(page_title="Draw Me a Story", page_icon="✦", layout="wide")

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --ink:#20211f; --paper:#f4f0e7; --orange:#f26c43; --muted:#817d72; }
html, body, [class*="css"] { font-family:'Space Grotesk',sans-serif; color:var(--ink); }
.stApp { background:var(--paper); }
[data-testid="stSidebar"] { background:#e9e3d6; }
.hero { padding:2.1rem 0 1.2rem; border-bottom:1px solid #c9c2b5; margin-bottom:1.6rem; }
.eyebrow { font-family:'DM Mono',monospace; font-size:.72rem; letter-spacing:.13em; text-transform:uppercase; color:var(--orange); }
.hero h1 { font-size:clamp(2.6rem,6vw,5rem); line-height:.95; letter-spacing:-.075em; margin:.5rem 0 1rem; }
.hero p { color:#656156; font-size:1.05rem; max-width:620px; }
.comic-card { background:#fffdf8; border:2px solid var(--ink); border-radius:5px; overflow:hidden; box-shadow:4px 4px 0 var(--ink); margin:0 0 1.2rem; }
.comic-card img { display:block; width:100%; aspect-ratio:4/3; object-fit:cover; background:#e9e3d6; }
.comic-caption { padding:.85rem 1rem 1rem; border-top:2px solid var(--ink); }
.comic-caption small { font: .68rem 'DM Mono',monospace; color:var(--orange); text-transform:uppercase; letter-spacing:.08em; }
.comic-caption p { margin:.35rem 0 0; font-size:.94rem; line-height:1.45; }
.note { color:#777164; font-size:.82rem; }
div.stButton > button[kind="primary"] { background:var(--orange); border:2px solid var(--ink); color:#fff; font-weight:700; box-shadow:3px 3px 0 var(--ink); }
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)


def demo_panels(story: str, count: int) -> list[dict[str, str]]:
    """A deterministic local preview so the app is usable without API credentials."""
    bits = [part.strip() for part in story.replace("!", ".").replace("?", ".").split(".") if part.strip()]
    if not bits:
        bits = [story.strip()]
    colors = ["#f7b267", "#8ecae6", "#cdb4db", "#a8dadc", "#ffafcc", "#b7d7a8"]
    panels = []
    for i in range(count):
        sentence = bits[min(round(i * (len(bits) - 1) / max(count - 1, 1)), len(bits) - 1)]
        panels.append({
            "scene": sentence,
            "caption": sentence,
            "image": make_placeholder(sentence, colors[i % len(colors)]),
        })
    return panels


def make_placeholder(caption: str, color: str) -> bytes:
    image = Image.new("RGB", (900, 675), "#fffdf8")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((16, 16, 884, 659), radius=20, fill=color, outline="#20211f", width=8)
    # A simple scene stage makes demo panels feel like comic frames, not broken images.
    draw.ellipse((330, 150, 570, 390), fill="#f4f0e7", outline="#20211f", width=7)
    draw.arc((370, 235, 490, 330), start=15, end=165, fill="#20211f", width=7)
    draw.ellipse((390, 230, 410, 250), fill="#20211f")
    draw.ellipse((490, 230, 510, 250), fill="#20211f")
    draw.rounded_rectangle((275, 390, 625, 470), radius=24, fill="#fffdf8", outline="#20211f", width=6)
    try:
        font = ImageFont.truetype("Arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    lines = textwrap.wrap(caption, width=33)[:2]
    for n, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font)
        draw.text(((900 - (box[2] - box[0])) / 2, 505 + n * 39), line, fill="#20211f", font=font)
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def generate_with_openai(story: str, count: int, style: str) -> list[dict[str, str]]:
    """Generate panel plans and images using OpenAI when a key is configured."""
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(
        model=os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini"),
        instructions=(
            "Adapt the user's short story into a faithful comic. Return JSON only with a 'panels' array. "
            "Each panel must contain 'scene' (visual description) and 'caption' (short narration/dialogue). "
            "Preserve the story's characters and sequence. Do not add plot events."
        ),
        input=f"Make exactly {count} panels in this art direction: {style}. Story:\n{story}",
        text={"format": {"type": "json_object"}},
    )
    plan = json.loads(response.output_text)
    panels = []
    for panel in plan["panels"][:count]:
        image_response = client.images.generate(
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            prompt=(f"Single comic panel illustration, {style}. Scene: {panel['scene']}. "
                    "No words or lettering inside the image. Clear composition, expressive characters."),
            size="1024x1024",
        )
        panels.append({**panel, "image": base64.b64decode(image_response.data[0].b64_json)})
    return panels


st.markdown(
    '<div class="hero"><div class="eyebrow">A tiny story studio · Prototype 01</div>'
    '<h1>Draw me<br>a story.</h1>'
    '<p>Drop in a short story. Get a sequence of illustrated comic panels, ready to read and share.</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Make it yours")
    panel_count = st.slider("Panels", min_value=2, max_value=6, value=4)
    art_style = st.selectbox("Art direction", ["Warm indie comic", "Watercolor picture book", "Bold graphic novel", "Playful Saturday cartoon"])
    st.markdown("---")
    st.markdown('<p class="note">Add an <code>OPENAI_API_KEY</code> to enable generated artwork. Without one, the local preview still works.</p>', unsafe_allow_html=True)

story = st.text_area(
    "Your story",
    placeholder="A curious little fox found a brass key beneath the old apple tree...",
    height=190,
    max_chars=5000,
    label_visibility="collapsed",
)
left, right = st.columns([1, 2])
with left:
    make_comic = st.button("✦  Make my comic", type="primary", use_container_width=True)
with right:
    st.markdown('<p class="note">A few sentences work best. Your story becomes a panel-by-panel visual retelling.</p>', unsafe_allow_html=True)

if make_comic:
    if len(story.strip()) < 20:
        st.warning("Add a little more story first (at least a sentence or two).")
    else:
        with st.spinner("Laying out your story…"):
            try:
                if os.getenv("OPENAI_API_KEY"):
                    st.session_state.panels = generate_with_openai(story, panel_count, art_style)
                    st.session_state.demo = False
                else:
                    st.session_state.panels = demo_panels(story, panel_count)
                    st.session_state.demo = True
                st.session_state.source_story = story
            except Exception as exc:
                st.error(f"Comic generation hit a snag: {exc}")

if st.session_state.get("panels"):
    st.markdown("---")
    title_col, tag_col = st.columns([3, 1])
    with title_col:
        st.markdown("## Your story, panel by panel")
    with tag_col:
        if st.session_state.get("demo"):
            st.caption("LOCAL PREVIEW · API KEY NOT SET")
    panels = st.session_state.panels
    cols = st.columns(2)
    for i, panel in enumerate(panels):
        with cols[i % 2]:
            st.markdown(
                f'<div class="comic-card"><img src="data:image/png;base64,{base64.b64encode(panel["image"]).decode()}">'
                f'<div class="comic-caption"><small>Panel {i + 1:02d}</small><p>{html.escape(panel["caption"])}</p></div></div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                f"Download panel {i + 1}", panel["image"], file_name=f"story-panel-{i + 1}.png",
                mime="image/png", key=f"download-{i}",
            )
