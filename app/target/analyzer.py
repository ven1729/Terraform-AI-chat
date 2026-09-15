import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.github_client.client import GitHubClient


class TargetRepositoryAnalyzer:
    """
    Analyze Terraform in the entire selected repository branch.

    Important design rule:
        Terraform location is arbitrary.

    Root-level files such as main.tf/variables.tf/outputs.tf are scanned,
    as are Terraform files under any directory. No resource/module folder
    naming convention is required.
    """

    BLOCK_PATTERNS = {
        "resource": re.compile(
            r'(?m)^\s*resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
        ),
        "data": re.compile(
            r'(?m)^\s*data\s+"([^"]+)"\s+"([^"]+)"\s*\{'
        ),
        "module": re.compile(
            r'(?m)^\s*module\s+"([^"]+)"\s*\{'
        ),
        "variable": re.compile(
            r'(?m)^\s*variable\s+"([^"]+)"\s*\{'
        ),
        "output": re.compile(
            r'(?m)^\s*output\s+"([^"]+)"\s*\{'
        ),
        "provider": re.compile(
            r'(?m)^\s*provider\s+"([^"]+)"\s*\{'
        ),
    }

    TERRAFORM_BLOCK_PATTERN = re.compile(
        r'(?m)^\s*terraform\s*\{'
    )

    # Simple attribute extraction is deliberately conservative. It is used
    # for inventory/duplicate analysis, not to evaluate Terraform.
    SOURCE_PATTERN = re.compile(
        r'(?m)^\s*source\s*=\s*"([^"]+)"'
    )
    TYPE_PATTERN = re.compile(
        r'(?m)^\s*type\s*=\s*(.+?)\s*$'
    )
    DEFAULT_PATTERN = re.compile(
        r'(?m)^\s*default\s*=\s*(.+?)\s*$'
    )
    DESCRIPTION_PATTERN = re.compile(
        r'(?m)^\s*description\s*=\s*"([^"]*)"'
    )

    def __init__(
        self,
        repository_name: Optional[str] = None,
        branch_name: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> None:
        self.github = GitHubClient()
        self.repository_name = repository_name
        self.branch_name = branch_name or branch

    @staticmethod
    def _clean(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _directory(path: str) -> str:
        path = str(path or "").strip().strip("/")
        return path.rsplit("/", 1)[0] if "/" in path else ""

    @staticmethod
    def _basename(path: str) -> str:
        path = str(path or "").strip().strip("/")
        if not path:
            return "."
        return path.rsplit("/", 1)[-1]

    @staticmethod
    def _line_number(content: str, offset: int) -> int:
        return content.count("\n", 0, offset) + 1

    @staticmethod
    def _strip_inline_comment(value: str) -> str:
        value = str(value or "").strip()
        if " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        return value

    def _extract_modules(
        self,
        content: str,
        path: str,
    ) -> List[Dict[str, Any]]:
        results = []
        for match in self.BLOCK_PATTERNS["module"].finditer(content):
            name = match.group(1)
            block_start = match.end()
            block_end = self._find_block_end(content, block_start)
            body = content[block_start:block_end]
            source_match = self.SOURCE_PATTERN.search(body)
            source = source_match.group(1).strip() if source_match else ""
            results.append(
                {
                    "name": name,
                    "source": source,
                    "path": path,
                    "line": self._line_number(content, match.start()),
                }
            )
        return results

    def _extract_variables(
        self,
        content: str,
        path: str,
    ) -> List[Dict[str, Any]]:
        results = []
        for match in self.BLOCK_PATTERNS["variable"].finditer(content):
            name = match.group(1)
            block_start = match.end()
            block_end = self._find_block_end(content, block_start)
            body = content[block_start:block_end]
            type_match = self.TYPE_PATTERN.search(body)
            default_match = self.DEFAULT_PATTERN.search(body)
            description_match = self.DESCRIPTION_PATTERN.search(body)
            results.append(
                {
                    "name": name,
                    "type": self._strip_inline_comment(type_match.group(1)) if type_match else "",
                    "default": self._strip_inline_comment(default_match.group(1)) if default_match else None,
                    "description": description_match.group(1) if description_match else "",
                    "path": path,
                    "line": self._line_number(content, match.start()),
                }
            )
        return results

    def _extract_outputs(
        self,
        content: str,
        path: str,
    ) -> List[Dict[str, Any]]:
        results = []
        for match in self.BLOCK_PATTERNS["output"].finditer(content):
            results.append(
                {
                    "name": match.group(1),
                    "path": path,
                    "line": self._line_number(content, match.start()),
                }
            )
        return results

    def _extract_resources(
        self,
        content: str,
        path: str,
    ) -> List[Dict[str, Any]]:
        results = []
        for match in self.BLOCK_PATTERNS["resource"].finditer(content):
            results.append(
                {
                    "type": match.group(1),
                    "name": match.group(2),
                    "path": path,
                    "line": self._line_number(content, match.start()),
                }
            )
        return results

    def _extract_data_sources(
        self,
        content: str,
        path: str,
    ) -> List[Dict[str, Any]]:
        results = []
        for match in self.BLOCK_PATTERNS["data"].finditer(content):
            results.append(
                {
                    "type": match.group(1),
                    "name": match.group(2),
                    "path": path,
                    "line": self._line_number(content, match.start()),
                }
            )
        return results

    def _extract_providers(
        self,
        content: str,
        path: str,
    ) -> List[Dict[str, Any]]:
        results = []
        for match in self.BLOCK_PATTERNS["provider"].finditer(content):
            results.append(
                {
                    "name": match.group(1),
                    "path": path,
                    "line": self._line_number(content, match.start()),
                }
            )
        return results

    @staticmethod
    def _find_block_end(content: str, start: int) -> int:
        """Find the matching closing brace for a Terraform block."""
        depth = 1
        in_string = False
        escaped = False
        in_line_comment = False
        in_block_comment = False
        i = start

        while i < len(content):
            char = content[i]
            next_char = content[i + 1] if i + 1 < len(content) else ""

            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                if char == "*" and next_char == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if not in_string and char == "#":
                in_line_comment = True
                i += 1
                continue

            if not in_string and char == "/" and next_char == "/":
                in_line_comment = True
                i += 2
                continue

            if not in_string and char == "/" and next_char == "*":
                in_block_comment = True
                i += 2
                continue

            if char == '"' and not escaped:
                in_string = not in_string
                i += 1
                continue

            if in_string:
                escaped = char == "\\" and not escaped
                if char != "\\":
                    escaped = False
                i += 1
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return i

            i += 1

        return len(content)

    def analyze(self) -> Dict[str, Any]:
        repository = self._clean(self.repository_name)
        branch = self._clean(self.branch_name)

        if not repository:
            raise ValueError("Target repository is not configured.")
        if not branch:
            raise ValueError("Target branch is not configured.")

        files = self.github.get_terraform_files(repository, branch)

        resources: List[Dict[str, Any]] = []
        data_sources: List[Dict[str, Any]] = []
        modules: List[Dict[str, Any]] = []
        variables: List[Dict[str, Any]] = []
        outputs: List[Dict[str, Any]] = []
        providers: List[Dict[str, Any]] = []
        terraform_files: List[Dict[str, Any]] = []
        directories: Dict[str, Dict[str, Any]] = {}

        for file in files:
            path = file["path"]
            content = file["content"]
            directory = file.get("directory", self._directory(path))

            terraform_files.append(
                {
                    "path": path,
                    "name": file["name"],
                    "directory": directory,
                }
            )

            directory_entry = directories.setdefault(
                directory,
                {
                    "name": self._basename(directory),
                    "path": directory,
                    "terraform_files": [],
                    "resource_count": 0,
                    "module_count": 0,
                    "variable_count": 0,
                    "output_count": 0,
                },
            )
            directory_entry["terraform_files"].append(file["name"])

            file_resources = self._extract_resources(content, path)
            file_data_sources = self._extract_data_sources(content, path)
            file_modules = self._extract_modules(content, path)
            file_variables = self._extract_variables(content, path)
            file_outputs = self._extract_outputs(content, path)
            file_providers = self._extract_providers(content, path)

            resources.extend(file_resources)
            data_sources.extend(file_data_sources)
            modules.extend(file_modules)
            variables.extend(file_variables)
            outputs.extend(file_outputs)
            providers.extend(file_providers)

            directory_entry["resource_count"] += len(file_resources)
            directory_entry["module_count"] += len(file_modules)
            directory_entry["variable_count"] += len(file_variables)
            directory_entry["output_count"] += len(file_outputs)

        # Directory-level Terraform configurations. Root is represented as
        # '.' and is intentionally retained for infrastructure inventory.
        terraform_directories = sorted(
            directories.values(),
            key=lambda item: item["path"].lower(),
        )

        # `module_directories` is only the non-root subset. This keeps the
        # existing DuplicateChecker contract while allowing arbitrary paths.
        module_directories = [
            item
            for item in terraform_directories
            if item["path"]
        ]

        # Stable unique provider list.
        provider_names = []
        seen_providers = set()
        for provider in providers:
            name = provider["name"]
            if name not in seen_providers:
                seen_providers.add(name)
                provider_names.append(name)
        provider_names.sort(key=str.lower)

        return {
            "repository": repository,
            "branch": branch,
            "scan_mode": "branch-wide-recursive",
            "terraform_file_count": len(terraform_files),
            "terraform_files": terraform_files,
            "terraform_directories": terraform_directories,
            "module_directories": module_directories,
            "module_directory_count": len(module_directories),
            "resources": resources,
            "resource_count": len(resources),
            "data_sources": data_sources,
            "data_source_count": len(data_sources),
            "modules": modules,
            "module_call_count": len(modules),
            "variables": variables,
            "variable_count": len(variables),
            "outputs": outputs,
            "output_count": len(outputs),
            "providers": provider_names,
            "provider_blocks": providers,
            "exists": True,
            "message": (
                f"Scanned {len(terraform_files)} Terraform file(s) across the "
                f"entire '{branch}' branch."
                if terraform_files
                else f"No Terraform .tf files were found anywhere on branch '{branch}'."
            ),
        }


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    analyzer = TargetRepositoryAnalyzer(
        repository_name=os.getenv("TARGET_REPO"),
        branch_name=os.getenv("TARGET_BRANCH", "main"),
    )
    result = analyzer.analyze()
    print(result["message"])
    print(f"Resources : {result['resource_count']}")
    print(f"Modules   : {result['module_call_count']}")
    print(f"Variables : {result['variable_count']}")
    print(f"Outputs   : {result['output_count']}")