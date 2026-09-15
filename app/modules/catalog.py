import json
from pathlib import Path


class ModuleCatalog:

    def __init__(
        self,
        catalog_file: str = "catalog/modules.json"
    ):

        self.catalog_file = Path(
            catalog_file
        )

        if not self.catalog_file.exists():

            raise FileNotFoundError(
                f"Catalog file not found: "
                f"{self.catalog_file}"
            )

        with open(
            self.catalog_file,
            "r",
            encoding="utf-8"
        ) as file:

            self.catalog = json.load(
                file
            )

    # --------------------------------------------------
    # Catalog Metadata
    # --------------------------------------------------

    def get_catalog_version(self):

        return self.catalog.get(
            "catalog_version"
        )

    def get_repository_name(self):

        return self.catalog.get(
            "repository_name"
        )

    def get_branch_name(self):

        return self.catalog.get(
            "branch_name"
        )

    def get_module_count(self):

        return self.catalog.get(
            "module_count",
            0
        )

    def get_dependency_count(self):

        return self.catalog.get(
            "dependency_count",
            0
        )

    def get_generated_at(self):

        return self.catalog.get(
            "generated_at"
        )

    # --------------------------------------------------
    # Module Collection
    # --------------------------------------------------

    def get_all_modules(self):

        return self.catalog.get(
            "modules",
            []
        )

    def list_modules(self):

        return [
            module["name"]
            for module in self.get_all_modules()
        ]

    def module_exists(
        self,
        module_name: str
    ):

        return (
            self.get_module(
                module_name
            )
            is not None
        )

    # --------------------------------------------------
    # Module Lookup
    # --------------------------------------------------

    def get_module(
        self,
        module_name: str
    ):

        for module in (
            self.get_all_modules()
        ):

            if (
                module["name"]
                .lower()
                ==
                module_name.lower()
            ):

                return module

        return None

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------

    def get_module_path(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return None

        return module.get(
            "path"
        )

    def get_module_repository(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return None

        return module.get(
            "repository"
        )

    # --------------------------------------------------
    # Terraform Compatibility
    # --------------------------------------------------

    def get_provider(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return []

        return module.get(
            "provider",
            []
        )

    def get_terraform_version(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return None

        return module.get(
            "terraform_version"
        )

    # --------------------------------------------------
    # Retrieval Metadata
    # --------------------------------------------------

    def get_summary(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return ""

        return module.get(
            "summary",
            ""
        )

    def get_tags(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return []

        return module.get(
            "tags",
            []
        )

    # --------------------------------------------------
    # Resources
    # --------------------------------------------------

    def get_resources(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return []

        return module.get(
            "resources",
            []
        )

    # --------------------------------------------------
    # Inputs
    # --------------------------------------------------

    def get_inputs(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return []

        return module.get(
            "inputs",
            []
        )

    # --------------------------------------------------
    # Outputs
    # --------------------------------------------------

    def get_outputs(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return []

        return module.get(
            "outputs",
            []
        )

    # --------------------------------------------------
    # Dependencies
    # --------------------------------------------------

    def get_dependencies(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return []

        return module.get(
            "dependencies",
            []
        )

    # --------------------------------------------------
    # Source Files
    # --------------------------------------------------

    def get_files(
        self,
        module_name: str
    ):

        module = self.get_module(
            module_name
        )

        if not module:
            return []

        return module.get(
            "files",
            []
        )

    # --------------------------------------------------
    # Search Helpers
    # --------------------------------------------------

    def find_modules_by_tag(
        self,
        tag: str
    ):

        matches = []

        for module in (
            self.get_all_modules()
        ):

            if tag.lower() in [

                t.lower()

                for t in module.get(
                    "tags",
                    []
                )
            ]:

                matches.append(
                    module
                )

        return matches

    def find_modules_by_resource(
        self,
        resource_type: str
    ):

        matches = []

        for module in (
            self.get_all_modules()
        ):

            for resource in module.get(
                "resources",
                []
            ):

                if (
                    resource.get("type")
                    ==
                    resource_type
                ):

                    matches.append(
                        module
                    )

                    break

        return matches

    # --------------------------------------------------
    # AI Helper
    # --------------------------------------------------

    def get_catalog_summary(self):

        return {
            "repository_name":
                self.get_repository_name(),

            "branch_name":
                self.get_branch_name(),

            "module_count":
                self.get_module_count(),

            "dependency_count":
                self.get_dependency_count(),

            "generated_at":
                self.get_generated_at()
        }