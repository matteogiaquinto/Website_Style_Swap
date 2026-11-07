"""
Local web app for testing the crawler.

Run:
    pip install -r requirements.txt
    python -m playwright install chromium
    python app.py
Then open http://127.0.0.1:5050

Each crawl runs in a background thread ("job") so the page stays responsive.
The browser polls /api/jobs/<id> every second to show progress.
"""

import io
import os
import json
import re
import secrets
import threading
import uuid
import zipfile
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

from crawler import crawl

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "crawls"
DATA_DIR.mkdir(exist_ok=True)

MAX_PAGES_LIMIT = 200  # hard cap so nobody accidentally crawls 10,000 pages

app = Flask(__name__, static_folder="static")

# In-memory job store. Fine for local testing; a real app would use a database + queue.
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def run_job(job_id: str, url: str, max_pages: int, delay: float, download_images: bool) -> None:
    job = jobs[job_id]
    out_dir = DATA_DIR / job_id

    def on_progress(record, done, total):
        with jobs_lock:
            job["pages"].append(record)
            job["done"] = done

    def should_stop():
        return job["stop_requested"]

    try:
        results = crawl(url, max_pages, out_dir, delay,
                        on_progress=on_progress, should_stop=should_stop,
                        download_images=download_images)
        (out_dir / "pages.json").write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        with jobs_lock:
            job["status"] = "stopped" if job["stop_requested"] else "finished"
    except Exception as exc:
        with jobs_lock:
            job["status"] = "error"
            job["error"] = f"{type(exc).__name__}: {exc}"


@app.get("/crawler")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/crawl")
def start_crawl():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if url and "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify(error="Please enter a valid http(s) URL."), 400

    try:
        max_pages = max(1, min(int(data.get("max_pages", 20)), MAX_PAGES_LIMIT))
        delay = max(0.0, min(float(data.get("delay", 1.0)), 10.0))
    except (TypeError, ValueError):
        return jsonify(error="max_pages and delay must be numbers."), 400
    download_images = bool(data.get("download_images", True))

    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id, "url": url, "max_pages": max_pages,
            "status": "running", "done": 0, "pages": [],
            "error": None, "stop_requested": False,
        }
    threading.Thread(target=run_job, args=(job_id, url, max_pages, delay, download_images), daemon=True).start()
    return jsonify(id=job_id)


def get_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if not job:
        abort(404)
    return job


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    job = get_job(job_id)
    with jobs_lock:
        return jsonify({k: v for k, v in job.items() if k != "stop_requested"})


@app.post("/api/jobs/<job_id>/stop")
def stop_job(job_id):
    job = get_job(job_id)
    with jobs_lock:
        job["stop_requested"] = True
    return jsonify(ok=True)


@app.get("/api/jobs/<job_id>/page/<int:index>")
def page_html(job_id, index):
    """Serve a saved page for the preview. Scripts are blocked by CSP for safety."""
    job = get_job(job_id)
    with jobs_lock:
        if index < 0 or index >= len(job["pages"]):
            abort(404)
        record = job["pages"][index]
    if not record.get("file"):
        abort(404)
    path = (DATA_DIR / job_id / record["file"]).resolve()
    if not path.is_relative_to((DATA_DIR / job_id).resolve()) or not path.exists():
        abort(404)

    html = path.read_text(encoding="utf-8")
    # A <base> tag makes relative images/CSS load from the original site in the preview.
    base_url = record.get("final_url") or record["url"]
    base = f'<base href="{escape(base_url, quote=True)}">'
    html, n = re.subn(r"(<head[^>]*>)", r"\1" + base.replace("\\", "\\\\"), html, count=1, flags=re.I)
    if n == 0:
        html = base + html

    resp = app.response_class(html, mimetype="text/html")
    resp.headers["Content-Security-Policy"] = "script-src 'none'; object-src 'none'"
    return resp


@app.get("/api/jobs/<job_id>/files/<path:subpath>")
def job_file(job_id, subpath):
    """Serve a downloaded file (e.g. assets/images/logo_ab12.png) from a crawl folder."""
    if not re.fullmatch(r"[0-9a-f]{12}", job_id):
        abort(404)
    # send_from_directory refuses paths that try to escape the folder (../).
    resp = send_from_directory(DATA_DIR / job_id, subpath)
    # Downloaded SVGs can contain scripts; never let them run on this app's address.
    resp.headers["Content-Security-Policy"] = "script-src 'none'; object-src 'none'"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.get("/api/jobs/<job_id>/download")
