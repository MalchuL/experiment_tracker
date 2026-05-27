from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Protocol, TypeVar, cast

from experiment_tracker_sdk.client.request_types import ApiRequestSpec

ItemT = TypeVar("ItemT")
PageT = TypeVar("PageT", bound="PaginatedPage[Any]")
PageT_co = TypeVar("PageT_co", bound="PaginatedPage[Any]", covariant=True)

DEFAULT_FETCH_LIMIT = 100


class PaginatedPage(Protocol[ItemT]):
    """Minimal pagination envelope shared by SDK list responses.

    Args:
        ItemT: Item type stored in the response ``data`` list.

    Attributes:
        data: Items returned for the current page.
        size: Number of items returned for the current page.
        total: Total number of items matching the endpoint query before
            pagination is applied.
    """

    data: list[ItemT]
    size: int
    total: int


class PageFetcher(Protocol[PageT_co]):
    """Callable that fetches one page with standard limit/offset arguments.

    Args:
        PageT_co: Concrete paginated response type returned by the callable.

    The callable must accept keyword-only ``limit`` and ``offset`` arguments and
    return a paginated response exposing ``data``, ``size``, ``total`` and either
    ``hasNext`` or ``has_next``.
    """

    def __call__(self, *, limit: int, offset: int) -> PageT_co: ...


class RequestSpecFactory(Protocol):
    """Callable that builds one paginated SDK request spec.

    The callable must accept keyword-only ``limit`` and ``offset`` arguments and
    return an :class:`ApiRequestSpec` for an endpoint that returns a paginated
    response.
    """

    def __call__(
        self, *, limit: int, offset: int
    ) -> ApiRequestSpec[Any]: ...


def _page_has_next(page: PaginatedPage[Any]) -> bool:
    """Return whether a paginated response reports another page.

    Args:
        page: Paginated response object with either ``hasNext`` or ``has_next``.

    Returns:
        ``True`` when the response reports that another page is available,
        otherwise ``False``.

    Raises:
        AttributeError: If the response exposes neither ``hasNext`` nor
            ``has_next``.
    """
    if hasattr(page, "hasNext"):
        return bool(getattr(page, "hasNext"))
    if hasattr(page, "has_next"):
        return bool(getattr(page, "has_next"))
    raise AttributeError("paginated response must expose hasNext or has_next")


def _page_size(page: PaginatedPage[Any]) -> int:
    """Return the number of items in a page.

    Args:
        page: Paginated response object.

    Returns:
        The response ``size`` field when it is an integer, otherwise
        ``len(page.data)``.
    """
    size = getattr(page, "size", None)
    if isinstance(size, int):
        return size
    return len(page.data)


def _as_paginated_page(value: Any) -> PaginatedPage[Any]:
    """Validate and cast an arbitrary request result to a paginated page.

    Args:
        value: Value returned by an SDK request call.

    Returns:
        The value cast as a ``PaginatedPage`` protocol.

    Raises:
        TypeError: If ``value`` does not expose a ``data`` attribute.
    """
    if not hasattr(value, "data"):
        raise TypeError("request did not return a paginated response")
    return cast(PaginatedPage[Any], value)


def iter_pages(
    fetch_page: PageFetcher[PageT],
    *,
    limit: int = DEFAULT_FETCH_LIMIT,
    offset: int = 0,
    max_pages: int | None = None,
) -> Iterator[PageT]:
    """Yield pages until a paginated endpoint reports that no next page exists.

    The backend list endpoints use ``limit`` and ``offset`` query arguments and
    return pagination metadata including ``data``, ``size``, ``total`` and
    ``hasNext``. This helper follows that contract and advances offsets by the
    number of items actually returned, matching the web infinite-query behavior.

    Args:
        fetch_page: Callable that fetches one page for keyword-only ``limit``
            and ``offset`` arguments.
        limit: Maximum number of items to request per page.
        offset: Initial offset to start fetching from.
        max_pages: Optional cap on the number of pages to yield. This is useful
            for bounded previews or tests.

    Yields:
        Each paginated response returned by ``fetch_page``.

    Raises:
        ValueError: If ``limit`` is not positive, ``offset`` is negative, or
            ``max_pages`` is provided and not positive.
        AttributeError: If a page does not expose ``hasNext`` or ``has_next``.
        RuntimeError: If a page reports another page but returns zero items,
            because the next offset cannot advance safely.
    """
    if limit <= 0:
        raise ValueError("limit must be greater than 0")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to 0")
    if max_pages is not None and max_pages <= 0:
        raise ValueError("max_pages must be greater than 0 when provided")

    current_offset = offset
    pages_fetched = 0

    while True:
        page = fetch_page(limit=limit, offset=current_offset)
        yield page
        pages_fetched += 1

        if max_pages is not None and pages_fetched >= max_pages:
            return
        if not _page_has_next(page):
            return

        page_size = _page_size(page)
        if page_size <= 0:
            raise RuntimeError(
                "paginated response reported another page but returned no items"
            )
        current_offset += page_size


