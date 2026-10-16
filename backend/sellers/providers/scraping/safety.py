"""[IMPLEMENTED] Connection-Time SSRF Defense & IP Destination Policy Enforcement."""
import ipaddress
import socket
from urllib.parse import urlparse
from typing import List, Optional
from backend.sellers.providers.errors import ProviderSSRFBlockedError

# Prohibited destination hostnames and metadata services
BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

BLOCKED_EXACT_IPS = {
    "169.254.169.254",     # AWS/GCP/Azure link-local metadata
    "fd00:ec2::254",        # AWS IPv6 metadata
    "100.100.100.200",      # Alibaba metadata
}

# Standard web ports permitted for scraping
ALLOWED_PORTS = {80, 443}


def validate_url_syntax(url: str) -> None:
    """Validate URL scheme, structure, ports, and absence of user-info tricks."""
    if not url or not url.strip():
        raise ProviderSSRFBlockedError("URL cannot be empty.", destination=url)
    
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise ProviderSSRFBlockedError(
            f"Unsupported scheme '{parsed.scheme}'. Only http and https are allowed.",
            destination=url
        )
    
    if parsed.username or parsed.password:
        raise ProviderSSRFBlockedError(
            "URLs containing embedded userinfo credentials are not permitted.",
            destination=url
        )

    if not parsed.hostname:
        raise ProviderSSRFBlockedError("URL must contain a valid hostname.", destination=url)

    # Port restriction
    if parsed.port is not None and parsed.port not in ALLOWED_PORTS:
        raise ProviderSSRFBlockedError(
            f"Port {parsed.port} is not permitted. Only ports 80 and 443 are allowed.",
            destination=url
        )

    host_lower = parsed.hostname.lower()
    if host_lower in BLOCKED_HOSTNAMES or any(host_lower.endswith(f".{suffix}") for suffix in ("local", "internal", "localhost")):
        raise ProviderSSRFBlockedError(
            f"Access to local or internal domain '{host_lower}' is blocked.",
            destination=host_lower
        )

    # If hostname is an IP string, validate safety immediately
    try:
        ipaddress.ip_address(host_lower)
        validate_ip_address_safety(host_lower)
    except ValueError:
        pass

    # Check for integer or unusual IP encodings in hostname (e.g., 2130706433 or 0x7f000001)
    if host_lower.isdigit():
        try:
            int_val = int(host_lower)
            decoded_ip = str(ipaddress.IPv4Address(int_val))
            validate_ip_address_safety(decoded_ip)
        except ValueError:
            pass


def validate_ip_address_safety(ip_str: str) -> None:
    """Validate an IP address against RFC private, loopback, link-local, carrier-grade NAT, and metadata rules."""
    if ip_str in BLOCKED_EXACT_IPS:
        raise ProviderSSRFBlockedError(
            f"Access to cloud metadata IP '{ip_str}' is strictly blocked.",
            destination=ip_str
        )
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError as val_err:
        raise ProviderSSRFBlockedError(f"Invalid IP address format: {val_err}", destination=ip_str)

    # Check for IPv4-mapped IPv6 address (e.g. ::ffff:127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if ip.is_loopback:
        raise ProviderSSRFBlockedError(f"Access to loopback IP '{ip}' is blocked.", destination=ip_str)
    if ip.is_private:
        raise ProviderSSRFBlockedError(f"Access to private subnet IP '{ip}' is blocked.", destination=ip_str)
    if ip.is_link_local:
        raise ProviderSSRFBlockedError(f"Access to link-local IP '{ip}' is blocked.", destination=ip_str)
    if ip.is_multicast:
        raise ProviderSSRFBlockedError(f"Access to multicast IP '{ip}' is blocked.", destination=ip_str)
    if ip.is_unspecified:
        raise ProviderSSRFBlockedError(f"Access to unspecified IP '{ip}' is blocked.", destination=ip_str)
    if ip.is_reserved:
        raise ProviderSSRFBlockedError(f"Access to reserved IP '{ip}' is blocked.", destination=ip_str)

    # Carrier-grade NAT (100.64.0.0/10)
    if isinstance(ip, ipaddress.IPv4Address):
        cgnat_network = ipaddress.IPv4Network("100.64.0.0/10")
        if ip in cgnat_network:
            raise ProviderSSRFBlockedError(f"Access to shared/carrier-grade NAT IP '{ip}' is blocked.", destination=ip_str)


def resolve_and_validate_destination(hostname: str) -> List[str]:
    """Resolve hostname to IP addresses and assert every IP passes destination safety checks.
    
    Returns:
        List of verified safe IP addresses.
    Raises:
        ProviderSSRFBlockedError if any resolved IP violates policy.
    """
    # If the hostname is already an IP address, validate directly
    try:
        ipaddress.ip_address(hostname)
        validate_ip_address_safety(hostname)
        return [hostname]
    except ValueError:
        pass

    # Check numeric integer hostnames
    if hostname.isdigit():
        try:
            decoded_ip = str(ipaddress.IPv4Address(int(hostname)))
            validate_ip_address_safety(decoded_ip)
            return [decoded_ip]
        except ValueError:
            pass

    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as gai_err:
        raise ProviderSSRFBlockedError(f"Could not resolve hostname '{hostname}': {gai_err}", destination=hostname)

    resolved_ips = []
    for family, socktype, proto, canonname, sockaddr in addr_info:
        ip_addr = sockaddr[0]
        validate_ip_address_safety(ip_addr)
        if ip_addr not in resolved_ips:
            resolved_ips.append(ip_addr)

    if not resolved_ips:
        raise ProviderSSRFBlockedError(f"Hostname '{hostname}' resolved to zero IP addresses.", destination=hostname)

    return resolved_ips
