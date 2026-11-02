"""Byte-only loopback HTTP primitive; no parser, retry, persistence or authority.

Not a runnable LLM lane. The caller must durably claim a budgeted dispatch before
POST and capture the returned bytes before parsing. LP-01 governs that future
integration. Only a locally controlled, cloud-disabled server may be used.
"""
from dataclasses import dataclass
import http.client
import math
import re
import socket
import threading
import time


VERSION = 's02-local-transport/2'
_ENDPOINT = re.compile(r'http://127\.0\.0\.1:([1-9][0-9]{0,4})\Z')
_HEADERS = frozenset({'content-type', 'content-length', 'content-encoding', 'retry-after'})


class _FramedResponse(http.client.HTTPResponse):
    """Keep stdlib streaming/deadlines, but require unambiguous HTTP framing."""
    def begin(self):
        super().begin()
        lengths = [v.strip() for line in self.headers.get_all('content-length', [])
                   for v in line.split(',')]
        transfers = self.headers.get_all('transfer-encoding', [])
        if lengths and (any(not re.fullmatch(r'[0-9]+', v) for v in lengths)
                        or len({int(v) for v in lengths}) != 1):
            raise http.client.HTTPException('conflicting or invalid content length')
        if transfers and (lengths or ','.join(transfers).lower().strip() != 'chunked'):
            raise http.client.HTTPException('ambiguous transfer framing')
        if lengths and not transfers:
            self.length = int(lengths[0])

    def _read_next_chunk_size(self):
        line = self.fp.readline(65537)
        if len(line) > 65536 or not re.fullmatch(rb'[0-9a-fA-F]+(?:;[^\r\n]*)?\r\n', line):
            raise http.client.HTTPException('invalid chunk size framing')
        return int(line.split(b';', 1)[0].strip(), 16)

    def _get_chunk_left(self):
        left = self.chunk_left
        if left is None or left == 0:
            if left is not None and self._safe_read(2) != b'\r\n':
                raise http.client.HTTPException('invalid chunk terminator')
            left = self._read_next_chunk_size()
            if left == 0:
                self._read_and_discard_trailer()
                self._close_conn()
                left = None
            self.chunk_left = left
        return left

    def _read_and_discard_trailer(self):
        for _ in range(100):
            line = self.fp.readline(65537)
            if line == b'\r\n':
                return
            if len(line) > 65536 or not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9a-zA-Z-]+:[^\r\n]*\r\n", line):
                raise http.client.HTTPException('incomplete or invalid trailer')
        raise http.client.HTTPException('trailer limit')


@dataclass(frozen=True)
class Exchange:
    status: int | None
    headers: tuple[tuple[str, str], ...]
    body: bytes
    complete_body: bool
    send_started: bool
    error: str | None
    elapsed_ms: int


def exchange(endpoint, *, method, path, body, timeout_seconds, response_limit_bytes):
    """One exchange, unchanged entity bytes, no proxy/DNS/redirect/decompression.

    Timeout is a wall deadline including response headers and trickled body.
    An incomplete result contains only the received prefix; it is never a valid
    candidate. send_started is conservative, not proof the server executed it.
    Invalid arguments raise before connecting. HTTP errors are captured as-is.
    """
    match = _ENDPOINT.fullmatch(endpoint) if type(endpoint) is str else None
    if match is None or int(match[1]) > 65535:
        raise ValueError('endpoint must be http://127.0.0.1:PORT, without a path')
    if (method, path) not in {('GET', '/api/tags'), ('GET', '/api/version'), ('POST', '/api/chat')}:
        raise ValueError('unsupported local operation')
    if type(body) is not bytes or (method == 'GET' and body):
        raise ValueError('body must be exact bytes; GET body must be empty')
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0):
        raise ValueError('timeout_seconds must be finite and positive')
    if type(response_limit_bytes) is not int or response_limit_bytes <= 0:
        raise ValueError('response_limit_bytes must be a positive integer')
    started = time.monotonic()
    deadline = started + timeout_seconds
    conn = http.client.HTTPConnection('127.0.0.1', int(match[1]), timeout=timeout_seconds)
    conn.response_class = _FramedResponse
    expired = threading.Event()
    timer = None
    response = None
    status = None
    headers = ()
    data = bytearray()
    send_started = False
    complete = False
    error = None
    try:
        conn.connect()
        # Hold the actual socket: HTTPConnection may detach it for Connection:
        # close responses while HTTPResponse still reads the socket file.
        connected = conn.sock

        def expire():
            expired.set()
            try:
                connected.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        timer = threading.Timer(remaining, expire)
        timer.daemon = True
        timer.start()
        send_started = True
        conn.request(method, path, body=body, headers={
            'Content-Type': 'application/json', 'Accept': 'application/json',
            'Accept-Encoding': 'identity', 'Connection': 'close',
        })
        response = conn.getresponse()
        status = response.status
        headers = tuple((k.lower(), v) for k, v in response.getheaders() if k.lower() in _HEADERS)
        while True:
            if expired.is_set() or time.monotonic() >= deadline:
                raise TimeoutError()
            chunk = response.read1(min(65536, response_limit_bytes + 1 - len(data)))
            if not chunk:
                if response.length not in (None, 0):
                    error = 'incomplete_body'
                else:
                    complete = True
                break
            data.extend(chunk)
            if len(data) > response_limit_bytes:
                del data[response_limit_bytes:]
                error = 'response_limit'
                break
        if expired.is_set() or time.monotonic() >= deadline:
            complete = False
            error = 'timeout'
    except (OSError, http.client.HTTPException) as exc:
        complete = False
        error = ('timeout' if expired.is_set() or isinstance(exc, TimeoutError)
                 else 'transport_error' if send_started else 'connect_failed')
    finally:
        if timer is not None:
            timer.cancel()
            timer.join()
        if response is not None:
            response.close()
        conn.close()
    return Exchange(status, headers, bytes(data), complete, send_started, error,
                    int((time.monotonic() - started) * 1000))
