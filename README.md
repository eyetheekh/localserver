# localserver

A simple Python HTTP filesystem server.  
Think of it as a lightweight alternative to `python -m http.server`, packaged with a CLI.

---

## Installation

Available on **TestPyPI** for now:

```bash
pip install -i https://test.pypi.org/simple/ localserver
```

## Usage
Run the server:
```bash
localserver
```
by default, it will listen on 0.0.0.0:8000

You can also specify host and port:
```bash
localserver -b <host> -p <port>
```

# Known Issues
- HEAD requests are not yet implemented.
- File responses can sometimes be slow.
