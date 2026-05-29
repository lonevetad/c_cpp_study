"""Tests for the fcpp_bridge logging module."""

import io
import logging
import tempfile
import os

import pytest

from fcpp_bridge.log import (
    configure_bridge_logging,
    set_bridge_logging,
    is_bridge_logging_enabled,
    get_logger,
    _ROOT_NAME,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_logging():
    """Restore bridge logger to silent-by-default state after each test."""
    root = logging.getLogger(_ROOT_NAME)
    root.handlers.clear()
    root.addHandler(logging.NullHandler())
    root.setLevel(logging.DEBUG)


@pytest.fixture(autouse=True)
def reset_after():
    yield
    _reset_logging()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_logger_returns_child_of_root():
    log = get_logger("my_module")
    assert log.name == f"{_ROOT_NAME}.my_module"


def test_get_logger_already_rooted():
    log = get_logger(f"{_ROOT_NAME}.something")
    assert log.name == f"{_ROOT_NAME}.something"


def test_get_logger_exact_root():
    log = get_logger(_ROOT_NAME)
    assert log.name == _ROOT_NAME


def test_bridge_logging_enabled_by_default():
    assert is_bridge_logging_enabled() is True


def test_set_bridge_logging_false_silences():
    set_bridge_logging(False)
    assert is_bridge_logging_enabled() is False


def test_set_bridge_logging_true_restores():
    set_bridge_logging(False)
    set_bridge_logging(True)
    assert is_bridge_logging_enabled() is True


def test_configure_to_stream():
    buf = io.StringIO()
    configure_bridge_logging(level=logging.DEBUG, stream=buf)

    log = get_logger("test_stream")
    log.debug("hello stream")

    output = buf.getvalue()
    assert "hello stream" in output


def test_configure_log_level_filters():
    buf = io.StringIO()
    configure_bridge_logging(level=logging.WARNING, stream=buf)

    log = get_logger("test_filter")
    log.debug("should be hidden")
    log.warning("should appear")

    output = buf.getvalue()
    assert "should be hidden" not in output
    assert "should appear" in output


def test_configure_to_file():
    with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as f:
        path = f.name
    try:
        configure_bridge_logging(level=logging.INFO, filename=path)
        log = get_logger("test_file")
        log.info("written to file")

        with open(path) as fh:
            content = fh.read()
        assert "written to file" in content
    finally:
        # Close file handler so the temp file can be removed on Windows
        logging.getLogger(_ROOT_NAME).handlers.clear()
        os.unlink(path)


def test_configure_timed_format():
    buf = io.StringIO()
    configure_bridge_logging(level=logging.DEBUG, stream=buf, timed=True)

    log = get_logger("test_timed")
    log.info("timed message")

    output = buf.getvalue()
    # Timestamped format includes a colon-separated time string
    assert "timed message" in output


def test_configure_custom_format():
    buf = io.StringIO()
    configure_bridge_logging(
        level=logging.DEBUG, stream=buf, fmt="CUSTOM %(message)s"
    )

    log = get_logger("test_fmt")
    log.info("fmt_test")

    output = buf.getvalue()
    assert output.startswith("CUSTOM")
    assert "fmt_test" in output


def test_null_handler_when_unconfigured():
    """Before configure_bridge_logging, NullHandler must be present (library best practice)."""
    _reset_logging()
    root = logging.getLogger(_ROOT_NAME)
    assert any(isinstance(h, logging.NullHandler) for h in root.handlers)


def test_set_bridge_logging_false_produces_no_output():
    buf = io.StringIO()
    configure_bridge_logging(level=logging.DEBUG, stream=buf)
    set_bridge_logging(False)

    log = get_logger("test_silent")
    log.debug("this should not appear")

    assert buf.getvalue() == ""


def test_configure_replaces_existing_handlers():
    buf1 = io.StringIO()
    buf2 = io.StringIO()
    configure_bridge_logging(level=logging.DEBUG, stream=buf1)
    configure_bridge_logging(level=logging.DEBUG, stream=buf2)

    log = get_logger("test_replace")
    log.debug("only in buf2")

    assert "only in buf2" not in buf1.getvalue()
    assert "only in buf2" in buf2.getvalue()
