"""
VisRender — Render Generator (Stability AI)
Takes a garden photo and description, generates an AI render,
and emails the before & after to the landscaper.

Setup:
  pip3 install requests resend

Usage:
  python3 generate_render.py --photo garden.jpg --email james@example.com
                              --description "Replace lawn with porcelain slabs"
                              --company "Green Gardens Ltd"
                              --style "Modern"
"""

import requests
import resend
import base64
import argparse
from pathlib import Path
from config import STABILITY_API_KEY, RESEND_API_KEY, FROM_EMAIL, FROM_NAME

resend.api_key = RESEND_API_KEY

STABILITY_URL = "https://api.stability.ai/v2beta/stable-image/control/structure"


def generate_render(photo_path, description, style=None):
    """
    Use Stability AI structure control to transform a garden photo.
    Preserves the garden's layout (fences, trees, walls) while
    applying the new design. Returns image bytes.
    """
    style_hint = f" {style} style," if style else ""
    prompt = (
        f"Professional landscape garden design,{style_hint} "
        f"{description}. "
        "Photorealistic, beautifully designed garden, natural daylight, "
        "high quality photography, ground level view. "
        "Keep existing fences, walls and fixed structures."
    )

    ext = Path(photo_path).suffix.lstrip(".").lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    with open(photo_path, "rb") as f:
        img_bytes = f.read()

    response = requests.post(
        STABILITY_URL,
        headers={
            "authorization": f"Bearer {STABILITY_API_KEY}",
            "accept": "image/*",
        },
        files={"image": (Path(photo_path).name, img_bytes, mime)},
        data={
            "prompt":           prompt,
            "control_strength": 0.7,   # 0=ignore original, 1=copy original exactly
            "output_format":    "jpeg",
        },
        timeout=60,
    )

    if response.status_code != 200:
        raise ValueError(f"Stability AI error {response.status_code}: {response.text}")

    return response.content


def send_render_email(to_email, company_name, before_path, render_bytes, description):
    """Email the before + after render to the landscaper."""
    with open(before_path, "rb") as f:
        before_b64 = base64.b64encode(f.read()).decode("utf-8")
    after_b64 = base64.b64encode(render_bytes).decode("utf-8")

    first_name = company_name.split()[0] if company_name else "there"
    short_desc = description[:80] + ("..." if len(description) > 80 else "")

    html = f"""<!DOCTYPE html>
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
  .label {{ font-family: sans-serif; font-size: 11px; letter-spacing: 0.12em;
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
    <p>Hi {first_name},</p>
    <p>Your garden render is ready. Here's the before &amp; after
    for: <em>{short_desc}</em></p>

    <div class="img-wrap">
      <div class="label">Before</div>
      <img src="data:image/jpeg;base64,{before_b64}" alt="Before">
    </div>
    <div class="img-wrap">
      <div class="label">After — VisRender</div>
      <img src="data:image/jpeg;base64,{after_b64}" alt="After render">
    </div>

    <p>Show this to your customer at your next meeting. If you'd like any
    changes — different materials, colours or style — just reply and
    we'll update it within 24 hours.</p>

    <p>Ready for your next render?<br>
    <a href="https://visrender.co.uk/order.html" style="color:#2C4A2E">
    visrender.co.uk/order.html</a></p>

    <p>Best,<br>Tom<br>VisRender</p>
  </div>
  <div class="footer">
    &copy; 2026 VisRender &middot;
    <a href="mailto:hello@visrender.co.uk">hello@visrender.co.uk</a>
  </div>
</div>
</body>
</html>"""

    resend.Emails.send({
        "from":    f"{FROM_NAME} <{FROM_EMAIL}>",
        "to":      [to_email],
        "subject": "Your garden render is ready — VisRender",
        "html":    html,
    })
    print(f"Render emailed to {to_email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a garden render with Stability AI")
    parser.add_argument("--photo",       required=True, help="Path to the garden photo")
    parser.add_argument("--email",       required=True, help="Landscaper's email address")
    parser.add_argument("--description", required=True, help="What the client wants")
    parser.add_argument("--company",     default="",    help="Company name")
    parser.add_argument("--style",       default="",    help="Style (e.g. Modern, Cottage)")
    parser.add_argument("--save",        default="render_output.jpg", help="Save render locally")
    args = parser.parse_args()

    print("Generating render...")
    render_bytes = generate_render(args.photo, args.description, args.style or None)

    with open(args.save, "wb") as f:
        f.write(render_bytes)
    print(f"Render saved to {args.save}")

    print("Sending email...")
    send_render_email(args.email, args.company or args.email, args.photo, render_bytes, args.description)
    print("Done.")
