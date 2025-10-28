"""pytest configuration for testinfra tests."""

import os

import pytest

# Set Ansible inventory path via environment variable to avoid CLI conflicts
os.environ["ANSIBLE_INVENTORY"] = "inventory/hosts.yml"
