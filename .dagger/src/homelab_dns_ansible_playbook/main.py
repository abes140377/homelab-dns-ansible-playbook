import dagger
from dagger import dag, function, object_type


@object_type
class HomelabDnsAnsiblePlaybook:
    @function
    async def ansible_build(
        self,
        directory: dagger.Directory,
        playbook: str = "site.yml",
        inventory: str = "inventory/hosts.yml",
        requirements_file: str = "requirements.yml",
        ssh_private_key: dagger.Secret | None = None,
    ) -> str:
        """
        Runs an Ansible playbook using the remote Ansible module.

        Args:
            directory: The project directory containing the playbook and inventory
            playbook: The name of the playbook file to run (default: site.yml)
            ssh_private_key: SSH private key for Ansible connections

        Returns:
            Output from the Ansible playbook run
        """
        # Use the installed Ansible module dependency
        result = await dag.ansible().run_playbook(
            directory=directory,
            playbook=playbook,
            inventory=inventory,
            requirements_file=requirements_file,
            ssh_private_key=ssh_private_key,
        )

        return result
