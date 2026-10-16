"""Re-export buyer router for backward compatibility with main app mounting."""
from backend.buyer.router import router

__all__ = ["router"]
