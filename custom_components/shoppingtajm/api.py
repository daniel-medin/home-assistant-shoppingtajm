"""Async client for the ShoppingTajm REST API."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any, Self
from urllib.parse import quote, urlencode, urljoin

from aiohttp import (
    ClientConnectionError,
    ClientError,
    ClientResponse,
    ClientSession,
    ClientTimeout,
)

from .const import STATUS_ACTIVE, STATUS_COMPLETED

_LOGGER = logging.getLogger(__name__)

_RETRYABLE_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_REQUEST_TIMEOUT = ClientTimeout(total=20)
_EVENT_STREAM_TIMEOUT = ClientTimeout(total=None, sock_connect=20)


class ShoppingTajmError(Exception):
    """Base ShoppingTajm API error."""


class ShoppingTajmAuthError(ShoppingTajmError):
    """Authentication failed."""


class ShoppingTajmForbiddenError(ShoppingTajmError):
    """The authenticated user is not allowed to perform the action."""


class ShoppingTajmNotFoundError(ShoppingTajmError):
    """The requested resource was not found."""


class ShoppingTajmConnectionError(ShoppingTajmError):
    """Could not connect to ShoppingTajm."""


class ShoppingTajmServerError(ShoppingTajmError):
    """ShoppingTajm returned a server-side error."""


class ShoppingTajmValidationError(ShoppingTajmError):
    """ShoppingTajm rejected the request."""


@dataclass(slots=True, frozen=True)
class ShoppingTajmAudio:
    """A ShoppingTajm item audio response."""

    content: bytes
    content_type: str


@dataclass(slots=True, frozen=True)
class ShoppingTajmEvent:
    """A ShoppingTajm server-sent event."""

    event: str
    id: str | None
    data: str


@dataclass(slots=True, frozen=True)
class ShoppingTajmList:
    """A ShoppingTajm shopping list."""

    id: int
    name: str
    item_count: int | None
    update_count: int | None
    list_type: str | None
    list_kind: str | None
    is_cost_list: bool | None
    is_grocery_list: bool | None
    raw: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Self:
        """Build a list object from API data."""
        return cls(
            id=_as_int(data.get("id") or data.get("Id")),
            name=str(data.get("name") or data.get("Name") or ""),
            item_count=_as_optional_int(data.get("itemCount") or data.get("ItemCount")),
            update_count=_as_optional_int(
                data.get("updateCount") or data.get("UpdateCount")
            ),
            list_type=_as_optional_str(_api_value(data, "listType", "ListType")),
            list_kind=_as_optional_str(_api_value(data, "listKind", "ListKind")),
            is_cost_list=_as_optional_bool(
                _api_value(data, "isCostList", "IsCostList")
            ),
            is_grocery_list=_as_optional_bool(
                _api_value(data, "isGroceryList", "IsGroceryList")
            ),
            raw=data,
        )

    @property
    def supports_items(self) -> bool:
        """Return whether this list is a grocery list with item support."""
        if self.is_grocery_list is not None:
            return self.is_grocery_list
        if self.is_cost_list is True:
            return False

        list_kind = (self.list_kind or "").lower()
        if list_kind:
            return list_kind == "grocerylist"

        list_type = (self.list_type or "").lower()
        if list_type:
            return list_type == "shopping"

        return True


@dataclass(slots=True, frozen=True)
class ShoppingTajmItem:
    """A ShoppingTajm shopping item."""

    id: int
    name: str
    status: str
    extra_count: int | None
    created_at: str | None
    raw: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Self:
        """Build an item object from API data."""
        return cls(
            id=_as_int(data.get("id") or data.get("Id")),
            name=str(data.get("name") or data.get("Name") or ""),
            status=str(data.get("status") or data.get("Status") or "").lower(),
            extra_count=_as_optional_int(
                data.get("extraCount") or data.get("ExtraCount")
            ),
            created_at=_as_optional_str(data.get("createdAt") or data.get("CreatedAt")),
            raw=data,
        )


@dataclass(slots=True, frozen=True)
class ShoppingTajmData:
    """Normalized ShoppingTajm data for Home Assistant entities."""

    server_url: str
    total_lists: int
    active_list_id: int | None
    active_list_name: str | None
    remaining_items: int
    completed_items: int
    last_updated: str
    lists: tuple[ShoppingTajmList, ...]
    items: tuple[ShoppingTajmItem, ...]
    api_status: dict[str, Any] | None = None

    @property
    def stable_unique_suffix(self) -> str:
        """Return a stable suffix for entity unique IDs."""
        return hashlib.sha256(self.server_url.encode()).hexdigest()[:10]


class ShoppingTajmApiClient:
    """ShoppingTajm REST API client."""

    def __init__(
        self,
        session: ClientSession,
        server_url: str,
        token: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self.server_url = normalize_server_url(server_url)
        self._token = token

    @property
    def token_fingerprint(self) -> str:
        """Return a non-secret fingerprint of the configured token."""
        return hashlib.sha256(self._token.encode()).hexdigest()[:12]

    async def async_validate_credentials(self) -> dict[str, Any] | None:
        """Validate credentials against the Home Assistant status endpoint.

        A 404 fallback is allowed for older ShoppingTajm servers that expose the
        documented list/item API but not yet `/api/ha/status`.
        """
        try:
            status = await self.async_get_ha_status()
        except ShoppingTajmNotFoundError:
            _LOGGER.debug(
                "ShoppingTajm /api/ha/status is unavailable; falling back to /api/lists"
            )
            await self.async_get_lists()
            return None
        return status

    async def async_get_data(self) -> ShoppingTajmData:
        """Fetch and normalize data for Home Assistant."""
        status: dict[str, Any] | None
        try:
            status = await self.async_get_ha_status()
        except ShoppingTajmNotFoundError:
            status = None

        if status is not None and _status_has_summary(status):
            return await self._data_from_status(status)

        lists = _grocery_lists(tuple(await self.async_get_lists()))
        active_list_id = await self.async_get_active_list_id()
        active_list = _list_by_id(lists, active_list_id) or _pick_active_list(lists)
        active_list_id = active_list.id if active_list is not None else None
        items = (
            tuple(await self.async_get_items(active_list_id))
            if active_list_id is not None
            else ()
        )

        return ShoppingTajmData(
            server_url=self.server_url,
            total_lists=len(lists),
            active_list_id=active_list_id,
            active_list_name=active_list.name if active_list else None,
            remaining_items=sum(1 for item in items if item.status == STATUS_ACTIVE),
            completed_items=sum(1 for item in items if item.status == STATUS_COMPLETED),
            last_updated=datetime.now(UTC).isoformat(),
            lists=lists,
            items=items,
            api_status=status,
        )

    async def async_get_ha_status(self) -> dict[str, Any]:
        """Fetch the ShoppingTajm Home Assistant status payload."""
        data = await self._request("GET", "/api/ha/status")
        if not isinstance(data, dict):
            raise ShoppingTajmValidationError("Unexpected status response from API")
        return data

    async def async_get_lists(self) -> list[ShoppingTajmList]:
        """Fetch accessible shopping lists."""
        data = await self._request("GET", "/api/lists")
        if not isinstance(data, list):
            raise ShoppingTajmValidationError("Unexpected list response from API")
        return [
            ShoppingTajmList.from_api(item) for item in data if isinstance(item, dict)
        ]

    async def async_get_active_list_id(self) -> int | None:
        """Fetch the active ShoppingTajm list ID for the authenticated user."""
        data = await self._request("GET", "/api/auth/me")
        if not isinstance(data, dict):
            raise ShoppingTajmValidationError("Unexpected account response from API")
        return _as_optional_int(data.get("activeListId") or data.get("ActiveListId"))

    async def async_get_items(
        self, list_id: int | None = None
    ) -> list[ShoppingTajmItem]:
        """Fetch shopping items for a list, or the active list when omitted."""
        path = "/api/items"
        if list_id is not None:
            path = f"{path}?listId={list_id}"
        data = await self._request("GET", path)
        if not isinstance(data, list):
            raise ShoppingTajmValidationError("Unexpected item response from API")
        return [
            ShoppingTajmItem.from_api(item) for item in data if isinstance(item, dict)
        ]

    async def async_add_item(self, list_id: int, item_name: str) -> None:
        """Add an item to a ShoppingTajm list."""
        await self._request(
            "POST",
            "/api/items",
            json={"listId": list_id, "name": item_name},
        )

    async def async_update_item_name(
        self,
        list_id: int,
        item_id: int,
        item_name: str,
    ) -> None:
        """Update a ShoppingTajm item name."""
        await self._request(
            "PUT",
            f"/api/items/{item_id}?{urlencode({'listId': str(list_id)})}",
            json={"name": item_name},
        )

    async def async_set_item_quantity(
        self,
        list_id: int,
        item_id: int,
        quantity: int,
    ) -> None:
        """Set the visible ShoppingTajm item quantity."""
        extra_count = max(quantity - 1, 0)
        await self._request(
            "PUT",
            f"/api/items/{item_id}/extra-count?{urlencode({'listId': str(list_id)})}",
            json={"extraCount": extra_count},
        )

    async def async_complete_item(
        self,
        item_id: int,
        list_id: int | None = None,
    ) -> None:
        """Mark an item as completed/cart in the active list."""
        path = f"/api/items/{item_id}/status"
        if list_id is not None:
            path = f"{path}?{urlencode({'listId': str(list_id)})}"
        await self._request(
            "PUT",
            path,
            json={"status": STATUS_COMPLETED},
        )

    async def async_delete_item(
        self,
        item_id: int,
        list_id: int | None = None,
    ) -> None:
        """Delete an item from the active list."""
        path = f"/api/items/{item_id}"
        if list_id is not None:
            path = f"{path}?{urlencode({'listId': str(list_id)})}"
        await self._request("DELETE", path)

    async def async_create_list(self, name: str) -> None:
        """Create and activate a ShoppingTajm list."""
        await self._request("POST", "/api/lists", json={"name": name, "activate": True})

    async def async_activate_list(self, list_id: int) -> None:
        """Set the active ShoppingTajm list."""
        await self._request("PUT", "/api/lists/active", json={"listId": list_id})

    async def async_reorder_items(
        self,
        list_id: int,
        status: str,
        item_ids: list[int],
    ) -> None:
        """Persist ShoppingTajm item sort order."""
        await self._request(
            "PUT",
            "/api/items/reorder",
            json={"listId": list_id, "status": status, "itemIds": item_ids},
        )

    async def async_get_item_suggestions(
        self,
        query: str,
        list_id: int,
    ) -> list[dict[str, Any]]:
        """Fetch item suggestions for the custom card autocomplete."""
        params = {"listId": str(list_id)}
        if query:
            params["q"] = query
        data = await self._request("GET", f"/api/items/suggestions?{urlencode(params)}")
        if not isinstance(data, list):
            raise ShoppingTajmValidationError("Unexpected suggestion response from API")
        return [item for item in data if isinstance(item, dict)]

    async def async_get_item_audio(
        self,
        list_id: int,
        item_id: int,
    ) -> ShoppingTajmAudio:
        """Fetch item audio bytes for the custom card."""
        return await self._request_bytes(
            "GET",
            f"/api/items/{item_id}/audio?{urlencode({'listId': str(list_id)})}",
        )

    async def async_iter_events(
        self,
        last_event_id: str | None = None,
    ) -> AsyncIterator[ShoppingTajmEvent]:
        """Stream ShoppingTajm server-sent events."""
        url = urljoin(f"{self.server_url}/", "/api/ha/events".lstrip("/"))
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "text/event-stream",
        }
        if last_event_id is not None:
            headers["Last-Event-ID"] = last_event_id

        try:
            async with self._session.get(
                url,
                headers=headers,
                timeout=_EVENT_STREAM_TIMEOUT,
            ) as response:
                await self._raise_for_status(response)
                content_type = response.headers.get("Content-Type", "")
                if "text/event-stream" not in content_type.lower():
                    raise ShoppingTajmValidationError(
                        f"Unexpected ShoppingTajm event content type: {content_type}"
                    )

                async for event in _iter_sse_events(response):
                    yield event
        except (ClientConnectionError, TimeoutError) as err:
            raise ShoppingTajmConnectionError(
                "Could not connect to ShoppingTajm event stream"
            ) from err
        except ClientError as err:
            raise ShoppingTajmConnectionError(
                "Could not communicate with ShoppingTajm event stream"
            ) from err

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make an API request with retries for transient failures."""
        url = urljoin(f"{self.server_url}/", path.lstrip("/"))
        last_error: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                async with self._session.request(
                    method,
                    url,
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Accept": "application/json",
                    },
                    json=json,
                    timeout=_REQUEST_TIMEOUT,
                ) as response:
                    return await self._handle_response(response)
            except (ClientConnectionError, TimeoutError) as err:
                last_error = err
                if attempt == _MAX_ATTEMPTS - 1:
                    raise ShoppingTajmConnectionError(
                        "Could not connect to ShoppingTajm"
                    ) from err
            except ShoppingTajmServerError as err:
                last_error = err
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            except ClientError as err:
                raise ShoppingTajmConnectionError(
                    "Could not communicate with ShoppingTajm"
                ) from err

            await asyncio.sleep(0.5 * 2**attempt)

        raise ShoppingTajmConnectionError("ShoppingTajm request failed") from last_error

    async def _request_bytes(
        self,
        method: str,
        path: str,
    ) -> ShoppingTajmAudio:
        """Make an API request and return raw response bytes."""
        url = urljoin(f"{self.server_url}/", path.lstrip("/"))
        last_error: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                async with self._session.request(
                    method,
                    url,
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Accept": "audio/*, application/octet-stream",
                    },
                    timeout=_REQUEST_TIMEOUT,
                ) as response:
                    await self._raise_for_status(response)
                    return ShoppingTajmAudio(
                        content=await response.read(),
                        content_type=response.headers.get(
                            "Content-Type",
                            "audio/mpeg",
                        ),
                    )
            except (ClientConnectionError, TimeoutError) as err:
                last_error = err
                if attempt == _MAX_ATTEMPTS - 1:
                    raise ShoppingTajmConnectionError(
                        "Could not connect to ShoppingTajm"
                    ) from err
            except ShoppingTajmServerError as err:
                last_error = err
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            except ClientError as err:
                raise ShoppingTajmConnectionError(
                    "Could not communicate with ShoppingTajm"
                ) from err

            await asyncio.sleep(0.5 * 2**attempt)

        raise ShoppingTajmConnectionError("ShoppingTajm request failed") from last_error

    async def _handle_response(self, response: ClientResponse) -> Any:
        """Convert an HTTP response into JSON or an integration exception."""
        await self._raise_for_status(response)

        if response.status == HTTPStatus.NO_CONTENT:
            return None

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            text = await response.text()
            if not text:
                return None
            raise ShoppingTajmValidationError(
                f"Unexpected ShoppingTajm response content type: {content_type}"
            )

        return await response.json()

    async def _raise_for_status(self, response: ClientResponse) -> None:
        """Raise a typed integration exception for unsuccessful responses."""
        if response.status == HTTPStatus.UNAUTHORIZED:
            raise ShoppingTajmAuthError("Invalid ShoppingTajm personal access token")
        if response.status == HTTPStatus.FORBIDDEN:
            raise ShoppingTajmForbiddenError("Access to ShoppingTajm resource denied")
        if response.status == HTTPStatus.NOT_FOUND:
            raise ShoppingTajmNotFoundError("ShoppingTajm resource not found")

        if response.status in _RETRYABLE_STATUSES:
            text = await response.text()
            raise ShoppingTajmServerError(
                f"ShoppingTajm returned {response.status}: {text}"
            )

        if response.status >= HTTPStatus.BAD_REQUEST:
            text = await response.text()
            raise ShoppingTajmValidationError(
                f"ShoppingTajm returned {response.status}: {text}"
            )

    async def _data_from_status(self, status: dict[str, Any]) -> ShoppingTajmData:
        """Normalize a rich `/api/ha/status` response."""
        lists_value = status.get("lists") or status.get("Lists") or []
        items_value = status.get("items") or status.get("Items") or []
        lists = _grocery_lists(
            tuple(
                ShoppingTajmList.from_api(item)
                for item in lists_value
                if isinstance(item, dict)
            )
        )
        requested_active_list_id = _as_optional_int(
            status.get("activeListId") or status.get("ActiveListId")
        )
        active_list = _extract_active_list(status, lists)
        active_list_id = active_list.id if active_list is not None else None
        if active_list_id == requested_active_list_id:
            items: tuple[ShoppingTajmItem, ...] = tuple(
                ShoppingTajmItem.from_api(item)
                for item in items_value
                if isinstance(item, dict)
            )
        elif active_list_id is not None:
            items = tuple(await self.async_get_items(active_list_id))
        else:
            items = ()
        use_status_item_summary = (
            active_list_id is not None and active_list_id == requested_active_list_id
        )
        return ShoppingTajmData(
            server_url=self.server_url,
            total_lists=len(lists),
            active_list_id=active_list_id,
            active_list_name=active_list.name if active_list else None,
            remaining_items=(
                _as_optional_int(
                    status.get("remainingItems") or status.get("RemainingItems")
                )
                if use_status_item_summary
                else None
            )
            or sum(1 for item in items if item.status == STATUS_ACTIVE),
            completed_items=(
                _as_optional_int(
                    status.get("completedItems") or status.get("CompletedItems")
                )
                if use_status_item_summary
                else None
            )
            or sum(1 for item in items if item.status == STATUS_COMPLETED),
            last_updated=_as_optional_str(
                status.get("lastUpdated") or status.get("LastUpdated")
            )
            or datetime.now(UTC).isoformat(),
            lists=lists,
            items=items,
            api_status=status,
        )


def normalize_server_url(server_url: str) -> str:
    """Normalize a ShoppingTajm server URL."""
    return server_url.strip().rstrip("/")


def unique_id_for_config(server_url: str, token_fingerprint: str) -> str:
    """Build a stable non-secret unique ID for a config entry."""
    normalized = normalize_server_url(server_url).lower()
    return f"{normalized}:{token_fingerprint}"


def _status_has_summary(status: dict[str, Any]) -> bool:
    """Return true when the status payload has entity summary fields."""
    keys = {key.lower() for key in status}
    return bool(
        {
            "totallists",
            "activelistname",
            "remainingitems",
            "completeditems",
            "lastupdated",
            "lists",
            "items",
        }
        & keys
    )


def _extract_active_list(
    status: dict[str, Any],
    lists: tuple[ShoppingTajmList, ...],
) -> ShoppingTajmList | None:
    """Extract active list from a status response."""
    active_value = status.get("activeList") or status.get("ActiveList")
    if isinstance(active_value, dict):
        active_list = ShoppingTajmList.from_api(active_value)
        if active_list.supports_items:
            return active_list

    active_id = _as_optional_int(
        status.get("activeListId") or status.get("ActiveListId")
    )
    if active_id is not None:
        for item in lists:
            if item.id == active_id:
                return item

    return _pick_active_list(lists)


def _grocery_lists(lists: tuple[ShoppingTajmList, ...]) -> tuple[ShoppingTajmList, ...]:
    """Return only lists that expose grocery item behavior."""
    return tuple(item for item in lists if item.supports_items)


def _pick_active_list(lists: tuple[ShoppingTajmList, ...]) -> ShoppingTajmList | None:
    """Pick the most likely active list from list summaries."""
    if not lists:
        return None
    for item in lists:
        raw = item.raw
        if raw.get("isActive") is True or raw.get("IsActive") is True:
            return item
    return lists[0]


def _list_by_id(
    lists: tuple[ShoppingTajmList, ...],
    list_id: int | None,
) -> ShoppingTajmList | None:
    """Return a list matching the given ID."""
    if list_id is None:
        return None
    for item in lists:
        if item.id == list_id:
            return item
    return None


def _as_int(value: Any) -> int:
    """Convert API value to int."""
    try:
        return int(value)
    except (TypeError, ValueError) as err:
        raise ShoppingTajmValidationError("API response is missing an ID") from err


def _api_value(data: dict[str, Any], *keys: str) -> Any:
    """Return the first present API value, preserving false-y values."""
    for key in keys:
        if key in data:
            return data[key]
    return None


def _as_optional_int(value: Any) -> int | None:
    """Convert API value to optional int."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_bool(value: Any) -> bool | None:
    """Convert API value to optional bool."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no"}:
            return False
    if isinstance(value, int):
        return bool(value)
    return None


def _as_optional_str(value: Any) -> str | None:
    """Convert API value to optional string."""
    if value is None:
        return None
    text = str(value)
    return text if text else None


def quote_path_value(value: str) -> str:
    """Quote a value for use in an API path."""
    return quote(value, safe="")


async def _iter_sse_events(
    response: ClientResponse,
) -> AsyncIterator[ShoppingTajmEvent]:
    """Parse server-sent event frames from an aiohttp response."""
    event_type = "message"
    event_id: str | None = None
    data_lines: list[str] = []

    async for raw_line in response.content:
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if not line:
            if data_lines:
                yield ShoppingTajmEvent(
                    event=event_type,
                    id=event_id,
                    data="\n".join(data_lines),
                )
            event_type = "message"
            event_id = None
            data_lines = []
            continue

        if line.startswith(":"):
            continue

        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]

        if field == "event":
            event_type = value
        elif field == "id":
            event_id = value
        elif field == "data":
            data_lines.append(value)