def download(job_id):
    get_job(job_id)
    folder = DATA_DIR / job_id
    if not folder.exists():
        abort(404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in folder.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(folder))
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name=f"crawl_{job_id}.zip")


# The restyling MVP uses its own jobs so the original crawler API stays intact.
from ai_transfer import build as build_transfer, MODEL_DEFAULT, GenerationCancelled
TRANSFER_DIR = BASE_DIR / 'transfers'
TRANSFER_DIR.mkdir(exist_ok=True)
transfers = {}
pending_confirmations = {}
CONFIRMATION_TIMEOUT_SECONDS = 1800

@app.get('/')
@app.get('/restyle')
def restyle_interface():
    return send_from_directory(app.static_folder, 'restyle.html')

def run_transfer(job_id, old_url, ref_url, api_key):
    def progress(stage, completed_steps):
        with jobs_lock:
            transfers[job_id]['stage'] = stage
            transfers[job_id]['completed_steps'] = max(transfers[job_id]['completed_steps'], min(completed_steps, 5))
    def confirm_large_page(character_count, threshold):
        pending = {'event': threading.Event(), 'approved': None}
        with jobs_lock:
            pending_confirmations[job_id] = pending
            transfers[job_id].update(status='awaiting_approval', stage='Confirmation required',
                                     confirmation={'characters': character_count, 'threshold': threshold})
        pending['event'].wait(CONFIRMATION_TIMEOUT_SECONDS)
        with jobs_lock:
            pending_confirmations.pop(job_id, None)
            approved = pending['approved']
        if approved is None:
            raise TimeoutError('Confirmation expired; no content was sent to Claude.')
        if not approved:
            raise GenerationCancelled('Generation cancelled; no content was sent to Claude.')
    try:
        report = build_transfer(old_url, ref_url, TRANSFER_DIR / job_id, progress, api_key=api_key,
                                confirm_large_page=confirm_large_page)
        with jobs_lock:
            transfers[job_id].update(status='finished', report=report, stage='Preview ready', completed_steps=5)
    except GenerationCancelled as exc:
        with jobs_lock:
            transfers[job_id].update(status='cancelled', stage='Generation cancelled', error=str(exc))
    except Exception as exc:
        with jobs_lock:
            message = str(exc).replace(api_key, '[redacted]') if api_key else str(exc)
            transfers[job_id].update(status='error', error=f'{type(exc).__name__}: {message}')

CONTROLS_PATH = BASE_DIR / 'static' / 'preview-controls.js'

def with_preview_controls(html, nonce, trusted_scripts, download_url):
    # Only the preview controls and the trusted demo script receive the nonce.
    if nonce and trusted_scripts:
        html = re.sub(r'<script(?=[\s>])', lambda match: match.group(0) + ' nonce="' + nonce + '"', html, flags=re.I)
    nonce_attr = f' nonce="{nonce}"' if nonce else ''
    controls = CONTROLS_PATH.read_text(encoding='utf-8').replace('__RESTYLE_DOWNLOAD__', json.dumps(download_url))
    overlay = '<script' + nonce_attr + '>' + controls + '</script>'
    if re.search(r'</body\s*>', html, flags=re.I):
        return re.sub(r'</body\s*>', lambda match: overlay + match.group(0), html, count=1, flags=re.I)
    return html + overlay

def overlay_preview(html, download_url, trusted_scripts=False):
    nonce = secrets.token_urlsafe(24)
    resp = app.response_class(with_preview_controls(html, nonce, trusted_scripts, download_url), mimetype='text/html')
    resp.headers['Content-Security-Policy'] = f"default-src 'none'; img-src https: http: data:; media-src https: http: data:; style-src 'unsafe-inline'; font-src https: http: data:; script-src 'nonce-{nonce}'; form-action 'none'; base-uri 'none'; sandbox allow-scripts allow-downloads allow-popups allow-popups-to-escape-sandbox"
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp

DEMO_PATH = BASE_DIR.resolve() / 'docs' / 'classy-eth-preview' / 'index.html'

@app.get('/simulation/preview')
def simulation_preview():
    if not DEMO_PATH.is_file(): abort(404)
    return overlay_preview(DEMO_PATH.read_text(encoding='utf-8'), '/simulation/download', trusted_scripts=True)


