"""Cross-Platform Development Server Runner for DI-06."""
import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Start DI-06 Agent Economy Dev Environment")
    parser.add_argument("--host", default="0.0.0.0", help="Backend host")
    parser.add_argument("--port", type=int, default=8000, help="Backend port")
    parser.add_argument("--backend-only", action="store_true", help="Start only the backend server")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")
    args = parser.parse_args()

    # Ensure project root is in PYTHONPATH
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)
    os.environ["PYTHONPATH"] = project_root

    print("=" * 60)
    print("[START] STARTING DI-06 PAY-PER-CALL AGENT ECONOMY")
    print(f"Host: {args.host}:{args.port}")
    print(f"Swagger Docs: http://localhost:{args.port}/docs")
    print(f"Health: http://localhost:{args.port}/health")
    print("=" * 60)

    try:
        import uvicorn
        uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=args.reload)
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped by user.")
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
