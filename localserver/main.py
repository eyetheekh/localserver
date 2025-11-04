import os
import socket
import mimetypes
from email.utils import formatdate  # for RFC compliance
from typing import Dict, Tuple


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
            response_headers = {"Content-Type": "text/plain;charset=utf-8"}
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

    def send_headers_only(
        self,
        client_socket: socket.socket,
        response_headers: Dict[str, str],
        status_code: int,
        msg: str,
    ) -> None:
        try:
            formatted_headers = "\r\n".join(
                f"{key}: {value}" for key, value in response_headers.items()
            )

            header_response = f"{self.http_version} {status_code} {msg}\r\n{formatted_headers}\r\n\r\n"
            client_socket.sendall(header_response.encode("utf-8"))
        except Exception as e:
            print(f"Error sending headers: {e}")
            self.send_error_response(client_socket, 500, "Internal Server Error")

        finally:
            del formatted_headers, header_response

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

        finally:
            del content_bytes, formatted_headers, response

    def send_error_response(
        self, client_socket: socket.socket, status_code: int, message: str
    ):
        """send error response"""
        try:
            content = f"""
            <html>
            <head>
                <title>{status_code} {message}</title>
                <style>
                    body {{
                        background: radial-gradient(circle at center, #0f0f1a, #050510);
                        color: #f0f0ff;
                        font-family: 'Orbitron', sans-serif;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        overflow: hidden;
                    }}
                    h1 {{
                        font-size: 4rem;
                        color: #ff00ff;
                        text-shadow: 0 0 10px #ff00ff, 0 0 30px #ff00ff, 0 0 60px #ff00ff;
                        animation: flicker 3s infinite;
                    }}
                    p {{
                        font-size: 1.2rem;
                        color: #00ffff;
                        text-shadow: 0 0 10px #00ffff;
                    }}
                    a {{
                        color: #00ffcc;
                        text-decoration: none;
                        border: 1px solid #00ffcc;
                        padding: 10px 20px;
                        margin-top: 20px;
                        border-radius: 10px;
                        transition: 0.3s;
                        box-shadow: 0 0 10px #00ffcc;
                    }}
                    a:hover {{
                        background: #00ffcc;
                        color: #0b0b17;
                        box-shadow: 0 0 20px #00ffcc, 0 0 40px #00ffcc;
                    }}
                    @keyframes flicker {{
                        0%, 19%, 21%, 23%, 25%, 54%, 56%, 100% {{ opacity: 1; }}
                        20%, 24%, 55% {{ opacity: 0.6; }}
                    }}
                    @keyframes moveStars {{
                        from {{ background-position: 0 0; }}
                        to {{ background-position: 10000px 10000px; }}
                    }}
                    body::after {{
                        content: "";
                        position: fixed;
                        top: 0; left: 0;
                        width: 200%;
                        height: 200%;
                        background: transparent url("data:image/svg+xml,\
                        <svg xmlns='http://www.w3.org/2000/svg' width='3' height='3'>\
                        <circle cx='1' cy='1' r='1' fill='white' opacity='0.15'/>\
                        </svg>") repeat;
                        background-size: 3px 3px;
                        animation: moveStars 300s linear infinite;
                        opacity: 0.1;
                        z-index: -2;
                    }}
                </style>
            </head>
            <body>
                <h1>{status_code} {message}</h1>
                <p>Oops! Something broke the neon grid...</p>
                <a href="/">Return to Home</a>
            </body>
            </html>
            """
            response_headers = {"Content-Type": "text/html;charset=utf-8"}
            self.send_response(
                client_socket, response_headers, status_code, message, content
            )
        except Exception as e:
            print(f"Error sending error response: {e}")

    def handle_head_request(self, abs_path: str, client_socket: socket.socket):
        try:
            """handles head request"""
            if os.path.isfile(abs_path):
                file_size = os.path.getsize(abs_path)

                # get mime type
                mime_type, _ = mimetypes.guess_type(abs_path)
                if mime_type is None:
                    mime_type = "application/octet-stream"

                headers = {
                    "Date": str(formatdate(timeval=None, localtime=False, usegmt=True)),
                    "Content-Length": str(file_size),
                    "Content-Type": mime_type,
                    "Connection": "close",
                }

                self.send_headers_only(
                    client_socket,
                    headers,
                    200,
                    "OK",
                )

            elif os.path.isdir(abs_path):
                # get mime type
                mime_type, _ = mimetypes.guess_type(abs_path)
                if mime_type is None:
                    mime_type = "application/octet-stream"

                headers = {
                    "Date": str(formatdate(timeval=None, localtime=False, usegmt=True)),
                    "Content-Type": mime_type,
                    "Content-Length": 0,
                    "Connection": "close",
                }

                self.send_headers_only(
                    client_socket,
                    headers,
                    200,
                    "OK",
                )

            else:
                headers = {
                    "Date": str(formatdate(timeval=None, localtime=False, usegmt=True)),
                    "Content-Length": 0,
                    "Content-Type": "text/html;charset=utf-8",
                    "Connection": "close",
                }
                self.send_headers_only(
                    client_socket,
                    headers,
                    404,
                    "Not Found",
                )

        except PermissionError:
            self.send_error_response(client_socket, 403, "Forbidden")

    def handle_get_request(
        self,
        request_path: str,
        abs_path: str,
        client_socket: socket.socket,
    ):
        """handle get request"""

        if request_path == "/favicon.ico":
            self.send_error_response(client_socket, 404, "Not Found")
            return

        if os.path.isdir(abs_path):
            self.handle_directory_listing(client_socket, abs_path, request_path)

        elif os.path.isfile(abs_path):
            self.send_file_response(client_socket, abs_path)

        else:
            self.send_error_response(client_socket, 404, "Not Found")

    def handle_request(
        self,
        client_socket: socket.socket,
        request_path: str,
        method: str,
    ) -> None:
        try:
            # decode url encoded paths
            request_path = request_path.replace("%20", " ")  # "%20" is space
            print(request_path)
            clean_path = request_path.lstrip("/")
            abs_path = os.path.abspath(os.path.join(os.getcwd(), clean_path))

            # check if path is within current directory to avoid lookbacks to prarent dirs
            if not abs_path.startswith(os.getcwd()):
                self.send_error_response(client_socket, 403, "Forbidden")
                return

            if method == "HEAD":
                self.handle_head_request(abs_path, client_socket)

            elif method == "GET":
                self.handle_get_request(request_path, abs_path, client_socket)

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

            response_headers = {"Content-Type": "text/html;charset=utf-8"}

            content = f"""
            <html>
            <head>
                <title>Index of {request_path}</title>
                <style>
                    body {{
                        background: linear-gradient(135deg, #0d0221, #1b0033, #050510);
                        font-family: 'Orbitron', sans-serif;
                        margin: 0;
                        padding: 40px;
                        color: #f5e1ff;
                        overflow-x: hidden;
                    }}
                    h1 {{
                        color: #ff00ff;
                        text-shadow: 0 0 10px #ff00ff, 0 0 30px #ff00ff;
                        font-size: 2.5rem;
                        animation: flicker 4s infinite;
                    }}
                    ul {{
                        list-style-type: none;
                        padding: 0;
                    }}
                    li {{
                        margin: 10px 0;
                    }}
                    a {{
                        color: #00ffff;
                        text-decoration: none;
                        font-size: 1.1rem;
                        text-shadow: 0 0 5px #00ffff, 0 0 10px #00ffff;
                        transition: 0.3s;
                    }}
                    a:hover {{
                        color: #ff00ff;
                        text-shadow: 0 0 15px #ff00ff, 0 0 40px #ff00ff;
                        transform: scale(1.1);
                    }}
                    .container {{
                        background: rgba(20, 20, 40, 0.6);
                        border: 2px solid transparent;
                        border-radius: 15px;
                        padding: 30px;
                        box-shadow: 0 0 20px #ff00ff55, 0 0 40px #00ffff22 inset;
                        border-image: linear-gradient(45deg, #ff00ff, #00ffff, #ff00ff) 1;
                        animation: borderShift 5s linear infinite;
                    }}
                    .footer {{
                        margin-top: 40px;
                        color: #888;
                        font-size: 0.9rem;
                        text-align: center;
                    }}
                    @keyframes flicker {{
                        0%, 18%, 22%, 25%, 53%, 57%, 100% {{ opacity: 1; }}
                        20%, 24%, 55% {{ opacity: 0.6; }}
                    }}
                    @keyframes borderShift {{
                        0% {{ border-image: linear-gradient(45deg, #ff00ff, #00ffff, #ff00ff) 1; }}
                        50% {{ border-image: linear-gradient(45deg, #00ffff, #ff00ff, #00ffff) 1; }}
                        100% {{ border-image: linear-gradient(45deg, #ff00ff, #00ffff, #ff00ff) 1; }}
                    }}
                    @keyframes gridMove {{
                        from {{ background-position: 0 0, 0 0; }}
                        to {{ background-position: 100px 100px, 100px 100px; }}
                    }}
                    body::before {{
                        content: "";
                        position: fixed;
                        top: 0; left: 0;
                        width: 100%; height: 100%;
                        background:
                            linear-gradient(90deg, rgba(255, 0, 255, 0.05) 1px, transparent 1px),
                            linear-gradient(0deg, rgba(0, 255, 255, 0.05) 1px, transparent 1px);
                        background-size: 40px 40px;
                        animation: gridMove 20s linear infinite;
                        z-index: -1;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 id="title">📂 Index of {request_path}</h1>
                    <ul>
            """

            # parent directory
            if request_path != "/":
                parent_path = "/".join(request_path.rstrip("/").split("/")[:-1]) or "/"
                content += f'<li>⬆️ <a href="{parent_path}">Parent Directory</a></li>'

            for item in files_and_dirs:
                item_url = request_path.rstrip("/") + "/" + item
                item_path = os.path.join(dir_path, item)
                if os.path.isdir(item_path):
                    content += f'<li>📁 <a href="{item_url}/">{item}/</a></li>'
                else:
                    try:
                        size = os.path.getsize(item_path)
                        size_str = self.format_file_size(size)
                        content += f'<li>📄 <a href="{item_url}">{item}</a> — <span style="color:#aaa;">{size_str}</span></li>'
                    except OSError:
                        content += f'<li>📄 <a href="{item_url}">{item}</a></li>'

            content += """
                    </ul>
                    <div class="footer">🌐 2049</div>
                </div>
                <script>
                let text = document.getElementById("title").innerText;
                let el = document.getElementById("title");
                el.innerText = "";
                let i = 0;
                function type() {
                    if (i < text.length) {{
                        el.innerHTML = text.slice(0, i + 1) + "_";
                        i++;
                        setTimeout(type, 80);
                    }} else {{
                        el.innerHTML = text;
                    }}
                }
                type();
                </script>
            </body>
            </html>
            """

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
                    client_socket.settimeout(5.0)

                    request = client_socket.recv(4096).decode("utf-8")
                    if not request.strip():
                        print("Empty request received")
                        self.send_error_response(
                            client_socket, 400, "Empty Request Received"
                        )
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

                    # handle GET & HEAD requests
                    if method not in {"HEAD", "GET"}:
                        self.send_error_response(
                            client_socket, 501, "Method Not Allowed"
                        )
                        continue

                    # handle the request
                    self.handle_request(client_socket, path, method)

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
