import httpx

from experiment_tracker_sdk.client.request import FileUploadSpec
from experiment_tracker_sdk.client.queue import RequestItem, RequestQueue


def test_request_queue_flush_sends_request():
    received = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="http://test", transport=transport)
    queue = RequestQueue(client, poll_interval=0.01)

    queue.enqueue(RequestItem(method="POST", path="/api/metrics", json={"ok": True}))
    queue.flush()
    queue.close()

    assert len(received) == 1


def test_request_queue_flush_sends_multipart_request() -> None:
    received = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="http://test", transport=transport)
    request_queue = RequestQueue(client, poll_interval=0.01)

    request_queue.enqueue(
        RequestItem(
            method="POST",
            path="/metrics",
            form_data={"name": "loss"},
            files={
                "file": FileUploadSpec(
                    filename="loss.txt",
                    content=b"0.123",
                    content_type="text/plain",
                )
            },
        )
    )
    request_queue.flush()
    request_queue.close()

    assert len(received) == 1
    sent_request = received[0]
    assert "multipart/form-data" in sent_request.headers.get("content-type", "")
    assert b'name="name"' in sent_request.content
    assert b"loss" in sent_request.content
    assert b'filename="loss.txt"' in sent_request.content
    assert b"0.123" in sent_request.content
