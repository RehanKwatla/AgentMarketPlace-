"""Database seed script for DI-06 Pay-Per-Call Agent Economy."""
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.registry.service_catalog import ServiceCatalog

def seed():
    """Verify and initialize default registry services."""
    print("[SEED] Initializing ServiceCatalog...")
    catalog = ServiceCatalog()
    services = catalog.list_services()
    print(f"[SEED] Successfully loaded {len(services)} services into catalog:")
    for s in services:
        print(f"  - [{s.service_id}] {s.name} ({s.category.value}) @ {s.price_usdc} USDC")

if __name__ == "__main__":
    seed()
