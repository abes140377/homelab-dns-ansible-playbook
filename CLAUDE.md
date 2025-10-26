# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ansible playbook project for managing homelab DNS infrastructure. The project follows Ansible's playbook project pattern (as opposed to a collection project intended for distribution). It uses a custom collection `homelab.dns` that lives locally in `collections/ansible_collections/homelab/dns/`.

## Architecture

**Project Type**: Playbook project with co-located collection
- Main playbook: `site.yml` - applies `homelab.dns.install` role to all hosts
- Collection namespace: `homelab.dns`
- Current role: `install` (placeholder with debug tasks)

**Inventory Structure**:
- Primary inventory: `inventory/hosts.yml`
- Host groups: `primary_servers` (dns1), `secondary_servers` (dns2)
- Host-specific vars: `inventory/host_vars/{dns1,dns2}.yml`
- Group vars: `inventory/group_vars/{all,primary_servers,secondary_servers}.yml`

**Key Files**:
- `ansible.cfg`: Configures inventory path, verbosity=2, remote_user, timeout settings
- `ansible-navigator.yml`: Debug logging to `.logs/` directory, enables playbook artifacts
- `.pre-commit-config.yaml`: Runs gitleaks and basic file checks
- `mise.toml`: Project automation using mise, manages Python virtual environment with uv
- `AGENTS.md`: References official Ansible agent guidelines (must follow practices from ansible-creator docs)

## Development Commands

### Environment Setup
```bash
# Mise handles environment setup automatically on directory entry
# Manually trigger if needed:
mise install
mise run install-deps
```

This installs:
- Python dependencies via uv (ansible-dev-tools~=25.9)
- Pre-commit hooks (gitleaks, end-of-file-fixer, trailing-whitespace)

### Running Playbooks
```bash
# Run main playbook against all hosts
ansible-playbook site.yml

# Run with specific inventory
ansible-playbook site.yml -i inventory/hosts.yml

# Limit to specific host/group
ansible-playbook site.yml --limit dns1
ansible-playbook site.yml --limit primary_servers

# Check mode (dry run)
ansible-playbook site.yml --check

# With ansible-navigator (generates artifacts in .logs/)
ansible-navigator run site.yml
```

### Argument Specification Validation
```bash
# Example playbook demonstrating play-level argument validation
ansible-playbook argspec_validation_plays.yml \
  -e message=hello \
  -i inventory/argspec_validation_inventory.yml
```

### Linting & Validation
```bash
# Lint all Ansible content (requires ansible-lint from ansible-dev-tools)
ansible-lint

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Testing Individual Roles
```bash
# Navigate to role directory
cd collections/ansible_collections/homelab/dns/roles/install

# Test role tasks
ansible-playbook -i localhost, -c local tests/test.yml
```

## Ansible Best Practices (per AGENTS.md)

### Code Structure
- **Always use FQCN** (Fully Qualified Collection Names): `ansible.builtin.debug`, not `debug`
- **Playbooks should be minimal**: Just list roles in the `roles` section, avoid mixing `tasks` and `roles`
- **Roles follow functional naming**: Focus on outcome (e.g., "install") not implementation details
- **Use `argument_specs.yml`** in roles to define input contracts

### Variable Management
- **Precedence**: defaults → inventory → facts → role vars → scoped vars → runtime → extra_vars
- **Avoid playbook-level vars**: Use inventory instead
- **Group vars file naming**: Match role names (e.g., `install.yml`) or use `ansible.yml` for cross-cutting config
- **Internal variables**: Prefix with `__double_underscore` to signal implementation details

### Task Writing
- **Idempotency is mandatory**: Second runs must produce no changes
- **Support check mode**: Tasks should report expected changes without executing
- **Task names**: Imperative form with capital letters (e.g., "Install DNS server")
- **Prefer specific modules**: Use `ansible.builtin.copy` over `command`/`shell`
- **Always set `changed_when`** when using `command` or `shell`

### YAML Formatting
- 2-space indentation
- Boolean literals: `true`/`false` (not `yes`/`no`)
- Double quotes for strings
- Max ~160 characters per line
- Trailing newline required

### Role Design
- Keep entry point (`tasks/main.yml`) minimal, delegate to discrete task files
- Separate defaults (`defaults/main.yml`) from vars (`vars/main.yml`)
- Platform-specific variables in `vars/` with conditional includes
- Templates must include `ansible_managed` headers

### Testing & Validation
- All code must pass ansible-lint before committing
- Use Molecule for role testing across platforms
- Write integration tests for complete workflows
- Check mode must be supported and tested

## Project-Specific Notes

- **Default remote user**: `myuser` (set in ansible.cfg)
- **SSH keys**: Configured per-host in inventory
- **Logging**: ansible-navigator logs to `.logs/ansible-navigator.log`
- **Credentials**: `.creds.env.yaml` is git-ignored, loaded by mise (redacted in output)
- **Python**: Project uses uv for fast dependency management, auto-creates venv
- **Collection version**: Currently 0.0.1, update in `collections/ansible_collections/homelab/dns/galaxy.yml`