@app.get('/simulation/download')
def simulation_download():
    if not DEMO_PATH.is_file(): abort(404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(DEMO_PATH, 'index.html')
    buf.seek(0)
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name='classy-eth-simulation.zip')

@app.get('/api/config')
def transfer_config():
    return jsonify(engine='claude-agent', model=os.environ.get('ANTHROPIC_MODEL', MODEL_DEFAULT), effort='medium', version=2)

@app.post('/api/transfers')
def start_transfer():
    data = request.get_json(silent=True) or {}
    api_key = data.get('api_key', '')
    if not isinstance(api_key, str) or len(api_key) > 512:
        return jsonify(error='Invalid API key.'), 400
    api_key = api_key.strip() or os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        return jsonify(error='Enter your Claude API key to start generation.'), 400
    urls = []
    for key in ('old_url', 'reference_url'):
        value = data.get(key, '')
        if not isinstance(value, str): return jsonify(error='Invalid URL.'), 400
        value = value.strip()
        if value and '://' not in value: value = 'https://' + value
        parsed = urlparse(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            return jsonify(error='Enter two valid HTTP or HTTPS URLs.'), 400
        urls.append(value)
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        transfers[job_id] = {'id':job_id, 'status':'running', 'stage':'Starting', 'completed_steps':0, 'total_steps':5, 'error':None}
    threading.Thread(target=run_transfer, args=(job_id, *urls, api_key), daemon=True).start()
    return jsonify(id=job_id, engine='claude-agent'), 202

@app.post('/api/transfers/<job_id>/approval')
def approve_transfer(job_id):
    if not re.fullmatch(r'[0-9a-f]{12}', job_id): abort(404)
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get('approve'), bool):
        return jsonify(error='Specify whether generation should continue.'), 400
    with jobs_lock:
        job = transfers.get(job_id)
        pending = pending_confirmations.get(job_id)
        if not job or not pending or job['status'] != 'awaiting_approval':
            return jsonify(error='This confirmation is no longer active.'), 409
        pending['approved'] = data['approve']
        job['status'] = 'running' if data['approve'] else 'cancelled'
        job['stage'] = 'Resuming generation' if data['approve'] else 'Generation cancelled'
        pending['event'].set()
    return jsonify(ok=True)

@app.get('/api/transfers/<job_id>')
def transfer_status(job_id):
    if not re.fullmatch(r'[0-9a-f]{12}', job_id): abort(404)
    with jobs_lock:
        job = transfers.get(job_id)
        if job:
            return jsonify(job)
    # Finished results remain usable after a server restart.
    folder = TRANSFER_DIR / job_id
    try:
        if not (folder / 'index.html').is_file(): abort(404)
        report = json.loads((folder / 'design-report.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        abort(404)
    return jsonify(id=job_id, status='finished', stage='Preview ready', completed_steps=5, total_steps=5, error=None, report=report)

@app.get('/api/transfers/<job_id>/preview')
def transfer_preview(job_id):
    if not re.fullmatch(r'[0-9a-f]{12}', job_id) or not (TRANSFER_DIR/job_id/'index.html').exists(): abort(404)
    return overlay_preview((TRANSFER_DIR/job_id/'index.html').read_text(encoding='utf-8'), f'/api/transfers/{job_id}/download')


@app.get('/api/transfers/<job_id>/design-specification')
def transfer_specification(job_id):
    if not re.fullmatch(r'[0-9a-f]{12}', job_id): abort(404)
    return send_from_directory(TRANSFER_DIR/job_id, 'design-specification.md', mimetype='text/plain')

@app.get('/api/transfers/<job_id>/source/assets/images/<path:filename>')
def transfer_image(job_id, filename):
    if not re.fullmatch(r'[0-9a-f]{12}', job_id): abort(404)
    resp = send_from_directory(TRANSFER_DIR/job_id/'source'/'assets'/'images', filename)
    resp.headers['Content-Security-Policy'] = "default-src 'none'; sandbox"
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp

@app.get('/api/transfers/<job_id>/download')
def transfer_download(job_id):
    if not re.fullmatch(r'[0-9a-f]{12}', job_id) or not (TRANSFER_DIR/job_id/'index.html').exists(): abort(404)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as zf:
        for f in (TRANSFER_DIR/job_id).rglob('*'):
            if f.is_file():
                zf.write(f,f.relative_to(TRANSFER_DIR/job_id))
    buf.seek(0)
    return send_file(buf,mimetype='application/zip',as_attachment=True,download_name=f'restyle-{job_id}.zip')


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)
