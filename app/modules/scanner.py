from typing import Any, Dict, List

from app.github_client.client import GitHubClient
from app.modules.parser import TerraformParser


class ModuleScanner:
    """
    Compatibility scanner for the older module-catalog workflow.

    It no longer assumes `modules/<name>/`. It discovers Terraform
    directories anywhere in the selected branch and parses the .tf files
    directly found in each directory.
    """

    def __init__(self, repository_name: str, branch_name: str):
        self.repository_name = repository_name
        self.branch_name = branch_name
        self.github = GitHubClient()
        self.parser = TerraformParser()

    def get_modules(self):
        inventory = self.github.scan_terraform_branch(
            self.repository_name,
            self.branch_name,
        )

        class ModuleEntry:
            def __init__(self, name: str, path: str, terraform_files: List[str]):
                self.name = name
                self.path = path
                self.terraform_files = terraform_files

        return [
            ModuleEntry(
                item["name"],
                item["path"],
                item.get("terraform_files", []),
            )
            for item in inventory.get("modules", [])
        ]

    def scan(self) -> List[Dict[str, Any]]:
        modules_catalog: List[Dict[str, Any]] = []
        modules = self.get_modules()

        for module in modules:
            module_files: Dict[str, str] = {}

            contents = self.github.get_contents(
                self.repository_name,
                module.path,
                self.branch_name,
            )
            if not isinstance(contents, list):
                contents = [contents]

            for file in contents:
                if getattr(file, "type", None) != "file":
                    continue
                if not str(getattr(file, "name", "")).lower().endswith(".tf"):
                    continue

                module_files[file.name] = self.github.get_file_content(
                    self.repository_name,
                    file.path,
                    self.branch_name,
                )

            parsed_module = self.parser.parse_module(
                module_name=module.name,
                module_path=module.path,
                repository_name=self.repository_name,
                files=module_files,
            )
            modules_catalog.append(parsed_module)

        return modules_catalog

    def build_dependency_map(self, modules):
        output_index = {}
        for module in modules:
            for output in module.get("outputs", []):
                output_name = output.get("name")
                if output_name:
                    output_index[output_name] = module["name"]

        dependency_count = 0
        for module in modules:
            module_dependencies = []
            for module_input in module.get("inputs", []):
                variable_name = module_input.get("name")
                if variable_name in output_index:
                    dependency = {
                        "module": output_index[variable_name],
                        "input": variable_name,
                    }
                    module_dependencies.append(dependency)
                    dependency_count += 1
            module["dependencies"] = module_dependencies

        return {
            "modules": modules,
            "dependency_count": dependency_count,
        }


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    repository = os.getenv("TARGET_REPO")
    branch = os.getenv("TARGET_BRANCH", "main")

    if not repository:
        raise ValueError("TARGET_REPO is not configured")

    scanner = ModuleScanner(repository, branch)
    result = scanner.scan()
    print(f"Discovered {len(result)} Terraform directories")