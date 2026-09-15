import re


class TerraformParser:

    RESOURCE_TAGS = {
        "azurerm_kubernetes_cluster": [
            "aks",
            "kubernetes",
            "containers"
        ],
        "azurerm_storage_account": [
            "storage",
            "blob",
            "fileshare"
        ],
        "azurerm_virtual_network": [
            "networking",
            "vnet"
        ],
        "azurerm_subnet": [
            "networking",
            "subnet"
        ]
    }

    def _generate_tags(
        self,
        module_name,
        resources,
        variables,
        outputs
    ):

        tags = set()

        tags.add(
            module_name.lower()
        )

        for resource in resources:

            tags.update(
                self.RESOURCE_TAGS.get(
                    resource["type"],
                    []
                )
            )

        for variable in variables:

            name = variable["name"].lower()

            if "subnet" in name:
                tags.add("networking")

            if "vnet" in name:
                tags.add("networking")

            if "storage" in name:
                tags.add("storage")

        for output in outputs:

            name = output["name"].lower()

            if "subnet" in name:
                tags.add("networking")

        return sorted(tags)

    def parse_module(
        self,
        module_name,
        module_path,
        repository_name,
        files
    ):

        resources = []
        inputs = []
        outputs = []

        providers = set()
        terraform_version = None

        readme_text = ""

        for file_name, content in files.items():

            if file_name.lower() == "readme.md":
                readme_text = content

            version_match = re.search(
                r'required_version\s*=\s*"([^"]+)"',
                content
            )

            if version_match:
                terraform_version = version_match.group(1)

            provider_matches = re.findall(
                r'(azurerm|aws|google|kubernetes)\s*=\s*\{',
                content
            )

            providers.update(provider_matches)

            resource_matches = re.findall(
                r'resource\s+"([^"]+)"\s+"([^"]+)"',
                content
            )

            for rtype, rname in resource_matches:
                resources.append(
                    {
                        "type": rtype,
                        "name": rname
                    }
                )

            variable_blocks = re.finditer(
                r'variable\s+"([^"]+)"\s*\{(.*?)\}',
                content,
                re.DOTALL
            )

            for variable in variable_blocks:

                body = variable.group(2)

                description_match = re.search(
                    r'description\s*=\s*"([^"]+)"',
                    body
                )

                required = (
                    "default"
                    not in body
                )

                inputs.append(
                    {
                        "name":
                            variable.group(1),
                        "description":
                            description_match.group(1)
                            if description_match
                            else "",
                        "required":
                            required
                    }
                )

            output_matches = re.findall(
                r'output\s+"([^"]+)"',
                content
            )

            for output_name in output_matches:

                outputs.append(
                    {
                        "name": output_name
                    }
                )

        tags = self._generate_tags(
            module_name,
            resources,
            inputs,
            outputs
        )

        summary = (
            readme_text.splitlines()[0]
            if readme_text.strip()
            else f"Creates {len(resources)} Terraform resource(s)"
        )

        return {
            "name": module_name,
            "path": module_path,
            "repository": repository_name,

            "provider": sorted(
                list(providers)
            ),

            "terraform_version":
                terraform_version,

            "summary": summary,

            "tags": tags,

            "resources": resources,
            "inputs": inputs,
            "outputs": outputs,

            "dependencies": [],

            "files": list(files.keys())
        }