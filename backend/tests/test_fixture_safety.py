"""Destructive integration setup must never accept the ordinary application database."""

import pytest

from tests.conftest import _safe_test_urls


@pytest.mark.parametrize(
    ("runtime", "owner"),
    [
        (
            "postgresql+asyncpg://runtime@localhost/tracker",
            "postgresql+asyncpg://owner@localhost/tracker",
        ),
        ("sqlite:///tracker_test", "sqlite:///tracker_test"),
        (
            "postgresql+asyncpg://runtime@localhost/a_test",
            "postgresql+asyncpg://owner@localhost/b_test",
        ),
        (
            "postgresql+asyncpg://runtime@localhost/a_test",
            "postgresql+asyncpg://owner@elsewhere/a_test",
        ),
        (
            "postgresql+asyncpg://runtime@localhost:5433/a_test",
            "postgresql+asyncpg://owner@localhost:5432/a_test",
        ),
    ],
)
def test_database_reset_rejects_unsafe_targets(runtime: str, owner: str) -> None:
    with pytest.raises(pytest.fail.Exception):
        _safe_test_urls(runtime, owner)


def test_database_reset_accepts_two_credentials_for_same_explicit_test_database() -> None:
    urls = _safe_test_urls(
        "postgresql+asyncpg://runtime@localhost/tracker_test",
        "postgresql+asyncpg://owner@localhost:5432/tracker_test",
    )
    assert urls.runtime.endswith("tracker_test")
