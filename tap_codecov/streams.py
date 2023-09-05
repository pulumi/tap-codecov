"""Stream type classes for tap-codecov."""

from __future__ import annotations

import typing as t
from pathlib import Path

from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_codecov.client import CodecovStream

# TODO: Delete this is if not using json files for schema definition
SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")
# TODO: - Override `UsersStream` and `GroupsStream` with your own stream definition.
#       - Copy-paste as many times as needed to create multiple stream types.


class RepositoriesStream(CodecovStream):
    name = "repositories"
    path = "/repos/"
    primary_keys: t.ClassVar[list[str]] = ["name"]
    replication_key = None
    default_params = {"active": True}
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    # schema_filepath = SCHEMAS_DIR / "users.json"  # noqa: ERA001
    schema = th.PropertiesList(
        th.Property("name", th.StringType),
        th.Property("private", th.BooleanType),
        th.Property("updatestamp", th.DateTimeType),
        th.Property("author", th.ObjectType(
            th.Property("service", th.StringType),
            th.Property("name", th.StringType),
            th.Property("username", th.StringType),
        )),
        th.Property("language", th.StringType),
        th.Property("branch", th.StringType),
        th.Property("active", th.BooleanType),
        th.Property("activated", th.BooleanType)

    ).to_dict()

    def get_child_context(self, record: t.Dict, context: t.Optional[t.Dict]) -> dict:

        return {
            "repository": record["name"],
            "branch": record["branch"]
        }
    
class CommitStream(CodecovStream):
    name = "commits"
    path = "/repos/{repository}/commits/"
    parent_stream_type = RepositoriesStream
    primary_keys: t.ClassVar[list[str]] = ["repository", "branch", "commitid"]
    replication_key = None
    tolerated_http_errors = [404]

    params_from_context = ["branch"]

    schema = th.PropertiesList(
        # Parent keys
        th.Property("repository", th.StringType),
        th.Property("branch", th.StringType),

        # Stream fields
        th.Property("commitid", th.StringType),
        th.Property("message", th.StringType),
        th.Property("timestamp", th.DateTimeType),
        th.Property("ci_passed", th.BooleanType),
        th.Property("author", th.ObjectType(
            th.Property("service", th.StringType),
            th.Property("name", th.StringType),
            th.Property("username", th.StringType),
        )),
        th.Property("branch", th.StringType),
        th.Property("totals", th.ObjectType(
            th.Property("files", th.IntegerType),
            th.Property("lines", th.IntegerType),
            th.Property("hits", th.IntegerType),
            th.Property("misses", th.IntegerType),
            th.Property("partials", th.IntegerType),
            th.Property("coverage", th.NumberType),
            th.Property("branches", th.IntegerType),
            th.Property("methods", th.IntegerType),
            th.Property("messages", th.IntegerType),
            th.Property("sessions", th.IntegerType),
            th.Property("complexity", th.NumberType),
            th.Property("complexity_total", th.NumberType),
            th.Property("complexity_ratio", th.NumberType),
            th.Property("diff", th.IntegerType)
        )),
        th.Property("state", th.StringType),
        
    ).to_dict()
