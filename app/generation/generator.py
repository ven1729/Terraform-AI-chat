
import os
import copy
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from app.generation.plan import GenerationPlanner


class TerraformGenerator:
    """
    Production Terraform generator.

    Responsibilities:
        1. Consume a READY GenerationPlanner plan.
        2. Generate main.tf.
        3. Generate variables.tf.
        4. Generate outputs.tf.
        5. Generate providers.tf.
        6. Respect CREATE / REUSE / ADAPT decisions.
        7. Respect ReviewResolver mappings.
        8. Respect dependency mappings.
        9. Avoid duplicate module blocks.
        10. Avoid unnecessary root variables.
        11. Preserve Terraform variable types/defaults/descriptions.
        12. Never interpret natural-language user requests directly.

    IMPORTANT:
        generate() expects a GenerationPlanner result.
        It does NOT expect the user's natural-language request.
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        target_repository: Optional[str] = None,
        target_branch: Optional[str] = None,
    ):
        load_dotenv()

        self.owner = self._required_env(
            "GITHUB_OWNER"
        )

        self.module_repository = (
            os.getenv("MODULE_REPO")
            or "umbrella"
        )

        self.module_branch = (
            os.getenv("MODULE_BRANCH")
            or "main"
        )

        self.target_repository = (
            target_repository
            or os.getenv("TARGET_REPO")
            or "target"
        )

        self.target_branch = (
            target_branch
            or os.getenv("TARGET_BRANCH")
            or "main"
        )

        self.output_dir = Path(
            output_dir
            or os.getenv(
                "GENERATED_TERRAFORM_DIR",
                "generated",
            )
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ============================================================
    # ENVIRONMENT
    # ============================================================

    @staticmethod
    def _required_env(
        name: str,
    ) -> str:
        value = os.getenv(name)

        if not value:
            raise ValueError(
                f"{name} is not configured"
            )

        return value

    # ============================================================
    # GENERIC HELPERS
    # ============================================================

    @staticmethod
    def _normalize(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        return str(value).strip()

    @staticmethod
    def _as_list(
        value: Any,
    ) -> List[Any]:

        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        if isinstance(value, set):
            return list(value)

        return [value]

    @staticmethod
    def _terraform_identifier(
        value: str,
    ) -> str:

        value = str(value).strip()

        cleaned = []

        for char in value:
            if char.isalnum() or char == "_":
                cleaned.append(char)
            else:
                cleaned.append("_")

        result = "".join(
            cleaned
        ).strip("_")

        if not result:
            result = "value"

        if result[0].isdigit():
            result = f"_{result}"

        return result

    @staticmethod
    def _clean_type_expression(
        value: Any,
    ) -> Optional[str]:
        """
        Normalize Terraform type expressions.

        Examples:

            string
            ${string}
            "string"
            list(string)
            ${list(string)}
            map(string)
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        if (
            value.startswith("${")
            and value.endswith("}")
        ):
            value = value[2:-1].strip()

        if (
            len(value) >= 2
            and value[0] == '"'
            and value[-1] == '"'
        ):
            value = value[1:-1].strip()

        return value or None

    @staticmethod
    def _clean_string_value(
        value: Any,
    ) -> Any:

        if not isinstance(value, str):
            return value

        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == '"'
            and value[-1] == '"'
        ):
            value = value[1:-1]

        value = value.replace(
            '\\"',
            '"',
        )

        return value

    @staticmethod
    def _hcl_string(
        value: Any,
    ) -> str:

        text = str(value)

        text = (
            text
            .replace(
                "\\",
                "\\\\",
            )
            .replace(
                '"',
                '\\"',
            )
        )

        return f'"{text}"'

    # ============================================================
    # HCL VALUE SERIALIZATION
    # ============================================================

    def _hcl_value(
        self,
        value: Any,
    ) -> str:
        """
        Convert Python/catalog values into valid HCL literals.
        """

        value = self._clean_string_value(
            value
        )

        if value is None:
            return "null"

        if isinstance(value, bool):
            return (
                "true"
                if value
                else "false"
            )

        if isinstance(
            value,
            (int, float),
        ):
            return str(value)

        if isinstance(value, str):
            return self._hcl_string(
                value
            )

        if isinstance(value, list):
            return (
                "["
                + ", ".join(
                    self._hcl_value(item)
                    for item in value
                )
                + "]"
            )

        if isinstance(value, tuple):
            return (
                "["
                + ", ".join(
                    self._hcl_value(item)
                    for item in value
                )
                + "]"
            )

        if isinstance(value, dict):

            entries = []

            for key, item in value.items():

                key = self._clean_string_value(
                    key
                )

                entries.append(
                    f"{self._hcl_string(key)} = "
                    f"{self._hcl_value(item)}"
                )

            return (
                "{ "
                + ", ".join(entries)
                + " }"
            )

        return self._hcl_string(
            value
        )

    # ============================================================
    # TYPE INFERENCE
    # ============================================================

    def _infer_type_from_default(
        self,
        default: Any,
    ) -> Optional[str]:

        if default is None:
            return None

        if isinstance(
            default,
            bool,
        ):
            return "bool"

        if isinstance(
            default,
            (int, float),
        ):
            return "number"

        if isinstance(default, list):

            if not default:
                return "list(string)"

            first_type = (
                self._infer_type_from_default(
                    default[0]
                )
            )

            return (
                f"list({first_type or 'string'})"
            )

        if isinstance(default, dict):

            if not default:
                return "map(string)"

            first_value = next(
                iter(default.values())
            )

            value_type = (
                self._infer_type_from_default(
                    first_value
                )
            )

            return (
                f"map({value_type or 'string'})"
            )

        if isinstance(
            default,
            str,
        ):
            return "string"

        return None

    def _infer_type_from_name(
        self,
        variable_name: str,
    ) -> str:

        name = (
            self._terraform_identifier(
                variable_name
            ).lower()
        )

        # Collections
        if name in {
            "tags",
            "labels",
            "subnets",
        }:
            return "map(string)"

        if name in {
            "address_space",
            "address_spaces",
            "subnet_prefixes",
        }:
            return "list(string)"

        # Boolean variables
        if (
            name.startswith("enable_")
            or name.startswith("disable_")
            or name.startswith("is_")
            or name.startswith("has_")
            or name.startswith("use_")
        ):
            return "bool"

        # Numeric variables
        if (
            name.endswith("_count")
            or name.endswith("_size")
            and name in {
                "count",
                "node_count",
            }
        ):
            return "number"

        if name in {
            "count",
            "node_count",
            "replicas",
            "instance_count",
            "min_count",
            "max_count",
        }:
            return "number"

        # Everything else is safely represented as string.
        return "string"

    def _terraform_type(
        self,
        metadata: Optional[
            Dict[str, Any]
        ],
        variable_name: str = "",
    ) -> str:
        """
        Determine a real Terraform type.

        Priority:

            1. Explicit metadata type.
            2. Default-value inference.
            3. Variable-name inference.
            4. string fallback.

        We intentionally avoid `any` for generated
        root variables unless an explicitly supplied
        Terraform type cannot be interpreted.
        """

        metadata = (
            metadata
            if isinstance(
                metadata,
                dict,
            )
            else {}
        )

        explicit_type = (
            metadata.get("type")
            or metadata.get(
                "terraform_type"
            )
        )

        explicit_type = (
            self._clean_type_expression(
                explicit_type
            )
        )

        if explicit_type:
            return explicit_type

        if "default" in metadata:

            inferred = (
                self._infer_type_from_default(
                    metadata.get(
                        "default"
                    )
                )
            )

            if inferred:
                return inferred

        return self._infer_type_from_name(
            variable_name
        )

    # ============================================================
    # MODULE METADATA
    # ============================================================

    def _module_source(
        self,
        module: Dict[str, Any],
    ) -> str:

        path = self._normalize(
            module.get("path")
        )

        if not path:
            raise ValueError(
                "Approved module "
                f"'{module.get('name')}' "
                "has no path"
            )

        path = path.replace(
            "\\",
            "/",
        )

        return (
            "git::https://github.com/"
            f"{self.owner}/"
            f"{self.module_repository}"
            f".git//{path}"
            f"?ref={self.module_branch}"
        )

    def _module_name(
        self,
        module: Dict[str, Any],
    ) -> str:

        name = self._normalize(
            module.get("name")
            or module.get(
                "module_name"
            )
        )

        if not name:
            raise ValueError(
                "Module definition has no name"
            )

        return self._terraform_identifier(
            name
        )

    def _get_catalog_module(
        self,
        module_name: str,
        selected_modules: Any,
    ) -> Optional[
        Dict[str, Any]
    ]:

        module_name = self._normalize(
            module_name
        )

        if not module_name:
            return None

        if isinstance(
            selected_modules,
            dict,
        ):

            direct = (
                selected_modules.get(
                    module_name
                )
            )

            if isinstance(
                direct,
                dict,
            ):
                return direct

            iterable = (
                selected_modules.values()
            )

        elif isinstance(
            selected_modules,
            (
                list,
                tuple,
                set,
            ),
        ):

            iterable = selected_modules

        else:
            return None

        for module in iterable:

            if not isinstance(
                module,
                dict,
            ):
                continue

            name = self._normalize(
                module.get("name")
            )

            if (
                name.lower()
                == module_name.lower()
            ):
                return module

            module_id = (
                self._normalize(
                    module.get(
                        "module_name"
                    )
                )
            )

            if (
                module_id.lower()
                == module_name.lower()
            ):
                return module

        return None

    # ============================================================
    # PLAN ACTION HELPERS
    # ============================================================

    @staticmethod
    def _action_name(
        planned_module: Dict[str, Any],
    ) -> str:

        return str(
            planned_module.get(
                "action",
                "",
            )
        ).strip().upper()

    def _get_duplicate_check(
        self,
        planned_module: Dict[str, Any],
    ) -> Dict[str, Any]:

        duplicate = (
            planned_module.get(
                "duplicate_check"
            )
        )

        if isinstance(
            duplicate,
            dict,
        ):
            return duplicate

        return {}

    def _has_existing_module_call(
        self,
        planned_module: Dict[str, Any],
    ) -> bool:

        duplicate = (
            self._get_duplicate_check(
                planned_module
            )
        )

        if duplicate.get(
            "existing_module"
        ):
            return True

        if duplicate.get(
            "existing_module_call"
        ):
            return True

        return False

    def _get_existing_directory(
        self,
        planned_module: Dict[str, Any],
    ) -> Optional[
        Dict[str, Any]
    ]:

        duplicate = (
            self._get_duplicate_check(
                planned_module
            )
        )

        directory = (
            duplicate.get(
                "existing_directory"
            )
        )

        if isinstance(
            directory,
            dict,
        ):
            return directory

        return None

    def _local_module_source(
        self,
        planned_module: Dict[str, Any],
        module: Dict[str, Any],
    ) -> str:

        existing_directory = (
            self._get_existing_directory(
                planned_module
            )
        )

        if existing_directory:

            path = self._normalize(
                existing_directory.get(
                    "path"
                )
            )

            if path:

                path = path.replace(
                    "\\",
                    "/",
                )

                if not path.startswith(
                    "./"
                ):
                    path = (
                        "./"
                        + path
                    )

                return path

        catalog_path = self._normalize(
            module.get("path")
        )

        if catalog_path:

            catalog_path = (
                catalog_path.replace(
                    "\\",
                    "/",
                )
            )

            if not catalog_path.startswith(
                "./"
            ):
                return (
                    "./"
                    + catalog_path
                )

            return catalog_path

        raise ValueError(
            "Cannot determine local "
            "module source for "
            f"'{module.get('name')}'"
        )

    def _should_generate_module_call(
        self,
        planned_module: Dict[str, Any],
    ) -> bool:

        action = self._action_name(
            planned_module
        )

        if action == "CREATE":
            return True

        if action in {
            "ADAPT",
            "REUSE",
        }:
            return not (
                self._has_existing_module_call(
                    planned_module
                )
            )

        return False

    # ============================================================
    # DEPENDENCIES
    # ============================================================

    def _dependency_module_name(
        self,
        dependency: Dict[str, Any],
    ) -> str:

        for key in (
            "module",
            "module_name",
            "dependency",
            "name",
            "target_module",
        ):

            value = dependency.get(
                key
            )

            if value:
                return self._normalize(
                    value
                )

        return ""

    def _dependency_output_name(
        self,
        dependency: Dict[str, Any],
    ) -> str:

        for key in (
            "output",
            "output_name",
            "source_output",
            "dependency_output",
        ):

            value = dependency.get(
                key
            )

            if value:
                return self._normalize(
                    value
                )

        return ""

    def _get_dependency_definitions(
        self,
        module: Dict[str, Any],
    ) -> List[
        Dict[str, Any]
    ]:

        dependencies = (
            module.get(
                "dependencies"
            )
        )

        if dependencies is None:
            return []

        if isinstance(
            dependencies,
            dict,
        ):
            return [
                dependencies
            ]

        return [
            item
            for item in self._as_list(
                dependencies
            )
            if isinstance(
                item,
                dict,
            )
        ]

    def _dependency_reference_for_input(
        self,
        module: Dict[str, Any],
        input_name: str,
    ) -> str:

        dependencies = (
            self._get_dependency_definitions(
                module
            )
        )

        for dependency in dependencies:

            dependency_name = (
                self._dependency_module_name(
                    dependency
                )
            )

            output_name = (
                self._dependency_output_name(
                    dependency
                )
            )

            if not (
                dependency_name
                and output_name
            ):
                continue

            if (
                input_name
                != output_name
            ):
                continue

            dependency_identifier = (
                self._terraform_identifier(
                    dependency_name
                )
            )

            output_identifier = (
                self._terraform_identifier(
                    output_name
                )
            )

            return (
                f"module."
                f"{dependency_identifier}."
                f"{output_identifier}"
            )

        return ""

    # ============================================================
    # ADAPT MAPPINGS
    # ============================================================

    def _get_adapt_mappings(
        self,
        planned_module: Dict[str, Any],
    ) -> Dict[str, Any]:

        for key in (
            "mappings",
            "mapping",
            "resolved_inputs",
        ):

            value = (
                planned_module.get(
                    key
                )
            )

            if isinstance(
                value,
                dict,
            ):
                return value

        review = (
            planned_module.get(
                "review"
            )
        )

        if isinstance(
            review,
            dict,
        ):

            mapping = (
                review.get(
                    "mapping"
                )
            )

            if isinstance(
                mapping,
                dict,
            ):
                return mapping

        resolution = (
            planned_module.get(
                "review_resolution"
            )
        )

        if isinstance(
            resolution,
            dict,
        ):

            mapping = (
                resolution.get(
                    "mapping"
                )
            )

            if isinstance(
                mapping,
                dict,
            ):
                return mapping

        return {}

    def _resolved_mapping_for_input(
        self,
        planned_module: Dict[str, Any],
        input_name: str,
    ) -> str:

        mappings = (
            self._get_adapt_mappings(
                planned_module
            )
        )

        value = mappings.get(
            input_name
        )

        if value is None:
            value = mappings.get(
                self._normalize(
                    input_name
                )
            )

        if isinstance(
            value,
            str,
        ):
            value = value.strip()

            if value:
                return value

        return ""

    # ============================================================
    # INPUT / OUTPUT METADATA
    # ============================================================

    def _input_metadata(
        self,
        module: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:

        inputs = module.get(
            "inputs"
        )

        result = {}

        if isinstance(
            inputs,
            dict,
        ):

            for name, metadata in (
                inputs.items()
            ):

                name = self._normalize(
                    name
                )

                if not name:
                    continue

                if isinstance(
                    metadata,
                    dict,
                ):
                    value = copy.deepcopy(
                        metadata
                    )
                else:
                    value = {}

                value.setdefault(
                    "name",
                    name,
                )

                result[name] = value

            return result

        for item in self._as_list(
            inputs
        ):

            if isinstance(
                item,
                str,
            ):

                name = self._normalize(
                    item
                )

                if name:
                    result[name] = {
                        "name": name
                    }

                continue

            if not isinstance(
                item,
                dict,
            ):
                continue

            name = (
                item.get("name")
                or item.get("input")
                or item.get("variable")
                or item.get(
                    "input_name"
                )
            )

            name = self._normalize(
                name
            )

            if not name:
                continue

            value = copy.deepcopy(
                item
            )

            value["name"] = name

            result[name] = value

        return result

    def _input_names(
        self,
        module: Dict[str, Any],
    ) -> List[str]:

        return list(
            self._input_metadata(
                module
            ).keys()
        )

    def _output_names(
        self,
        module: Dict[str, Any],
    ) -> List[str]:

        outputs = module.get(
            "outputs"
        )

        result = []

        if isinstance(
            outputs,
            dict,
        ):

            for name in outputs:

                name = self._normalize(
                    name
                )

                if name:
                    result.append(
                        name
                    )

            return result

        for item in self._as_list(
            outputs
        ):

            if isinstance(
                item,
                str,
            ):

                name = self._normalize(
                    item
                )

            elif isinstance(
                item,
                dict,
            ):

                name = self._normalize(
                    item.get("name")
                    or item.get("output")
                )

            else:
                continue

            if name:
                result.append(
                    name
                )

        return list(
            dict.fromkeys(
                result
            )
        )

    # ============================================================
    # TARGET VARIABLE METADATA
    # ============================================================

    def _target_variable_metadata(
        self,
        variable_name: str,
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> Dict[str, Any]:

        if not target_analysis:
            return {
                "name": variable_name
            }

        variables = (
            target_analysis.get(
                "variables",
                [],
            )
            or []
        )

        if isinstance(
            variables,
            dict,
        ):

            value = variables.get(
                variable_name
            )

            if isinstance(
                value,
                dict,
            ):

                result = copy.deepcopy(
                    value
                )

                result.setdefault(
                    "name",
                    variable_name,
                )

                return result

        for variable in self._as_list(
            variables
        ):

            if isinstance(
                variable,
                str,
            ):

                if (
                    self._normalize(
                        variable
                    )
                    == self._normalize(
                        variable_name
                    )
                ):
                    return {
                        "name":
                            variable_name
                    }

                continue

            if not isinstance(
                variable,
                dict,
            ):
                continue

            name = (
                variable.get("name")
                or variable.get(
                    "variable"
                )
                or variable.get("key")
            )

            if (
                self._normalize(name)
                == self._normalize(
                    variable_name
                )
            ):
                return copy.deepcopy(
                    variable
                )

        return {
            "name": variable_name
        }

    # ============================================================
    # TARGET MODULE VARIABLES
    # ============================================================

    def _target_module_path(
        self,
        planned_module: Dict[str, Any],
    ) -> str:

        duplicate = (
            self._get_duplicate_check(
                planned_module
            )
        )

        directory = (
            duplicate.get(
                "existing_directory"
            )
        )

        if isinstance(
            directory,
            dict,
        ):

            path = self._normalize(
                directory.get(
                    "path"
                )
            )

            if path:
                return (
                    path
                    .replace(
                        "\\",
                        "/",
                    )
                    .rstrip("/")
                )

        module_name = self._normalize(
            planned_module.get(
                "module"
            )
        )

        if not module_name:
            module_name = self._normalize(
                planned_module.get(
                    "name"
                )
            )

        return (
            f"modules/{module_name}"
        )

    def _target_module_variables(
        self,
        planned_module: Dict[str, Any],
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> Dict[
        str,
        Dict[str, Any]
    ]:

        if not target_analysis:
            return {}

        directory_path = (
            self._target_module_path(
                planned_module
            )
        )

        variables = (
            target_analysis.get(
                "variables",
                [],
            )
            or []
        )

        result = {}

        if isinstance(
            variables,
            dict,
        ):

            for name, metadata in (
                variables.items()
            ):

                name = self._normalize(
                    name
                )

                if not name:
                    continue

                if isinstance(
                    metadata,
                    dict,
                ):
                    value = copy.deepcopy(
                        metadata
                    )
                else:
                    value = {}

                value.setdefault(
                    "name",
                    name,
                )

                result[name] = value

            return result

        for item in self._as_list(
            variables
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            name = (
                item.get("name")
                or item.get(
                    "variable"
                )
                or item.get("key")
            )

            name = self._normalize(
                name
            )

            if not name:
                continue

            file_path = self._normalize(
                item.get("file")
                or item.get("path")
                or item.get(
                    "filename"
                )
            ).replace(
                "\\",
                "/",
            )

            # If the analyzer does not provide a file,
            # retain the variable because it has already
            # been identified by the target analyzer.
            if file_path:

                if not (
                    file_path == directory_path
                    or file_path.startswith(
                        directory_path
                        + "/"
                    )
                ):
                    continue

            value = copy.deepcopy(
                item
            )

            value["name"] = name

            result[name] = value

        return result

    # ============================================================
    # PLAN ACTIONS
    # ============================================================

    def _plan_actions(
        self,
        plan: Dict[str, Any],
    ) -> List[
        Dict[str, Any]
    ]:

        actions = (
            plan.get("actions")
            or plan.get("modules")
            or plan.get(
                "selected_modules"
            )
            or []
        )

        result = []

        for item in self._as_list(
            actions
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            module_name = (
                item.get("module")
                or item.get("name")
                or item.get(
                    "module_name"
                )
            )

            if not module_name:
                continue

            result.append(
                item
            )

        return result

    def _action_map(
        self,
        plan: Dict[str, Any],
    ) -> Dict[
        str,
        Dict[str, Any]
    ]:

        result = {}

        for action in self._plan_actions(
            plan
        ):

            name = self._normalize(
                action.get(
                    "module"
                )
                or action.get(
                    "name"
                )
                or action.get(
                    "module_name"
                )
            )

            if name:
                result[name] = action

        return result

    def _effective_module(
        self,
        action: Dict[str, Any],
        selected_modules: Any,
    ) -> Optional[
        Dict[str, Any]
    ]:

        module_name = self._normalize(
            action.get(
                "module"
            )
            or action.get(
                "name"
            )
            or action.get(
                "module_name"
            )
        )

        module = self._get_catalog_module(
            module_name,
            selected_modules,
        )

        if isinstance(
            module,
            dict,
        ):
            return module

        module = action.get(
            "catalog"
        )

        if isinstance(
            module,
            dict,
        ):
            return module

        module = action.get(
            "module_definition"
        )

        if isinstance(
            module,
            dict,
        ):
            return module

        module = action.get(
            "definition"
        )

        if isinstance(
            module,
            dict,
        ):
            return module

        return None

    # ============================================================
    # ROOT VARIABLE COLLECTION
    # ============================================================

    def _collect_variable_metadata(
        self,
        plan: Dict[str, Any],
        selected_modules: Any,
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> Dict[
        str,
        Dict[str, Any]
    ]:
        """
        Collect only variables actually required by
        generated module calls.

        Local ADAPT/REUSE target interfaces receive
        higher metadata priority than approved CREATE
        module interfaces.
        """

        collected = {}

        for action in self._plan_actions(
            plan
        ):

            action_type = (
                self._action_name(
                    action
                )
            )

            if action_type not in {
                "CREATE",
                "ADAPT",
                "REUSE",
            }:
                continue

            if not self._should_generate_module_call(
                action
            ):
                continue

            module = self._effective_module(
                action,
                selected_modules,
            )

            if not isinstance(
                module,
                dict,
            ):
                continue

            if action_type in {
                "ADAPT",
                "REUSE",
            }:

                input_metadata = (
                    self._target_module_variables(
                        action,
                        target_analysis,
                    )
                )

                # Fall back to the effective catalog if
                # target analysis did not expose variables.
                if not input_metadata:
                    input_metadata = (
                        self._input_metadata(
                            module
                        )
                    )

                priority = 100

            else:

                input_metadata = (
                    self._input_metadata(
                        module
                    )
                )

                priority = 50

            mappings = (
                self._get_adapt_mappings(
                    action
                )
            )

            for input_name, metadata in (
                input_metadata.items()
            ):

                input_name = (
                    self._terraform_identifier(
                        input_name
                    )
                )

                # Mapped values are expressions, not
                # root variables.
                if (
                    input_name in mappings
                    or input_name in {
                        self._terraform_identifier(
                            key
                        )
                        for key in mappings
                    }
                ):
                    continue

                metadata = (
                    copy.deepcopy(
                        metadata
                    )
                    if isinstance(
                        metadata,
                        dict,
                    )
                    else {}
                )

                metadata.setdefault(
                    "name",
                    input_name,
                )

                metadata["_priority"] = (
                    priority
                )

                self._merge_variable_metadata(
                    collected,
                    input_name,
                    metadata,
                )

        return collected

    def _merge_variable_metadata(
        self,
        collected: Dict[
            str,
            Dict[str, Any]
        ],
        variable_name: str,
        incoming: Dict[str, Any],
    ) -> None:

        incoming_priority = int(
            incoming.get(
                "_priority",
                0,
            )
        )

        existing = collected.get(
            variable_name
        )

        if existing is None:
            collected[
                variable_name
            ] = incoming
            return

        existing_priority = int(
            existing.get(
                "_priority",
                0,
            )
        )

        if (
            incoming_priority
            > existing_priority
        ):

            merged = copy.deepcopy(
                incoming
            )

            # Preserve a useful lower-priority
            # description if the higher-priority
            # metadata does not provide one.
            if not merged.get(
                "description"
            ) and existing.get(
                "description"
            ):
                merged[
                    "description"
                ] = existing[
                    "description"
                ]

            collected[
                variable_name
            ] = merged

            return

        if (
            incoming_priority
            < existing_priority
        ):
            return

        # Same priority: merge missing fields.
        merged = copy.deepcopy(
            existing
        )

        if not merged.get(
            "type"
        ) and incoming.get(
            "type"
        ):
            merged[
                "type"
            ] = incoming[
                "type"
            ]

        if not merged.get(
            "description"
        ) and incoming.get(
            "description"
        ):
            merged[
                "description"
            ] = incoming[
                "description"
            ]

        if (
            "default" not in merged
            and "default" in incoming
        ):
            merged[
                "default"
            ] = incoming[
                "default"
            ]

        collected[
            variable_name
        ] = merged

    # ============================================================
    # ROOT VARIABLE NAMES
    # ============================================================

    def _root_variable_names(
        self,
        plan: Dict[str, Any],
        selected_modules: Any,
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> List[str]:

        metadata = (
            self._collect_variable_metadata(
                plan,
                selected_modules,
                target_analysis,
            )
        )

        return sorted(
            metadata.keys()
        )

    # ============================================================
    # MODULE BLOCK
    # ============================================================

    def _generate_module_block(
        self,
        planned_module: Dict[str, Any],
        module: Dict[str, Any],
        root_variable_names: List[str],
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> str:

        action = self._action_name(
            planned_module
        )

        module_name = (
            self._module_name(
                module
            )
        )

        if action == "CREATE":

            source = (
                self._module_source(
                    module
                )
            )

        elif action in {
            "ADAPT",
            "REUSE",
        }:

            source = (
                self._local_module_source(
                    planned_module,
                    module,
                )
            )

        else:
            raise ValueError(
                "Cannot generate module "
                f"block for action "
                f"'{action}'"
            )

        lines = [
            f'module "{module_name}" {{',
            f'  source = "{source}"',
        ]

        input_metadata = (
            self._input_metadata(
                module
            )
        )

        if action in {
            "ADAPT",
            "REUSE",
        }:

            target_inputs = (
                self._target_module_variables(
                    planned_module,
                    target_analysis,
                )
            )

            if target_inputs:
                input_metadata = (
                    target_inputs
                )

        mappings = (
            self._get_adapt_mappings(
                planned_module
            )
        )

        normalized_mapping_keys = {
            self._terraform_identifier(
                key
            ): value
            for key, value
            in mappings.items()
        }

        for original_input_name in (
            input_metadata.keys()
        ):

            input_name = (
                self._terraform_identifier(
                    original_input_name
                )
            )

            # ----------------------------------------------------
            # 1. Explicit mapping.
            # ----------------------------------------------------

            resolved_mapping = (
                mappings.get(
                    original_input_name
                )
                or normalized_mapping_keys.get(
                    input_name
                )
            )

            if isinstance(
                resolved_mapping,
                str,
            ):
                resolved_mapping = (
                    resolved_mapping.strip()
                )

            if resolved_mapping:
                lines.append(
                    f"  {input_name} = "
                    f"{resolved_mapping}"
                )
                continue

            # ----------------------------------------------------
            # 2. Dependency reference.
            # ----------------------------------------------------

            dependency_reference = (
                self._dependency_reference_for_input(
                    module,
                    original_input_name,
                )
            )

            if dependency_reference:

                lines.append(
                    f"  {input_name} = "
                    f"{dependency_reference}"
                )

                continue

            # ----------------------------------------------------
            # 3. Root variable.
            # ----------------------------------------------------

            if (
                input_name
                in root_variable_names
            ):

                lines.append(
                    f"  {input_name} = "
                    f"var.{input_name}"
                )

                continue

            # ----------------------------------------------------
            # 4. No assignment.
            #
            # This allows the target module's own
            # Terraform default to apply.
            # ----------------------------------------------------

        lines.append("}")

        return "\n".join(
            lines
        )

    # ============================================================
    # main.tf
    # ============================================================

    def _generate_main_tf(
        self,
        plan: Dict[str, Any],
        selected_modules: Any,
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> str:

        root_variable_names = (
            self._root_variable_names(
                plan,
                selected_modules,
                target_analysis,
            )
        )

        action_map = (
            self._action_map(
                plan
            )
        )

        generation_order = (
            plan.get(
                "generation_order"
            )
            or plan.get(
                "order"
            )
            or []
        )

        ordered_actions = []

        for module_name in (
            self._as_list(
                generation_order
            )
        ):

            normalized_name = (
                self._normalize(
                    module_name
                )
            )

            action = action_map.get(
                normalized_name
            )

            if action:
                ordered_actions.append(
                    action
                )

        # Fallback if generation_order is absent.
        if not ordered_actions:

            ordered_actions = (
                self._plan_actions(
                    plan
                )
            )

        blocks = []

        emitted_modules = set()

        for action in ordered_actions:

            action_type = (
                self._action_name(
                    action
                )
            )

            if action_type not in {
                "CREATE",
                "ADAPT",
                "REUSE",
            }:
                continue

            module_name = self._normalize(
                action.get(
                    "module"
                )
                or action.get(
                    "name"
                )
                or action.get(
                    "module_name"
                )
            )

            if not module_name:
                continue

            canonical_name = (
                self._terraform_identifier(
                    module_name
                )
            )

            if canonical_name in emitted_modules:
                continue

            if not self._should_generate_module_call(
                action
            ):
                continue

            module = self._effective_module(
                action,
                selected_modules,
            )

            if not isinstance(
                module,
                dict,
            ):
                raise ValueError(
                    "Module definition "
                    f"not found for "
                    f"'{module_name}'"
                )

            blocks.append(
                self._generate_module_block(
                    planned_module=action,
                    module=module,
                    root_variable_names=(
                        root_variable_names
                    ),
                    target_analysis=(
                        target_analysis
                    ),
                )
            )

            emitted_modules.add(
                canonical_name
            )

        if not blocks:
            return ""

        return (
            "\n\n".join(
                blocks
            )
            + "\n"
        )

    # ============================================================
    # variables.tf
    # ============================================================

    def _generate_variables_tf(
        self,
        plan: Dict[str, Any],
        selected_modules: Any,
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> str:

        metadata = (
            self._collect_variable_metadata(
                plan,
                selected_modules,
                target_analysis,
            )
        )

        blocks = []

        for name in sorted(
            metadata.keys()
        ):

            variable_name = (
                self._terraform_identifier(
                    name
                )
            )

            item = metadata[
                name
            ]

            variable_type = (
                self._terraform_type(
                    item,
                    variable_name,
                )
            )

            description = (
                item.get(
                    "description"
                )
                or f"Input variable '{variable_name}'"
            )

            description = (
                self._clean_string_value(
                    description
                )
            )

            lines = [
                f'variable "{variable_name}" {{',
                f"  type        = {variable_type}",
                (
                    "  description = "
                    f"{self._hcl_string(description)}"
                ),
            ]

            if "default" in item:

                default = item.get(
                    "default"
                )

                # A null default is deliberately NOT
                # emitted for required variables.
                #
                # This prevents:
                #
                #     resource_group_name = null
                #
                # when the module requires a real value.
                if default is not None:

                    lines.append(
                        "  default     = "
                        f"{self._hcl_value(default)}"
                    )

            lines.append("}")

            blocks.append(
                "\n".join(lines)
            )

        if not blocks:
            return ""

        return (
            "\n\n".join(
                blocks
            )
            + "\n"
        )

    # ============================================================
    # outputs.tf
    # ============================================================

    def _generate_outputs_tf(
        self,
        plan: Dict[str, Any],
        selected_modules: Any,
    ) -> str:

        blocks = []

        emitted_outputs = set()

        for action in self._plan_actions(
            plan
        ):

            action_type = (
                self._action_name(
                    action
                )
            )

            if action_type not in {
                "CREATE",
                "ADAPT",
                "REUSE",
            }:
                continue

            if not self._should_generate_module_call(
                action
            ):
                continue

            module_name = self._normalize(
                action.get(
                    "module"
                )
                or action.get(
                    "name"
                )
                or action.get(
                    "module_name"
                )
            )

            if not module_name:
                continue

            module = self._effective_module(
                action,
                selected_modules,
            )

            if not isinstance(
                module,
                dict,
            ):
                continue

            module_identifier = (
                self._terraform_identifier(
                    module_name
                )
            )

            for output_name in (
                self._output_names(
                    module
                )
            ):

                output_identifier = (
                    self._terraform_identifier(
                        output_name
                    )
                )

                root_output_name = (
                    f"{module_identifier}_"
                    f"{output_identifier}"
                )

                if (
                    root_output_name
                    in emitted_outputs
                ):
                    continue

                blocks.append(
                    "\n".join(
                        [
                            (
                                f'output '
                                f'"{root_output_name}" {{'
                            ),
                            (
                                "  value = "
                                f"module."
                                f"{module_identifier}."
                                f"{output_identifier}"
                            ),
                            "}",
                        ]
                    )
                )

                emitted_outputs.add(
                    root_output_name
                )

        if not blocks:
            return ""

        return (
            "\n\n".join(
                blocks
            )
            + "\n"
        )

    # ============================================================
    # PROVIDERS
    # ============================================================

    def _provider_name(
        self,
        provider: Any,
    ) -> Optional[str]:

        if provider is None:
            return None

        if isinstance(
            provider,
            str,
        ):

            value = provider.strip()

            return (
                value
                if value
                else None
            )

        if isinstance(
            provider,
            dict,
        ):

            for key in (
                "name",
                "provider",
                "type",
            ):

                value = (
                    self._provider_name(
                        provider.get(
                            key
                        )
                    )
                )

                if value:
                    return value

            return None

        if isinstance(
            provider,
            list,
        ):

            for item in provider:

                value = (
                    self._provider_name(
                        item
                    )
                )

                if value:
                    return value

        return None

    def _provider_names_from_plan(
        self,
        plan: Dict[str, Any],
        selected_modules: Any,
    ) -> List[str]:

        providers = set()

        for action in self._plan_actions(
            plan
        ):

            action_type = (
                self._action_name(
                    action
                )
            )

            if action_type not in {
                "CREATE",
                "ADAPT",
                "REUSE",
            }:
                continue

            module = self._effective_module(
                action,
                selected_modules,
            )

            if not isinstance(
                module,
                dict,
            ):
                continue

            provider = self._provider_name(
                module.get(
                    "provider"
                )
            )

            if provider:
                providers.add(
                    provider
                )

        return sorted(
            providers
        )

    def _provider_names_from_target(
        self,
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> List[str]:

        if not target_analysis:
            return []

        providers = (
            target_analysis.get(
                "providers",
                [],
            )
            or []
        )

        result = set()

        if isinstance(
            providers,
            dict,
        ):
            providers = list(
                providers.keys()
            )

        for provider in self._as_list(
            providers
        ):

            name = self._provider_name(
                provider
            )

            if name:
                result.add(
                    name
                )

        return sorted(
            result
        )

    def _generate_providers_tf(
        self,
        plan: Dict[str, Any],
        selected_modules: Any,
        target_analysis: Optional[
            Dict[str, Any]
        ],
    ) -> str:

        providers = set(
            self._provider_names_from_plan(
                plan,
                selected_modules,
            )
        )

        providers.update(
            self._provider_names_from_target(
                target_analysis
            )
        )

        if not providers:
            return ""

        blocks = []

        for provider in sorted(
            providers
        ):

            identifier = (
                self._terraform_identifier(
                    provider
                )
            )

            if identifier == "azurerm":

                blocks.append(
                    """terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}"""
                )

                continue

            # Generic fallback.
            blocks.append(
                "\n".join(
                    [
                        "terraform {",
                        "  required_providers {",
                        f"    {identifier} = {{",
                        (
                            f'      source = '
                            f'"{identifier}"'
                        ),
                        "    }",
                        "  }",
                        "}",
                        "",
                        (
                            f'provider '
                            f'"{identifier}" {{'
                        ),
                        "}",
                    ]
                )
            )

        return (
            "\n\n".join(
                blocks
            )
            + "\n"
        )

    # ============================================================
    # PLAN NORMALIZATION
    # ============================================================

    def _normalize_plan(
        self,
        plan: Any,
    ) -> Dict[str, Any]:

        if isinstance(
            plan,
            dict,
        ):
            return plan

        for attribute in (
            "plan",
            "data",
            "result",
            "generation_plan",
        ):

            value = getattr(
                plan,
                attribute,
                None,
            )

            if isinstance(
                value,
                dict,
            ):
                return value

        raise TypeError(
            "Generation plan must be "
            "a dictionary or expose a "
            "dictionary through "
            "plan/data/result/"
            "generation_plan."
        )

    # ============================================================
    # terraform.tfvars
    # ============================================================

    @staticmethod
    def _format_tfvars_value(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, str):
            return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        if isinstance(value, list):
            return "[" + ", ".join(TerraformGenerator._format_tfvars_value(v) for v in value) + "]"
        if isinstance(value, dict):
            return "{ " + ", ".join('"' + str(k) + '" = ' + TerraformGenerator._format_tfvars_value(v) for k, v in value.items()) + " }"
        return TerraformGenerator._format_tfvars_value(str(value))

    def _generate_tfvars(
        self,
        plan: Dict[str, Any],
        variable_values: Optional[Dict[str, Any]] = None,
    ) -> str:
        values = variable_values or {}
        metadata = self._collect_variable_metadata(
            plan,
            None,
            plan.get("target_analysis"),
        )
        mappings_by_name = set()
        for action in self._plan_actions(plan):
            mappings = action.get("mappings") or action.get("mapping") or {}
            if isinstance(mappings, dict):
                mappings_by_name.update(str(k) for k in mappings)

        lines=[]
        for name, item in sorted(metadata.items()):
            if name in mappings_by_name:
                continue
            if isinstance(item, dict) and item.get("generated") is True:
                continue
            value = values[name] if name in values else item.get("default") if isinstance(item,dict) and "default" in item else None
            if name not in values and not (isinstance(item,dict) and "default" in item):
                continue
            lines.append(f"{name} = {self._format_tfvars_value(value)}")
        return "\n\n".join(lines) + ("\n" if lines else "# No user-configurable Terraform variables.\n")

    # ============================================================
    # GENERATE
    # ============================================================

    def generate(
        self,
        plan: Any,
        selected_modules: Optional[Any] = None,
        target_analysis: Optional[Dict[str, Any]] = None,
        variable_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Terraform from a READY generation plan.

        IMPORTANT:
            `plan` is the GenerationPlanner result.

        Do not pass a natural-language request here.
        """

        plan = self._normalize_plan(
            plan
        )

        status = str(
            plan.get(
                "status",
                "",
            )
        ).strip().upper()

        if status != "READY":

            return {
                "status": "BLOCKED",
                "reason": (
                    "Terraform generation "
                    "was blocked because "
                    "the generation plan "
                    f"status is "
                    f"'{status or 'UNKNOWN'}'."
                ),
                "output_directory": None,
                "files": [],
            }

        if selected_modules is None:

            selected_modules = []

            for action in (
                self._plan_actions(
                    plan
                )
            ):

                module = (
                    action.get(
                        "catalog"
                    )
                    or action.get(
                        "module_definition"
                    )
                    or action.get(
                        "definition"
                    )
                )

                if not isinstance(
                    module,
                    dict,
                ):
                    continue

                name = (
                    module.get("name")
                    or action.get(
                        "module"
                    )
                    or action.get(
                        "name"
                    )
                )

                if name:
                    selected_modules.append(
                        module
                    )

        if target_analysis is None:

            target_analysis = (
                plan.get(
                    "target_analysis"
                )
            )

        # The generated/ directory is a request-scoped workspace.
        # Remove the previous generation completely so stale files
        # (for example generated/modules/vnet/*) can never leak into
        # a later fresh-infrastructure request.
        if self.output_dir.exists():
            if self.output_dir.is_dir():
                shutil.rmtree(self.output_dir)
            else:
                self.output_dir.unlink()

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        main_tf = (
            self._generate_main_tf(
                plan,
                selected_modules,
                target_analysis,
            )
        )

        variables_tf = (
            self._generate_variables_tf(
                plan,
                selected_modules,
                target_analysis,
            )
        )

        outputs_tf = (
            self._generate_outputs_tf(
                plan,
                selected_modules,
            )
        )

        providers_tf = (
            self._generate_providers_tf(
                plan,
                selected_modules,
                target_analysis,
            )
        )

        files = {
            "main.tf": main_tf,
            "variables.tf": variables_tf,
            "outputs.tf": outputs_tf,
            "providers.tf": providers_tf,
            "terraform.tfvars": self._generate_tfvars(plan, variable_values),
        }

        generated_files = []

        for filename, content in (
            files.items()
        ):

            path = (
                self.output_dir
                / filename
            )

            path.write_text(
                content,
                encoding="utf-8",
            )

            generated_files.append(
                str(path)
            )

        return {
            "status": "GENERATED",
            "reason": (
                "Terraform configuration "
                "generated successfully."
            ),
            "repository": (
                self.target_repository
            ),
            "branch": (
                self.target_branch
            ),
            "output_directory": str(
                self.output_dir
            ),
            "files": generated_files,
        }

    # ============================================================
    # GITHUB PUBLISH / PULL REQUEST
    # ============================================================

    def publish_to_github(
        self,
        plan: Dict[str, Any],
        working_branch: Optional[str] = None,
        pr_title: str = "AI Terraform Generation",
    ) -> Dict[str, Any]:
        """Create the selected working branch, publish only the current
        generated root Terraform files, and open a PR.

        The publisher intentionally does NOT recursively upload the entire
        ``generated/`` directory. That directory is cleaned on every
        generation, but publishing is additionally allow-listed so stale or
        unexpected nested files can never reach the PR.
        """
        if str(plan.get("status", "")).upper() != "READY":
            raise ValueError("Cannot publish because the generation plan is not READY.")

        from github import Github

        token = os.getenv("GITHUB_TOKEN")
        owner = os.getenv("GITHUB_OWNER")
        if not token or not owner:
            raise ValueError("GITHUB_TOKEN and GITHUB_OWNER must be configured")

        repository_name = plan.get("repository") or self.target_repository
        base_branch = plan.get("branch") or self.target_branch
        branch_name = (working_branch or plan.get("working_branch") or "").strip()

        if not repository_name:
            raise ValueError("Target repository is required.")
        if not base_branch:
            raise ValueError("Base branch is required.")
        if not branch_name:
            raise ValueError("Working branch is required.")
        if branch_name == base_branch:
            raise ValueError("Working branch must be different from the base branch.")

        if not self.output_dir.exists() or not self.output_dir.is_dir():
            raise FileNotFoundError(
                "Generated Terraform directory does not exist. Generate Terraform first."
            )

        # Only these files belong to the generated root configuration.
        # Nested module source files are deliberately excluded.
        allowed_files = (
            "main.tf",
            "variables.tf",
            "outputs.tf",
            "providers.tf",
            "terraform.tfvars",
        )

        files_to_publish = []
        for filename in allowed_files:
            path = self.output_dir / filename
            if path.is_file():
                files_to_publish.append((filename, path))

        if not files_to_publish:
            raise FileNotFoundError(
                "No generated Terraform files were found. Generate Terraform first."
            )

        # Safety check: a nested modules directory is never part of the
        # publish set. It may exist only if something external created it.
        nested_paths = [
            path
            for path in self.output_dir.rglob("*")
            if path.is_file() and path.relative_to(self.output_dir).parts
            and len(path.relative_to(self.output_dir).parts) > 1
        ]
        if nested_paths:
            # Do not fail the PR because of stale local artifacts; simply
            # ignore them. The explicit allow-list above is authoritative.
            pass

        repo = Github(token).get_repo(f"{owner}/{repository_name}")

        # Verify the base branch exists before creating anything remotely.
        base_ref = repo.get_git_ref(f"heads/{base_branch}")

        try:
            repo.get_branch(branch_name)
            raise ValueError(
                f"Working branch '{branch_name}' already exists. Choose a new branch name."
            )
        except ValueError:
            raise
        except Exception as exc:
            if getattr(exc, "status", None) != 404:
                raise

        # Create the working branch from the exact selected base branch.
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base_ref.object.sha,
        )

        published = []
        for relative, path in files_to_publish:
            content = path.read_text(encoding="utf-8")
            try:
                existing = repo.get_contents(relative, ref=branch_name)
                repo.update_file(
                    relative,
                    f"AI Terraform generation: update {relative}",
                    content,
                    existing.sha,
                    branch=branch_name,
                )
            except Exception as exc:
                if getattr(exc, "status", None) != 404:
                    raise
                repo.create_file(
                    relative,
                    f"AI Terraform generation: add {relative}",
                    content,
                    branch=branch_name,
                )
            published.append(relative)

        pr = repo.create_pull(
            title=pr_title,
            body=(
                "Generated by Terraform AI Copilot. Review before merging. "
                "Only the current generated root Terraform files are included. "
                "Terraform CLI validation is not performed by the publisher."
            ),
            head=branch_name,
            base=base_branch,
        )

        return {
            "status": "PUBLISHED",
            "repository": f"{owner}/{repository_name}",
            "base_branch": base_branch,
            "branch": branch_name,
            "files": published,
            "pull_request": {
                "number": pr.number,
                "url": pr.html_url,
                "title": pr.title,
                "state": pr.state,
                "head_branch": branch_name,
                "base_branch": base_branch,
            },
        }

    # ============================================================
    # DISPLAY
    # ============================================================

    @staticmethod
    def print_result(
        result: Dict[str, Any],
    ) -> None:

        print()
        print("=" * 60)
        print(
            "TERRAFORM GENERATION"
        )
        print("=" * 60)

        print(
            f"Status : "
            f"{result.get('status')}"
        )

        print(
            f"Reason : "
            f"{result.get('reason')}"
        )

        if result.get(
            "repository"
        ):
            print(
                f"Repository : "
                f"{result.get('repository')}"
            )

        if result.get(
            "branch"
        ):
            print(
                f"Branch     : "
                f"{result.get('branch')}"
            )

        print()
        print(
            "Output directory:"
        )

        print(
            f"  "
            f"{result.get('output_directory')}"
        )

        print()
        print(
            "Generated files:"
        )

        for filename in (
            result.get(
                "files",
                [],
            )
        ):
            print(
                f"  - {filename}"
            )

        print("=" * 60)


# ================================================================
# DIRECT EXECUTION
# ================================================================

def main() -> None:
    """
    Direct production execution.

    This mode uses every approved module in the catalog.
    The normal application path should instead obtain
    selected_modules from AIPlanner + ModuleSelector.
    """

    load_dotenv()

    planner = GenerationPlanner()

    catalog_modules = (
        planner._get_all_catalog_modules()
    )

    if not catalog_modules:
        raise RuntimeError(
            "No approved modules were "
            "found in the module catalog."
        )

    selected_modules = []

    for module in catalog_modules:

        if not isinstance(
            module,
            dict,
        ):
            continue

        name = (
            planner._normalize(
                module.get(
                    "name"
                )
            )
        )

        if name:
            selected_modules.append(
                {
                    "module": name
                }
            )

    if not selected_modules:
        raise RuntimeError(
            "No valid approved modules "
            "were found in the catalog."
        )

    generation_plan = (
        planner.build(
            selected_modules=selected_modules
        )
    )

    planner.print_plan(
        generation_plan
    )

    if generation_plan.get(
        "status"
    ) != "READY":

        raise RuntimeError(
            "Generation plan is not READY."
        )

    generator = TerraformGenerator()

    result = generator.generate(
        plan=generation_plan,
        selected_modules=catalog_modules,
        target_analysis=(
            generation_plan.get(
                "target_analysis"
            )
        ),
    )

    generator.print_result(
        result
    )


if __name__ == "__main__":
    main()