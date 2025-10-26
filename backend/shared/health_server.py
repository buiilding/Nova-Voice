"""
health_server.py - Shared health check and metrics HTTP server

Provides standardized health check and metrics endpoints for worker services.
Handles CORS setup and server lifecycle management.
"""

import time
import logging
from aiohttp import web
import aiohttp_cors
from typing import Optional, Dict, Any, Callable


class HealthServer:
    """HTTP server for health checks and metrics"""

    def __init__(self, instance_id: str, port: int, logger: logging.Logger,
                 get_health_data: Callable[[], Dict[str, Any]],
                 get_metrics_data: Optional[Callable[[], Dict[str, Any]]] = None):
        """
        Initialize health server

        Args:
            instance_id: Unique identifier for this instance
            port: Port to listen on
            logger: Logger instance
            get_health_data: Function that returns health data dict
            get_metrics_data: Optional function that returns detailed metrics
        """
        self.instance_id = instance_id
        self.port = port
        self.logger = logger
        self.get_health_data = get_health_data
        self.get_metrics_data = get_metrics_data

    async def health_check_handler(self, request):
        """Health check endpoint"""
        try:
            health_data = self.get_health_data()
            return web.json_response({
                "status": "healthy",
                "instance_id": self.instance_id,
                "timestamp": time.time(),
                **health_data
            })
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e), "instance_id": self.instance_id},
                status=500
            )

    async def metrics_handler(self, request):
        """Metrics endpoint"""
        try:
            metrics_data = {}
            if self.get_metrics_data:
                metrics_data = self.get_metrics_data()
            else:
                metrics_data = self.get_health_data()

            return web.json_response({
                "instance_id": self.instance_id,
                "timestamp": time.time(),
                **metrics_data
            })
        except Exception as e:
            self.logger.error(f"Metrics endpoint error: {e}")
            return web.json_response(
                {"error": str(e), "instance_id": self.instance_id},
                status=500
            )

    async def start_server(self):
        """Start the health check HTTP server"""
        app = web.Application()
        app.router.add_get('/health', self.health_check_handler)
        app.router.add_get('/metrics', self.metrics_handler)

        # Disable aiohttp access logging
        logging.getLogger('aiohttp.access').setLevel(logging.CRITICAL)

        # Add CORS support
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        for route in list(app.router.routes()):
            cors.add(route)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        self.logger.info(f"Health server started on port {self.port}")
