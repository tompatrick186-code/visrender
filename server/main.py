"""
VisRender — Auto Render Server
Receives order form submissions, generates AI renders, emails results.
"""

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import resend
import requests
import base64
import os
import uuid
from pathlib import Path
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STABILITY_API_KEY = os.environ["STABILITY_API_KEY"].strip()
RESEND_API_KEY    = os.environ["RESEND_API_KEY"].strip()
FROM_EMAIL        = "hello@visrender.co.uk"
FROM_NAME         = "Tom at VisRender"
NOTIFY_EMAIL      = "hello@visrender.co.uk"

resend.api_key = RESEND_API_KEY

STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/control/structure"


def generate_render(photo_bytes: bytes, filename: str, description: str, style: str = "") -> bytes:
    style_hint = f" {style} style," if style else ""
    prompt = (
        f"Professional landscape garden design,{style_hint} "
        f"{description}. "
        "Photorealistic, beautifully designed garden, natural daylight, "
        "high quality photography, ground level view. "
        "Keep existing fences, walls and fixed structures."
    )

    ext = Path(filename).suffix.lstrip(".").lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    response = requests.post(
        STABILITY_URL,
        headers={
            "authorization": f"Bearer {STABILITY_API_KEY}",
            "accept": "image/*",
        },
        files={"image": (filename, photo_bytes, mime)},
        data={
            "prompt":           prompt,
            "control_strength": 0.7,
            "output_format":    "jpeg",
        },
        timeout=90,
    )

    if response.status_code != 200:
        raise ValueError(f"Stability AI error {response.status_code}: {response.text}")

    return response.content


def send_render_email(to_email: str, company: str, name: str,
                      before_bytes: bytes, render_bytes: bytes, description: str):
    before_b64 = base64.b64encode(before_bytes).decode("utf-8")
    after_b64  = base64.b64encode(render_bytes).decode("utf-8")
    first = name.split()[0] if name else "there"
    short_desc = description[:80] + ("..." if len(description) > 80 else "")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body{{font-family:Georgia,serif;background:#F7F3EC;margin:0;padding:0}}
.wrap{{max-width:620px;margin:40px auto;background:#fff;border:1px solid #e8e2d8}}
.header{{background:#2C4A2E;padding:28px 36px}}
.logo{{font-size:22px;color:#fff}}.logo span{{color:#5A8F5E;font-style:italic}}
.body{{padding:36px;color:#1A1A18;font-size:15px;line-height:1.75}}
.body p{{margin:0 0 16px}}
.label{{font-family:sans-serif;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#9e9e8e;margin:8px 0 4px}}
.img-wrap{{margin-bottom:24px}}.img-wrap img{{width:100%;display:block}}
.footer{{padding:20px 36px;border-top:1px solid #e8e2d8;font-family:sans-serif;font-size:11px;color:#9e9e8e}}
.footer a{{color:#5A8F5E}}
</style></head><body>
<div class="wrap">
<div class="header"><div class="logo">Vis<span>Render</span></div></div>
<div class="body">
<p>Hi {first},</p>
<p>Your garden render is ready. Here's the before &amp; after for: <em>{short_desc}</em></p>
<div class="img-wrap"><div class="label">Before</div>
<img src="data:image/jpeg;base64,{before_b64}" alt="Before"></div>
<div class="img-wrap"><div class="label">After — VisRender</div>
<img src="data:image/jpeg;base64,{after_b64}" alt="After render"></div>
<p>Show this to your customer at your next meeting. If you'd like any changes —
different materials, colours or style — just reply and we'll update it within 24 hours.</p>
<p>Ready for your next render?<br>
<a href="https://visrender.co.uk/order.html" style="color:#2C4A2E">visrender.co.uk/order.html</a></p>
<p>Best,<br>Tom<br>VisRender</p>
</div>
<div class="footer">&copy; 2026 VisRender &middot;
<a href="mailto:hello@visrender.co.uk">hello@visrender.co.uk</a></div>
</div></body></html>"""

    resend.Emails.send({
        "from":    f"{FROM_NAME} <{FROM_EMAIL}>",
        "to":      [to_email],
        "subject": "Your garden render is ready — VisRender",
        "html":    html,
    })


def send_notification_email(company: str, name: str, email: str, description: str):
    resend.Emails.send({
        "from":    f"{FROM_NAME} <{FROM_EMAIL}>",
        "to":      [NOTIFY_EMAIL],
        "subject": f"New order from {company} — render sent automatically",
        "html":    f"<p><b>Company:</b> {company}<br><b>Name:</b> {name}<br><b>Email:</b> {email}<br><b>Description:</b> {description}</p><p>Render has been generated and emailed automatically.</p>",
    })


def process_order(photo_bytes: bytes, filename: str, email: str,
                  company: str, name: str, description: str, style: str):
    try:
        print(f"Processing order for {company} ({email})")
        render_bytes = generate_render(photo_bytes, filename, description, style)
        print(f"Render generated, emailing to {email}")
        send_render_email(email, company, name, photo_bytes, render_bytes, description)
        send_notification_email(company, name, email, description)
        print(f"Done — order complete for {email}")
    except Exception as e:
        print(f"Error processing order: {e}")
        # Notify Tom something went wrong
        resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to":   [NOTIFY_EMAIL],
            "subject": f"Order processing failed — {company}",
            "html": f"<p>Order from {company} ({email}) failed to process automatically.</p><p>Error: {e}</p><p>Description: {description}</p>",
        })


@app.post("/order")
async def receive_order(
    background_tasks: BackgroundTasks,
    photo:       UploadFile = File(...),
    email:       str        = Form(...),
    company:     str        = Form(...),
    name:        str        = Form(...),
    description: str        = Form(...),
    style:       str        = Form(default=""),
    phone:       str        = Form(default=""),
    notes:       str        = Form(default=""),
):
    photo_bytes = await photo.read()
    full_description = description
    if notes:
        full_description += f". Additional notes: {notes}"

    # Process in background so we return immediately to the user
    background_tasks.add_task(
        process_order,
        photo_bytes, photo.filename, email,
        company, name, full_description, style
    )

    return {"status": "received", "message": "Your order is being processed. Render will be emailed within 30 minutes."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug-key")
def debug_key():
    key = os.environ.get("STABILITY_API_KEY", "NOT SET")
    cleaned = key.strip()
    return {
        "raw_length": len(key),
        "cleaned_length": len(cleaned),
        "starts_with": cleaned[:8] if len(cleaned) >= 8 else cleaned,
        "ends_with": cleaned[-4:] if len(cleaned) >= 4 else cleaned,
        "has_spaces": " " in key,
        "has_newline": "\n" in key or "\r" in key,
    }
