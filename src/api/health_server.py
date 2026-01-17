"""
FastAPI Health Check Server
Exposes health status and metrics for monitoring, load balancers, and Kubernetes probes
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.models.transaction_models import HealthCheckResponse

logger = logging.getLogger(__name__)


class HealthServer:
    """
    Health check and metrics server

    Exposes HTTP endpoints for:
    - /health - Overall system health
    - /health/live - Liveness probe (is the service running?)
    - /health/ready - Readiness probe (is the service ready to accept traffic?)
    - /metrics - Prometheus-compatible metrics
    - /stats - Detailed processing statistics
    """

    def __init__(self, orchestrator=None, port: int = 8080):
        """
        Initialize health server

        Args:
            orchestrator: FraudOrchestrator instance to get stats from
            port: Port to run the server on (default 8080)
        """
        self.orchestrator = orchestrator
        self.port = port
        self.app = FastAPI(
            title="Fraud Detection Health API",
            description="Health checks and metrics for fraud detection system",
            version="1.0.0"
        )
        self.start_time = time.time()

        # Register endpoints
        self._register_endpoints()

        logger.info(f"✅ Health server initialized on port {port}")

    def _register_endpoints(self):
        """Register all health check endpoints"""

        @self.app.get("/", response_model=Dict)
        async def root():
            """Root endpoint - API information"""
            return {
                "service": "Fraud Detection Health API",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "/health": "Overall health status",
                    "/health/live": "Liveness probe",
                    "/health/ready": "Readiness probe",
                    "/metrics": "System metrics",
                    "/stats": "Processing statistics"
                }
            }

        @self.app.get("/health", response_model=HealthCheckResponse)
        async def health_check():
            """
            Overall health check endpoint

            Returns detailed health status including:
            - Overall status (healthy/degraded/unhealthy)
            - Component health (Redis, Qdrant, Database, etc.)
            - System metrics
            """
            try:
                components = {}
                overall_status = "healthy"

                # Check if running in minimal mode
                if not self.orchestrator:
                    return HealthCheckResponse(
                        status="healthy",
                        timestamp=datetime.now(),
                        components={
                            "mode": "minimal",
                            "message": "Running in minimal mode - orchestrator not initialized"
                        },
                        metrics={
                            "uptime_seconds": time.time() - self.start_time,
                            "uptime_human": self._format_uptime(time.time() - self.start_time)
                        }
                    )

                # Check orchestrator
                if self.orchestrator:
                    # Check Redis
                    if self.orchestrator.redis_memory:
                        try:
                            redis_stats = self.orchestrator.redis_memory.get_stats()
                            components["redis"] = {
                                "status": "healthy",
                                "stats": redis_stats
                            }
                        except Exception as e:
                            components["redis"] = {
                                "status": "unhealthy",
                                "error": str(e)
                            }
                            overall_status = "degraded"
                    else:
                        components["redis"] = {"status": "disabled"}

                    # Check Qdrant
                    if self.orchestrator.qdrant_knowledge:
                        try:
                            qdrant_stats = self.orchestrator.qdrant_knowledge.get_stats()
                            components["qdrant"] = {
                                "status": "healthy",
                                "stats": qdrant_stats
                            }
                        except Exception as e:
                            components["qdrant"] = {
                                "status": "unhealthy",
                                "error": str(e)
                            }
                            overall_status = "degraded"
                    else:
                        components["qdrant"] = {"status": "disabled"}

                    # Check AI Agents
                    if self.orchestrator.agent_crew:
                        components["agents"] = {"status": "healthy"}

                    # ML Detector
                    if self.orchestrator.ml_detector:
                        ml_info = self.orchestrator.ml_detector.get_model_info()
                        components["ml_detector"] = {
                            "status": "healthy" if ml_info.get('trained') else "unhealthy",
                            "info": ml_info
                        }

                    # Velocity Detector
                    if self.orchestrator.velocity_detector:
                        components["velocity_detector"] = {"status": "healthy"}

                else:
                    overall_status = "unhealthy"
                    components["orchestrator"] = {"status": "not_initialized"}

                # System metrics
                uptime_seconds = time.time() - self.start_time
                metrics = {
                    "uptime_seconds": uptime_seconds,
                    "uptime_human": self._format_uptime(uptime_seconds)
                }

                return HealthCheckResponse(
                    status=overall_status,
                    timestamp=datetime.now(),
                    components=components,
                    metrics=metrics
                )

            except Exception as e:
                logger.error(f"Health check failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Health check failed: {str(e)}"
                )

        @self.app.get("/health/live")
        async def liveness_probe():
            """
            Kubernetes liveness probe

            Returns 200 if the service is running (even if degraded)
            Returns 503 if the service should be restarted
            """
            # Simple check - is the process running?
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "alive",
                    "timestamp": datetime.now().isoformat()
                }
            )

        @self.app.get("/health/ready")
        async def readiness_probe():
            """
            Kubernetes readiness probe

            Returns 200 if the service is ready to accept traffic
            Returns 503 if the service is not ready (e.g., initializing)
            """
            try:
                # In minimal mode, always return ready (for basic liveness)
                if self.orchestrator is None:
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "status": "ready",
                            "mode": "minimal",
                            "timestamp": datetime.now().isoformat()
                        }
                    )

                # Check if ML model is trained
                if self.orchestrator.ml_detector:
                    ml_info = self.orchestrator.ml_detector.get_model_info()
                    if not ml_info.get('trained'):
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="ML model not trained"
                        )

                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status": "ready",
                        "timestamp": datetime.now().isoformat()
                    }
                )

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Service not ready: {str(e)}"
                )

        @self.app.get("/metrics")
        async def metrics():
            """
            Prometheus-compatible metrics endpoint

            Returns metrics in a format that can be scraped by Prometheus
            """
            try:
                uptime_seconds = time.time() - self.start_time

                if not self.orchestrator:
                    # Minimal mode - only uptime metric
                    metrics_output = []
                    metrics_output.append("# HELP fraud_detection_uptime_seconds Service uptime in seconds")
                    metrics_output.append("# TYPE fraud_detection_uptime_seconds gauge")
                    metrics_output.append(f"fraud_detection_uptime_seconds {uptime_seconds}")
                    metrics_output.append("")
                    metrics_output.append("# HELP fraud_detection_mode Health server mode")
                    metrics_output.append("# TYPE fraud_detection_mode gauge")
                    metrics_output.append("fraud_detection_mode{mode=\"minimal\"} 1")

                    return JSONResponse(
                        content="\n".join(metrics_output),
                        media_type="text/plain"
                    )

                stats = self.orchestrator.get_stats()

                # Prometheus-style metrics
                metrics_output = []
                metrics_output.append(f"# HELP fraud_detection_uptime_seconds Service uptime in seconds")
                metrics_output.append(f"# TYPE fraud_detection_uptime_seconds gauge")
                metrics_output.append(f"fraud_detection_uptime_seconds {uptime_seconds}")

                metrics_output.append(f"# HELP fraud_detection_transactions_total Total transactions processed")
                metrics_output.append(f"# TYPE fraud_detection_transactions_total counter")
                metrics_output.append(f"fraud_detection_transactions_total {stats.get('total_transactions', 0)}")

                metrics_output.append(f"# HELP fraud_detection_fraud_detected_total Total fraud cases detected")
                metrics_output.append(f"# TYPE fraud_detection_fraud_detected_total counter")
                metrics_output.append(f"fraud_detection_fraud_detected_total {stats.get('fraud_detected', 0)}")

                metrics_output.append(f"# HELP fraud_detection_agent_investigations_total Total AI agent investigations")
                metrics_output.append(f"# TYPE fraud_detection_agent_investigations_total counter")
                metrics_output.append(f"fraud_detection_agent_investigations_total {stats.get('agent_investigations', 0)}")

                metrics_output.append(f"# HELP fraud_detection_velocity_fraud_total Total velocity fraud cases")
                metrics_output.append(f"# TYPE fraud_detection_velocity_fraud_total counter")
                metrics_output.append(f"fraud_detection_velocity_fraud_total {stats.get('velocity_fraud_count', 0)}")

                metrics_output.append(f"# HELP fraud_detection_card_testing_total Total card testing cases")
                metrics_output.append(f"# TYPE fraud_detection_card_testing_total counter")
                metrics_output.append(f"fraud_detection_card_testing_total {stats.get('card_testing_count', 0)}")

                return JSONResponse(
                    content="\n".join(metrics_output),
                    media_type="text/plain"
                )

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate metrics: {str(e)}"
                )

        @self.app.get("/stats")
        async def detailed_stats():
            """
            Detailed processing statistics

            Returns comprehensive statistics including:
            - Transaction processing stats
            - Redis stats
            - Qdrant stats
            - Velocity detection stats
            """
            try:
                uptime_seconds = time.time() - self.start_time

                if not self.orchestrator:
                    return {
                        "timestamp": datetime.now().isoformat(),
                        "mode": "minimal",
                        "uptime_seconds": uptime_seconds,
                        "uptime_human": self._format_uptime(uptime_seconds),
                        "message": "Running in minimal mode - full stats require orchestrator initialization"
                    }

                stats = self.orchestrator.get_stats()

                return {
                    "timestamp": datetime.now().isoformat(),
                    "uptime_seconds": uptime_seconds,
                    "uptime_human": self._format_uptime(uptime_seconds),
                    "statistics": stats
                }

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get stats: {str(e)}"
                )

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)

    def run(self, host: str = "0.0.0.0"):
        """
        Run the health server

        Args:
            host: Host to bind to (default 0.0.0.0 for all interfaces)
        """
        import uvicorn

        logger.info(f"🚀 Starting health server on {host}:{self.port}")
        logger.info(f"   Health endpoint: http://{host}:{self.port}/health")
        logger.info(f"   Metrics endpoint: http://{host}:{self.port}/metrics")

        uvicorn.run(
            self.app,
            host=host,
            port=self.port,
            log_level="info"
        )


def create_health_server(orchestrator, port: int = 8080) -> HealthServer:
    """
    Factory function to create a health server

    Args:
        orchestrator: FraudOrchestrator instance
        port: Port to run the server on

    Returns:
        HealthServer instance
    """
    return HealthServer(orchestrator=orchestrator, port=port)
