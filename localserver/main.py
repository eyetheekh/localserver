import os
import socket
import mimetypes
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
        content: str = "OK",
        response_headers: Dict[str, str] = None,  # pyright: ignore[reportArgumentType]
    ) -> Tuple[str, int, str, str, Dict]:
        if response_headers is None:
            response_headers = {"Content-Type": "text/plain"}
        return self.http_version, status_code, msg, content, response_headers

    def send_file_response(
        self,
        client_socket: socket.socket,
        file_path: str,
        status_code: int = 200,
        msg: str = "OK",
    ) -> None:
        try:
            with open(file_path, "rb") as f:
                # get file size for Content-Length
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                f.seek(0)

                # get mime type
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = "application/octet-stream"

                response_headers = {
                    "Content-Type": mime_type,
                    "Content-Length": str(file_size),
                    "Connection": "close",
                }

                headers_formatted = "\r\n".join(
                    f"{key}: {value}" for key, value in response_headers.items()
                )

                # send headers
                response_header = f"{self.http_version} {status_code} {msg}\r\n{headers_formatted}\r\n\r\n"
                client_socket.sendall(response_header.encode())

                # send file content
                while True:
                    chunk = f.read(8192)  # read file content in chunks
                    if not chunk:
                        break
                    client_socket.sendall(chunk)

        except Exception as e:
            print(f"Error sending file {file_path}: {e}")
            self.send_error_response(client_socket, 500, "Internal Server Error")

    def send_response(
        self,
        client_socket: socket.socket,
        response_headers: Dict[str, str],
        status_code: int,
        msg: str,
        content: str,
    ) -> None:
        try:
            # add Content-Length and connection headers
            content_bytes = content.encode("utf-8")
            response_headers["Content-Length"] = str(len(content_bytes))
            response_headers["Connection"] = "close"

            formatted_headers = "\r\n".join(
                f"{key}: {value}" for key, value in response_headers.items()
            )

            response = f"{self.http_version} {status_code} {msg}\r\n{formatted_headers}\r\n\r\n"
            client_socket.sendall(response.encode("utf-8"))
            client_socket.sendall(content_bytes)
        except Exception as e:
            print(f"Error sending response: {e}")

    def send_error_response(
        self, client_socket: socket.socket, status_code: int, message: str
    ):
        """send error response"""
        try:
            content = f"<html><body><h1>{status_code} {message}</h1></body></html>"
            response_headers = {"Content-Type": "text/html", "Connection": "close"}
            self.send_response(
                client_socket, response_headers, status_code, message, content
            )
        except Exception as e:
            print(f"Error sending error response: {e}")

    def handle_request(
        self,
        client_socket: socket.socket,
        request: str,
        request_path: str,
    ) -> None:
        try:
            # decode url encoded paths
            request_path = request_path.replace("%20", " ")  # "%20" is space

            if request_path == "/":
                self.handle_directory_listing(client_socket, os.getcwd())
            else:
                clean_path = request_path.lstrip("/")
                abs_path = os.path.abspath(os.path.join(os.getcwd(), clean_path))

                # check if path is within current directory to avoid lookbacks to prarent dirs
                if not abs_path.startswith(os.getcwd()):
                    self.send_error_response(client_socket, 403, "Forbidden")
                    return

                if os.path.isdir(abs_path):
                    self.handle_directory_listing(client_socket, abs_path, request_path)
                elif os.path.isfile(abs_path):
                    self.send_file_response(client_socket, abs_path)
                else:
                    self.send_error_response(client_socket, 404, "Not Found")

        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_error_response(client_socket, 500, "Internal Server Error")

    def handle_directory_listing(
        self, client_socket: socket.socket, dir_path: str, request_path: str = "/"
    ):
        """directory listing"""
        try:
            files_and_dirs = os.listdir(dir_path)
            files_and_dirs.sort()

            response_headers = {"Content-Type": "text/html"}

            # html content template
            content = f"""
            <html>
            <head>
                <title>Directory listing for {request_path}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1 {{ color: #333; }}
                    a {{ text-decoration: none; color: #0066cc; }}
                    a:hover {{ text-decoration: underline; }}
                    li {{ margin: 5px 0; }}
                </style>
            </head>
            <body>
                <h1>Directory listing for {request_path}</h1>
                <ul>
            """

            # add  link to parent directory if request path is not at root
            if request_path != "/":
                parent_path = "/".join(request_path.rstrip("/").split("/")[:-1]) or "/"
                print("parent_path", parent_path)
                content += f'<li><a href="{parent_path}">..(Parent Directory)</a></li>'

            for item in files_and_dirs:
                if request_path.endswith("/"):
                    item_url = request_path + item
                else:
                    item_url = request_path + "/" + item

                item_path = os.path.join(dir_path, item)
                if os.path.isdir(item_path):
                    content += f'<li><a href="{item_url}/">{item}/</a></li>'
                else:
                    # file size
                    try:
                        size = os.path.getsize(item_path)
                        size_str = self.format_file_size(size)
                        content += (
                            f'<li><a href="{item_url}">{item}</a> ({size_str})</li>'
                        )
                    except OSError:
                        content += f'<li><a href="{item_url}">{item}</a></li>'

            content += "</ul></body></html>"

            self.send_response(client_socket, response_headers, 200, "OK", content)

        except PermissionError:
            self.send_error_response(client_socket, 403, "Forbidden")
        except Exception as e:
            print(f"Error listing directory {dir_path}: {e}")
            self.send_error_response(client_socket, 500, "Internal Server Error")

    def format_file_size(self, size_bytes: float) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    def start_listening(self) -> None:
        self.server_socket.listen(5)

    def accept_connections(self):
        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"Connection from {client_address}")

                try:
                    # Set socket timeout to prevent hanging
                    client_socket.settimeout(30.0)

                    request = client_socket.recv(4096).decode("utf-8")
                    if not request.strip():
                        print("Empty request received")
                        continue

                    # Parse request line
                    request_lines = request.split("\r\n")
                    if not request_lines:
                        print("No request line found")
                        continue

                    request_line = request_lines[0].strip()
                    if not request_line:
                        print("Empty request line")
                        continue

                    request_parts = request_line.split()
                    if len(request_parts) != 3:
                        print(f"Invalid request format: {request_line}")
                        self.send_error_response(client_socket, 400, "Bad Request")
                        continue

                    method, path, http_version = request_parts
                    print(f"Request: {method} {path} {http_version}")

                    # Only handle GET requests for now
                    if method != "GET":
                        self.send_error_response(
                            client_socket, 405, "Method Not Allowed"
                        )
                        continue

                    self.handle_request(client_socket, request, path)

                except socket.timeout:
                    print("Client connection timed out")
                except Exception as e:
                    print(f"Error handling client connection: {e}")
                    try:
                        self.send_error_response(
                            client_socket, 500, "Internal Server Error"
                        )
                    except:  # noqa: E722
                        pass
                finally:
                    # close the client socket
                    try:
                        client_socket.close()
                    except:  # noqa: E722
                        pass

        except KeyboardInterrupt:
            print("\nShutting down server...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            try:
                self.server_socket.close()
            except:  # noqa: E722
                pass
            print("Server closed.")

    def start_server(self):
        try:
            self.start_listening()
            print(f"Server listening on http://{self.host}:{self.port}")
            self.accept_connections()
        except OSError as e:
            if e.errno == 98:  # address already in use
                print(f"Error: Port {self.port} is already in use.")
            else:
                print(f"Error starting server: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    local_server = LocalServer()
    local_server.start_server()
