from typing import Any, Dict, Optional

from app.modules.ai_planner import AIPlanner
from app.modules.selector import AISelector
from app.modules.dependency_resolver import DependencyResolver
from app.generation.plan import GenerationPlanner


class ChatService:
    """Orchestrate AI planning, selection, dependency resolution and generation planning."""

    def __init__(self) -> None:
        self.planner = AIPlanner()
        self.selector = AISelector()
        self.resolver = DependencyResolver()

    def process(
        self,
        requirement: str,
        target_repository: Optional[str] = None,
        target_branch: Optional[str] = None,
        infrastructure_decisions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        plan = self.planner.create_plan(requirement)
        selection = self.selector.select_primary_and_supporting(plan)
        recommendations = selection["recommendations"]
        selected_modules = selection["selected_modules"]

        resolver_order = self.resolver.resolve(
            selected_modules,
            plan,
        )

        generation_planner = GenerationPlanner(
            target_repository=target_repository,
            target_branch=target_branch,
        )

        generation_plan = generation_planner.build(
            selected_modules=selected_modules,
            infrastructure_decisions=infrastructure_decisions or {},
        )

        final_order = (
            generation_plan.get("generation_order")
            or resolver_order
        )

        return {
            "requirement": requirement,
            "plan": plan,
            "recommended_modules": recommendations,
            "selected_modules": selected_modules,
            "deployment_order": final_order,
            "generation_plan": generation_plan,
        }


def main() -> None:
    requirement = input("Enter infrastructure requirement: ").strip()
    if not requirement:
        return

    result = ChatService().process(requirement)
    GenerationPlanner.print_plan(result["generation_plan"])


if __name__ == "__main__":
    main()