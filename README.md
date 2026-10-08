# SERS Foundation Website — Django edition

A fully dynamic database-driven Django project designed with HTML, CSS and JavaScript.

## Run it
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # loads all the original content + creates admin / admin12345
python manage.py runserver
```
Site: http://127.0.0.1:8000/  ·  Admin: http://127.0.0.1:8000/admin/ (change the password!)
Run tests: `python manage.py test`

## Everything is editable in the admin
No visible wording, link or image is hard-coded. Where to change what:

| You want to change… | Admin section |
|---|---|
| **Any button, label, heading, placeholder, error/success message, email wording, page title, footer text, aria/alt text** | **Site texts** — search for the words you see on the site. Rows appear automatically for every text the site uses; "Reset to original" is available. Keep `{placeholders}` such as `{site_name}` in place. |
| Section copy, banners, call-to-action bands, story text + their images and button links | **Content blocks** (add any new key you like) |
| Header menu, header buttons, footer link columns (labels, links, icons, who sees them, log-out button) | **Menu items** |
| Facebook/YouTube/… icons and links | **Social links** |
| Home-page counters (label, live source or manual number, suffix) | **Stats** |
| Logo, site name, contact details, footer blurb, currency, sapling price, mission/vision | **Site settings** |
| Programs, gallery, hero photos, divisions/map, value cards, targets, timeline | their own sections |

Form labels, placeholders, validation messages and the password-reset email are under **Site texts** too.
Starting content lives in `core/seed/content.json`. `python manage.py seed_demo` loads it and only fills *empty* fields, so re-running never overwrites edits.
`python manage.py sync_texts` registers any new wording added to the code.
Developers: `{% t "some.key" "Default wording" name=value %}` in templates (`{% load gb %}`) or `text("some.key", "Default")` in Python.

Moderation: Admin → Tree plantings → select → "Approve selected plantings".

Not editable: Django's built-in password-strength messages and the admin interface itself.

## Google Maps
The home/contact maps use **Google Maps**. In Admin → Site settings → *Google Maps* paste a **Maps JavaScript API key**
(console.cloud.google.com → enable "Maps JavaScript API" → Credentials → API key; billing must be enabled; restrict the key
by HTTP referrer to your domain, plus `127.0.0.1/*` and `localhost/*` for testing). Optional: Map ID, centre, zoom.
With a key you get the interactive map with division and approved-planting markers. Without a key (or if Google rejects it)
the site shows a plain Google Maps embed of the fallback place, without custom markers.

## Notes
- Config via env vars: `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_EMAIL_BACKEND` (+ `EMAIL_*`). With `DJANGO_DEBUG=0` a secret key is required. Emails print to the console by default.
- Production: `python manage.py collectstatic`, serve `/static/` and `/media/` from your web server (or add WhiteNoise), use PostgreSQL if desired.
- Donations are *pledges* only — no payment gateway is wired in. The Google/Facebook login buttons from the mock were removed since they did nothing.
