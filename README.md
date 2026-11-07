# Website Style Swap

> **Experimental prototype:** this is a proof of concept, not a finished product. Results may be incomplete, inaccurate, or unusable and must be reviewed before use.

Website Style Swap explores applying the visual style of a reference website to the content of a source website. The local application crawls a source page, examines a reference page, and asks Claude to produce a design specification and a new HTML/CSS page. You can preview and download the result and supporting files. A separate crawler can explore multiple pages and save their images.

## Requirements and setup

- Python 3.10 or newer and an Internet connection.
- An Anthropic account, a **valid Anthropic API key**, and access to a compatible model for generation. A Claude subscription does not necessarily include API access.
- Chromium, installed by Playwright as shown below.

From the repository root, in PowerShell:

```powershell
cd crawler-app/crawler-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

On macOS or Linux, activate the environment with `source .venv/bin/activate` instead. Open <http://127.0.0.1:5050>, enter the source and reference URLs and your Anthropic API key, then start generation. Alternatively, set `ANTHROPIC_API_KEY` before starting the server. Never commit your key. Set `ANTHROPIC_MODEL` to select a model available to your account; the default model in the code must be available to you.

The standalone crawler is available at <http://127.0.0.1:5050/crawler> and does not require a Claude API key. Stop the server with `Ctrl+C`.

## How it works

1. Playwright visits the source page, saves its rendered HTML, and retrieves available images.
2. The application examines the reference and takes screenshots at different sizes.
3. Claude uses `website_design_extraction_specification.md` to produce a design specification and an HTML/CSS page, then attempts a visual review.
4. The interface provides a preview and downloads. Results are stored locally in `crawler-app/crawler-app/transfers/` and crawls in `crawls/`.

The Flask server is in `app.py`, the crawler in `crawler.py`, Claude generation in `ai_transfer.py`, and the interface in `static/`. `classy-eth-preview/` and `interface_front_end.html` contain interface previews or experiments. See the READMEs in `crawler-app/crawler-app/` for more detail.

## Costs, data, and limitations

Anthropic API calls may be billed to your account, and the application imposes no spending limit. Source content, observations, and reference screenshots are sent to Anthropic: do not use data you do not want to share. Only use websites and content you are authorized to access and use.

The generated page is a draft: text, images, links, layout, and accessibility may contain errors or omissions. Complex interactions, forms, and external services may not be reproduced. The preview blocks scripts in the generated page, and some website resources may be inaccessible. The application is intended for local use and should not be exposed to the Internet as-is.

## Disclaimer

This prototype is provided **as is**, without warranties of functionality, reliability, security, or fitness for a particular purpose. Users are responsible for reviewing results and complying with applicable rights and terms. To the extent permitted by applicable law, the authors disclaim liability for errors, losses, or direct or indirect damage arising from its use.

## Local test

From `crawler-app/crawler-app`, run `python test_transfer_smoke.py` to test the pipeline with simulated Claude responses and no paid API call. This does not guarantee the quality of a real generation.
