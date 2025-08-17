from .main import LocalServer
import argparse


def main():
    parser = argparse.ArgumentParser(description="Run local static file server")
    parser.add_argument("-b", "--host", default="0.0.0.0")
    parser.add_argument("-p", "--port", type=int, default=8000)
    args = parser.parse_args()

    server = LocalServer(host=args.host, port=args.port)
    server.start_server()


if __name__ == "__main__":
    main()