def fetch_all(
    fetch_page: PageFetcher[PaginatedPage[ItemT]],
    *,
    limit: int = DEFAULT_FETCH_LIMIT,
    offset: int = 0,
    max_pages: int | None = None,
) -> list[ItemT]:
    """Fetch and flatten every item from a paginated endpoint.

    Args:
        fetch_page: Callable that fetches one page for keyword-only ``limit``
            and ``offset`` arguments.
        limit: Maximum number of items to request per page.
        offset: Initial offset to start fetching from.
        max_pages: Optional cap on the number of pages to fetch.

    Returns:
        A flat list containing all items from every fetched page, in page order.

    Raises:
        ValueError: If pagination arguments are invalid.
        AttributeError: If a page does not expose ``hasNext`` or ``has_next``.
        RuntimeError: If a page reports another page but returns zero items.
    """
    items: list[ItemT] = []
    for page in iter_pages(
        fetch_page,
        limit=limit,
        offset=offset,
        max_pages=max_pages,
    ):
        items.extend(page.data)
    return items


def iter_request_pages(
    request: Callable[[ApiRequestSpec[Any]], Any],
    make_request_spec: RequestSpecFactory,
    *,
    limit: int = DEFAULT_FETCH_LIMIT,
    offset: int = 0,
    max_pages: int | None = None,
) -> Iterator[PaginatedPage[Any]]:
    """Yield pages by building request specs and sending them through a client.

    Example:
        ``iter_request_pages(client.request, make_experiments_request)``

    Args:
        request: Callable that executes an :class:`ApiRequestSpec`, usually
            ``ExperimentTrackerClient.request``.
        make_request_spec: Callable that builds a paginated request spec for
            keyword-only ``limit`` and ``offset`` arguments.
        limit: Maximum number of items to request per page.
        offset: Initial offset to start fetching from.
        max_pages: Optional cap on the number of pages to yield.

    Yields:
        Paginated response pages returned by ``request``.

    Raises:
        TypeError: If ``request`` does not return a paginated response.
        ValueError: If pagination arguments are invalid.
        AttributeError: If a page does not expose ``hasNext`` or ``has_next``.
        RuntimeError: If a page reports another page but returns zero items.
    """

    def fetch_page(*, limit: int, offset: int) -> PaginatedPage[Any]:
        return _as_paginated_page(
            request(make_request_spec(limit=limit, offset=offset))
        )

    yield from iter_pages(
        fetch_page,
        limit=limit,
        offset=offset,
        max_pages=max_pages,
    )


def fetch_all_requests(
    request: Callable[[ApiRequestSpec[Any]], Any],
    make_request_spec: RequestSpecFactory,
    *,
    limit: int = DEFAULT_FETCH_LIMIT,
    offset: int = 0,
    max_pages: int | None = None,
) -> list[Any]:
    """Fetch and flatten all items using SDK ``ApiRequestSpec`` factories.

    Args:
        request: Callable that executes an :class:`ApiRequestSpec`, usually
            ``ExperimentTrackerClient.request``.
        make_request_spec: Callable that builds a paginated request spec for
            keyword-only ``limit`` and ``offset`` arguments.
        limit: Maximum number of items to request per page.
        offset: Initial offset to start fetching from.
        max_pages: Optional cap on the number of pages to fetch.

    Returns:
        A flat list containing all items from every fetched response page, in
        page order.

    Raises:
        TypeError: If ``request`` does not return a paginated response.
        ValueError: If pagination arguments are invalid.
        AttributeError: If a page does not expose ``hasNext`` or ``has_next``.
        RuntimeError: If a page reports another page but returns zero items.
    """
    items: list[Any] = []
    for page in iter_request_pages(
        request,
        make_request_spec,
        limit=limit,
        offset=offset,
        max_pages=max_pages,
    ):
        items.extend(page.data)
    return items
