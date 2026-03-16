"""
VisRender — Adobe Firefly Render Generator (Phase 3)
Takes a garden photo and description, generates an AI render via
Adobe Firefly API, and emails the result to the landscaper.

Setup:
  pip install requests resend Pillow
  Set ADOBE_CLIENT_ID, ADOBE_CLIENT_SECRET, RESEND_API_KEY in config.py

Adobe Firefly API:
  1. Go to https://developer.adobe.com/firefly-api/
  2. Create a project → get Client ID and Client Secret
  3. Free tier includes limited credits for testing

Usage:
  python generate_render.py --photo garden.jpg --email james@example.com
                             --description "Replace lawn with porcelain slabs"
                             --company "Green Gardens Ltd"
"""

import requests
import resend
import base64
import argparse
import os
from pathlib import Path
from config import (
    RESEND_API_KEY, FROM_EMAIL, FROM_NAME,
    ADOBE_CLIENT_ID, ADOBE_CLIENT_SECRET
)

resend.api_key = RESEND_API_KEY

ADOBE_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
FIREFLY_FILL_URL = "https://firefly-api.adobe.io/v3/images/fill"
FIREFLY_GENERATE_URL = "https://firefly-api.adobe.io/v3/images/generate"


def get_adobe_token():
    """Get a short-lived Adobe access token."""
    resp = requests.post(ADOBE_TOKEN_URL, data={
        "grant_type":    "client_credentials",
        "client_id":     ADOBE_CLIENT_ID,
        "client_secret": ADOBE_CLIENT_SECRET,
        "scope":         "firefly_api,openid,AdobeID",
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def encode_image(path):
    """Base64-encode an image file."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_render(photo_path, description, style=None):
    """
    Use Firefly Generative Fill to transform a garden photo.
    Returns the rendered image as bytes.
    """
    token = get_adobe_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-key":     ADOBE_CLIENT_ID,
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }

    # Build the prompt from the description
    style_hint = f" in a {style} style" if style else ""
    prompt = (
        f"Professional garden landscape design{style_hint}. "
        f"{description}. "
        "Photorealistic, high quality, natural lighting, shot from ground level. "
        "Keep the same fence, walls and fixed structures."
    )

    # Upload the reference image
    img_b64 = encode_image(photo_path)
    ext = Path(photo_path).suffix.lstrip(".").lower()
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    payload = {
        "prompt": prompt,
        "image": {
            "source": {
                "dataUrl": f"data:{media_type};base64,{img_b64}"
            }
        },
        "size": {"width": 1792, "height": 1024},
        "n": 1,
        "contentClass": "photo",
    }

    resp = requests.post(FIREFLY_FILL_URL, json=payload, headers=headers, timeout=60)

    if resp.status_code != 200:
        print(f"Firefly error {resp.status_code}: {resp.text}")
        resp.raise_for_status()

    result = resp.json()
    # The API returns a URL or base64 image
    output = result["outputs"][0]
    if "image" in output and "url" in output["image"]:
        img_resp = requests.get(output["image"]["url"], timeout=30)
        return img_resp.content
    elif "image" in output and "dataUrl" in output["image"]:
        data_url = output["image"]["dataUrl"]
        b64_part = data_url.split(",", 1)[1]
        return base64.b64decode(b64_part)

    raise ValueError(f"Unexpected Firefly response: {result}")


def send_render_email(to_email, company_name, before_path, render_bytes, description):
    """Email the before + after render to the landscaper."""
    before_b64 = encode_image(before_path)
    after_b64  = base64.b64encode(render_bytes).decode("utf-8")

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Georgia, serif; background: #F7F3EC; margin: 0; padding: 0; }}
  .wrap {{ max-width: 620px; margin: 40px auto; background: #fff; border: 1px solid #e8e2d8; }}
  .header {{ background: #2C4A2E; padding: 28px 36px; }}
  .logo {{ font-size: 22px; color: #fff; letter-spacing: 0.02em; }}
  .logo span {{ color: #5A8F5E; font-style: italic; }}
  .body {{ padding: 36px; color: #1A1A18; font-size: 15px; line-height: 1.75; }}
  .body p {{ margin: 0 0 16px; }}
  .img-label {{ font-family: sans-serif; font-size: 11px; letter-spacing: 0.12em;
                text-transform: uppercase; color: #9e9e8e; margin: 8px 0 4px; }}
  .img-wrap {{ margin-bottom: 24px; }}
  .img-wrap img {{ width: 100%; display: block; }}
  .footer {{ padding: 20px 36px; border-top: 1px solid #e8e2d8;
             font-family: sans-serif; font-size: 11px; color: #9e9e8e; }}
  .footer a {{ color: #5A8F5E; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header"><div class="logo">Vis<span>Render</span></div></div>
  <div class="body">
    <p>Hi {company_name.split()[0]},</p>
    <p>Your garden render is ready. Here's the before &amp; after for <em>{description[:80]}{'...' if len(description)>80 else ''}</em></p>

    <div class="img-wrap">
      <div class="img-label">Before</div>
      <img src="data:image/jpeg;base64,{before_b64}" alt="Before">
    </div>

    <div class="img-wrap">
      <div class="img-label">After — AI Render</div>
      <img src="data:image/jpeg;base64,{after_b64}" alt="After render">
    </div>

    <p>Feel free to use this image when presenting to your customer.
    If you'd like any adjustments — different materials, colours, or style — just reply
    to this email and we'll update it within 24 hours.</p>

    <p>When you're ready for your next render, visit:
    <a href="https://visrender.co.uk/order.html" style="color:#2C4A2E">visrender.co.uk/order.html</a></p>

    <p>Best,<br>Tom<br>VisRender</p>
  </div>
  <div class="footer">
    &copy; 2026 VisRender &middot;
    <a href="mailto:hello@visrender.co.uk">hello@visrender.co.uk</a>
  </div>
</div>
</body>
</html>
"""

    resend.Emails.send({
        "from":    f"{FROM_NAME} <{FROM_EMAIL}>",
        "to":      [to_email],
        "subject": f"Your garden render is ready — VisRender",
        "html":    html,
    })
    print(f"Render emailed to {to_email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a garden render with Adobe Firefly")
    parser.add_argument("--photo",       required=True, help="Path to the garden photo")
    parser.add_argument("--email",       required=True, help="Landscaper's email address")
    parser.add_argument("--description", required=True, help="What the client wants")
    parser.add_argument("--company",     default="",    help="Company name")
    parser.add_argument("--style",       default="",    help="Style preference")
    parser.add_argument("--save",        default="render_output.jpg", help="Save render to file")
    args = parser.parse_args()

    print("Generating render with Adobe Firefly...")
    render_bytes = generate_render(args.photo, args.description, args.style or None)

    with open(args.save, "wb") as f:
        f.write(render_bytes)
    print(f"Render saved to {args.save}")

    print("Sending email...")
    send_render_email(args.email, args.company or args.email, args.photo, render_bytes, args.description)
    print("Done.")
