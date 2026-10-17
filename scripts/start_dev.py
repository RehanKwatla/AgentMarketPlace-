"""Start the DI-06 API and Vite UI as one supervised local development command."""
from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
STARTUP_TIMEOUT_SECONDS = 90


class StartupError(RuntimeError):
    """A child service could not start or become ready."""


def _validate_host(host: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", host):
        raise argparse.ArgumentTypeError("Host must be a hostname or IP address")
    return host


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")
    return port


def _port_is_available(host: str, port: int) -> bool:
    """Check a local bind target without changing or terminating its owner."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            return sock.connect_ex((host, port)) != 0
    except OSError:
        # A failed probe is not permission to take over the port. Let bind report it.
        return True


def _stream_child_output(name: str, stream, stop_event: threading.Event) -> None:
    try:
        for line in iter(stream.readline, ""):
            if not line:
                break
            print(f"[{name}] {line.rstrip()}", flush=True)
    finally:
        stop_event.set()
        try:
            stream.close()
        except OSError:
            pass


def _popen_options() -> dict:
    options = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
               "stdin": subprocess.DEVNULL, "text": True, "bufsize": 1}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    return options


def _stop_child(process: subprocess.Popen, name: str, timeout: float = 8.0) -> None:
    if process.poll() is not None:
        return
    print(f"[STOP] Stopping {name}...", flush=True)
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ValueError):
        try:
            process.terminate()
        except OSError:
            pass
    try:
        process.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        pass

    if os.name == "nt":
        # The process tree is rooted at this Popen child, which this launcher created.
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        print(f"[WARN] {name} did not exit after forced shutdown.", flush=True)


def _is_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _backend_command(host: str, port: int, reload: bool) -> list[str]:
    command = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", host, "--port", str(port)]
    if reload:
        command.append("--reload")
    return command


def _frontend_command(host: str, port: int) -> list[str]:
    args = ["run", "dev", "--", "--host", host, "--port", str(port), "--strictPort"]
    if os.name == "nt":
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            raise StartupError("npm was not found. Install Node.js with npm and reopen the terminal.")
        node = shutil.which("node")
        npm_cli = Path(npm).resolve().parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
        if not node or not npm_cli.is_file():
            raise StartupError("Could not locate Node.js or npm's CLI script. Reinstall Node.js/npm and reopen the terminal.")
        # Run the same npm script through Node directly. This avoids a cmd.exe/npm.cmd
        # batch wrapper, which can prompt interactively on Ctrl+Break during shutdown.
        return [node, str(npm_cli), *args]
    npm = shutil.which("npm")
    if not npm:
        raise StartupError("npm was not found. Install Node.js with npm and reopen the terminal.")
    return [npm, *args]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the DI-06 API and frontend locally")
    parser.add_argument("--host", type=_validate_host, default="127.0.0.1", help="Backend bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=_port, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--frontend-host", type=_validate_host, default="127.0.0.1", help="Vite bind host")
    parser.add_argument("--frontend-port", type=_port, default=5173, help="Vite port (default: 5173)")
    parser.add_argument("--backend-only", action="store_true", help="Run only FastAPI (for containers/deployments)")
    reload_group = parser.add_mutually_exclusive_group()
    reload_group.add_argument("--reload", dest="reload", action="store_true", help="Enable backend auto-reload (default)")
    reload_group.add_argument("--no-reload", dest="reload", action="store_false", help="Disable backend auto-reload")
    parser.set_defaults(reload=True)
    parser.add_argument("--startup-timeout", type=float, default=STARTUP_TIMEOUT_SECONDS,
                        help="Seconds to wait for readiness (default: 90)")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.startup_timeout <= 0:
        print("[ERROR] --startup-timeout must be greater than zero.", file=sys.stderr)
        return 2

    if not (PROJECT_ROOT / "backend" / "main.py").is_file() or not (FRONTEND_ROOT / "package.json").is_file():
        print("[ERROR] Expected backend/main.py and frontend/package.json under the repository root.", file=sys.stderr)
        return 2
    if not args.backend_only and not (FRONTEND_ROOT / "node_modules").is_dir():
        print("[ERROR] Frontend dependencies are missing. Run `npm install` in the frontend directory.", file=sys.stderr)
        return 2
    if not args.backend_only and shutil.which("node") is None:
        print("[ERROR] Node.js was not found. Install Node.js and npm, then reopen the terminal.", file=sys.stderr)
        return 2
    try:
        __import__("uvicorn")
    except ImportError:
        print(f"[ERROR] Uvicorn is missing from {sys.executable}. Install backend requirements first.", file=sys.stderr)
        return 2

    targets = [(args.host, args.port, "backend")]
    if not args.backend_only:
        targets.append((args.frontend_host, args.frontend_port, "frontend"))
    for host, port, name in targets:
        if not _port_is_available(host, port):
            print(f"[ERROR] {name.capitalize()} port {host}:{port} is already in use. "
                  "Stop the service that owns it or choose another port; no process was terminated.", file=sys.stderr)
            return 2

    child_specs = []
    backend_env = os.environ.copy()
    previous_pythonpath = backend_env.get("PYTHONPATH", "")
    backend_env["PYTHONPATH"] = str(PROJECT_ROOT) + (os.pathsep + previous_pythonpath if previous_pythonpath else "")
    if not args.backend_only:
        allowed_origins = [origin.strip() for origin in backend_env.get("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
        for origin in (f"http://127.0.0.1:{args.frontend_port}", f"http://localhost:{args.frontend_port}"):
            if origin not in allowed_origins:
                allowed_origins.append(origin)
        backend_env["CORS_ALLOWED_ORIGINS"] = ",".join(allowed_origins)
    try:
        child_specs.append(("API", _backend_command(args.host, args.port, args.reload), PROJECT_ROOT, backend_env))
        if not args.backend_only:
            frontend_command = _frontend_command(args.frontend_host, args.frontend_port)
            frontend_env = os.environ.copy()
            frontend_env["VITE_API_BASE_URL"] = f"http://127.0.0.1:{args.port}"
            child_specs.append(("Vite", frontend_command, FRONTEND_ROOT, frontend_env))
    except StartupError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    processes: list[tuple[str, subprocess.Popen, threading.Event]] = []
    try:
        for name, command, cwd, env in child_specs:
            try:
                process = subprocess.Popen(command, cwd=str(cwd), env=env,
                                           **_popen_options())
            except OSError as exc:
                raise StartupError(f"Could not start {name}: {exc}") from exc
            ended = threading.Event()
            thread = threading.Thread(target=_stream_child_output, args=(name, process.stdout, ended), daemon=True)
            thread.start()
            processes.append((name, process, ended))

        api_url = f"http://127.0.0.1:{args.port}"
        if args.backend_only:
            readiness = [("backend health", api_url + "/health")]
        else:
            readiness = [("backend health", api_url + "/health"),
                         ("frontend", f"http://127.0.0.1:{args.frontend_port}/")]
        deadline = time.monotonic() + args.startup_timeout
        while time.monotonic() < deadline:
            for name, process, _ in processes:
                return_code = process.poll()
                if return_code is not None:
                    raise StartupError(f"{name} exited during startup with code {return_code}.")
            if all(_is_ready(url) for _, url in readiness):
                break
            time.sleep(0.25)
        else:
            pending = [label for label, url in readiness if not _is_ready(url)]
            raise StartupError(f"Timed out waiting for: {', '.join(pending)}. "
                               "Check the service logs above and verify local database/configuration readiness.")

        if args.backend_only:
            print(f"[READY] Backend: http://localhost:{args.port}", flush=True)
        else:
            print(f"[READY] Frontend: http://localhost:{args.frontend_port}/", flush=True)
            print(f"[READY] Backend:  http://localhost:{args.port}/health", flush=True)
            print(f"[READY] API docs: http://localhost:{args.port}/docs", flush=True)
        print("[INFO] Press Ctrl+C to stop services started by this launcher.", flush=True)

        while True:
            for name, process, _ in processes:
                return_code = process.poll()
                if return_code is not None:
                    raise StartupError(f"{name} exited unexpectedly with code {return_code}.")
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\n[STOP] Shutdown requested.", flush=True)
        return 0
    except StartupError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        for name, process, _ in reversed(processes):
            _stop_child(process, name)


if __name__ == "__main__":
    raise SystemExit(main())
