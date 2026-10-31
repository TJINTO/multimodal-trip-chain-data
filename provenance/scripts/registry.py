"""Capture source evidence with explicit time, hash and redistribution scopes."""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urljoin
import hashlib
import io
import json
import re
import time
import unicodedata

from bs4 import BeautifulSoup
import requests


TZ = timezone(timedelta(hours=8))
SECRET_KEYS = {"key", "api_key", "apikey", "token", "access_token", "authorization", "password"}


def now():
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def normalized_text(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip() + "\n"


def text_hash(text):
    return hashlib.sha256(normalized_text(text).encode("utf-8")).hexdigest()


def validate_source_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only credential-free HTTP(S) source URLs are allowed")
    if SECRET_KEYS.intersection(key.lower() for key in parse_qs(parsed.query)):
        raise ValueError("Secret-bearing URL is not suitable for publication")
    return True


def extract_html(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    challenge = any(key in title.casefold() for key in ["checking your browser", "just a moment", "access denied", "security check", "captcha"])
    permanent = ""
    link = soup.find(id="t-permalink")
    if link and link.find("a", href=True):
        permanent = urljoin("https://en.wikipedia.org/", link.find("a")["href"])
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "form"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.find(id="mw-content-text") or soup.body or soup
    text = normalized_text(main.get_text(" ", strip=True))
    if len(text) < 500 and any(term in text.casefold() for term in ["recaptcha", "checking your browser", "enable javascript and cookies"]):
        challenge = True
    return title, text, challenge, permanent


def capture(source, private_root, public_root, check_wayback=False):
    source = dict(source)
    data_id = source["data_id"]
    validate_source_url(source["source_url"])
    fetch_url = source.get("capture_url", source["source_url"])
    validate_source_url(fetch_url)
    mode = source.get("capture_mode", "get")
    receipt = {"data_id": data_id, "source_url": source["source_url"], "capture_url": fetch_url,
        "capture_started_at": now(), "capture_status": "not_attempted", "http_status": "",
        "http_method": mode.upper(), "response_sha256": "", "content_hash": "",
        "extraction_method": "", "content_characters": 0, "content_path": "",
        "public_text_snapshot": False, "external_archive_url": "", "external_archive_timestamp": "",
        "external_archive_status": "not_checked", "publisher_snapshot_url": ""}
    text = ""
    if mode == "reference_only":
        receipt["capture_status"] = "reference_only_no_request"
        receipt["capture_started_at"] = ""
    else:
        session = requests.Session()
        session.headers["User-Agent"] = "TransportResearchSourceAudit/1.0 (public-source reproducibility)"
        try:
            started = time.monotonic()
            response = session.request("HEAD" if mode == "head" else "GET", fetch_url, timeout=(10, 20),
                allow_redirects=True, stream=True)
            validate_source_url(response.url)
            receipt.update(http_status=response.status_code, resolved_url=response.url,
                response_content_type=response.headers.get("Content-Type", ""),
                response_last_modified=response.headers.get("Last-Modified", ""),
                response_etag=response.headers.get("ETag", ""))
            if mode == "head":
                receipt["capture_status"] = "headers_only" if response.ok else "http_error"
            else:
                chunks, size = [], 0
                for block in response.iter_content(chunk_size=65536):
                    size += len(block)
                    if size > 25 * 1024 * 1024 or time.monotonic() - started > 50:
                        raise ValueError("Response exceeds audit capture size/time limit")
                    chunks.append(block)
                body = b"".join(chunks)
                receipt["response_sha256"] = hashlib.sha256(body).hexdigest()
                receipt["response_bytes"] = len(body)
                private_root.mkdir(parents=True, exist_ok=True)
                (private_root / (data_id + ".response")).write_bytes(body)
                if not response.ok:
                    receipt["capture_status"] = "http_error"
                elif body.startswith(b"%PDF"):
                    from pypdf import PdfReader
                    reader = PdfReader(io.BytesIO(body))
                    text = normalized_text("\n".join(page.extract_text() or "" for page in reader.pages))
                    receipt.update(capture_status="captured_text", extraction_method="pypdf-5.9.0; NFC; collapse-whitespace; UTF-8; final-LF", pdf_pages=len(reader.pages))
                else:
                    response._content = body
                    response.encoding = response.apparent_encoding or "utf-8"
                    if "json" in receipt["response_content_type"].lower():
                        parsed = response.json()
                        text = normalized_text(json.dumps(parsed, ensure_ascii=False, sort_keys=True))
                        receipt.update(capture_status="captured_text", extraction_method="JSON parsed/sorted; NFC; collapse-whitespace; UTF-8; final-LF")
                    else:
                        title, text, challenge, permalink = extract_html(response.text)
                        receipt["retrieved_title"] = title[:400]
                        receipt["publisher_snapshot_url"] = permalink
                        if challenge:
                            text = ""
                            receipt["capture_status"] = "blocked_or_challenge"
                        elif len(text) < 80:
                            receipt["capture_status"] = "insufficient_text_or_js_shell"
                            text = ""
                        else:
                            receipt.update(capture_status="captured_text", extraction_method="BeautifulSoup article/main/body; remove script/style/navigation; NFC; collapse-whitespace; UTF-8; final-LF")
                if text:
                    text = normalized_text(text)
                    with (private_root / (data_id + ".txt")).open("w", encoding="utf-8", newline="\n") as handle:
                        handle.write(text)
                    receipt.update(content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(), content_characters=len(text))
                    if source.get("public_text_allowed") and receipt["capture_status"] == "captured_text":
                        path = public_root / "snapshots" / (data_id + ".txt")
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with path.open("w", encoding="utf-8", newline="\n") as handle:
                            handle.write(text)
                        receipt.update(public_text_snapshot=True, content_path="provenance/snapshots/" + data_id + ".txt")
            response.close()
        except Exception as exc:
            receipt["capture_status"] = "capture_error"
            receipt["error_type"] = type(exc).__name__
            receipt["error_message"] = str(exc)[:500]
    receipt["capture_finished_at"] = now() if mode != "reference_only" else ""
    if check_wayback and source["source_type"] in {"news", "report", "academic_article"}:
        try:
            result = requests.get("https://archive.org/wayback/available", params={"url": source["source_url"]}, timeout=(5, 8))
            result.raise_for_status()
            closest = result.json().get("archived_snapshots", {}).get("closest", {})
            if closest.get("available") and closest.get("url", "").startswith(("https://web.archive.org/", "http://web.archive.org/")):
                archive = closest["url"].replace("http://", "https://", 1)
                checked = requests.head(archive, timeout=(5, 8), allow_redirects=True)
                if checked.ok:
                    receipt.update(external_archive_url=archive, external_archive_timestamp=closest.get("timestamp", ""),
                        external_archive_status="archive_endpoint_verified_content_not_compared")
                else:
                    receipt["external_archive_status"] = "archive_endpoint_unavailable"
            else:
                receipt["external_archive_status"] = "no_snapshot_returned"
        except Exception:
            receipt["external_archive_status"] = "archive_check_failed"
    public_receipt = dict(receipt, title=source["title"], rights_status=source["rights_status"],
        source_type=source["source_type"], original_use_evidence=source["source_locator"],
        historical_recorded_at=source.get("historical_recorded_at", ""),
        historical_time_basis=source.get("historical_time_basis", "unknown"))
    (public_root / "capture_receipts").mkdir(parents=True, exist_ok=True)
    with (public_root / "capture_receipts" / (data_id + ".json")).open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(public_receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return public_receipt
