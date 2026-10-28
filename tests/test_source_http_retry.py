"""Injected transports only; no provider requests."""

import errno
import socket
import ssl
import unittest
from http.client import IncompleteRead
from io import BytesIO
from typing import ClassVar
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from scripts import source_http_retry as retry


class Response(BytesIO):
    status = 200
    headers: ClassVar[dict] = {"Date": "Thu, 29 Oct 2026 00:00:00 GMT"}

    def geturl(self):
        return "https://example.invalid/record"


class RetryTests(unittest.TestCase):
    def test_partial_read_and_storage_error_are_retained_without_network_retry(self):
        response = Response(b"")
        response.read = Mock(side_effect=IncompleteRead(b"partial bytes", 20))
        saved = []
        transport = Mock(return_value=response)
        with self.assertRaises(IncompleteRead):
            retry.read_response(
                Request("https://example.invalid/record"),
                [],
                opener=transport,
                max_attempts=4,
                retain=lambda *args: saved.append(args),
            )
        transport.assert_called_once()
        self.assertEqual(saved[0][0], b"partial bytes")
        transport = Mock(return_value=Response(b"{}"))
        with self.assertRaises(OSError):
            retry.read_response(
                Request("https://example.invalid/record"),
                [],
                opener=transport,
                max_attempts=4,
                retain=Mock(side_effect=OSError("fictional storage")),
            )
        transport.assert_called_once()

    def test_default_transport_installs_redirect_refusal_without_opening_network(self):
        transport = Mock()
        with patch.object(retry, "build_opener", return_value=transport) as builder:
            request = Request("https://example.invalid/record")
            retry.guarded_urlopen(request)
        handler = builder.call_args.args[0]
        self.assertIsNone(
            handler.redirect_request(
                request, None, 302, "redirect", {}, "https://other.invalid/record"
            )
        )
        transport.open.assert_called_once_with(request, timeout=45)

    def test_oversized_response_keeps_only_bounded_diagnostic_prefix(self):
        saved = []
        transport = Mock(return_value=Response(b"0123456789"))
        with (
            patch.object(retry, "MAX_RAW_BYTES", 5),
            self.assertRaisesRegex(ValueError, "bounded"),
        ):
            retry.read_response(
                Request("https://example.invalid/record"),
                [],
                opener=transport,
                retain=lambda *args: saved.append(args),
            )
        self.assertEqual(saved[0][0], b"012345")
        transport.assert_called_once()

    def test_classifier_excludes_tls_unknown_permanent_dns_and_http(self):
        for error in (
            ssl.SSLError("tls"),
            URLError(ssl.SSLError("tls")),
            URLError("unknown"),
            socket.gaierror(socket.EAI_NONAME, "permanent"),
            HTTPError("https://example.invalid", 403, "denied", {}, None),
        ):
            self.assertFalse(retry.is_retryable_request_error(error, {429, 503}))
            if isinstance(error, HTTPError):
                error.close()
        for error in (
            TimeoutError(),
            ConnectionResetError(),
            URLError(OSError(errno.ENETUNREACH, "offline")),
            socket.gaierror(socket.EAI_AGAIN, "temporary"),
        ):
            self.assertTrue(retry.is_retryable_request_error(error, {429, 503}))

    def test_default_does_not_retry_and_retains_error_body_before_classification(self):
        error = HTTPError(
            "https://example.invalid/record",
            429,
            "limited",
            {},
            BytesIO(b"complete error"),
        )
        transport = Mock(side_effect=error)
        saved = []
        attempts = []
        sleep = Mock()
        with self.assertRaises(HTTPError):
            retry.read_response(
                Request("https://example.invalid/record"),
                attempts,
                opener=transport,
                retain=lambda *args: saved.append(args),
                sleep=sleep,
            )
        transport.assert_called_once()
        sleep.assert_not_called()
        self.assertEqual(saved[0][0], b"complete error")
        self.assertEqual(attempts[0]["attempt"], 1)

    def test_explicit_bounded_retry_retains_first_failure_and_success(self):
        error = HTTPError(
            "https://example.invalid/record",
            503,
            "temporary",
            {},
            BytesIO(b"first failure"),
        )
        transport = Mock(side_effect=[error, Response(b'{"unknown":true}')])
        saved = []
        attempts = []
        sleep = Mock()
        raw, status, _, count = retry.read_response(
            Request("https://example.invalid/record"),
            attempts,
            opener=transport,
            retain=lambda *args: saved.append(args),
            max_attempts=2,
            sleep=sleep,
        )
        self.assertEqual((raw, status, count), (b'{"unknown":true}', 200, 2))
        self.assertEqual([s[0] for s in saved], [b"first failure", b'{"unknown":true}'])
        self.assertTrue(attempts[0]["retryable"])
        sleep.assert_called_once_with(10)

    def test_redirect_and_bad_attempt_budget_fail_without_retry(self):
        response = Response(b"foreign response")
        response.geturl = lambda: "https://other.invalid/record"
        saved = []
        transport = Mock(return_value=response)
        with self.assertRaisesRegex(ValueError, "origin"):
            retry.read_response(
                Request("https://example.invalid/record"),
                [],
                opener=transport,
                retain=lambda *args: saved.append(args),
            )
        self.assertEqual(saved[0][0], b"foreign response")
        for budget in (True, 0, 5, 1.0):
            transport = Mock()
            with self.assertRaises(ValueError):
                retry.read_response(
                    Request("https://example.invalid/record"),
                    [],
                    opener=transport,
                    retain=lambda *args: None,
                    max_attempts=budget,
                )
            transport.assert_not_called()
