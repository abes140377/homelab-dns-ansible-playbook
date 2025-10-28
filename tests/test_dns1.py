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


@pytest.mark.parametrize("service_name", ["adguardhome", "bind9"])
def test_service_enabled(host, service_name):
    """Verify systemd services are enabled."""
    service = host.service(service_name)
    assert service.is_enabled


@pytest.mark.parametrize("service_name", ["adguardhome", "bind9"])
def test_service_running(host, service_name):
    """Verify systemd services are running."""
    service = host.service(service_name)
    assert service.is_running
