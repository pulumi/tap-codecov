"""REST client handling, including CodecovStream base class."""

from __future__ import annotations
from http import HTTPStatus

from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, parse_qsl, urlparse

import requests
from singer_sdk.authenticators import BearerTokenAuthenticator
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.pagination import BaseAPIPaginator  # noqa: TCH002
from singer_sdk.streams import RESTStream
from singer_sdk.pagination import BaseHATEOASPaginator
from singer_sdk.exceptions import FatalAPIError, RetriableAPIError

class CodeCovPaginator(BaseHATEOASPaginator):
    def get_next_url(self, response):
        data = response.json()
        return data.get("next")
    
_Auth = Callable[[requests.PreparedRequest], requests.PreparedRequest]
SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class CodecovStream(RESTStream):
    """Codecov stream class."""

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        # TODO: hardcode a value here, or retrieve it from self.config
        return f"https://api.codecov.io/api/v2/{self.config['service']}/{self.config['owner']}"

    records_jsonpath = "$.results[*]"
    default_params = {"page_size": 1000}
    params_from_context = []
    tolerated_http_errors = []
    # Set this value or override `get_new_paginator`.
    next_page_token_jsonpath = "$.next"  # noqa: S105

    @property
    def authenticator(self) -> BearerTokenAuthenticator:
        """Return a new authenticator object.

        Returns:
            An authenticator instance.
        """
        return BearerTokenAuthenticator.create_for_stream(
            self,
            token=self.config.get("auth_token", ""),
        )

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed.

        Returns:
            A dictionary of HTTP headers.
        """
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        # If not using an authenticator, you may also provide inline auth headers:
        # headers["Private-Token"] = self.config.get("auth_token")  # noqa: ERA001
        return headers

    def get_new_paginator(self) -> BaseAPIPaginator:
        return CodeCovPaginator()

    def get_url_params(
        self,
        context: dict | None,  # noqa: ARG002
        next_page_token: Any | None,  # noqa: ANN401
    ) -> dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization.

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary of URL query parameters.
        """
        params: dict = self.default_params
        if next_page_token:
            params.update(parse_qsl(next_page_token.query))

        for pc in self.params_from_context:
            if pc in context:
                params[pc] = context[pc]

        return params

    def prepare_request_payload(
        self,
        context: dict | None,  # noqa: ARG002
        next_page_token: Any | None,  # noqa: ARG002, ANN401
    ) -> dict | None:
        """Prepare the data payload for the REST API request.

        By default, no payload will be sent (return None).

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary with the JSON body for a POST requests.
        """
        return None

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result records.

        Args:
            response: The HTTP ``requests.Response`` object.

        Yields:
            Each record from the source.
        """
        if response.status_code in self.tolerated_http_errors:
            return []
        for record in extract_jsonpath(self.records_jsonpath, input=response.json()):
            yield record
            

    def post_process(
        self,
        row: dict,
        context: dict | None = None,  # noqa: ARG002
    ) -> dict | None:
        """As needed, append or transform raw data to match expected structure.

        Args:
            row: An individual record from the stream.
            context: The stream context.

        Returns:
            The updated record dictionary, or ``None`` to skip the record.
        """
        return row


    def validate_response(self, response: requests.Response) -> None:
        if response.status_code in self.tolerated_http_errors:
            full_path = urlparse(response.url).path
            query = urlparse(response.url).query
            msg = (
                f"{response.status_code} Tolerated Status Code "
                f"(Reason: {response.reason}) for path: {full_path}"
                f"Query: {query}"
            )
            self.logger.warn(msg)
            return

        if (
            response.status_code in self.extra_retry_statuses
            or HTTPStatus.INTERNAL_SERVER_ERROR
            <= response.status_code
            <= max(HTTPStatus)
        ):
            msg = self.response_error_message(response)
            raise RetriableAPIError(msg, response)

        if (
            HTTPStatus.BAD_REQUEST
            <= response.status_code
            < HTTPStatus.INTERNAL_SERVER_ERROR
        ):
            msg = self.response_error_message(response)
            raise FatalAPIError(msg)