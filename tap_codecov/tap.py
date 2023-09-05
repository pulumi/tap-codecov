"""Codecov tap class."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th  # JSON schema typing helpers

# TODO: Import your custom stream types here:
from tap_codecov import streams


class TapCodecov(Tap):
    """Codecov tap class."""

    name = "tap-codecov"

    # TODO: Update this section with the actual config values you expect:
    config_jsonschema = th.PropertiesList(
        th.Property(
            "auth_token",
            th.StringType,
            required=True,
            secret=True,  # Flag config as protected.
            description="The token to authenticate against the API service",
        ),
        th.Property(
            "service",
            th.StringType,
            default="github",
            description="Which service to use (github, github_enterprise, gitlab, gitlab_enterprise, bitbucket, bitbucket_server)",
        ),
        th.Property(
            "owner",
            th.StringType,
            description="Which owner to query (Usually the organization name)",
        ),
    ).to_dict()

    def discover_streams(self) -> list[streams.CodecovStream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [
            streams.RepositoriesStream(self),
            streams.CommitStream(self)
        ]


if __name__ == "__main__":
    TapCodecov.cli()
