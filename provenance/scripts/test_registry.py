import hashlib

import pytest

from registry import normalized_text, text_hash, validate_source_url, extract_html


def test_hash_uses_documented_unicode_and_newline_normalization():
    assert normalized_text("Cafe\u0301\r\n  text\tvalue ") == "Caf\u00e9 text value\n"
    assert text_hash("a\r\nb") == hashlib.sha256(b"a b\n").hexdigest()


def test_urls_with_credentials_are_not_allowed_in_public_metadata():
    assert validate_source_url("https://example.org/report?id=10")
    for url in ["https://example.org/?key=secret", "https://user:pass@example.org/", "file:///private"]:
        with pytest.raises(ValueError):
            validate_source_url(url)


def test_article_extraction_excludes_scripts_and_detects_challenges():
    title, text, blocked, _ = extract_html("<html><title>A report</title><article><p>Four metro lines.</p><script>secret</script></article></html>")
    assert title == "A report" and "Four metro lines" in text and "secret" not in text
    assert not blocked
    assert extract_html("<html><title>Checking your browser</title><p>reCAPTCHA</p></html>")[2]


def test_wikipedia_revision_link_survives_navigation_removal():
    page = '<nav><li id="t-permalink"><a href="/w/index.php?title=A&oldid=42">Permanent link</a></li></nav><article>Sample article body.</article>'
    assert extract_html(page)[3] == "https://en.wikipedia.org/w/index.php?title=A&oldid=42"
