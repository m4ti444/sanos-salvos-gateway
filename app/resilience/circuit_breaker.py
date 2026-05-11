"""
Sanos y Salvos — Circuit Breaker Pattern
Protects service-to-service communication from cascading failures.
"""

import pybreaker
import httpx
import logging
from typing import Optional

logger = logging.getLogger("circuit_breaker")


class ServiceCircuitBreaker:
    """
    Circuit Breaker wrapper for microservice HTTP calls.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is down, requests fail fast with fallback
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, service_name: str, fail_max: int = 5, reset_timeout: int = 30):
        self.service_name = service_name
        self.breaker = pybreaker.CircuitBreaker(
            fail_max=fail_max,
            reset_timeout=reset_timeout,
            name=service_name,
            listeners=[CircuitBreakerListener(service_name)],
        )

    async def call(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: float = 10.0,
    ) -> httpx.Response:
        """
        Make an HTTP request through the circuit breaker.
        """
        try:
            return await self.breaker.call_async(
                self._make_request, method, url, headers, json, params, timeout
            )
        except pybreaker.CircuitBreakerError:
            logger.warning(
                f"Circuit breaker OPEN for {self.service_name}. Returning fallback."
            )
            raise ServiceUnavailableError(self.service_name)

    @staticmethod
    async def _make_request(
        method: str,
        url: str,
        headers: Optional[dict],
        json: Optional[dict],
        params: Optional[dict],
        timeout: float,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
            )
            response.raise_for_status()
            return response


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Logs circuit breaker state transitions."""

    def __init__(self, service_name: str):
        self.service_name = service_name

    def state_change(self, cb, old_state, new_state):
        logger.info(
            f"[{self.service_name}] Circuit Breaker: {old_state.name} → {new_state.name}"
        )

    def failure(self, cb, exc):
        logger.warning(f"[{self.service_name}] Request failed: {exc}")

    def success(self, cb):
        logger.debug(f"[{self.service_name}] Request successful")


class ServiceUnavailableError(Exception):
    """Raised when a service circuit breaker is open."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Service '{service_name}' is currently unavailable")


# Pre-configured circuit breakers for each microservice
pets_breaker = ServiceCircuitBreaker("pets-service")
geo_breaker = ServiceCircuitBreaker("geolocation-service")
match_breaker = ServiceCircuitBreaker("match-service")
notifications_breaker = ServiceCircuitBreaker("notifications-service")
