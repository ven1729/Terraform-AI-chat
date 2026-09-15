import os
from typing import Any, Dict, List, Set

from dotenv import load_dotenv

from app.modules.catalog import ModuleCatalog
from app.target.analyzer import TargetRepositoryAnalyzer


class DuplicateChecker:
    """
    Compare approved Terraform modules against Terraform already present
    anywhere in the selected target branch.

    Decisions:
        CREATE - no equivalent implementation exists
        REUSE  - an existing module call exists, or a compatible directory
                 implementation exists
        REVIEW - matching infrastructure exists but cannot safely be
                 treated as the approved module
    """

    def __init__(self):
        load_dotenv()
        self.catalog = ModuleCatalog()
        self.repository_name = os.getenv("TARGET_REPO") or ""
        self.analyzer = TargetRepositoryAnalyzer(self.repository_name)

    @staticmethod
    def _normalize(value: Any) -> str:
        if value is None:
            return ""
        value = str(value).strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        return value.replace("\\", "/")

    def _resource_types_from_catalog(self, module: Dict[str, Any]) -> Set[str]:
        result = set()
        for resource in module.get("resources", []):
            if isinstance(resource, str):
                value = resource
            elif isinstance(resource, dict):
                value = (
                    resource.get("type")
                    or resource.get("resource_type")
                    or resource.get("name")
                )
            else:
                continue
            if value:
                result.add(self._normalize(value))
        return result

    def _input_names_from_catalog(self, module: Dict[str, Any]) -> Set[str]:
        result = set()
        for item in module.get("inputs") or module.get("variables") or []:
            if isinstance(item, str):
                value = item
            elif isinstance(item, dict):
                value = item.get("name")
            else:
                continue
            if value:
                result.add(self._normalize(value))
        return result

    def _output_names_from_catalog(self, module: Dict[str, Any]) -> Set[str]:
        result = set()
        for item in module.get("outputs", []):
            if isinstance(item, str):
                value = item
            elif isinstance(item, dict):
                value = item.get("name")
            else:
                continue
            if value:
                result.add(self._normalize(value))
        return result

    @staticmethod
    def _path_matches_directory(file_path: str, directory: str) -> bool:
        file_path = str(file_path or "").strip().strip("/").replace("\\", "/")
        directory = str(directory or "").strip().strip("/").replace("\\", "/")
        if not directory:
            return False
        return file_path == directory or file_path.startswith(directory + "/")

    def _target_module_resources(
        self,
        module_name: str,
        analysis: Dict[str, Any],
    ) -> Set[str]:
        """Get resources from the actual discovered directory for module_name."""
        matching = [
            item
            for item in analysis.get("module_directories", [])
            if self._normalize(item.get("name")).lower() == module_name.lower()
        ]

        if not matching:
            return set()

        result = set()
        for directory in matching:
            directory_path = directory.get("path", "")
            for resource in analysis.get("resources", []):
                path = resource.get("path") or resource.get("file") or ""
                if self._path_matches_directory(path, directory_path):
                    resource_type = resource.get("type")
                    if resource_type:
                        result.add(self._normalize(resource_type))
        return result

    def _target_module_variables(
        self,
        module_name: str,
        analysis: Dict[str, Any],
    ) -> Set[str]:
        matching = [
            item
            for item in analysis.get("module_directories", [])
            if self._normalize(item.get("name")).lower() == module_name.lower()
        ]
        if not matching:
            return set()

        result = set()
        for directory in matching:
            directory_path = directory.get("path", "")
            for variable in analysis.get("variables", []):
                path = variable.get("path") or variable.get("file") or ""
                if self._path_matches_directory(path, directory_path):
                    name = variable.get("name")
                    if name:
                        result.add(self._normalize(name))
        return result

    def _target_module_outputs(
        self,
        module_name: str,
        analysis: Dict[str, Any],
    ) -> Set[str]:
        matching = [
            item
            for item in analysis.get("module_directories", [])
            if self._normalize(item.get("name")).lower() == module_name.lower()
        ]
        if not matching:
            return set()

        result = set()
        for directory in matching:
            directory_path = directory.get("path", "")
            for output in analysis.get("outputs", []):
                path = output.get("path") or output.get("file") or ""
                if self._path_matches_directory(path, directory_path):
                    name = output.get("name")
                    if name:
                        result.add(self._normalize(name))
        return result

    def _check_module_compatibility(
        self,
        module: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        module_name = self._normalize(module.get("name"))
        approved_resources = self._resource_types_from_catalog(module)
        target_resources = self._target_module_resources(module_name, analysis)
        approved_inputs = self._input_names_from_catalog(module)
        target_inputs = self._target_module_variables(module_name, analysis)
        approved_outputs = self._output_names_from_catalog(module)
        target_outputs = self._target_module_outputs(module_name, analysis)

        resource_match = not approved_resources or approved_resources == target_resources
        input_match = not approved_inputs or approved_inputs.issubset(target_inputs)
        output_match = not approved_outputs or approved_outputs.issubset(target_outputs)

        differences = []
        missing_resources = approved_resources - target_resources
        additional_resources = target_resources - approved_resources
        missing_inputs = approved_inputs - target_inputs
        additional_inputs = target_inputs - approved_inputs
        missing_outputs = approved_outputs - target_outputs
        additional_outputs = target_outputs - approved_outputs

        if missing_resources:
            differences.append(f"missing resources: {sorted(missing_resources)}")
        if additional_resources:
            differences.append(f"additional resources: {sorted(additional_resources)}")
        if missing_inputs:
            differences.append(f"missing inputs: {sorted(missing_inputs)}")
        if additional_inputs:
            differences.append(f"additional inputs: {sorted(additional_inputs)}")
        if missing_outputs:
            differences.append(f"missing outputs: {sorted(missing_outputs)}")
        if additional_outputs:
            differences.append(f"additional outputs: {sorted(additional_outputs)}")

        return {
            "compatible": resource_match and input_match and output_match,
            "approved_resources": sorted(approved_resources),
            "target_resources": sorted(target_resources),
            "approved_inputs": sorted(approved_inputs),
            "target_inputs": sorted(target_inputs),
            "approved_outputs": sorted(approved_outputs),
            "target_outputs": sorted(target_outputs),
            "differences": differences,
        }

    def check_module(
        self,
        selected_module: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        module_name = self._normalize(selected_module.get("module"))
        module = self.catalog.get_module(module_name)

        if not module:
            return {
                "module": module_name,
                "decision": "REVIEW",
                "reason": "Module is not present in the approved catalog",
            }

        # 1. Existing module block anywhere in the branch.
        for existing in analysis.get("modules", []):
            if self._normalize(existing.get("name")).lower() == module_name.lower():
                return {
                    "module": module_name,
                    "decision": "REUSE",
                    "reason": "Existing Terraform module call found anywhere in the selected branch",
                    "existing_module": existing,
                }

        # 2. Existing directory anywhere in the branch.
        matching_directories = [
            directory
            for directory in analysis.get("module_directories", [])
            if self._normalize(directory.get("name")).lower() == module_name.lower()
        ]

        if matching_directories:
            compatibility = self._check_module_compatibility(module, analysis)
            if compatibility["compatible"]:
                return {
                    "module": module_name,
                    "decision": "REUSE",
                    "reason": "Existing Terraform directory is compatible with the approved module",
                    "existing_directory": matching_directories[0],
                    "compatibility": compatibility,
                }
            return {
                "module": module_name,
                "decision": "REVIEW",
                "reason": "Existing Terraform directory was found, but its implementation differs from the approved module",
                "existing_directory": matching_directories[0],
                "compatibility": compatibility,
            }

        # 3. Matching resource anywhere in the branch.
        approved_resources = self._resource_types_from_catalog(module)
        matching_resources = [
            resource
            for resource in analysis.get("resources", [])
            if self._normalize(resource.get("type")) in approved_resources
        ]

        if matching_resources:
            return {
                "module": module_name,
                "decision": "REVIEW",
                "reason": "Matching Terraform resources already exist somewhere in the selected branch",
                "matching_resources": matching_resources,
            }

        return {
            "module": module_name,
            "decision": "CREATE",
            "reason": "No existing Terraform module call, module directory, or matching resource found anywhere in the selected branch",
        }

    def analyze(self, selected_modules: List[Dict[str, Any]]):
        analysis = self.analyzer.analyze()
        return [self.check_module(module, analysis) for module in selected_modules]

    @staticmethod
    def summarize(decisions: List[Dict[str, Any]]) -> Dict[str, int]:
        summary = {"CREATE": 0, "REUSE": 0, "REVIEW": 0}
        for decision in decisions:
            value = decision.get("decision")
            if value in summary:
                summary[value] += 1
        return summary


if __name__ == "__main__":
    checker = DuplicateChecker()
    selected_modules = [
        {"module": module["name"]}
        for module in checker.catalog.get_all_modules()
    ]
    decisions = checker.analyze(selected_modules)
    print("TARGET INFRASTRUCTURE DECISIONS")
    for decision in decisions:
        print(f"{decision['module']}: {decision['decision']} - {decision['reason']}")