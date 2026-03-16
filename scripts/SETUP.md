# VisRender Scripts — Setup Guide

## 1. Install Python dependencies

```bash
pip install requests resend Pillow
```

## 2. Get your free API keys

### Google Places API (find businesses)
1. Go to https://console.cloud.google.com
2. Create a new project called "VisRender"
3. Go to APIs & Services → Enable APIs → enable **Places API** and **Geocoding API**
4. Go to APIs & Services → Credentials → Create API Key
5. Paste it into `config.py` as `GOOGLE_API_KEY`

### Resend (send emails — free: 3,000/month)
1. Go to https://resend.com and sign up free
2. Go to API Keys → Create API Key
3. Paste it into `config.py` as `RESEND_API_KEY`
4. Add your domain (visrender.co.uk) under Domains and verify it

### Adobe Firefly API (generate renders)
1. Go to https://developer.adobe.com/firefly-api/
2. Sign in with a free Adobe account
3. Create a project → copy Client ID and Client Secret
4. Paste both into `config.py`

---

## 3. Find landscaping businesses

```bash
cd scripts
python find_businesses.py
```

This searches 10 major UK cities and saves results to `businesses.csv`.

To search a specific city:
```bash
python find_businesses.py --location "Bristol"
```

---

## 4. Send outreach emails

First do a dry run to preview:
```bash
python send_outreach.py --dry-run
```

Then send (50 at a time is a safe starting point):
```bash
python send_outreach.py --limit 50
```

Already-emailed businesses are marked in the CSV so they won't be emailed twice.

---

## 5. Generate a render manually

When an order comes in via the website:

```bash
python generate_render.py \
  --photo garden_photo.jpg \
  --email james@greengardens.co.uk \
  --description "Replace lawn with grey porcelain slabs, add raised oak planters" \
  --company "Green Gardens Ltd" \
  --style "Modern"
```

The render will be emailed directly to the landscaper.
