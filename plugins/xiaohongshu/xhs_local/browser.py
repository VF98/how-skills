"""Private, short-lived headless Chrome over loopback CDP. No credential APIs.

Uses installed Chrome, never a downloader. The request gate fails closed on
mutations; the only allowed POSTs are three explicit public-content read APIs.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

from .errors import XHSError

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
READ_POSTS = {
    "/api/sns/web/v1/search/notes",
    "/api/sns/web/v1/feed",
    "/api/sns/web/v2/user/otherinfo",
}
READ_HOSTS = {"edith.xiaohongshu.com", "www.xiaohongshu.com"}


def request_allowed(method, url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"https", "http", "data", "file", "blob", "chrome"}:
        return False
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return True
    return (method.upper() == "POST" and parsed.scheme == "https"
            and parsed.hostname in READ_HOSTS and parsed.path in READ_POSTS)


class WebSocket:
    """Small RFC6455 client for Chrome's local endpoint, including fragmentation."""

    def __init__(self, port, path, timeout=20):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buffer = bytearray()
        nonce = base64.b64encode(os.urandom(16)).decode()
        request = (f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                   f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {nonce}\r\n"
                   "Sec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(request.encode())
        while b"\r\n\r\n" not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                self.close()
                raise XHSError("cdp_handshake", "Chrome 调试握手连接已关闭")
            self.buffer.extend(chunk)
            if len(self.buffer) > 65536:
                raise XHSError("cdp_handshake", "Chrome 调试连接响应过大")
        headers, rest = bytes(self.buffer).split(b"\r\n\r\n", 1)
        self.buffer = bytearray(rest)
        accept = base64.b64encode(hashlib.sha1(
            (nonce + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest())
        if not headers.startswith(b"HTTP/1.1 101 ") or accept.lower() not in headers.lower():
            self.close()
            raise XHSError("cdp_handshake", "Chrome 调试连接握手失败")

    def _read(self, n):
        while len(self.buffer) < n:
            chunk = self.sock.recv(max(4096, n - len(self.buffer)))
            if not chunk:
                raise XHSError("cdp_closed", "Chrome 调试连接已关闭")
            self.buffer.extend(chunk)
        result = bytes(self.buffer[:n])
        del self.buffer[:n]
        return result

    def send(self, data, opcode=1):
        payload = data.encode() if isinstance(data, str) else data
        mask = os.urandom(4)
        size = len(payload)
        header = bytes([0x80 | opcode])
        if size < 126:
            header += bytes([0x80 | size])
        elif size < 65536:
            header += b"\xfe" + struct.pack("!H", size)
        else:
            header += b"\xff" + struct.pack("!Q", size)
        masked = bytes(v ^ mask[i % 4] for i, v in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def receive(self):
        fragments = bytearray()
        while True:
            first, second = self._read(2)
            size = second & 127
            if size == 126:
                size = struct.unpack("!H", self._read(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self._read(8))[0]
            if size > 16 * 1024 * 1024 or len(fragments) + size > 16 * 1024 * 1024:
                raise XHSError("cdp_frame_limit", "Chrome 响应超过大小限制")
            mask = self._read(4) if second & 128 else None
            data = self._read(size)
            if mask:
                data = bytes(v ^ mask[i % 4] for i, v in enumerate(data))
            opcode = first & 15
            if opcode == 8:
                raise XHSError("cdp_closed", "Chrome 调试连接已关闭")
            if opcode == 9:
                self.send(data, 10)
                continue
            if opcode == 10:
                continue
            if opcode not in {0, 1}:
                raise XHSError("cdp_frame_type", "Chrome 返回了非文本数据")
            fragments.extend(data)
            if first & 128:
                return json.loads(fragments)

    def close(self):
        self.sock.close()


class Browser:
    def __init__(self, profile=None, executable=CHROME, request_policy=request_allowed):
        self.executable = Path(executable)
        self.profile = Path(profile) if profile else None
        self.process = None
        self.ws = None
        self.session = None
        self.sequence = 0
        self.blocked_requests = 0
        self.request_policy = request_policy
        self.temporary = None

    def __enter__(self):
        try:
            return self._start()
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def _start(self):
        if not self.executable.is_file():
            raise XHSError("chrome_missing", "未找到这台 Mac 已安装的 Google Chrome")
        if self.profile is None:
            self.temporary = tempfile.TemporaryDirectory(prefix="xhs-offline-")
            self.profile = Path(self.temporary.name)
        if self.profile.is_symlink():
            raise XHSError("unsafe_profile", "专用浏览器目录不能是符号链接")
        self.profile.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.profile, 0o700)
        self.lock = (self.profile / ".adapter.lock").open("a+")
        os.chmod(self.profile / ".adapter.lock", 0o600)
        import fcntl
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise XHSError("profile_busy", "专用浏览器正在执行另一项操作，请稍后重试")
        singleton = self.profile / "SingletonLock"
        if singleton.is_symlink():
            try:
                owner_pid = int(os.readlink(singleton).rsplit("-", 1)[1])
                os.kill(owner_pid, 0)
            except ProcessLookupError:
                singleton.unlink()  # A dead process's lock, only inside our dedicated profile.
            except (ValueError, PermissionError):
                raise XHSError("profile_busy", "无法确认专用浏览器锁的状态") from None
            else:
                raise XHSError("profile_busy", "请先关闭用于登录的专用 Chrome 窗口，再运行后台读取")
        elif singleton.exists():
            raise XHSError("profile_busy", "专用 Chrome 目录正在使用")
        active = self.profile / "DevToolsActivePort"
        active.unlink(missing_ok=True)
        args = [str(self.executable), "--headless=new", "--remote-debugging-address=127.0.0.1",
                "--remote-debugging-port=0", f"--user-data-dir={self.profile}",
                "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
                "--disable-component-update", "--disable-sync", "--window-size=1280,900", "about:blank"]
        self.process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 20
        while not active.exists():
            if self.process.poll() is not None or time.monotonic() > deadline:
                raise XHSError("chrome_start_failed", "无头 Chrome 未能启动；没有尝试打开 GUI")
            time.sleep(0.1)
        lines = active.read_text().splitlines()
        self.ws = WebSocket(int(lines[0]), lines[1])
        target = self.call("Target.createTarget", {"url": "about:blank"})["targetId"]
        self.session = self.call("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})
        return self

    def _send(self, method, params=None, session=True):
        self.sequence += 1
        item = {"id": self.sequence, "method": method, "params": params or {}}
        if session and self.session:
            item["sessionId"] = self.session
        self.ws.send(json.dumps(item))
        return self.sequence

    def call(self, method, params=None):
        wanted = self._send(method, params)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            response = self.ws.receive()
            if response.get("method") == "Fetch.requestPaused":
                p = response["params"]
                allowed = self.request_policy(p["request"]["method"], p["request"]["url"])
                if allowed:
                    self._send("Fetch.continueRequest", {"requestId": p["requestId"]})
                else:
                    self.blocked_requests += 1
                    self._send("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "BlockedByClient"})
            if response.get("id") == wanted:
                if "error" in response:
                    raise XHSError("cdp_error", "Chrome 页面命令失败；未重试账号写入")
                return response.get("result", {})
        raise XHSError("cdp_timeout", "Chrome 页面响应超时")

    def navigate(self, url):
        previous = self.evaluate("location.href")
        result = self.call("Page.navigate", {"url": url})
        if result.get("errorText"):
            raise XHSError("navigation_failed", "网页导航失败")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                current, state = self.evaluate("[location.href,document.readyState]")
                if state == "complete" and (current != previous or current == url):
                    return
            except XHSError:
                pass
            time.sleep(0.2)
        raise XHSError("page_timeout", "页面加载超时")

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True,
                                                "awaitPromise": True, "timeout": 10000})
        if result.get("exceptionDetails"):
            raise XHSError("page_changed", "页面读取脚本失败，需重新核查网页结构")
        return result.get("result", {}).get("value")

    def __exit__(self, *unused):
        if self.ws:
            try:
                self._send("Browser.close", session=False)
            except (OSError, XHSError):
                pass
            self.ws.close()
        if self.process and self.process.poll() is None:
            try:
                self.process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
        if hasattr(self, "lock"):
            self.lock.close()
        if self.temporary:
            self.temporary.cleanup()
