from __future__ import annotations

from typing import Any, Dict, List, Optional


class ReviewResolver:
    """
    Resolves REVIEW decisions produced by the duplicate checker.

    The resolver does not modify Terraform files.

    It determines whether an existing module can safely satisfy the
    approved module interface.

    Current supported adaptation:

        Approved:
            subnet_id

        Target:
            subnet_ids["subnet1"]

    If exactly one subnet is known, it is selected automatically.

    If multiple subnets are known, user input is required.

    If subnet names cannot be determined, generation remains blocked.
    """

    def resolve(
        self,
        module_name: str,
        duplicate_result: Dict[str, Any],
        target_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        decision = duplicate_result.get("decision")

        if decision != "REVIEW":
            return {
                "module": module_name,
                "status": "NO_REVIEW",
                "resolution": decision,
                "requires_user_input": False,
                "message": "No review resolution is required.",
                "mapping": {},
            }

        compatibility = duplicate_result.get(
            "compatibility",
            {},
        )

        missing_inputs = compatibility.get(
            "missing_inputs",
            [],
        )

        additional_inputs = compatibility.get(
            "additional_inputs",
            [],
        )

        missing_outputs = compatibility.get(
            "missing_outputs",
            [],
        )

        additional_outputs = compatibility.get(
            "additional_outputs",
            [],
        )

        # ------------------------------------------------------------
        # Supported subnet interface adaptation
        # ------------------------------------------------------------

        if self._is_subnet_output_adaptation(
            missing_outputs,
            additional_outputs,
        ):

            return self._resolve_subnet_mapping(
                module_name=module_name,
                target_analysis=target_analysis,
            )

        # ------------------------------------------------------------
        # Unknown REVIEW difference
        # ------------------------------------------------------------

        return {
            "module": module_name,
            "status": "BLOCKED",
            "resolution": "UNRESOLVED_REVIEW",
            "requires_user_input": False,
            "message": (
                f"Module '{module_name}' has interface differences "
                "that cannot currently be resolved safely."
            ),
            "mapping": {},
            "differences": {
                "missing_inputs": missing_inputs,
                "additional_inputs": additional_inputs,
                "missing_outputs": missing_outputs,
                "additional_outputs": additional_outputs,
            },
        }

    # ================================================================
    # SUBNET DETECTION
    # ================================================================

    @staticmethod
    def _is_subnet_output_adaptation(
        missing_outputs: List[str],
        additional_outputs: List[str],
    ) -> bool:

        return (
            "subnet_id" in missing_outputs
            and "subnet_ids" in additional_outputs
        )

    # ================================================================
    # SUBNET RESOLUTION
    # ================================================================

    def _resolve_subnet_mapping(
        self,
        module_name: str,
        target_analysis: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not target_analysis:

            return {
                "module": module_name,
                "status": "BLOCKED",
                "resolution": "SUBNET_INFORMATION_MISSING",
                "requires_user_input": False,
                "message": (
                    "Target subnet information is unavailable. "
                    "The existing VNet cannot be safely adapted."
                ),
                "available_subnets": [],
                "selected_subnet": None,
                "mapping": {},
            }

        subnet_analysis = target_analysis.get(
            "subnets",
            {},
        )

        subnet_names = subnet_analysis.get(
            "names",
            [],
        )

        names_known = subnet_analysis.get(
            "names_known",
            False,
        )

        # ------------------------------------------------------------
        # Subnet names are unknown
        # ------------------------------------------------------------

        if not names_known:

            return {
                "module": module_name,
                "status": "BLOCKED",
                "resolution": "SUBNET_SELECTION_REQUIRED",
                "requires_user_input": True,
                "message": (
                    "The target VNet uses multiple subnets, but their "
                    "names could not be determined from the Terraform "
                    "configuration."
                ),
                "available_subnets": [],
                "selected_subnet": None,
                "mapping": {},
            }

        # ------------------------------------------------------------
        # No subnet found
        # ------------------------------------------------------------

        if not subnet_names:

            return {
                "module": module_name,
                "status": "BLOCKED",
                "resolution": "NO_SUBNET_AVAILABLE",
                "requires_user_input": False,
                "message": (
                    f"No subnet was found in the existing "
                    f"'{module_name}' module."
                ),
                "available_subnets": [],
                "selected_subnet": None,
                "mapping": {},
            }

        # ------------------------------------------------------------
        # Exactly one subnet
        #
        # Safe automatic resolution.
        # ------------------------------------------------------------

        if len(subnet_names) == 1:

            subnet_name = subnet_names[0]

            return {
                "module": module_name,
                "status": "RESOLVED",
                "resolution": "SUBNET_MAPPING",
                "requires_user_input": False,
                "message": (
                    f"The existing VNet contains one subnet "
                    f"('{subnet_name}'). "
                    f"AKS subnet_id will use that subnet."
                ),
                "available_subnets": subnet_names,
                "selected_subnet": subnet_name,
                "mapping": {
                    "subnet_id": (
                        f'module.{module_name}.subnet_ids'
                        f'["{subnet_name}"]'
                    )
                },
            }

        # ------------------------------------------------------------
        # Multiple subnets
        #
        # Never guess.
        # ------------------------------------------------------------

        return {
            "module": module_name,
            "status": "NEEDS_USER_INPUT",
            "resolution": "SUBNET_SELECTION_REQUIRED",
            "requires_user_input": True,
            "message": (
                f"The existing VNet contains multiple subnets. "
                f"Select the subnet that AKS should use."
            ),
            "available_subnets": subnet_names,
            "selected_subnet": None,
            "mapping": {},
        }

    # ================================================================
    # USER SELECTION
    # ================================================================

    def apply_subnet_selection(
        self,
        resolution: Dict[str, Any],
        subnet_name: str,
    ) -> Dict[str, Any]:

        available_subnets = resolution.get(
            "available_subnets",
            [],
        )

        if subnet_name not in available_subnets:

            raise ValueError(
                f"Invalid subnet '{subnet_name}'. "
                f"Available subnets: {available_subnets}"
            )

        module_name = resolution["module"]

        return {
            "module": module_name,
            "status": "RESOLVED",
            "resolution": "SUBNET_MAPPING",
            "requires_user_input": False,
            "message": (
                f"Selected subnet '{subnet_name}' "
                f"for '{module_name}.subnet_id'."
            ),
            "available_subnets": available_subnets,
            "selected_subnet": subnet_name,
            "mapping": {
                "subnet_id": (
                    f'module.{module_name}.subnet_ids'
                    f'["{subnet_name}"]'
                )
            },
        }


def print_resolution(
    result: Dict[str, Any],
) -> None:

    print()
    print("REVIEW RESOLUTION")
    print("=" * 60)

    print(
        f"Module       : "
        f"{result.get('module')}"
    )

    print(
        f"Status       : "
        f"{result.get('status')}"
    )

    print(
        f"Resolution   : "
        f"{result.get('resolution')}"
    )

    print(
        f"User Input   : "
        f"{result.get('requires_user_input')}"
    )

    print(
        f"Message      : "
        f"{result.get('message')}"
    )

    available_subnets = result.get(
        "available_subnets",
        [],
    )

    if available_subnets:

        print()
        print("Available Subnets:")

        for index, subnet in enumerate(
            available_subnets,
            start=1,
        ):
            print(
                f"  {index}. {subnet}"
            )

    selected_subnet = result.get(
        "selected_subnet"
    )

    if selected_subnet:

        print()
        print(
            f"Selected Subnet : "
            f"{selected_subnet}"
        )

    mapping = result.get(
        "mapping",
        {},
    )

    if mapping:

        print()
        print("Resolved Mapping:")

        for key, value in mapping.items():

            print(
                f"  {key} -> {value}"
            )


if __name__ == "__main__":

    # Demonstration using the actual structure
    # discovered by TargetAnalyzer.

    duplicate_result = {
        "decision": "REVIEW",
        "compatibility": {
            "missing_inputs": [
                "subnet_name",
                "subnet_prefixes",
            ],
            "additional_inputs": [
                "subnets",
            ],
            "missing_outputs": [
                "subnet_id",
            ],
            "additional_outputs": [
                "subnet_ids",
                "subnet_prefixes",
                "vnet_name",
            ],
        },
    }

    target_analysis = {
        "subnets": {
            "names": [
                "subnet1",
            ],
            "names_known": True,
            "collection_type": "map",
            "source": "variable.default",
        }
    }

    resolver = ReviewResolver()

    result = resolver.resolve(
        module_name="vnet",
        duplicate_result=duplicate_result,
        target_analysis=target_analysis,
    )

    print_resolution(result)