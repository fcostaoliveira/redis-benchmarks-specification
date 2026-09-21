"""Commit timestamps must not depend on the trigger machine's timezone."""

import datetime
import time
from types import SimpleNamespace

import pytest

from redis_benchmarks_specification.__cli__.cli import (
    get_commits_by_branch,
    get_commits_by_tags,
)


@pytest.mark.skipif(
    not hasattr(time, "tzset"), reason="requires POSIX timezone support"
)
@pytest.mark.parametrize("host_tz", ["UTC0", "EST5EDT", "JST-9"])
@pytest.mark.parametrize(
    "committed_datetime,expected_ms",
    [
        ("2026-01-15T12:34:56+00:00", 1768480496000),
        ("2026-09-21T23:38:58+01:00", 1790030338000),
    ],
)
@pytest.mark.parametrize("source", ["branch", "tag"])
def test_commit_timestamp_is_timezone_independent(
    monkeypatch, host_tz, committed_datetime, expected_ms, source
):
    commit = SimpleNamespace(
        committed_datetime=datetime.datetime.fromisoformat(committed_datetime),
        hexsha="a" * 40,
        summary="test commit",
    )
    repo = SimpleNamespace(
        iter_commits=lambda: iter([commit]),
        active_branch=SimpleNamespace(name="unstable"),
        tags=[SimpleNamespace(name="8.10.1", commit=commit)],
    )
    # The date filter is expressed in UTC; retain the exact boundary behavior.
    utc_commit = commit.committed_datetime.astimezone(datetime.timezone.utc).replace(
        tzinfo=None
    )
    args = SimpleNamespace(
        from_date=utc_commit, to_date=utc_commit, last_n=1, tags_regexp=".*"
    )
    try:
        with monkeypatch.context() as context:
            context.setenv("TZ", host_tz)
            time.tzset()
            if source == "branch":
                commits, count = get_commits_by_branch(args, repo)
                assert count == 1
            else:
                commits = get_commits_by_tags(args, repo)
            assert len(commits) == 1
            assert commits[0]["git_timestamp_ms"] == expected_ms
    finally:
        time.tzset()
