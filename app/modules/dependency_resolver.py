from app.modules.catalog import ModuleCatalog


class DependencyResolver:
    """
    Resolves explicit module dependencies from modules.json.

    Also respects the AI plan:
        supporting modules -> primary modules

    Important:
    Supporting-service ordering is NOT treated as a Terraform
    dependency unless modules.json explicitly declares one.
    """

    def __init__(self):
        self.catalog = ModuleCatalog()

    def resolve(self, selected_modules, plan=None):

        if not selected_modules:
            return []

        plan = plan or {}

        primary_services = {
            str(service).lower()
            for service in plan.get(
                "primary_services",
                []
            )
        }

        supporting_services = {
            str(service).lower()
            for service in plan.get(
                "supporting_services",
                []
            )
        }

        # -----------------------------------------------------
        # Build selected module names
        # -----------------------------------------------------

        selected_names = []

        for item in selected_modules:

            name = item.get("module")

            if name and name.lower() not in selected_names:
                selected_names.append(
                    name.lower()
                )

        # -----------------------------------------------------
        # Resolve explicit dependencies
        # -----------------------------------------------------

        ordered = []

        visited = set()
        visiting = set()

        def visit(module_name):

            module_name = module_name.lower()

            if module_name in visited:
                return

            if module_name in visiting:

                raise ValueError(
                    "Circular dependency detected involving "
                    f"module '{module_name}'"
                )

            module = self.catalog.get_module(
                module_name
            )

            if not module:

                raise ValueError(
                    f"Module '{module_name}' "
                    "was not found in modules.json"
                )

            visiting.add(
                module_name
            )

            # -------------------------------------------------
            # REAL Terraform dependencies
            # -------------------------------------------------

            for dependency in module.get(
                "dependencies",
                []
            ):

                dependency_name = (
                    self._get_dependency_name(
                        dependency
                    )
                )

                if dependency_name:

                    visit(
                        dependency_name
                    )

            visiting.remove(
                module_name
            )

            visited.add(
                module_name
            )

            ordered.append(
                module_name
            )

        # -----------------------------------------------------
        # First resolve supporting modules
        # -----------------------------------------------------

        for item in selected_modules:

            module_name = item.get(
                "module"
            )

            if not module_name:
                continue

            normalized = module_name.lower()

            if (
                normalized in supporting_services
                or item.get("selection_type")
                == "supporting"
            ):

                visit(
                    normalized
                )

        # -----------------------------------------------------
        # Then resolve primary modules
        # -----------------------------------------------------

        for item in selected_modules:

            module_name = item.get(
                "module"
            )

            if not module_name:
                continue

            normalized = module_name.lower()

            if (
                normalized in primary_services
                or item.get("selection_type")
                == "primary"
            ):

                visit(
                    normalized
                )

        # -----------------------------------------------------
        # Finally handle anything not classified
        # -----------------------------------------------------

        for item in selected_modules:

            module_name = item.get(
                "module"
            )

            if not module_name:
                continue

            visit(
                module_name.lower()
            )

        return ordered

    @staticmethod
    def _get_dependency_name(
        dependency
    ):

        if isinstance(
            dependency,
            str
        ):
            return dependency

        if isinstance(
            dependency,
            dict
        ):

            return (
                dependency.get("module")
                or dependency.get("name")
            )

        return None