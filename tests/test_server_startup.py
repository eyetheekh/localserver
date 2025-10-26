from pathlib import Path
from localserver.main import LocalServer


def test_server_init():
    server = LocalServer(host="127.0.0.1", port=8080)
    assert server.host == "127.0.0.1"
    assert server.port == 8080


# dummy socket to capture output
class DummySocket:
    """
    a fake socket objct used for testing LocalServer responses without a network connection.
    DummySocket acts as a stand-in for a real socket:

    how it works:
    the server normally sends data using the socket object's methods like:
    - 1 : send()
    - 2 : sendall()
    - 3 : sendfile()
    DummySocket has these same methods, which technically makes it seem like a sokcet object.
    This way

    server.send_response(dummy, ..., ..., ..., content)
            └─> dummy.send(data) → stores data in dummy.data
            send() -> referenced as 1.
    """

    def __init__(self):
        self.data = b""
        self.file_sent = None

    def send(self, data):
        self.data += data

    def sendall(self, data):
        self.data += data

    def sendfile(self, file_obj):
        self.file_sent = file_obj.read()


def test_send_response():
    server = LocalServer()
    dummy = DummySocket()
    server.send_response(dummy, {"Content-Type": "text/plain"}, 200, "OK", "hello")  # type: ignore
    assert b"hello" in dummy.data


def test_send_file_response():
    # example test file
    file_path = Path("test.txt")
    file_path.write_text("This is a test file.")

    server = LocalServer()
    dummy = DummySocket()
    server.send_file_response(dummy, file_path, 200, "OK")  # type: ignore

    assert b"This is a test file." in dummy.data


def test_handle_head_request_for_file():
    file_path = Path("test.txt")
    file_path.write_text("HEAD test content")

    server = LocalServer()
    dummy = DummySocket()

    server.handle_request(dummy, f"/{file_path.name}", "HEAD")  # pyright: ignore[reportArgumentType]

    # Check headers only, no body
    assert b"200 OK" in dummy.data
    assert b"Content-Type" in dummy.data
    assert b"Content-Length" in dummy.data
    assert b"HEAD test content" not in dummy.data


def test_handle_head_request_missing_file():
    server = LocalServer()
    dummy = DummySocket()

    server.handle_request(dummy, "/nonexistent.txt", "HEAD")  # pyright: ignore[reportArgumentType]

    assert b"404 Not Found" in dummy.data
    assert b"Content-Length: 0" in dummy.data


def test_handle_get_request_for_file():
    file_path = Path("sample.txt")
    file_path.write_text("GET test content")

    server = LocalServer()
    dummy = DummySocket()

    server.handle_request(dummy, f"/{file_path.name}", "GET")  # pyright: ignore[reportArgumentType]

    assert b"200 OK" in dummy.data
    assert b"GET test content" in dummy.data


def test_handle_get_request_missing_file():
    server = LocalServer()
    dummy = DummySocket()

    server.handle_request(dummy, "/missing.txt", "GET")  # pyright: ignore[reportArgumentType]

    assert b"404 Not Found" in dummy.data
