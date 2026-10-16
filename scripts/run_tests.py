"""Automated Test Runner for DI-06."""
import subprocess
import sys
import os

def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.environ["PYTHONPATH"] = project_root

    print("=" * 60)
    print("[TESTS] RUNNING AUTOMATED TEST SUITE (pytest)")
    print("=" * 60)

    cmd = [sys.executable, "-m", "pytest", "backend/tests", "-v"]
    result = subprocess.run(cmd, cwd=project_root)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[FAILURE] SOME TESTS FAILED. Check test outputs above.")
        print("=" * 60)

    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
