"""Tests for local DNS resolution from local machine."""

import socket
import pytest


@pytest.mark.parametrize(
    "hostname",
    [
        "ns1",
        "ns2",
        "opnsense",
        "ap",
        "switch",
        "adguard",
        "proxmox",
        "speedport",
    ],
)
def test_local_dns_resolution_home_sflab_io(hostname):
    """Verify local DNS resolution for home.sflab.io domain."""
    fqdn = f"{hostname}.home.sflab.io"

    # Attempt to resolve the hostname
    try:
        result = socket.getaddrinfo(fqdn, None)
        # Check if we got at least one result
        assert len(result) > 0, f"No DNS response for {fqdn}"
        # Check if we got an IP address
        ip_address = result[0][4][0]
        assert ip_address, f"No IP address returned for {fqdn}"
    except socket.gaierror as e:
        pytest.fail(f"DNS resolution failed for {fqdn}: {e}")
