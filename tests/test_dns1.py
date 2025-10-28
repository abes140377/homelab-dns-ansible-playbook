"""Tests for dns1 host."""

import pytest

# Configure testinfra to use ansible backend for dns1
testinfra_hosts = ["ansible://dns1"]


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
        {"service_name": "bind9", "ip": "192.168.1.13", "port": 53, "protocol": "tcp"},
        {"service_name": "bind9", "ip": "192.168.1.13", "port": 53, "protocol": "udp"},
        {
            "service_name": "adguardhome",
            "ip": "127.0.0.1",
            "port": 3000,
            "protocol": "tcp",
        },
        {"service_name": "unbound", "ip": "127.0.0.1", "port": 5335, "protocol": "tcp"},
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
        {"fqdn": "ns1.home.sflab.io"},
        {"fqdn": "ns2.home.sflab.io"},
        # {"fqdn": "adguard.homelab.local", "dns_server": "192.168.1.13"},
        # {"fqdn": "unbound.homelab.local", "dns_server": "192.168.1.13"},
    ],
    ids=lambda config: f"{config['fqdn']}",
)
def test_internal_dns_resolution_on_bind9(host, dns_config):
    """Verify internal DNS resolution using dig."""
    fqdn = dns_config["fqdn"]
    dns_server = "192.168.1.13"

    # Run dig command to resolve FQDN
    cmd = host.run(f"dig @{dns_server} {fqdn} +short")

    # Check if dig command succeeded
    assert cmd.rc == 0, f"dig command failed for {fqdn}: {cmd.stderr}"

    # Check if we got a response (any IP address)
    assert cmd.stdout.strip(), f"No DNS response for {fqdn} from {dns_server}"
