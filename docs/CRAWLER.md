# Site Crawler (test app)

A local web app for testing the Playwright crawler: enter a URL, watch pages get crawled live,
preview each saved page and download everything as a .zip.

Only crawl sites you own or are allowed to crawl.

## Setup (once)

You need Python 3.10 or newer.

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python -m playwright install chromium
```

## Run

```bash
python app.py
```

Open http://127.0.0.1:5050 in your browser. Stop the server with Ctrl+C.

## Files

| File | What it is |
|---|---|
| `crawler.py` | The crawler. Also works on its own: `python crawler.py https://example.com --max-pages 20` |
| `app.py` | Flask server: starts crawls in the background and serves results to the page |
| `static/index.html` | The web page you interact with |
| `crawls/<job-id>/` | Output of each crawl: `pages.json` plus the saved HTML in `pages/`, and (unless turned off) `images.json` plus the images in `assets/images/` |

## Images

Before saving a page, the crawler scrolls to the bottom so lazy-loaded images load. It then finds images in
`<img>` (including the largest `srcset` size and common `data-src` lazy attributes), `<picture>`, CSS backgrounds
(including `::before`/`::after`), video posters, SVG `<image>`, favicons and `og:image`/`twitter:image`.

Each image is downloaded once (identical files are stored once even under different URLs), up to 15 MB each.
`images.json` lists for every image: original URL, saved file, type, size in bytes, width × height, where it was
found (`img`, `background`, `icon`, …), its alt texts, the pages that use it, and an error if the download failed.
Each page record in `pages.json` has `image_files`: `{original URL: saved file}`.

Turn it off with the "Download images" checkbox, `"download_images": false` in the API, or `--no-images` on the command line.

## API (for the rest of your pipeline)

| Method | Path | Does |
|---|---|---|
| POST | `/api/crawl` | Body `{"url", "max_pages", "delay", "download_images"}` → `{"id"}` |
| GET | `/api/jobs/<id>` | Status, progress and page records |
| POST | `/api/jobs/<id>/stop` | Stop after the current page |
| GET | `/api/jobs/<id>/page/<n>` | Saved HTML of page n (scripts disabled) |
| GET | `/api/jobs/<id>/files/<path>` | A file from the crawl folder, e.g. `assets/images/logo_ab12.png` |
| GET | `/api/jobs/<id>/download` | Everything as a .zip |

## Known limits

- Jobs are kept in memory: restarting the server forgets the job list (the files in `crawls/` stay).
- Pages are crawled one at a time; max 200 pages per crawl.
- Previews block JavaScript and load images/CSS from the original site, so they can look slightly different.
- No login support.
- Not saved as image files: inline `<svg>` icons (they stay inside the page HTML) and `data:` images.
