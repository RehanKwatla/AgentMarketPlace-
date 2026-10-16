"""[IMPLEMENTED] Connect-Time IP-Pinning HTTP Transport & Network Backend.

Provides protection against DNS Rebinding and Time-of-Check to Time-of-Use (TOCTOU) attacks:
1. Intercepts TCP connection establishment and routes socket directly to pre-validated IP.
2. Prevents the HTTP client transport from performing a second, unvalidated DNS lookup.
3. Preserves original hostname for HTTP Host header and TLS Server Name Indication (SNI).
4. Strictly preserves TLS certificate validation against the original hostname (verify=True).
5. Disables environment proxy discovery (trust_env=False) to avoid proxy-side re-resolution.
6. Verifies the OS-level connected peer address via anyio SocketAttribute.
"""
import logging
from typing import Optional, Iterable, Tuple, Any
import anyio
import anyio.abc
import httpcore
from httpcore._backends.anyio import AnyIOBackend
import httpx
from httpx._transports.default import create_ssl_context

from backend.sellers.providers.errors import ProviderSSRFBlockedError
from backend.sellers.providers.scraping.safety import validate_ip_address_safety

logger = logging.getLogger(__name__)


class PinnedAsyncNetworkBackend(httpcore.AsyncNetworkBackend):
    """Network backend that pins TCP socket connections to a pre-validated IP address.
    
    Prevents DNS TOCTOU race conditions where a domain changes its A/AAAA record
    between the application security check and the socket connect() call.
    """

    def __init__(self, pinned_ip: str):
        self._pinned_ip = pinned_ip
        # Enforce destination safety upon backend initialization
        validate_ip_address_safety(pinned_ip)
        self._backend = AnyIOBackend()

    @property
    def pinned_ip(self) -> str:
        return self._pinned_ip

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Optional[Iterable[Any]] = None,
    ) -> httpcore.AsyncNetworkStream:
        """Establish TCP connection directly to self._pinned_ip while preserving host for TLS SNI.
        
        Args:
            host: Original requested hostname (preserved for TLS SNI and cert check)
            port: Target port (validated by safety policy)
        """
        # 1. Re-verify pinned IP safety immediately prior to connect
        validate_ip_address_safety(self._pinned_ip)

        logger.debug(
            "Connecting TCP to pinned IP %s:%d (original host: %s)",
            self._pinned_ip, port, host
        )

        # 2. Connect to the exact approved IP address (no second DNS query)
        stream = await self._backend.connect_tcp(
            self._pinned_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

        # 3. Verify actual connected peer address at OS socket level
        try:
            raw_stream = getattr(stream, "_stream", None)
            if raw_stream is not None and hasattr(raw_stream, "extra"):
                remote_addr: Optional[Tuple[str, int]] = raw_stream.extra(
                    anyio.abc.SocketAttribute.remote_address, None
                )
                if remote_addr:
                    connected_ip = str(remote_addr[0])
                    # Ensure connected peer matches our pinned IP and passes safety check
                    if connected_ip != self._pinned_ip:
                        await stream.aclose()
                        raise ProviderSSRFBlockedError(
                            f"Connected peer IP '{connected_ip}' does not match pinned IP '{self._pinned_ip}'.",
                            destination=connected_ip,
                        )
                    validate_ip_address_safety(connected_ip)
        except ProviderSSRFBlockedError:
            raise
        except Exception as exc:
            logger.warning("OS peer verification check encountered non-fatal error: %s", exc)

        return stream

    async def sleep(self, seconds: float) -> None:
        return await self._backend.sleep(seconds)


class PinnedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """Custom HTTPX transport enforcing connect-time destination IP pinning.
    
    Guarantees:
    - Connection destination is pinned to pre-validated IP.
    - TLS certificate verification remains active and checks original hostname.
    - Environment proxies (HTTP_PROXY, HTTPS_PROXY) cannot hijack the connection.
    - Connection pooling across different pins/origins is prohibited (max_keepalive=0).
    """

    def __init__(
        self,
        pinned_ip: str,
        verify: bool = True,
        trust_env: bool = False,
        **kwargs,
    ):
        super().__init__(verify=verify, trust_env=trust_env, **kwargs)
        self._pinned_ip = pinned_ip
        self._pinned_backend = PinnedAsyncNetworkBackend(pinned_ip)

        ssl_context = create_ssl_context(verify=verify, trust_env=trust_env)
        # Create dedicated single-use connection pool bound to pinned network backend
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            network_backend=self._pinned_backend,
            max_connections=10,
            max_keepalive_connections=0,  # Prohibit keepalive reuse across different targets
            http1=True,
            http2=False,
            retries=0,
        )

    @property
    def pinned_ip(self) -> str:
        return self._pinned_ip
