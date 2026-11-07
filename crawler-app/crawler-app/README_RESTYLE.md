# Restyle — Claude prototype

Restyle uses the crawler to retrieve a source page, then Claude to examine a reference page, produce a Markdown design report based on `website_design_extraction_specification.md`, and generate a new HTML/CSS page.

## Setup and use

See the [root README](../../README.md) for prerequisites and installation. Run `python app.py` in this directory and open <http://127.0.0.1:5050>. Enter both URLs and an Anthropic API key, or set `ANTHROPIC_API_KEY` before starting the server. The key entered in the form is passed to the local server, kept in memory during the job, and excluded from result files and job status. The field is cleared after the job starts. Use `ANTHROPIC_MODEL` to select a model available to your account. The standalone crawler is at <http://127.0.0.1:5050/crawler>.

## Pipeline

1. The crawler saves one rendered source page, its links, and available images.
2. The browser examines the reference DOM and accessible stylesheets and takes desktop and mobile screenshots. Claude can request additional read-only style inspections.
3. Claude writes `design-specification.md`; generation stops if required sections are missing.
4. Claude generates HTML/CSS and attempts a visual review using screenshots. If review fails, the first version is retained. A rough text check flags potentially missing fragments in `design-report.json`. Preview scripts are blocked.
5. The downloadable archive contains the page, reports, observations, screenshots, and crawled source files.

## Costs and limitations

Each generation makes multiple billable Anthropic API calls, with no application spending limit. Source page data, reference observations, and screenshots are sent to Anthropic. If source HTML exceeds 500,000 characters, the application asks for confirmation before sending it; the prompt expires after 30 minutes. Page size alone does not predict cost or guarantee the content fits the model's limits.

Results are drafts and must be reviewed. Layout, text, links, images, and reports may contain errors or omissions. Inaccessible styles, interactive states, and some assets cannot be fully analyzed; generated pages do not recreate complex JavaScript, forms, or external services. Fonts are not automatically embedded. Jobs are stored in `transfers/`; completed results survive a restart, but running jobs do not resume. Use locally on 127.0.0.1 and only with sites you have permission to access and use.

Run `python test_transfer_smoke.py` for a local smoke test using simulated Claude responses without paid API calls. It does not prove real generation quality or account access.
