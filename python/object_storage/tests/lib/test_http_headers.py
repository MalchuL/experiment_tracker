from __future__ import annotations

from urllib.parse import unquote

from object_storage.lib.http_headers import attachment_content_disposition


def test_attachment_content_disposition_ascii() -> None:
    header = attachment_content_disposition("train.yaml")
    assert header == 'attachment; filename="train.yaml"'


def test_attachment_content_disposition_unicode() -> None:
    filename = "! Двач @dvachannel @rand2ch @ru2ch_ban ! (1).mp4"
    header = attachment_content_disposition(filename)
    assert header.startswith("attachment; filename*=UTF-8''")
    encoded = header.split("UTF-8''", 1)[1]
    assert unquote(encoded) == filename
    header.encode("latin-1")
