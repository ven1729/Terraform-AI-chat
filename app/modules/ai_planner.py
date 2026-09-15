import json
import re

from app.llm.client import LLMClient


class AIPlanner:
    """Converts natural-language infrastructure requests into a plan."""

    def __init__(self):
        self.llm = LLMClient()

    def create_plan(self, requirement: str):
        if not requirement or not requirement.strip():
            raise ValueError("Infrastructure requirement cannot be empty")

        system_prompt = """
You are a Terraform Infrastructure Planner.

Analyze the user's infrastructure request and return ONLY valid JSON.

Use this exact structure:

{
  "intent": "create_infrastructure",
  "primary_services": [],
  "supporting_services": [],
  "requirements": {
    "environment": null,
    "location": null,
    "private": null
  }
}

Rules:
1. primary_services contains the main infrastructure requested.
2. supporting_services contains explicitly requested supporting infrastructure.
3. Use the module vocabulary only when it is clearly supported by the request:
   - AKS / Kubernetes cluster -> aks
   - Azure Storage Account / storage -> storage
   - Azure Virtual Network / VNet / networking -> vnet
   - Key Vault -> keyvault
   - Log Analytics -> log-analytics
4. Do not invent services that the user did not request.
5. Extract environment only if the user specifies it.
6. Extract Azure location only if the user specifies it.
7. Set private to true only when the user explicitly requests private networking/private cluster/private access.
8. Otherwise use null.
9. Do not generate Terraform code.
10. Return JSON only.
"""

        response = self.llm.invoke(
            system_prompt,
            requirement
        )

        match = re.search(
            r"\{.*\}",
            response,
            re.DOTALL
        )

        if not match:
            raise ValueError(
                f"No JSON found in planner response: {response}"
            )

        try:
            plan = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Planner returned invalid JSON: {response}"
            ) from exc

        self._validate_plan(plan)
        return plan

    def _validate_plan(self, plan):
        required = [
            "intent",
            "primary_services",
            "supporting_services",
            "requirements",
        ]

        for field in required:
            if field not in plan:
                raise ValueError(
                    f"Planner response missing field: {field}"
                )

        if not isinstance(plan["primary_services"], list):
            raise ValueError("primary_services must be a list")

        if not isinstance(plan["supporting_services"], list):
            raise ValueError("supporting_services must be a list")

        if not isinstance(plan["requirements"], dict):
            raise ValueError("requirements must be an object")
