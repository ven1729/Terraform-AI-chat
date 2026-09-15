import os
import copy
import inspect

from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from app.modules.catalog import ModuleCatalog
from app.target.analyzer import TargetRepositoryAnalyzer
from app.target.duplicate_checker import DuplicateChecker
from app.generation.review_resolver import ReviewResolver


class GenerationPlanner:
    """
    Build a Terraform generation plan from:

        selected modules
            ↓
        dependency resolution
            ↓
        target repository analysis
            ↓
        duplicate / compatibility analysis
            ↓
        review resolution
            ↓
        CREATE / REUSE / ADAPT / REVIEW / BLOCKED

    The planner produces a generation-ready action contract
    for generator.py.
    """

    def __init__(
        self,
        target_repository: Optional[str] = None,
        target_branch: Optional[str] = None,
    ):
        load_dotenv()

        self.catalog = ModuleCatalog()

        target_repository = (
            target_repository
            or os.getenv("TARGET_REPO")
        )

        if not target_repository:
            raise ValueError(
                "TARGET_REPO is not configured"
            )

        target_branch = (
            target_branch
            or os.getenv("TARGET_BRANCH", "main")
        )

        self.target_repository = (
            target_repository
        )

        self.target_branch = (
            target_branch
        )

        # Keep the analyzer compatible with both versions of the
        # TargetRepositoryAnalyzer API: some versions accept the branch
        # in the constructor, while older versions read it from their
        # environment/configuration.
        analyzer_kwargs = {}
        try:
            parameters = inspect.signature(TargetRepositoryAnalyzer).parameters
            if "branch" in parameters:
                analyzer_kwargs["branch"] = self.target_branch
            elif "branch_name" in parameters:
                analyzer_kwargs["branch_name"] = self.target_branch
            elif "target_branch" in parameters:
                analyzer_kwargs["target_branch"] = self.target_branch
        except (TypeError, ValueError):
            analyzer_kwargs = {}

        self.target_analyzer = TargetRepositoryAnalyzer(
            target_repository,
            **analyzer_kwargs,
        )

        # Also expose the selected branch on common attribute names for
        # analyzers that resolve the branch at analyze() time.
        for attribute in ("branch", "branch_name", "target_branch"):
            try:
                setattr(self.target_analyzer, attribute, self.target_branch)
            except Exception:
                pass

        self.duplicate_checker = (
            DuplicateChecker()
        )

        self.review_resolver = (
            ReviewResolver()
        )

    # =========================================================
    # NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize(
        value: Any,
    ) -> str:
        """
        Normalize values returned by parsers,
        catalog data, or Terraform analysis.
        """

        if value is None:
            return ""

        value = str(
            value
        ).strip()

        if len(value) >= 2:

            if (
                value[0] == '"'
                and value[-1] == '"'
            ):
                value = value[1:-1]

        return value

    @staticmethod
    def _module_name(
        module: Any,
    ) -> str:
        """
        Extract a module name from:

            "aks"

        or:

            {"module": "aks"}

        or:

            {"name": "aks"}

        or:

            {"module_name": "aks"}
        """

        if isinstance(
            module,
            str,
        ):
            return module

        if isinstance(
            module,
            dict,
        ):

            for key in (
                "module",
                "name",
                "module_name",
            ):

                value = module.get(
                    key
                )

                if value:
                    return str(
                        value
                    )

        return ""

    # =========================================================
    # CATALOG
    # =========================================================

    def _get_catalog_module(
        self,
        module_name: str,
    ) -> Optional[
        Dict[str, Any]
    ]:
        """
        Retrieve one approved module from ModuleCatalog.
        """

        module_name = (
            self._normalize(
                module_name
            )
        )

        if not module_name:
            return None

        # -----------------------------------------------------
        # Current ModuleCatalog API.
        # -----------------------------------------------------

        get_module = getattr(
            self.catalog,
            "get_module",
            None,
        )

        if callable(
            get_module
        ):

            module = get_module(
                module_name
            )

            if module:
                return module

        # -----------------------------------------------------
        # Compatibility fallback.
        # -----------------------------------------------------

        find = getattr(
            self.catalog,
            "find",
            None,
        )

        if callable(
            find
        ):

            module = find(
                module_name
            )

            if module:
                return module

        # -----------------------------------------------------
        # Compatibility fallback.
        # -----------------------------------------------------

        get = getattr(
            self.catalog,
            "get",
            None,
        )

        if callable(
            get
        ):

            module = get(
                module_name
            )

            if module:
                return module

        # -----------------------------------------------------
        # Last-resort collection lookup.
        # -----------------------------------------------------

        modules = (
            self._get_all_catalog_modules()
        )

        for module in modules:

            if not isinstance(
                module,
                dict,
            ):
                continue

            name = self._normalize(
                module.get(
                    "name"
                )
            )

            if (
                name.lower()
                == module_name.lower()
            ):

                return module

        return None

    def _get_all_catalog_modules(
        self,
    ) -> List[
        Dict[str, Any]
    ]:
        """
        Retrieve all approved modules.

        Supports the current ModuleCatalog API and
        compatibility fallbacks.
        """

        get_all = getattr(
            self.catalog,
            "get_all_modules",
            None,
        )

        if callable(
            get_all
        ):

            modules = get_all()

            if isinstance(
                modules,
                list,
            ):
                return list(
                    modules
                )

            if isinstance(
                modules,
                dict,
            ):
                return list(
                    modules.values()
                )

        # -----------------------------------------------------
        # Compatibility fallbacks.
        # -----------------------------------------------------

        for method_name in (
            "list_modules",
            "all_modules",
            "modules",
        ):

            method = getattr(
                self.catalog,
                method_name,
                None,
            )

            if callable(
                method
            ):

                modules = method()

                if isinstance(
                    modules,
                    list,
                ):
                    return list(
                        modules
                    )

                if isinstance(
                    modules,
                    dict,
                ):
                    return list(
                        modules.values()
                    )

        # -----------------------------------------------------
        # Inspect catalog object directly.
        # -----------------------------------------------------

        for attribute_name in (
            "catalog",
            "data",
            "catalog_data",
        ):

            data = getattr(
                self.catalog,
                attribute_name,
                None,
            )

            if not isinstance(
                data,
                dict,
            ):
                continue

            module_list = data.get(
                "modules"
            )

            if isinstance(
                module_list,
                list,
            ):
                return list(
                    module_list
                )

            if isinstance(
                module_list,
                dict,
            ):
                return list(
                    module_list.values()
                )

        return []

    # =========================================================
    # TARGET ANALYSIS
    # =========================================================

    def _analyze_target(
        self,
    ) -> Dict[str, Any]:
        """
        Analyze the current target repository.
        """

        # Keep legacy analyzers that read TARGET_REPO / TARGET_BRANCH from
        # environment synchronized with the exact runtime selection.
        os.environ["TARGET_REPO"] = self.target_repository
        os.environ["TARGET_BRANCH"] = self.target_branch

        analyze = getattr(self.target_analyzer, "analyze")

        # Prefer an explicit branch argument when supported. This prevents
        # a selected UI branch from accidentally falling back to TARGET_BRANCH.
        try:
            parameters = inspect.signature(analyze).parameters
            if "branch" in parameters:
                return analyze(branch=self.target_branch)
            if "branch_name" in parameters:
                return analyze(branch_name=self.target_branch)
            if "target_branch" in parameters:
                return analyze(target_branch=self.target_branch)
        except (TypeError, ValueError):
            pass

        return analyze()

    # =========================================================
    # DUPLICATE CHECK
    # =========================================================

    def _run_duplicate_check(
        self,
        module_name: str,
        target_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run DuplicateChecker using its current API.

        DuplicateChecker.check_module() expects:

            selected_module
            analysis
        """

        return (
            self.duplicate_checker.check_module(
                {
                    "module": module_name,
                },
                target_analysis,
            )
        )

    # =========================================================
    # REVIEW RESULT NORMALIZATION
    # =========================================================

    @staticmethod
    def _parse_list_string(
        value: str,
    ) -> List[str]:
        """
        Parse simple list strings emitted by
        DuplicateChecker.

        Example:

            "['subnet_id']"

        becomes:

            ["subnet_id"]
        """

        value = value.strip()

        if not value:
            return []

        if (
            value.startswith("[")
            and value.endswith("]")
        ):

            value = (
                value[1:-1]
                .strip()
            )

        if not value:
            return []

        result = []

        for item in value.split(","):

            item = item.strip()

            if len(item) >= 2:

                if (
                    item[0]
                    in (
                        "'",
                        '"',
                    )
                    and item[-1]
                    == item[0]
                ):

                    item = item[1:-1]

            item = item.strip()

            if item:
                result.append(
                    item
                )

        return result

    @staticmethod
    def _prepare_review_result(
        duplicate_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize DuplicateChecker compatibility
        data into the structure expected by
        ReviewResolver.

        DuplicateChecker may expose:

            compatibility = {
                "differences": [
                    "missing inputs: [...]",
                    "additional inputs: [...]",
                    "missing outputs: [...]",
                    "additional outputs: [...]"
                ]
            }

        ReviewResolver expects:

            compatibility = {
                "missing_inputs": [...],
                "additional_inputs": [...],
                "missing_outputs": [...],
                "additional_outputs": [...]
            }
        """

        if not isinstance(
            duplicate_result,
            dict,
        ):
            return duplicate_result

        compatibility = (
            duplicate_result.get(
                "compatibility"
            )
        )

        if not isinstance(
            compatibility,
            dict,
        ):
            return duplicate_result

        normalized = dict(
            duplicate_result
        )

        normalized_compatibility = (
            dict(
                compatibility
            )
        )

        # -----------------------------------------------------
        # Existing explicit values.
        # -----------------------------------------------------

        missing_inputs = list(
            normalized_compatibility.get(
                "missing_inputs",
                [],
            )
            or []
        )

        additional_inputs = list(
            normalized_compatibility.get(
                "additional_inputs",
                [],
            )
            or []
        )

        missing_outputs = list(
            normalized_compatibility.get(
                "missing_outputs",
                [],
            )
            or []
        )

        additional_outputs = list(
            normalized_compatibility.get(
                "additional_outputs",
                [],
            )
            or []
        )

        # -----------------------------------------------------
        # Parse differences list.
        # -----------------------------------------------------

        differences = (
            normalized_compatibility.get(
                "differences",
                [],
            )
            or []
        )

        for difference in differences:

            if not isinstance(
                difference,
                str,
            ):
                continue

            text = difference.strip()

            if ":" not in text:
                continue

            label, raw_value = (
                text.split(
                    ":",
                    1,
                )
            )

            label = (
                label.strip()
                .lower()
            )

            parsed = (
                GenerationPlanner
                ._parse_list_string(
                    raw_value
                )
            )

            if label == "missing inputs":

                if not missing_inputs:
                    missing_inputs = parsed

            elif label == "additional inputs":

                if not additional_inputs:
                    additional_inputs = parsed

            elif label == "missing outputs":

                if not missing_outputs:
                    missing_outputs = parsed

            elif label == "additional outputs":

                if not additional_outputs:
                    additional_outputs = parsed

        normalized_compatibility[
            "missing_inputs"
        ] = missing_inputs

        normalized_compatibility[
            "additional_inputs"
        ] = additional_inputs

        normalized_compatibility[
            "missing_outputs"
        ] = missing_outputs

        normalized_compatibility[
            "additional_outputs"
        ] = additional_outputs

        normalized[
            "compatibility"
        ] = normalized_compatibility

        return normalized

    # =========================================================
    # REVIEW RESOLUTION
    # =========================================================

    def _resolve_review(
        self,
        module_name: str,
        duplicate_result: Dict[str, Any],
        target_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Resolve a REVIEW using ReviewResolver.
        """

        if (
            duplicate_result.get(
                "decision"
            )
            != "REVIEW"
        ):

            return {
                "module": module_name,
                "status": "NO_REVIEW",
                "resolution": (
                    duplicate_result.get(
                        "decision"
                    )
                ),
                "requires_user_input": False,
                "message": (
                    "No review resolution is required."
                ),
                "mapping": {},
            }

        review_input = (
            self._prepare_review_result(
                duplicate_result
            )
        )

        return (
            self.review_resolver.resolve(
                module_name=module_name,
                duplicate_result=review_input,
                target_analysis=target_analysis,
            )
        )

    # =========================================================
    # GENERATION CATALOG HELPERS
    # =========================================================

    @staticmethod
    def _normalize_provider(
        provider: Any,
    ) -> Optional[str]:
        """
        Normalize provider metadata.

        Examples:

            "azurerm"
                -> "azurerm"

            ["azurerm"]
                -> "azurerm"

            {"name": "azurerm"}
                -> "azurerm"
        """

        if provider is None:
            return None

        if isinstance(
            provider,
            str,
        ):

            value = (
                provider.strip()
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
                    GenerationPlanner
                    ._normalize_provider(
                        item
                    )
                )

                if value:
                    return value

            return None

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
                    GenerationPlanner
                    ._normalize_provider(
                        provider.get(
                            key
                        )
                    )
                )

                if value:
                    return value

            return None

        return str(
            provider
        ).strip()

    def _target_variable_metadata(
        self,
        variable_name: str,
        target_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Find metadata for one variable in the target
        repository analysis.
        """

        variables = (
            target_analysis.get(
                "variables",
                [],
            )
            or []
        )

        # -----------------------------------------------------
        # Variables represented as a list.
        # -----------------------------------------------------

        if isinstance(
            variables,
            list,
        ):

            for variable in variables:

                if not isinstance(
                    variable,
                    dict,
                ):
                    continue

                name = (
                    variable.get(
                        "name"
                    )
                    or variable.get(
                        "variable"
                    )
                    or variable.get(
                        "key"
                    )
                )

                if (
                    self._normalize(
                        name
                    )
                    == self._normalize(
                        variable_name
                    )
                ):

                    return dict(
                        variable
                    )

        # -----------------------------------------------------
        # Variables represented as a dictionary.
        # -----------------------------------------------------

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

                result = dict(
                    value
                )

                result.setdefault(
                    "name",
                    variable_name,
                )

                return result

        # -----------------------------------------------------
        # Safe fallback.
        # -----------------------------------------------------

        return {
            "name": variable_name,
            "type": "any",
            "description": (
                f"Input variable '{variable_name}'"
            ),
        }

    def _get_target_module_inputs(
        self,
        module_name: str,
        duplicate_result: Dict[str, Any],
        target_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build the actual input interface of the
        existing target module.

        DuplicateChecker provides:

            compatibility.target_inputs

        Example:

            [
                "address_space",
                "location",
                "resource_group_name",
                "subnets",
                "tags",
                "vnet_name"
            ]
        """

        compatibility = (
            duplicate_result.get(
                "compatibility",
                {},
            )
            or {}
        )

        target_inputs = (
            compatibility.get(
                "target_inputs",
                [],
            )
            or []
        )

        result = {}

        # -----------------------------------------------------
        # Target inputs as a list.
        # -----------------------------------------------------

        if isinstance(
            target_inputs,
            list,
        ):

            for item in target_inputs:

                if isinstance(
                    item,
                    str,
                ):

                    variable_name = (
                        item.strip()
                    )

                elif isinstance(
                    item,
                    dict,
                ):

                    variable_name = (
                        item.get(
                            "name"
                        )
                        or item.get(
                            "variable"
                        )
                    )

                    if variable_name:

                        variable_name = str(
                            variable_name
                        ).strip()

                else:
                    continue

                if not variable_name:
                    continue

                result[
                    variable_name
                ] = (
                    self._target_variable_metadata(
                        variable_name,
                        target_analysis,
                    )
                )

        # -----------------------------------------------------
        # Target inputs as a dictionary.
        # -----------------------------------------------------

        elif isinstance(
            target_inputs,
            dict,
        ):

            for variable_name, metadata in (
                target_inputs.items()
            ):

                variable_name = str(
                    variable_name
                ).strip()

                if not variable_name:
                    continue

                if isinstance(
                    metadata,
                    dict,
                ):

                    value = dict(
                        metadata
                    )

                    value.setdefault(
                        "name",
                        variable_name,
                    )

                    result[
                        variable_name
                    ] = value

                else:

                    result[
                        variable_name
                    ] = (
                        self._target_variable_metadata(
                            variable_name,
                            target_analysis,
                        )
                    )

        return result

    def _build_generation_catalog(
        self,
        module_name: str,
        catalog_module: Dict[str, Any],
        action_type: str,
        duplicate_result: Dict[str, Any],
        target_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build the catalog representation that
        generator.py should consume.

        CREATE:
            approved module interface

        REUSE:
            target module interface

        ADAPT:
            target module interface

        The original approved catalog is never mutated.
        """

        effective_catalog = (
            copy.deepcopy(
                catalog_module
            )
        )

        effective_catalog[
            "name"
        ] = module_name

        # -----------------------------------------------------
        # Normalize provider.
        # -----------------------------------------------------

        provider = (
            self._normalize_provider(
                effective_catalog.get(
                    "provider"
                )
            )
        )

        if provider:

            effective_catalog[
                "provider"
            ] = provider

        action_type = str(
            action_type or ""
        ).strip().upper()

        # =====================================================
        # REUSE / ADAPT
        # =====================================================

        if action_type in {
            "REUSE",
            "ADAPT",
        }:

            target_inputs = (
                self._get_target_module_inputs(
                    module_name=module_name,
                    duplicate_result=duplicate_result,
                    target_analysis=target_analysis,
                )
            )

            if target_inputs:

                effective_catalog[
                    "inputs"
                ] = target_inputs

            effective_catalog[
                "source_type"
            ] = "local"

            effective_catalog[
                "implementation"
            ] = "target"

        # =====================================================
        # CREATE
        # =====================================================

        else:

            effective_catalog[
                "source_type"
            ] = "remote"

            effective_catalog[
                "implementation"
            ] = "approved"

        return effective_catalog

    # =========================================================
    # DEPENDENCIES
    # =========================================================

    def _dependency_names(
        self,
        module: Dict[str, Any],
    ) -> List[str]:
        """
        Extract dependency module names from catalog metadata.
        """

        dependencies = module.get(
            "dependencies",
            [],
        )

        result = []

        # -----------------------------------------------------
        # Dictionary representation.
        # -----------------------------------------------------

        if isinstance(
            dependencies,
            dict,
        ):

            for key in dependencies:

                name = (
                    self._normalize(
                        key
                    )
                )

                if name:
                    result.append(
                        name
                    )

            return result

        # -----------------------------------------------------
        # List representation.
        # -----------------------------------------------------

        if not isinstance(
            dependencies,
            list,
        ):
            return result

        for dependency in dependencies:

            if isinstance(
                dependency,
                str,
            ):

                name = (
                    self._normalize(
                        dependency
                    )
                )

            elif isinstance(
                dependency,
                dict,
            ):

                name = (
                    self._normalize(
                        dependency.get(
                            "module"
                        )
                        or dependency.get(
                            "name"
                        )
                        or dependency.get(
                            "depends_on"
                        )
                    )
                )

            else:
                continue

            if name:
                result.append(
                    name
                )

        return result

    def _build_dependency_order(
        self,
        module_names: List[str],
    ) -> List[str]:
        """
        Build dependency-first generation order.

        Example:

            aks -> vnet

        becomes:

            vnet -> aks
        """

        selected = {
            self._normalize(
                name
            )
            for name in module_names
            if self._normalize(
                name
            )
        }

        order = []

        visiting = set()

        visited = set()

        def visit(
            module_name: str,
        ):

            module_name = (
                self._normalize(
                    module_name
                )
            )

            if not module_name:
                return

            if module_name in visited:
                return

            if module_name in visiting:

                raise ValueError(
                    "Circular module dependency "
                    f"detected around "
                    f"'{module_name}'"
                )

            visiting.add(
                module_name
            )

            module = (
                self._get_catalog_module(
                    module_name
                )
            )

            if module:

                dependencies = (
                    self._dependency_names(
                        module
                    )
                )

                for dependency in dependencies:

                    if dependency in selected:

                        visit(
                            dependency
                        )

            visiting.remove(
                module_name
            )

            visited.add(
                module_name
            )

            order.append(
                module_name
            )

        for module_name in module_names:

            visit(
                module_name
            )

        return order

    def _expand_dependency_closure(
        self,
        module_names: List[str],
    ) -> List[str]:
        """
        Add every transitive catalog dependency to the selected module set.

        Example:
            selected = ["aks", "storage"]
            catalog = aks -> vnet

        becomes:
            ["aks", "storage", "vnet"]

        The ordering is applied separately by _build_dependency_order().
        This is important because a dependency must be represented as an
        actual generation action, not merely mentioned on its parent module.
        """
        result = []
        seen = set()

        def add(name: str) -> None:
            normalized = self._normalize(name)
            if not normalized or normalized.lower() in seen:
                return

            seen.add(normalized.lower())
            result.append(normalized)

            module = self._get_catalog_module(normalized)
            if not module:
                return

            for dependency in self._dependency_names(module):
                add(dependency)

        for module_name in module_names:
            add(module_name)

        return result

    # =========================================================
    # MODULE ACTION
    # =========================================================

    def _build_module_action(
        self,
        module_name: str,
        catalog_module: Dict[str, Any],
        duplicate_result: Dict[str, Any],
        target_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert duplicate-check and review results into
        one generation-ready action.
        """

        decision = str(
            duplicate_result.get(
                "decision",
                "",
            )
        ).upper()

        dependencies = (
            self._dependency_names(
                catalog_module
            )
        )

        # -----------------------------------------------------
        # Build the initial generation catalog.
        # -----------------------------------------------------

        effective_catalog = (
            self._build_generation_catalog(
                module_name=module_name,
                catalog_module=catalog_module,
                action_type=decision,
                duplicate_result=duplicate_result,
                target_analysis=target_analysis,
            )
        )

        action = {
            "module": module_name,

            "action": decision,

            "decision": decision,

            "reason": (
                duplicate_result.get(
                    "reason",
                    "",
                )
            ),

            "dependencies": dependencies,

            # Generation-ready catalog.
            "catalog": effective_catalog,

            # Original approved catalog.
            "approved_catalog": copy.deepcopy(
                catalog_module
            ),

            "duplicate_check": (
                duplicate_result
            ),

            "review": None,

            # Canonical mapping.
            "mappings": {},

            # Backward-compatible singular mapping.
            "mapping": {},

            # Explicit resolved input expressions.
            "resolved_inputs": {},
        }

        # =====================================================
        # CREATE
        # =====================================================

        if decision == "CREATE":

            action[
                "action"
            ] = "CREATE"

            return action

        # =====================================================
        # REUSE
        # =====================================================

        if decision == "REUSE":

            action[
                "action"
            ] = "REUSE"

            return action

        # =====================================================
        # UNKNOWN DECISION
        # =====================================================

        if decision != "REVIEW":

            action[
                "action"
            ] = "BLOCKED"

            action[
                "blocked"
            ] = True

            return action

        # =====================================================
        # REVIEW
        # =====================================================

        review_result = (
            self._resolve_review(
                module_name,
                duplicate_result,
                target_analysis,
            )
        )

        action[
            "review"
        ] = review_result

        status = str(
            review_result.get(
                "status",
                "",
            )
        ).upper()

        # =====================================================
        # RESOLVED -> ADAPT
        # =====================================================

        if status == "RESOLVED":

            action[
                "action"
            ] = "ADAPT"

            action[
                "decision"
            ] = "ADAPT"

            # -------------------------------------------------
            # ReviewResolver returns:
            #
            # {
            #     "subnet_id":
            #         'module.vnet.subnet_ids["subnet1"]'
            # }
            # -------------------------------------------------

            mappings = (
                review_result.get(
                    "mapping",
                    {},
                )
                or {}
            )

            if not isinstance(
                mappings,
                dict,
            ):

                mappings = {}

            mappings = dict(
                mappings
            )

            # -------------------------------------------------
            # Store in all compatible fields.
            # -------------------------------------------------

            action[
                "mappings"
            ] = dict(
                mappings
            )

            action[
                "mapping"
            ] = dict(
                mappings
            )

            action[
                "resolved_inputs"
            ] = dict(
                mappings
            )

            # -------------------------------------------------
            # Selected subnet.
            # -------------------------------------------------

            selected_subnet = (
                review_result.get(
                    "selected_subnet"
                )
            )

            if selected_subnet:

                action[
                    "selected_subnet"
                ] = selected_subnet

            # -------------------------------------------------
            # Reason.
            # -------------------------------------------------

            action[
                "reason"
            ] = (
                review_result.get(
                    "message"
                )
                or review_result.get(
                    "resolution"
                )
                or duplicate_result.get(
                    "reason",
                    "",
                )
            )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # Rebuild catalog using the existing target
            # module interface.
            #
            # Approved VNet:
            #
            #     subnet_name
            #     subnet_prefixes
            #
            # Target VNet:
            #
            #     subnets
            #
            # Therefore generator.py will generate:
            #
            #     subnets = var.subnets
            #
            # instead of:
            #
            #     subnet_name = var.subnet_name
            #     subnet_prefixes = var.subnet_prefixes
            # -------------------------------------------------

            action[
                "catalog"
            ] = (
                self._build_generation_catalog(
                    module_name=module_name,
                    catalog_module=catalog_module,
                    action_type="ADAPT",
                    duplicate_result=duplicate_result,
                    target_analysis=target_analysis,
                )
            )

            return action

        # =====================================================
        # NEEDS USER INPUT
        # =====================================================

        if status == "NEEDS_USER_INPUT":

            action[
                "action"
            ] = "REVIEW"

            action[
                "user_input_required"
            ] = True

            return action

        # =====================================================
        # BLOCKED
        # =====================================================

        action[
            "action"
        ] = "BLOCKED"

        action[
            "blocked"
        ] = True

        return action

    # =========================================================
    # SUMMARY
    # =========================================================

    @staticmethod
    def _empty_summary() -> Dict[str, int]:
        return {
            "CREATE": 0,
            "REUSE": 0,
            "ADAPT": 0,
            "REVIEW": 0,
            "BLOCKED": 0,
        }

    @classmethod
    def _summarize(
        cls,
        actions: List[
            Dict[str, Any]
        ],
    ) -> Dict[str, int]:

        summary = (
            cls._empty_summary()
        )

        for action in actions:

            action_type = str(
                action.get(
                    "action",
                    "BLOCKED",
                )
            ).upper()

            if action_type not in summary:
                action_type = "BLOCKED"

            summary[
                action_type
            ] += 1

        return summary

    # =========================================================
    # READINESS
    # =========================================================

    @staticmethod
    def _is_ready(
        actions: List[
            Dict[str, Any]
        ],
    ) -> bool:

        for action in actions:

            action_type = str(
                action.get(
                    "action",
                    "",
                )
            ).upper()

            if action_type in {
                "REVIEW",
                "BLOCKED",
            }:

                return False

        return True

    # =========================================================
    # BUILD PLAN
    # =========================================================

    def build(
        self,
        selected_modules: List[Any],
        target_analysis: Optional[Dict[str, Any]] = None,
        infrastructure_decisions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Build the complete Terraform generation plan.

        Supports:

            ["aks", "vnet", "storage"]

        and:

            [
                {"module": "aks"},
                {"module": "vnet"},
                {"module": "storage"},
            ]

        Rich selected-module dictionaries are also supported.
        """

        print(
            "\nBuilding Terraform generation plan..."
        )

        # =====================================================
        # NORMALIZE MODULE NAMES
        # =====================================================

        module_names = []

        for selected in selected_modules:

            name = (
                self._module_name(
                    selected
                )
            )

            name = (
                self._normalize(
                    name
                )
            )

            if not name:
                continue

            if name not in module_names:

                module_names.append(
                    name
                )

        if not module_names:

            return {
                "status": "BLOCKED",
                "repository": (
                    self.target_repository
                ),
                "branch": (
                    self.target_branch
                ),
                "generation_order": [],
                "modules": [],
                "actions": [],
                "summary": (
                    self._empty_summary()
                ),
                "ready": False,
                "reason": (
                    "No modules were selected "
                    "for generation."
                ),
            }

        # =====================================================
        # EXPAND TRANSITIVE DEPENDENCIES
        # =====================================================

        # The AI selector returns user-requested modules. The generation
        # plan must also contain every approved catalog dependency so that
        # dependency modules receive their own CREATE/REUSE/ADAPT action.
        module_names = self._expand_dependency_closure(module_names)

        # =====================================================
        # ANALYZE TARGET
        # =====================================================

        if target_analysis is None:

            target_analysis = (
                self._analyze_target()
            )

        # =====================================================
        # DEPENDENCY ORDER
        # =====================================================

        generation_order = (
            self._build_dependency_order(
                module_names
            )
        )

        # =====================================================
        # ANALYZE EACH MODULE
        # =====================================================

        infrastructure_decisions = infrastructure_decisions or {}
        normalized_decisions = {
            self._normalize(key).lower(): str(value).strip().upper()
            for key, value in infrastructure_decisions.items()
            if self._normalize(key)
        }

        actions = []

        for module_name in generation_order:

            catalog_module = (
                self._get_catalog_module(
                    module_name
                )
            )

            # -------------------------------------------------
            # Missing approved catalog module.
            # -------------------------------------------------

            if not catalog_module:

                actions.append(
                    {
                        "module": module_name,
                        "action": "BLOCKED",
                        "decision": "REVIEW",
                        "reason": (
                            "Selected module is not "
                            "present in the approved "
                            "module catalog."
                        ),
                        "dependencies": [],
                        "catalog": None,
                        "approved_catalog": None,
                        "duplicate_check": None,
                        "review": None,
                        "mappings": {},
                        "mapping": {},
                        "resolved_inputs": {},
                        "blocked": True,
                    }
                )

                continue

            # -------------------------------------------------
            # Duplicate / compatibility check.
            # -------------------------------------------------

            duplicate_result = (
                self._run_duplicate_check(
                    module_name,
                    target_analysis,
                )
            )

            # -------------------------------------------------
            # Build generation action.
            # -------------------------------------------------

            user_decision = normalized_decisions.get(
                self._normalize(module_name).lower()
            )

            if user_decision == "CREATE":
                duplicate_result = dict(duplicate_result)
                duplicate_result["decision"] = "CREATE"
                duplicate_result["reason"] = (
                    "User selected creation of a new approved module "
                    "instead of reusing existing infrastructure."
                )

            elif user_decision == "USE_EXISTING":
                duplicate_result = dict(duplicate_result)
                automatic_decision = str(
                    duplicate_result.get("decision", "")
                ).upper()

                # An explicit user choice wins over automatic duplicate
                # classification. If the branch contains an existing module
                # call or directory, use it rather than blocking on REVIEW.
                if automatic_decision in {"REVIEW", "REUSE"}:
                    duplicate_result["decision"] = "REUSE"
                    duplicate_result["reason"] = (
                        "User selected reuse of the existing Terraform "
                        "infrastructure found on the selected branch."
                    )

            action = (
                self._build_module_action(
                    module_name,
                    catalog_module,
                    duplicate_result,
                    target_analysis,
                )
            )

            if user_decision:
                action["user_decision"] = user_decision

            actions.append(
                action
            )

        # =====================================================
        # SUMMARY
        # =====================================================

        summary = (
            self._summarize(
                actions
            )
        )

        ready = (
            self._is_ready(
                actions
            )
        )

        status = (
            "READY"
            if ready
            else "BLOCKED"
        )

        # =====================================================
        # REASON
        # =====================================================

        if ready:

            reason = (
                "All selected modules are ready "
                "for Terraform generation."
            )

        else:

            attention = [
                action[
                    "module"
                ]
                for action in actions
                if action.get(
                    "action"
                ) in {
                    "REVIEW",
                    "BLOCKED",
                }
            ]

            reason = (
                "Generation cannot proceed because "
                "one or more selected modules require "
                "review or are blocked."
            )

            if attention:

                reason += (
                    " Modules requiring attention: "
                    + ", ".join(
                        attention
                    )
                    + "."
                )

        return {
            "status": status,

            "repository": (
                self.target_repository
            ),

            "branch": (
                self.target_branch
            ),

            "generation_order": (
                generation_order
            ),

            "modules": actions,

            "actions": actions,

            "summary": summary,

            "ready": ready,

            "reason": reason,

            "target_analysis": (
                target_analysis
            ),
        }

    # =========================================================
    # VARIABLE SCHEMA FOR UI
    # =========================================================

    def get_variable_schema(
        self,
        generation_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Return unique user-configurable root variables."""
        actions = generation_plan.get("actions") or generation_plan.get("modules") or []
        result=[]
        seen=set()
        target_analysis=generation_plan.get("target_analysis") or {}
        variables=target_analysis.get("variables", []) if isinstance(target_analysis,dict) else []
        variable_map={}
        if isinstance(variables,dict): variable_map=variables
        elif isinstance(variables,list):
            for item in variables:
                if isinstance(item,dict) and item.get("name"): variable_map[item["name"]]=item

        for action in actions:
            if not isinstance(action,dict): continue
            action_type=str(action.get("action","")).upper()
            if action_type not in {"CREATE","REUSE","ADAPT"}: continue
            module_name=self._normalize(action.get("module"))
            catalog=action.get("catalog") or action.get("approved_catalog") or {}
            if not isinstance(catalog,dict): continue
            inputs=catalog.get("inputs",[]) or []
            if isinstance(inputs,dict):
                inputs=[dict(v,name=k) if isinstance(v,dict) else {"name":k,"type":v} for k,v in inputs.items()]
            # For existing implementations, use the actual target interface when available.
            if action_type in {"ADAPT","REUSE"}:
                target_inputs=(action.get("duplicate_check") or {}).get("compatibility",{}).get("target_inputs",[])
                if target_inputs:
                    inputs=[]
                    for name in target_inputs:
                        name=str(name); meta=dict(variable_map.get(name,{})); meta.setdefault("name",name); inputs.append(meta)
            mappings=action.get("mappings") or action.get("mapping") or {}
            if not isinstance(mappings,dict): mappings={}
            for item in inputs:
                if not isinstance(item,dict): continue
                name=self._normalize(item.get("name") or item.get("input_name") or item.get("variable"))
                if not name or name in mappings or any(self._normalize(k)==name for k in mappings): continue
                if item.get("generated") is True: continue
                ui=item.get("ui") or {}
                if isinstance(ui,dict) and ui.get("control")=="computed": continue
                if name in seen: continue
                seen.add(name)
                result.append({"module":module_name,"name":name,"type":item.get("type","string"),"required":bool(item.get("required",False)),"default":item.get("default"),"description":item.get("description",""),"ui":ui})
        return result

    # =========================================================
    # PRINT
    # =========================================================

    @staticmethod
    def print_plan(
        plan: Dict[str, Any],
    ) -> None:

        print()

        print(
            "=" * 60
        )

        print(
            "TERRAFORM GENERATION PLAN"
        )

        print(
            "=" * 60
        )

        print(
            f"Status     : "
            f"{plan.get('status', 'UNKNOWN')}"
        )

        print(
            f"Repository : "
            f"{plan.get('repository', '')}"
        )

        print(
            f"Branch     : "
            f"{plan.get('branch', '')}"
        )

        print(
            f"Reason     : "
            f"{plan.get('reason', '')}"
        )

        # =====================================================
        # GENERATION ORDER
        # =====================================================

        print()

        print(
            "Generation Order"
        )

        generation_order = (
            plan.get(
                "generation_order",
                [],
            )
        )

        if not generation_order:

            print(
                "  No modules"
            )

        else:

            for index, module_name in enumerate(
                generation_order,
                start=1,
            ):

                print(
                    f"  {index}. "
                    f"{module_name}"
                )

        # =====================================================
        # MODULE ACTIONS
        # =====================================================

        print()

        print(
            "Module Actions"
        )

        actions = (
            plan.get(
                "actions",
                [],
            )
        )

        if not actions:

            print(
                "  No module actions"
            )

        for action in actions:

            module_name = (
                action.get(
                    "module",
                    "unknown",
                )
            )

            action_type = (
                action.get(
                    "action",
                    "UNKNOWN",
                )
            )

            print()

            print(
                f"  {module_name} "
                f"→ {action_type}"
            )

            reason = (
                action.get(
                    "reason"
                )
            )

            if reason:

                print(
                    f"      Reason: "
                    f"{reason}"
                )

            dependencies = (
                action.get(
                    "dependencies",
                    [],
                )
            )

            if dependencies:

                print(
                    "      Dependencies: "
                    + ", ".join(
                        dependencies
                    )
                )

            mappings = (
                action.get(
                    "mappings",
                    {},
                )
            )

            if mappings:

                print(
                    "      Mappings:"
                )

                for source, target in (
                    mappings.items()
                ):

                    print(
                        f"        "
                        f"{source} = "
                        f"{target}"
                    )

            selected_subnet = (
                action.get(
                    "selected_subnet"
                )
            )

            if selected_subnet:

                print(
                    "      Selected subnet: "
                    f"{selected_subnet}"
                )

            # -------------------------------------------------
            # Generation catalog information.
            # -------------------------------------------------

            catalog = (
                action.get(
                    "catalog"
                )
            )

            if isinstance(
                catalog,
                dict,
            ):

                source_type = (
                    catalog.get(
                        "source_type"
                    )
                )

                implementation = (
                    catalog.get(
                        "implementation"
                    )
                )

                if source_type:

                    print(
                        "      Source type: "
                        f"{source_type}"
                    )

                if implementation:

                    print(
                        "      Implementation: "
                        f"{implementation}"
                    )

            review = (
                action.get(
                    "review"
                )
            )

            if isinstance(
                review,
                dict,
            ):

                if review.get(
                    "requires_user_input"
                ):

                    print(
                        "      User input "
                        "required: yes"
                    )

        # =====================================================
        # SUMMARY
        # =====================================================

        summary = (
            plan.get(
                "summary",
                {},
            )
        )

        print()

        print(
            "=" * 60
        )

        print(
            "SUMMARY"
        )

        print(
            "=" * 60
        )

        print(
            f"CREATE : "
            f"{summary.get('CREATE', 0)}"
        )

        print(
            f"REUSE  : "
            f"{summary.get('REUSE', 0)}"
        )

        print(
            f"ADAPT  : "
            f"{summary.get('ADAPT', 0)}"
        )

        print(
            f"REVIEW : "
            f"{summary.get('REVIEW', 0)}"
        )

        print(
            f"BLOCKED: "
            f"{summary.get('BLOCKED', 0)}"
        )

        print()

        if (
            plan.get(
                "status"
            )
            == "READY"
        ):

            print(
                "Generation is READY."
            )

        else:

            print(
                "Generation is BLOCKED."
            )

        print(
            "=" * 60
        )


# =============================================================
# DIRECT EXECUTION
# =============================================================

def main():

    load_dotenv()

    planner = (
        GenerationPlanner()
    )

    # ---------------------------------------------------------
    # Direct execution uses all approved catalog modules.
    #
    # The real chat flow will pass only the modules selected
    # by the AI planner/selector.
    # ---------------------------------------------------------

    catalog_modules = (
        planner._get_all_catalog_modules()
    )

    selected_modules = []

    for module in catalog_modules:

        if not isinstance(
            module,
            dict,
        ):
            continue

        module_name = (
            planner._normalize(
                module.get(
                    "name"
                )
            )
        )

        if module_name:

            selected_modules.append(
                {
                    "module": module_name
                }
            )

    if not selected_modules:

        raise ValueError(
            "No approved modules were found "
            "in the catalog."
        )

    plan = planner.build(
        selected_modules
    )

    planner.print_plan(
        plan
    )


if __name__ == "__main__":
    main()