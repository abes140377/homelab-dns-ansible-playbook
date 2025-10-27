# Dagger

dagger init
dagger develop --sdk=python

dagger -m github.com/abes140377/homelab-daggerverse/ansible call run-playbook --directory . --playbook site.yml

## Problem:
ssh private key as configured in inventory/hosts.yml is not available in build container.
-> no ssh access to remote hosts.

## Solution (maybe):

Create a ansible ssh key in ~/projects/sflab/src/homelab-packer-templates e.g.: ansible_id_ecdsa

```bash
create-ssh-key ansible ansible@sflab.io
''

Create ansible user in `http/ubuntu/user-data.pkrtpl.hcl` with the public key.

Provide the public key either by ssh-copy-id to all remote hosts not cloned from packer template (pi1, bind9-secondary lxc)

Provide the private key content as sops encrypted file in the repository.
Create the key file in the container at ~/.ssh/ansible_id_ecdsa.
We then can use this path on my local machine or in the dagger container as ansible_ssh_private_key_file in inventory/hosts.yml

dagger -m github.com/abes140377/homelab-daggerverse/ansible call run-playbook --directory . --playbook site.yml --ssh-private-key=file:./keys/ansible_id_ecdsa

# dagger -m github.com/abes140377/homelab-daggerverse/ansible \
#   call debug-container --directory . --ssh-private-key=file:./keys/ansible_id_ecdsa terminal
