"""Re-export registry router for backward compatibility with main app mounting."""
from backend.registry.router import router

__all__ = ["router"]
