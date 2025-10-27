# Dagger Integration Guide

This document describes how Dagger is integrated into this Ansible playbook project.

## Overview

Dagger provides containerized, reproducible execution of Ansible playbooks. The project uses:
- **Dagger version**: 0.19.3 (managed via mise)
- **SDK**: Python
- **Module location**: `.dagger/`
- **Dependencies**: `ansible` module from `github.com/abes140377/homelab-daggerverse/ansible`

## Initial Setup

Dagger was initialized with the following commands:

```bash
# Initialize Dagger with Python SDK
dagger init --sdk=python

# Install the remote Ansible module as a dependency
dagger install github.com/abes140377/homelab-daggerverse/ansible
```

This created:
- `dagger.json` - Module configuration and dependencies
- `.dagger/` - Python module source code
- `.dagger/src/homelab_dns_ansible_playbook/main.py` - Main Dagger functions

## Configuration

### dagger.json

The module configuration declares the Ansible dependency:

```json
{
  "name": "homelab-dns-ansible-playbook",
  "engineVersion": "v0.19.3",
  "sdk": {
    "source": "python"
  },
  "dependencies": [
    {
      "name": "ansible",
      "source": "github.com/abes140377/homelab-daggerverse/ansible@main",
      "pin": "0b025304ae0c0e62329858628feb470e3487d6a2"
    }
  ],
  "source": ".dagger"
}
```

### mise.toml

Dagger is managed as a mise tool and includes task shortcuts:

```toml
[tools]
dagger = "0.19.3"

[tasks."dagger:ansible-build"]
description = "Run Ansible playbook using local Dagger function"
run = '''
dagger call ansible-build \
  --playbook site.yml \
  --ssh-private-key=file:./keys/ansible_id_ecdsa
'''
```

## Available Functions

### ansible-build

Runs an Ansible playbook in a containerized environment with proper SSH key handling.

**Usage:**

```bash
# Direct dagger call
dagger call ansible-build \
  --playbook site.yml \
  --ssh-private-key=file:./keys/ansible_id_ecdsa

# Via mise task (recommended)
mise run dagger:ansible-build
```

**Parameters:**
- `--playbook` (string): Name of the playbook file to run (default: `site.yml`)
- `--ssh-private-key` (Secret): SSH private key for connecting to remote hosts
  - Use `file:./path/to/key` syntax to load from file
  - The key is securely mounted as a Dagger secret

**Example with custom playbook:**

```bash
dagger call ansible-build \
  --playbook argspec_validation_plays.yml \
  --ssh-private-key=file:./keys/ansible_id_ecdsa
```

### galaxy-install

Installs Ansible Galaxy collections from a requirements file into a container.

**Usage:**

```bash
# Direct dagger call
dagger call galaxy-install \
  --directory . \
  --requirements-file collections/requirements.yml

# Via mise task (recommended)
mise run dagger:galaxy-install
```

**Parameters:**
- `--directory` (Directory): Directory containing the requirements file (required)
- `--requirements-file` (string): Path to the requirements file (default: `requirements.yml`)

**Returns:**
A container with the collections installed. This can be further chained with other Dagger operations.

**Example usage:**

```bash
# Install collections and inspect the container
dagger call galaxy-install \
  --directory . \
  --requirements-file collections/requirements.yml \
  stdout
```

## SSH Key Management

The Ansible playbook requires SSH access to remote hosts. The SSH key workflow:

1. **Key creation**: SSH key `ansible_id_ecdsa` is stored in `keys/` directory
2. **Environment setup**: mise hooks populate the key from `ANSIBLE_SSH_PRIVATE_KEY` env var
3. **Dagger secret**: The key is passed to Dagger as a secret (never exposed in logs)
4. **Remote access**: Dagger mounts the secret in the container for Ansible to use

**Key file locations:**
- Private key: `./keys/ansible_id_ecdsa` (git-ignored)
- Public key: `./keys/ansible_id_ecdsa.pub`
- Environment variable: `ANSIBLE_SSH_PRIVATE_KEY` (set in `.creds.env.yaml`)

## Development

### Listing Available Functions

```bash
dagger functions
```

### Updating the Ansible Dependency

When a new version of the remote Ansible module is available:

```bash
# Update to latest version from main branch
dagger install github.com/abes140377/homelab-daggerverse/ansible

# Verify the update
git diff dagger.json

# Check available functions
dagger functions

# Test the updated module directly
dagger -m github.com/abes140377/homelab-daggerverse/ansible functions
```

The `dagger.json` file will be updated with a new commit pin, ensuring reproducible builds.

**What gets updated:**
- Commit pin in `dagger.json` dependencies section
- Access to new functions from the remote module
- Bug fixes and improvements from upstream

### Adding New Functions

Edit `.dagger/src/homelab_dns_ansible_playbook/main.py`:

```python
@function
async def my_new_function(self, arg: str) -> str:
    """Description of the function"""
    # Function implementation
    return result
```

### Testing Changes

```bash
# Validate module configuration
dagger develop

# Test function execution
dagger call my-new-function --arg "test"
```

## Troubleshooting

### "command not found: dagger"

Ensure mise is properly set up:

```bash
mise install
```

### SSH Connection Issues

Verify the SSH key is properly configured:

```bash
# Check key exists
ls -la ./keys/ansible_id_ecdsa

# Test SSH connection manually
ssh -i ./keys/ansible_id_ecdsa seba@192.168.1.13 (Pi1 Primary)
ssh -i ./keys/ansible_id_ecdsa seba@192.168.1.13 (bind9-secondary LXC secondary)
```

### Module Loading Errors

Re-generate the Dagger SDK:

```bash
dagger develop
```

### Dependency Update Needed

Check and update the pinned version:

```bash
dagger install github.com/abes140377/homelab-daggerverse/ansible
git diff dagger.json  # Review changes
```

## Best Practices

1. **Always use mise tasks** for consistent execution environment
2. **Pin dependency versions** in production (already done in `dagger.json`)
3. **Keep secrets in environment variables** (never commit to git)
4. **Test locally first** before running against production hosts
5. **Update dependencies regularly** to get latest features and fixes:
   ```bash
   dagger install github.com/abes140377/homelab-daggerverse/ansible
   ```
6. **Use `--check` mode** for dry runs:
   ```bash
   # Note: Need to extend ansible-build to support check mode
   ansible-playbook site.yml --check
   ```

## Changelog

### Latest Update
- **Updated dependency**: Ansible module pin updated to latest commit
- **Documentation**: Added comprehensive update instructions

## References

- [Dagger Documentation](https://docs.dagger.io)
- [Dagger Python SDK](https://docs.dagger.io/sdk/python)
- [Homelab Daggerverse Ansible Module](https://github.com/abes140377/homelab-daggerverse/tree/main/ansible)
- [Project CLAUDE.md](../CLAUDE.md#dagger-integration)
