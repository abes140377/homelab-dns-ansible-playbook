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


def test_dynamic_dns_update(host, dns_host_ip):
    """Verify dynamic DNS updates using nsupdate with TSIG key."""
    test_fqdn = f"test-dns-update.{get_domain()}"
    test_ip = "192.168.1.99"
    dns_server = dns_host_ip
    zone = get_domain()
    bind9_port = get_bind9_port("primary")

    # DDNS key configuration
    key_name = "ddnskey"
    key_algorithm = "hmac-sha512"
    key_secret = __import__("os").environ.get("DNS_KEY_SECRET")
    if not key_secret:
        raise RuntimeError("Environment variable DNS_KEY_SECRET is not set")

    logger.info(
        f"Testing dynamic DNS update for {test_fqdn} on {dns_server}:{bind9_port}"
    )

    try:
        # Step 1: Add A record using nsupdate with -y option for TSIG key
        nsupdate_add = f"""server {dns_server} {bind9_port}
zone {zone}
update add {test_fqdn} 300 A {test_ip}
send
"""
        add_cmd = host.run(
            f"echo '{nsupdate_add}' | nsupdate -y {key_algorithm}:{key_name}:{key_secret}"
        )
        assert add_cmd.rc == 0, (
            f"nsupdate add failed (rc={add_cmd.rc}): {add_cmd.stderr}\n"
            f"stdout: {add_cmd.stdout}"
        )
        logger.info(f"Successfully added A record for {test_fqdn}")

        # Step 2: Verify the DNS record exists
        dig_cmd = host.run(f"dig @{dns_server} -p {bind9_port} {test_fqdn} +short")
        assert dig_cmd.rc == 0, f"dig command failed: {dig_cmd.stderr}"
        assert test_ip in dig_cmd.stdout, (
            f"Expected IP {test_ip} not found in DNS response. Got: {dig_cmd.stdout}"
        )
        logger.info(f"Successfully verified A record: {test_fqdn} -> {test_ip}")

    finally:
        # Step 3: Cleanup - delete the A record
        nsupdate_delete = f"""server {dns_server} {bind9_port}
zone {zone}
update delete {test_fqdn} A
send
"""
        delete_cmd = host.run(
            f"echo '{nsupdate_delete}' | nsupdate -y {key_algorithm}:{key_name}:{key_secret}"
        )
        if delete_cmd.rc == 0:
            logger.info(f"Successfully deleted A record for {test_fqdn}")
        else:
            logger.warning(
                f"Failed to delete A record for {test_fqdn}: {delete_cmd.stderr}"
            )

        # Verify deletion
        verify_cmd = host.run(f"dig @{dns_server} -p {bind9_port} {test_fqdn} +short")
        if verify_cmd.rc == 0 and not verify_cmd.stdout.strip():
            logger.info(f"Verified A record deletion for {test_fqdn}")
        elif verify_cmd.rc == 0 and verify_cmd.stdout.strip():
            logger.warning(f"A record still exists after deletion: {verify_cmd.stdout}")
