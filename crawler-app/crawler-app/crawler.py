"""
Simple site crawler built on Playwright (Python).

What it does:
  1. Starts at one URL.
  2. Opens each page in a real (headless) browser, so JavaScript-rendered content is included.
  3. Scrolls each page to the bottom so lazy-loaded images actually load.
  4. Saves the rendered HTML of every page.
  5. Finds every image the page uses and downloads it (once) into assets/images/.
  6. Collects links and follows only those on the SAME domain.
  7. Writes index files: pages.json (every page) and images.json (every image).

Setup:
  pip install playwright
  playwright install chromium

Usage:
  python crawler.py https://example.com --max-pages 20 --out crawl_output
  python crawler.py https://example.com --no-images     # skip image downloading

Only crawl sites you own or have permission to crawl.
"""

import argparse
import hashlib
import json
import re
import struct
import time
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

USER_AGENT = "SiteMigrationBot/0.1 (student project)"

# File types we do not want to open as pages.
SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".pdf", ".zip", ".mp4", ".mp3", ".css", ".js", ".xml", ".json",
)

MAX_IMAGE_BYTES = 15 * 1024 * 1024  # skip anything bigger than 15 MB

IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/avif": ".avif", "image/svg+xml": ".svg",
    "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico", "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}

# Runs inside the page: scroll down step by step so lazy-loaded images start loading.
SCROLL_JS = """
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 40; i++) {               // at most 40 steps, so endless pages still finish
    window.scrollBy(0, window.innerHeight * 0.8);
    await sleep(150);
    if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) break;
  }
  window.scrollTo(0, 0);
}
"""

# Runs inside the page: list every image the page uses and where it was found.
FIND_IMAGES_JS = r"""
() => {
  const found = [];
  const abs = (u) => { try { return new URL(u.trim(), document.baseURI).href; } catch { return null; } };
  const add = (u, kind, el) => {
    const url = u && abs(u);
    if (!url || !/^https?:/i.test(url)) return;            // skips data: and blob: URLs
    const isImg = el && el.tagName === "IMG";
    found.push({
      url, kind,
      alt: isImg ? el.getAttribute("alt") : null,
      width: isImg && el.naturalWidth ? el.naturalWidth : null,
      height: isImg && el.naturalHeight ? el.naturalHeight : null,
    });
  };
  // srcset = "small.jpg 400w, big.jpg 1200w" -> keep the largest candidate.
  const largest = (srcset) => {
    if (!srcset) return null;
    const parts = srcset.trim().split(/\s+/);
    let best = null, bestSize = -1;
    for (let i = 0; i < parts.length; i++) {
      let url = parts[i], size = 1;
      if (url.endsWith(",")) url = url.slice(0, -1);
      else if (i + 1 < parts.length && /^[\d.]+[wxh],?$/.test(parts[i + 1])) size = parseFloat(parts[++i]);
      if (url && size > bestSize) { best = url; bestSize = size; }
    }
    return best;
  };
  const LAZY = ["data-src", "data-lazy-src", "data-original", "data-lazy", "data-bg", "data-background"];

  document.querySelectorAll("img").forEach(el => {
    add(el.currentSrc || el.getAttribute("src"), "img", el);
    add(largest(el.getAttribute("srcset")), "srcset", el);
    add(largest(el.getAttribute("data-srcset")), "srcset", el);
    LAZY.forEach(a => add(el.getAttribute(a), "lazy", el));
  });
  document.querySelectorAll("picture source[srcset], picture source[data-srcset]").forEach(el => {
    add(largest(el.getAttribute("srcset") || el.getAttribute("data-srcset")), "picture", el);
  });
  document.querySelectorAll("[data-bg], [data-background]").forEach(el => {
    add(el.getAttribute("data-bg") || el.getAttribute("data-background"), "lazy", el);
  });
  document.querySelectorAll("video[poster]").forEach(el => add(el.getAttribute("poster"), "video-poster", el));
  document.querySelectorAll("svg image").forEach(el =>
    add(el.getAttribute("href") || el.getAttribute("xlink:href"), "svg-image", el));
  document.querySelectorAll("link[rel~='icon'], link[rel='apple-touch-icon'], link[rel='mask-icon']")
    .forEach(el => add(el.getAttribute("href"), "icon", el));
  document.querySelectorAll("meta[property='og:image'], meta[name='twitter:image']")
    .forEach(el => add(el.getAttribute("content"), "social", el));

  // CSS background images, including ::before / ::after decorations.
  for (const el of document.querySelectorAll("*")) {
    for (const pseudo of [null, "::before", "::after"]) {
      const bg = getComputedStyle(el, pseudo).backgroundImage;
      if (!bg || bg === "none") continue;
      for (const m of bg.matchAll(/url\(\s*["']?(.*?)["']?\s*\)/g)) add(m[1], "background", el);
    }
  }
  return found;
}
"""


def normalize(url: str) -> str:
    """Remove #fragments and trailing slashes so the same page isn't visited twice."""
    url, _ = urldefrag(url)
    return url.rstrip("/")


