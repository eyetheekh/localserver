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


def test_send_file_response(tmp_path):
    # example test file
    file_path = tmp_path / "test.txt"
    file_path.write_text("This is a test file.")

    server = LocalServer()
    dummy = DummySocket()
    with open(file_path, "rb") as f:
        server.send_file_response(dummy, {}, 200, "OK", f)  # type: ignore

    assert dummy.file_sent == b"This is a test file."


