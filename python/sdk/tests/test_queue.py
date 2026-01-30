import httpx

from experiment_tracker_sdk.queue import RequestItem, RequestQueue


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
