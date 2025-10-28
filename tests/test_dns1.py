"""Tests for dns1 host."""

import logging
import pytest

from conftest import get_host_ip
from conftest import get_adguard_port
from conftest import get_bind9_port
from conftest import get_unbound_port
from conftest import get_domain

logger = logging.getLogger(__name__)

# Configure testinfra to use ansible backend for dns1
testinfra_hosts = ["ansible://dns1"]
loopback_ip = "127.0.0.1"


def test_distribution(host):
    """Verify host is running Ubuntu."""
    assert host.system_info.distribution == "ubuntu"


def test_distribution_version(host):
    """Verify host is running Ubuntu 24.04."""
    assert host.system_info.release == "24.04"


@pytest.mark.parametrize("service_name", ["adguardhome", "bind9", "unbound"])
def test_service_enabled(host, service_name):
    """Verify systemd services are enabled."""
    service = host.service(service_name)
    assert service.is_enabled
    assert service.is_running


@pytest.mark.parametrize(
    "service_config",
    [
        {
            "service_name": "adguardhome",
            "ip": get_host_ip("dns1"),
            "port": get_adguard_port("primary"),
            "protocol": "tcp",
        },
        {
            "service_name": "adguardhome",
            "ip": get_host_ip("dns1"),
            "port": get_adguard_port("primary"),
            "protocol": "udp",
        },
        {
            "service_name": "adguardhome",
            "ip": loopback_ip,
            "port": 3000,
            "protocol": "tcp",
        },
        {
            "service_name": "bind9",
            "ip": get_host_ip("dns1"),
            "port": get_bind9_port("primary"),
            "protocol": "tcp",
        },
        {
            "service_name": "bind9",
            "ip": get_host_ip("dns1"),
            "port": get_bind9_port("primary"),
            "protocol": "udp",
        },
        {
            "service_name": "unbound",
            "ip": loopback_ip,
            "port": get_unbound_port("primary"),
            "protocol": "tcp",
        },
    ],
    ids=lambda config: f"{config['service_name']}-{config['protocol']}-{config['ip']}:{config['port']}",
)
def test_service_port_listening(host, service_config):
    """Verify services are listening on expected ip and ports."""
    service_name = service_config["service_name"]
    ip = service_config["ip"]
    port = service_config["port"]
    protocol = service_config["protocol"]

    # Test if the service is listening on the ip and port
    socket = host.socket(f"{protocol}://{ip}:{port}")
    assert socket.is_listening, (
        f"{service_name} should be listening on {protocol}/{port}"
    )


@pytest.mark.parametrize(
    "dns_config",
    [
        {"fqdn": f"ns1.{get_domain()}"},
        {"fqdn": f"ns2.{get_domain()}"},
        {"fqdn": f"adguard.{get_domain()}"},
        {"fqdn": f"proxmox.{get_domain()}"},
    ],
    ids=lambda config: f"{config['fqdn']}",
)
def test_internal_dns_resolution_on_bind9(host, dns_config, dns_host_ip):
    """Verify internal DNS resolution using dig."""
    fqdn = dns_config["fqdn"]
    dns_server = dns_host_ip

    # Run dig command to resolve FQDN
    cmd = host.run(f"dig @{dns_server} {fqdn} +short")

    # Check if dig command succeeded
    assert cmd.rc == 0, f"dig command failed for {fqdn}: {cmd.stderr}"

    # Check if we got a response (any IP address)
    assert cmd.stdout.strip(), f"No DNS response for {fqdn} from {dns_server}"


def test_external_dns_resolution_on_bind9(host, dns_host_ip):
    """Verify internal DNS resolution using dig."""
    fqdn = "google.com"
    dns_server = dns_host_ip

    logger.info(
        f"Testing external DNS resolution for {fqdn} using DNS server {dns_server}"
    )
    print(f"Testing external DNS resolution for {fqdn} using DNS server {dns_server}")

    # Run dig command to resolve FQDN
    cmd = host.run(f"dig @{dns_server} {fqdn} +short")

    # Check if dig command succeeded
    assert cmd.rc == 0, f"dig command failed for {fqdn}: {cmd.stderr}"

    # Check if we got a response (any IP address)
    assert cmd.stdout.strip(), f"No DNS response for {fqdn} from {dns_server}"


def test_adguard_port():
    port = get_adguard_port("primary")
    assert port == 53


def test_bind9_port():
    port = get_bind9_port("primary")
    assert port == 5353


def test_unbound_port():
    port = get_unbound_port("primary")
    assert port == 5335


def test_domain():
    port = get_domain()
    assert port == "home.sflab.io"
