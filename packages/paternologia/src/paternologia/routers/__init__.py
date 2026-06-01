# ABOUTME: Router package for Paternologia API endpoints.
# ABOUTME: Exposes songs and devices routers for FastAPI app.

from paternologia.routers.devices import router as devices_router
from paternologia.routers.live import router as live_router
from paternologia.routers.pacer import router as pacer_router
from paternologia.routers.songs import router as songs_router

__all__ = ["songs_router", "devices_router", "pacer_router", "live_router"]
