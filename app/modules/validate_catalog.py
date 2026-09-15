import json


class CatalogValidator:

    def validate(
        self,
        path="catalog/modules.json"
    ):

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            catalog = json.load(file)

        root_fields = [
            "catalog_version",
            "repository_name",
            "branch_name",
            "module_count",
            "dependency_count",
            "generated_at",
            "modules"
        ]

        for field in root_fields:

            if field not in catalog:

                raise ValueError(
                    f"Missing field: {field}"
                )

        module_fields = [
            "name",
            "path",
            "repository",
            "provider",
            "terraform_version",
            "resources",
            "inputs",
            "outputs",
            "dependencies",
            "files"
        ]

        for module in catalog["modules"]:

            for field in module_fields:

                if field not in module:

                    raise ValueError(
                        f"Missing module field: {field}"
                    )

        print(
            f"Catalog validation successful"
        )

        return True