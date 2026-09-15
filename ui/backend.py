from typing import Any, Dict, List, Optional

from app.chat.chat_service import ChatService
from app.generation.generator import TerraformGenerator
from app.generation.plan import GenerationPlanner
from app.github_client.client import GitHubClient
from app.modules.catalog import ModuleCatalog
from app.target.analyzer import TargetRepositoryAnalyzer


class CopilotBackend:
    """Application service layer for Streamlit and future UIs."""

    def __init__(self) -> None:
        self.chat_service = ChatService()
        self.github = GitHubClient()
        self.catalog = ModuleCatalog()

    # =========================================================
    # GITHUB DISCOVERY
    # =========================================================

    def list_target_repositories(self) -> List[Dict[str, Any]]:
        return self.github.list_repositories(writable_only=True)

    def list_target_branches(self, repository: str) -> List[Dict[str, Any]]:
        return self.github.list_branches(repository)

    def inspect_target_modules(
        self,
        repository: str,
        branch: str,
    ) -> Dict[str, Any]:
        """
        Analyze the complete selected branch.

        This is intentionally not a `modules/` scan. Root-level Terraform
        and Terraform under arbitrary directories are both analyzed.
        """
        inventory = TargetRepositoryAnalyzer(
            repository_name=repository,
            branch_name=branch,
        ).analyze()

        module_calls = list(inventory.get("modules", []))

        approved_names = {
            str(module.get("name", "")).lower()
            for module in self.catalog.get_all_modules()
            if isinstance(module, dict)
        }

        enriched_modules = []
        for module in inventory.get("module_directories", []):
            name = str(module.get("name", ""))
            enriched_modules.append(
                {
                    **module,
                    "approved": name.lower() in approved_names,
                    "status": (
                        "APPROVED CATALOG NAME"
                        if name.lower() in approved_names
                        else "EXISTING TERRAFORM DIRECTORY"
                    ),
                }
            )

        inventory["modules"] = enriched_modules
        inventory["module_calls"] = module_calls
        inventory["approved_module_calls"] = [
            call
            for call in module_calls
            if str(call.get("name", "")).lower() in approved_names
        ]
        inventory["module_count"] = len(enriched_modules)
        inventory["approved_module_count"] = sum(
            1 for module in enriched_modules if module["approved"]
        )
        inventory["unmanaged_module_count"] = sum(
            1 for module in enriched_modules if not module["approved"]
        )
        inventory["resource_types"] = sorted(
            {
                str(resource.get("type"))
                for resource in inventory.get("resources", [])
                if resource.get("type")
            },
            key=str.lower,
        )

        return inventory

    # =========================================================
    # COPILOT WORKFLOW
    # =========================================================

    def process_request(
        self,
        requirement: str,
        target_repository: Optional[str] = None,
        target_branch: Optional[str] = None,
        infrastructure_decisions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        requirement = requirement.strip()
        if not requirement:
            raise ValueError("Infrastructure requirement cannot be empty.")
        if not target_repository:
            raise ValueError("Target repository must be selected.")
        if not target_branch:
            raise ValueError("Target branch must be selected.")

        return self.chat_service.process(
            requirement,
            target_repository=target_repository,
            target_branch=target_branch,
            infrastructure_decisions=infrastructure_decisions or {},
        )

    def get_variable_schema(self, generation_plan: Dict[str, Any]):
        planner = GenerationPlanner(
            target_repository=generation_plan.get("repository"),
            target_branch=generation_plan.get("branch"),
        )
        return planner.get_variable_schema(generation_plan)

    def validate_working_branch(
        self,
        repository: str,
        branch: str,
    ) -> Dict[str, Any]:
        return self.github.validate_new_branch_name(repository, branch)

    def publish_to_github(
        self,
        generation_plan: Dict[str, Any],
        working_branch: str,
    ) -> Dict[str, Any]:
        generator = TerraformGenerator(
            target_repository=generation_plan.get("repository"),
            target_branch=generation_plan.get("branch"),
        )
        return generator.publish_to_github(
            generation_plan,
            working_branch=working_branch,
        )

    def generate_terraform(
        self,
        generation_plan: Dict[str, Any],
        variable_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        generator = TerraformGenerator(
            target_repository=generation_plan.get("repository"),
            target_branch=generation_plan.get("branch"),
        )
        return generator.generate(
            generation_plan,
            variable_values=variable_values or {},
        )


_backend = CopilotBackend()


def process_request(
    requirement: str,
    target_repository: Optional[str] = None,
    target_branch: Optional[str] = None,
    infrastructure_decisions: Optional[Dict[str, str]] = None,
):
    return _backend.process_request(
        requirement,
        target_repository,
        target_branch,
        infrastructure_decisions,
    )


def list_target_repositories():
    return _backend.list_target_repositories()


def list_target_branches(repository: str):
    return _backend.list_target_branches(repository)


def inspect_target_modules(repository: str, branch: str):
    return _backend.inspect_target_modules(repository, branch)


def generate_terraform(
    generation_plan: Dict[str, Any],
    variable_values: Optional[Dict[str, Any]] = None,
):
    return _backend.generate_terraform(generation_plan, variable_values)


def validate_working_branch(repository: str, branch: str):
    return _backend.validate_working_branch(repository, branch)


def publish_to_github(generation_plan: Dict[str, Any], working_branch: str):
    return _backend.publish_to_github(generation_plan, working_branch)


if __name__ == "__main__":
    for repository in list_target_repositories():
        print(repository["full_name"])