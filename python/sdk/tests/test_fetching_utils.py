from __future__ import annotations

from pydantic import BaseModel

from experiment_tracker_sdk.client.request_types import ApiRequestSpec
from experiment_tracker_sdk.client.utils.fetching_utils import (
    fetch_all,
    fetch_all_requests,
    iter_pages,
)


class Page(BaseModel):
    data: list[int]
    hasNext: bool = False
    size: int = 0
    total: int = 0


def test_fetch_all_accumulates_pages_by_returned_size() -> None:
    calls: list[tuple[int, int]] = []
    pages = {
        5: Page(data=[1, 2], hasNext=True, size=2, total=5),
        7: Page(data=[3, 4, 5], hasNext=False, size=3, total=5),
    }

    def fetch_page(*, limit: int, offset: int) -> Page:
        calls.append((limit, offset))
        return pages[offset]

    assert fetch_all(fetch_page, limit=10, offset=5) == [1, 2, 3, 4, 5]
    assert calls == [(10, 5), (10, 7)]


def test_iter_pages_stops_at_max_pages() -> None:
    def fetch_page(*, limit: int, offset: int) -> Page:
        return Page(data=[offset], hasNext=True, size=1, total=10)

    pages = list(iter_pages(fetch_page, limit=1, max_pages=2))

    assert [page.data for page in pages] == [[0], [1]]


def test_fetch_all_rejects_empty_page_with_next_page() -> None:
    def fetch_page(*, limit: int, offset: int) -> Page:
        return Page(data=[], hasNext=True, size=0, total=1)

    try:
        fetch_all(fetch_page)
    except RuntimeError as exc:
        assert "returned no items" in str(exc)
        return
    raise AssertionError("Expected RuntimeError for a non-advancing page")


def test_fetch_all_requests_uses_request_specs() -> None:
    def make_request_spec(*, limit: int, offset: int) -> ApiRequestSpec[Page]:
        return ApiRequestSpec(
            method="GET",
            endpoint="/items",
            response_model=Page,
            query_params={"limit": limit, "offset": offset},
        )

    def request(spec: ApiRequestSpec[Page]) -> Page:
        assert spec.query_params is not None
        offset = spec.query_params["offset"]
        if offset == 0:
            return Page(data=[1, 2], hasNext=True, size=2, total=3)
        return Page(data=[3], hasNext=False, size=1, total=3)

    assert fetch_all_requests(request, make_request_spec, limit=2) == [1, 2, 3]
