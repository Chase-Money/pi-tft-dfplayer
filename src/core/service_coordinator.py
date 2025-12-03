"""Service coordinator for the v2 UI framework.

Manages application services and their lifecycle.
"""

import logging

logger = logging.getLogger(__name__)


class ServiceCoordinator:
    """Coordinates application services and their lifecycle."""

    def __init__(self, services: dict):
        """
        Initialize the service coordinator.

        Args:
            services: Dictionary of service instances
        """
        self.services = services
        self.state = services.get("state")
        self.backend = services.get("backend")
        self.framebuffer = services.get("framebuffer")
        self.touch_controller = services.get("touch_controller")

    def initialize_services(self) -> None:
        """Initialize all services."""
        # Services are initialized in Application.__init__, this is for future expansion
        pass

    def shutdown_services(self) -> None:
        """Shutdown all services gracefully."""
        logger.info("Shutting down application services")

        # Shutdown backend
        if self.backend:
            try:
                self.backend.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down backend: {e}")

        # Close framebuffer
        if self.framebuffer and hasattr(self.framebuffer, "close"):
            try:
                self.framebuffer.close()
            except Exception as e:
                logger.error(f"Error closing framebuffer: {e}")

        logger.info("Application services shutdown complete")

    def get_service(self, name: str):
        """Get a service by name."""
        return self.services.get(name)

    def set_service(self, name: str, service) -> None:
        """Set a service by name."""
        self.services[name] = service
        # Update local references if needed
        if name == "state":
            self.state = service
        elif name == "backend":
            self.backend = service
        elif name == "framebuffer":
            self.framebuffer = service
        elif name == "touch_controller":
            self.touch_controller = service