def same_site(url: str, start_host: str) -> bool:
    return urlparse(url).netloc == start_host


def is_html_candidate(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and not parsed.path.lower().endswith(SKIP_EXTENSIONS)


def slugify(text: str, limit: int = 60) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")[:limit]


def filename_for(url: str) -> str:
    """Readable, unique, filesystem-safe filename for a URL."""
    path = urlparse(url).path.strip("/") or "index"
    digest = hashlib.sha1(url.encode()).hexdigest()[:8]
    return f"{slugify(path)}_{digest}.html"


def load_robots(start_url: str) -> RobotFileParser:
    parsed = urlparse(start_url)
    rp = RobotFileParser()
    rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        rp.read()  # a 404 means "no rules" -> everything allowed
    except Exception:
        # Network/SSL error fetching robots.txt. Without this line the parser
        # would treat the file as "never read" and block EVERY page.
        rp.allow_all = True
    return rp


# ---------------------------------------------------------------- images

def sniff_image_type(data: bytes) -> str | None:
    """Recognise common image formats from their first bytes (for servers that send the wrong type)."""
    head = data[:64]
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif"
    if head.startswith(b"\x00\x00\x01\x00"):
        return "image/x-icon"
    if b"<svg" in data[:1024].lower():
        return "image/svg+xml"
    return None


def image_size(data: bytes) -> tuple[int, int] | None:
    """Width and height of a PNG, GIF, JPEG or WebP file, read from its header. None if unknown."""
    try:
        if data.startswith(b"\x89PNG"):
            return struct.unpack(">II", data[16:24])
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", data[6:10])
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            chunk = data[12:16]
            if chunk == b"VP8 ":
                w, h = struct.unpack("<HH", data[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if chunk == b"VP8L":
                b0, b1, b2, b3 = data[21:25]
                return 1 + (((b1 & 0x3F) << 8) | b0), 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
            if chunk == b"VP8X":
                return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
        if data.startswith(b"\xff\xd8"):
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):  # "start of frame"
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    except (struct.error, IndexError, ValueError):
        pass
    return None


class ImageDownloader:
    """Downloads each image once and keeps an index of where every image is used."""

    def __init__(self, request, out_dir: Path):
        self.request = request          # Playwright's request client: same user agent/cookies as the browser
        self.out_dir = out_dir
        self.images_dir = out_dir / "assets" / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.by_url: dict[str, dict] = {}
        self.file_by_hash: dict[str, str] = {}   # identical files under different URLs are stored once

    def process_page(self, found: list[dict], page_url: str) -> dict[str, str]:
        """Download everything in `found`. Returns {image url: saved file} for this page."""
        saved = {}
        for item in found:
            url = item["url"]
            entry = self.by_url.get(url)
            if entry is None:
                entry = self._download(url, referer=page_url)
                self.by_url[url] = entry
            if page_url not in entry["pages"]:
                entry["pages"].append(page_url)
            if item["kind"] not in entry["found_as"]:
                entry["found_as"].append(item["kind"])
            if item.get("alt") and item["alt"] not in entry["alt"]:
                entry["alt"].append(item["alt"])
            if item.get("width") and not entry["width"]:
                entry["width"], entry["height"] = item["width"], item["height"]
            if entry["file"]:
                saved[url] = entry["file"]
        return saved

    def _download(self, url: str, referer: str) -> dict:
        entry = {"url": url, "file": None, "content_type": None, "bytes": None,
                 "width": None, "height": None, "found_as": [], "alt": [], "pages": [], "error": None}
        try:
            # Referer: some sites refuse image requests that don't seem to come from their own pages.
            resp = self.request.get(url, headers={"Referer": referer}, timeout=20_000)
            if not resp.ok:
                entry["error"] = f"HTTP {resp.status}"
                return entry
            declared = int(resp.headers.get("content-length") or 0)
            if declared > MAX_IMAGE_BYTES:
                entry["error"] = f"too large ({declared} bytes)"
                return entry
            data = resp.body()
            if len(data) > MAX_IMAGE_BYTES:
                entry["error"] = f"too large ({len(data)} bytes)"
                return entry

            ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            if ctype not in IMAGE_EXTENSIONS:
                ctype = sniff_image_type(data) or ctype
            if not ctype.startswith("image/"):
                entry["error"] = f"not an image ({ctype or 'unknown type'})"
                return entry

            entry["content_type"] = ctype
            entry["bytes"] = len(data)
            size = image_size(data)
            if size:
                entry["width"], entry["height"] = size

            digest = hashlib.sha1(data).hexdigest()
            if digest in self.file_by_hash:
                entry["file"] = self.file_by_hash[digest]
            else:
                stem = Path(urlparse(url).path).stem or "image"
                ext = IMAGE_EXTENSIONS.get(ctype) or Path(urlparse(url).path).suffix.lower() or ".img"
                name = f"{slugify(stem, 50) or 'image'}_{digest[:10]}{ext}"
                (self.images_dir / name).write_bytes(data)
                entry["file"] = f"assets/images/{name}"
                self.file_by_hash[digest] = entry["file"]
        except PlaywrightTimeout:
            entry["error"] = "timeout"
        except Exception as exc:  # one broken image must not stop the crawl
            entry["error"] = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        return entry

    def write_index(self) -> None:
        (self.out_dir / "images.json").write_text(
            json.dumps(list(self.by_url.values()), indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- crawl

def crawl(start_url: str, max_pages: int, out_dir: Path, delay: float,
          on_progress=None, should_stop=None, download_images: bool = True) -> list[dict]:
    """
    on_progress(record, pages_done, max_pages) is called after every page.
    should_stop() is checked before every page; return True to end the crawl early.
    With download_images=True, images go to out_dir/assets/images and are listed in images.json.
    """
    start_url = normalize(start_url)
    start_host = urlparse(start_url).netloc
    robots = load_robots(start_url)

    pages_dir = out_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    queue = deque([start_url])
    seen = {start_url}
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        images = ImageDownloader(context.request, out_dir) if download_images else None

        try:
            while queue and len(results) < max_pages:
                if should_stop and should_stop():
                    break
                url = queue.popleft()

                print(f"[{len(results) + 1}/{max_pages}] {url}")
                record = {"url": url, "status": None, "title": None, "file": None,
                          "links": [], "images": [], "image_files": {}, "error": None}

                if not robots.can_fetch(USER_AGENT, url):
                    print("  skipped: blocked by robots.txt")
                    record["error"] = "blocked by robots.txt"
                    results.append(record)
                    if on_progress:
                        on_progress(record, len(results), max_pages)
                    continue

                try:
                    response = page.goto(url, wait_until="load", timeout=30_000)
                    # Give JavaScript a chance to finish loading content. Some sites
                    # never go idle (live chat, polling), so a timeout here is fine.
                    try:
                        page.wait_for_load_state("networkidle", timeout=5_000)
                    except PlaywrightTimeout:
                        pass

                    record["status"] = response.status if response else None
                    record["final_url"] = page.url  # after redirects; used as <base> in previews
                    content_type = (response.headers.get("content-type", "") if response else "")

                    if "text/html" not in content_type:
                        record["error"] = f"not HTML ({content_type})"
                    else:
                        # Scroll through the page so lazy-loaded images and content appear.
                        try:
                            page.evaluate(SCROLL_JS)
                            page.wait_for_load_state("networkidle", timeout=3_000)
                        except PlaywrightTimeout:
                            pass

                        record["title"] = page.title()
                        html = page.content()  # the DOM *after* JavaScript ran
                        filename = filename_for(url)
                        (pages_dir / filename).write_text(html, encoding="utf-8")
                        record["file"] = f"pages/{filename}"

                        found = page.evaluate(FIND_IMAGES_JS)
                        record["images"] = sorted({f["url"] for f in found})
                        if images:
                            record["image_files"] = images.process_page(found, url)
                            print(f"  images: {len(record['image_files'])}/{len(record['images'])} saved")

                        # a.href is already an absolute URL in the browser.
                        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                        for href in hrefs:
                            link = normalize(urljoin(url, href))
                            if not is_html_candidate(link):
                                continue
                            if same_site(link, start_host):
                                record["links"].append(link)
                                if link not in seen:
                                    seen.add(link)
                                    queue.append(link)
                        record["links"] = sorted(set(record["links"]))

                except PlaywrightTimeout:
                    record["error"] = "timeout"
                except Exception as exc:  # keep crawling even if one page breaks
                    # Playwright errors include a long call log; the first line is the useful part.
                    record["error"] = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__

                results.append(record)
                if on_progress:
                    on_progress(record, len(results), max_pages)
                time.sleep(delay)  # be polite: don't hammer the server
        finally:
            if images:
                images.write_index()  # also written when the crawl is stopped or crashes
            browser.close()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl a website with Playwright.")
    parser.add_argument("url", help="Start URL, e.g. https://example.com")
    parser.add_argument("--max-pages", type=int, default=20, help="Stop after this many pages")
    parser.add_argument("--out", default="crawl_output", help="Output folder")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait between pages")
    parser.add_argument("--no-images", action="store_true", help="Don't download images")
    args = parser.parse_args()

    out_dir = Path(args.out)
    results = crawl(args.url, args.max_pages, out_dir, args.delay,
                    download_images=not args.no_images)

    (out_dir / "pages.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    ok = sum(1 for r in results if r["file"])
    print(f"\nDone. {ok} pages saved, {len(results) - ok} failed/skipped. Index: {out_dir / 'pages.json'}")
    if not args.no_images:
        files = {f for r in results for f in r["image_files"].values()}
        print(f"Images: {len(files)} files in {out_dir / 'assets' / 'images'}, index: {out_dir / 'images.json'}")


if __name__ == "__main__":
    main()
