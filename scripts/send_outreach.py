"""
VisRender — Email Outreach Sender
Reads businesses.csv and sends a cold outreach email to each one
using Resend (free tier: 3,000 emails/month).

Setup:
  pip install resend
  Set RESEND_API_KEY in config.py

Usage:
  python send_outreach.py
  python send_outreach.py --csv businesses.csv --limit 50
  python send_outreach.py --dry-run   (preview without sending)
"""

import csv
import time
import argparse
import os
import resend
from config import RESEND_API_KEY, FROM_EMAIL, FROM_NAME

resend.api_key = RESEND_API_KEY

EMAIL_SUBJECT = "Free garden visualisation for your clients — VisRender"

def build_email_html(business_name):
    first_name = business_name.split()[0] if business_name else "there"
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Georgia', serif; background: #F7F3EC; margin: 0; padding: 0; }}
  .wrap {{ max-width: 560px; margin: 40px auto; background: #fff; border: 1px solid #e8e2d8; }}
  .header {{ background: #2C4A2E; padding: 28px 36px; }}
  .logo {{ font-size: 22px; color: #fff; letter-spacing: 0.02em; }}
  .logo span {{ color: #5A8F5E; font-style: italic; }}
  .body {{ padding: 36px; color: #1A1A18; font-size: 15px; line-height: 1.75; }}
  .body p {{ margin: 0 0 16px; }}
  .cta {{ display: inline-block; padding: 13px 28px; background: #2C4A2E; color: #fff;
          text-decoration: none; font-family: sans-serif; font-size: 13px;
          letter-spacing: 0.08em; text-transform: uppercase; margin: 8px 0 20px; }}
  .price-bar {{ background: #F7F3EC; border-left: 3px solid #2C4A2E;
                padding: 12px 16px; margin: 20px 0; font-family: sans-serif; font-size: 13px; }}
  .footer {{ padding: 20px 36px; border-top: 1px solid #e8e2d8;
             font-family: sans-serif; font-size: 11px; color: #9e9e8e; }}
  .footer a {{ color: #5A8F5E; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="logo">Vis<span>Render</span></div>
  </div>
  <div class="body">
    <p>Hi {first_name},</p>

    <p>I run <strong>VisRender</strong> — a service that turns a garden photo into a photorealistic
    before &amp; after visualisation within 24 hours.</p>

    <p>The idea is simple: when a customer can <em>see</em> what their garden could look like,
    they say yes much faster. No more trying to describe decking or porcelain slabs —
    just show them the finished result before a single slab is lifted.</p>

    <div class="price-bar">
      <strong>First render is completely free.</strong> After that it's £20 per render —
      most landscapers recoup that in the first 10 minutes of a job.
    </div>

    <p>All you need to do is send us one photo of the garden and a short description
    of what the client wants. We do the rest.</p>

    <a class="cta" href="https://visrender.co.uk/order.html">Claim your free render &rarr;</a>

    <p>Happy to answer any questions — just reply to this email.</p>

    <p>Best,<br>Tom<br>VisRender</p>
  </div>
  <div class="footer">
    &copy; 2026 VisRender &middot;
    <a href="mailto:hello@visrender.co.uk">hello@visrender.co.uk</a>
    &middot; <a href="https://visrender.co.uk">visrender.co.uk</a><br><br>
    You're receiving this because your business appeared in a local search for landscaping
    services. To stop receiving emails from us,
    <a href="mailto:hello@visrender.co.uk?subject=unsubscribe">click here to unsubscribe</a>.
  </div>
</div>
</body>
</html>
"""

def build_email_text(business_name):
    first_name = business_name.split()[0] if business_name else "there"
    return f"""Hi {first_name},

I run VisRender — a service that turns a garden photo into a photorealistic before & after visualisation within 24 hours.

When a customer can SEE what their garden could look like, they say yes much faster.

Your first render is completely free. After that it's £20 per render.

Just send us one photo and a short description of what the client wants — we do the rest.

Claim your free render: https://visrender.co.uk/order.html

Happy to answer questions — just reply.

Best,
Tom
VisRender
hello@visrender.co.uk

---
To unsubscribe: reply with "unsubscribe" in the subject line.
"""


def get_email_from_website(website):
    """
    Try to extract a contact email from a business website.
    Returns None if not found — we only email businesses where we have an address.
    """
    if not website:
        return None
    # Basic heuristic: try hello@, info@, contact@ with the domain
    try:
        from urllib.parse import urlparse
        domain = urlparse(website).netloc.replace("www.", "")
        if domain:
            return f"info@{domain}"
    except Exception:
        pass
    return None


def send_outreach(csv_file="businesses.csv", limit=None, dry_run=False, delay=1.5):
    updated_rows = []
    sent = 0
    skipped = 0

    with open(csv_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys()) if rows else []

    for row in rows:
        if row.get("emailed", "no").lower() == "yes":
            updated_rows.append(row)
            skipped += 1
            continue

        if limit and sent >= limit:
            updated_rows.append(row)
            continue

        # Try to get an email address
        to_email = get_email_from_website(row.get("website", ""))
        if not to_email:
            print(f"  Skipping (no email derivable): {row['name']}")
            updated_rows.append(row)
            skipped += 1
            continue

        print(f"  {'[DRY RUN] ' if dry_run else ''}Sending to {row['name']} <{to_email}>")

        if not dry_run:
            try:
                resend.Emails.send({
                    "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                    "to": [to_email],
                    "subject": EMAIL_SUBJECT,
                    "html": build_email_html(row["name"]),
                    "text": build_email_text(row["name"]),
                })
                row["emailed"] = "yes"
                sent += 1
                time.sleep(delay)
            except Exception as e:
                print(f"    Error: {e}")
        else:
            sent += 1

        updated_rows.append(row)

    # Write back updated CSV (marking sent ones)
    if not dry_run:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

    print(f"\nDone. Sent: {sent}  Skipped: {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send VisRender outreach emails")
    parser.add_argument("--csv", default="businesses.csv", help="Input CSV file")
    parser.add_argument("--limit", type=int, help="Max emails to send this run")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between emails")
    args = parser.parse_args()

    send_outreach(
        csv_file=args.csv,
        limit=args.limit,
        dry_run=args.dry_run,
        delay=args.delay,
    )
