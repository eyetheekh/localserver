import os
import socket
from typing import Any, Dict, Tuple, IO


class LocalServer:
    def __init__(
        self, host: str = "0.0.0.0", port: int = 8000, http_version: str = "HTTP/1.1"
    ):
        self.http_version = http_version
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))

    def get_default_response_context(
        self,
        status_code: int = 200,
        msg: str = "OK",
        content: str = "",
        response_headers: Dict[str, str] = {"Content-Type": "text/plain"},
    ) -> Tuple[str, int, str, str, Dict]:
        return self.http_version, status_code, msg, content, response_headers

    def send_file_response(
        self,
        socket: socket.socket,
        response_headers: Dict[str, str],
        status_code: int,
        msg: str,
        content: IO[bytes],
    ) -> None:
        response_headers = {"Content-Type": "application/octet-stream"}
        headers_formatted = "\r\n".join(
            f"{key}: {value}" for key, value in response_headers.items()
        )
        res = f"{self.http_version} {status_code} {msg}\r\n{headers_formatted}\r\n\r\n"
        socket.sendall(res.encode())
        socket.sendfile(content)

    def send_response(
        self,
        socket: socket.socket,
        response_headers: Dict[str, str],
        status_code: int,
        msg: str,
        content: str,
    ) -> None:
        formatted_headers = "\r\n".join(
            f"{key}: {value}" for key, value in response_headers.items()
        )

        response = f"{self.http_version} {status_code} {msg}\r\n{formatted_headers}\r\n\r\n{content}"
        socket.send(response.encode())

    def handle_request(
        self,
        socket: socket.socket,
        request: str,
        request_path: str,
    ) -> Any:
        # setting the defaults
        version, status_code, msg, content, response_headers = (
            self.get_default_response_context()
        )

        # TODO add support for other methods (Head; Post to copy something over network)
        if request_path == "/":
            files_or_directories_in_base_dir = []

            for file in os.listdir(os.getcwd()):
                files_or_directories_in_base_dir.append(file)

            if files_or_directories_in_base_dir:
                response_headers = {"Content-Type": "text/html"}
                content = "<html><head></head><body><ul>"

                for path in files_or_directories_in_base_dir:
                    content += f"<li><a href='http://{self.host}:{self.port}/{path}'>{path}</a></li>"
                content += "</ul></body></html>"

                return self.send_response(socket, response_headers, 200, "OK", content)
            else:
                return self.send_response(
                    socket, response_headers, 200, "OK", "empty directory"
                )

        elif request_path:
            try:
                files_or_directories_in_base_dir = []
                abs_dir = os.path.abspath(
                    os.path.join(os.getcwd(), request_path.strip("/"))
                )

                for dir_or_file_name in os.listdir(abs_dir):
                    files_or_directories_in_base_dir.append(dir_or_file_name)

                if files_or_directories_in_base_dir:
                    response_headers = {"Content-Type": "text/html"}
                    content = "<html><head></head><body><ul>"

                    for dir_or_file_name in files_or_directories_in_base_dir:
                        rel_path = os.path.join(
                            request_path.strip("/"), dir_or_file_name
                        )
                        content += (
                            f"<li><a href='/{rel_path}'>{dir_or_file_name}</a></li>"
                        )
                    content += "</ul></body></html>"

                    return self.send_response(
                        socket, response_headers, 200, "OK", content
                    )
            except FileNotFoundError:
                print(f"Not found {request_path.strip('/')}")
                self.send_response(
                    socket,
                    response_headers,
                    404,
                    "Bro, the thing you asked for is 404 Not Found",
                    "Cant give u that.",
                )
                socket.close()
                return
            except NotADirectoryError:
                print(f"Requested File: {request_path.strip('/')}")
                # TODO handle other mime types here. (pdf, txt, md, zips, etc)
                response_headers = {"Content-Type": "application/octet-stream"}
                content = open(os.getcwd() + request_path, "rb")
                return self.send_file_response(
                    socket, response_headers, 200, "OK", content
                )
            except Exception as e:
                print(f"Bad Requet {e}")
        return self.send_response(
            socket,
            response_headers,
            404,
            "Bro, the thing you asked for is 404 Not Found",
            content,
        )

    def start_listening(self) -> None:
        self.server_socket.listen(5)

    def accept_connections(self):
        try:
            while True:
                socket_object, socket_object_address = self.server_socket.accept()
                request = socket_object.recv(1024).decode()

                try:
                    request_line = request.split("\n")[0].strip()
                    if not request_line:  # empty request
                        raise ValueError("Empty request line")

                    request_parts = request_line.split()
                    if len(request_parts) != 3:
                        raise ValueError("Bad Request")
                    method, path, http_version = request_parts
                    print(f"Request Received: {method} {path} {http_version}")
                except ValueError as e:
                    print(f"Bad Request received {e}")
                    socket_object.close()
                    continue

                self.handle_request(socket_object, request, path)
                continue

        except KeyboardInterrupt:
            self.server_socket.close()
            print("server closed.")
        except Exception as e:
            print("something broke", e)
        finally:
            socket_object.close()

    def start_server(self):
        print(f"Listening on http://{self.host}:{self.port}")
        self.start_listening()
        self.accept_connections()


if __name__ == "__main__":
    local_server = LocalServer()
    local_server.start_server()
