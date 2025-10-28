"""pytest configuration for testinfra tests."""

import os

import pytest
import yaml

# Set Ansible inventory path via environment variable to avoid CLI conflicts
os.environ["ANSIBLE_INVENTORY"] = "inventory/hosts.yml"


def get_domain():
    """Get domain from Ansible variables (for use in parametrize decorators).

    This function loads the Ansible inventory at import time to provide
    domain for use in pytest.mark.parametrize decorators.

    Returns:
        str: The domain from Ansible variables
    """
    vars_path = "inventory/group_vars/all.yml"
    with open(vars_path) as f:
        vars = yaml.safe_load(f)

    return vars["domain"]


def get_host_ip(hostname):
    """Get host IP from Ansible inventory (for use in parametrize decorators).

    This function loads the Ansible inventory at import time to provide
    IP addresses for use in pytest.mark.parametrize decorators.

    Args:
        hostname: The hostname to look up (e.g., "dns1", "dns2")

    Returns:
        str: The IP address of the host from ansible_host variable
    """
    inventory_path = "inventory/hosts.yml"
    with open(inventory_path) as f:
        inventory = yaml.safe_load(f)

    return inventory["all"]["hosts"][hostname]["ansible_host"]


def get_adguard_port(server_type):
    """Get host AdGuard port from Ansible variables (for use in parametrize decorators).

    This function loads the Ansible configuration at import time to provide
    AdGuard port for use in pytest.mark.parametrize decorators.

    Args:
        server_type: The type of the dns server (e.g., "primary", "secondary")

    Returns:
        str: The AdGuard port of the host from config variable
    """
    vars_path = f"inventory/group_vars/{server_type}_servers.yml"
    with open(vars_path) as f:
        vars = yaml.safe_load(f)

    return vars["adguardhome_dnsport"]


def get_bind9_port(server_type):
    """Get host Bind9 port from Ansible variables (for use in parametrize decorators).

    This function loads the Ansible configuration at import time to provide
    AdGuard port for use in pytest.mark.parametrize decorators.

    Args:
        server_type: The type of the dns server (e.g., "primary", "secondary")

    Returns:
        str: The Bind9 port of the host from config variable
    """
    vars_path = f"inventory/group_vars/{server_type}_servers.yml"
    with open(vars_path) as f:
        vars = yaml.safe_load(f)

    return vars["bind9_port"]


def get_unbound_port(server_type):
    """Get host Bind9 port from Ansible variables (for use in parametrize decorators).

    This function loads the Ansible configuration at import time to provide
    AdGuard port for use in pytest.mark.parametrize decorators.

    Args:
        server_type: The type of the dns server (e.g., "primary", "secondary")

    Returns:
        str: The Unbound port of the host from config variable
    """
    config_path = f"inventory/group_vars/{server_type}_servers.yml"
    with open(config_path) as f:
        vars = yaml.safe_load(f)

    return int(vars["unbound_listen_addresses"][0].split("@")[-1])


@pytest.fixture
def dns_host_ip(host):
    """Get the DNS host IP address from Ansible inventory.

    This fixture provides the host IP address from the Ansible inventory
    (ansible_host variable) as the single source of truth.

    Alternative: Direct access to Ansible variables in tests:
        host_vars = host.ansible.get_variables()
        ip = host_vars["ansible_host"]

    Returns:
        str: The IP address of the DNS host (e.g., "192.168.1.13")
    """
    host_vars = host.ansible.get_variables()

    return host_vars["ansible_host"]
