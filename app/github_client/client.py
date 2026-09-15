import os
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from github import Github


class GitHubClient:
    """
    GitHub access layer for the Terraform AI Copilot.

    Target-repository scanning is branch-wide. It does NOT assume that
    Terraform lives under modules/. A repository may contain Terraform at:

        main.tf
        infrastructure/main.tf
        terraform/network.tf
        modules/vnet/main.tf
        any/other/path/*.tf

    The scanner uses the Git tree for the selected branch, then reads the
    Terraform blobs. This makes the target scan independent of directory
    naming conventions.
    """

    SKIP_DIRECTORIES = {
        ".git",
        ".github",
        ".terraform",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".idea",
        ".vscode",
        "generated",
    }

    def __init__(self) -> None:
        load_dotenv()

        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN is not configured")

        self.owner_name = os.getenv("GITHUB_OWNER")
        if not self.owner_name:
            raise ValueError("GITHUB_OWNER is not configured")

        self.github = Github(token)
        self.user = self.github.get_user()

    def get_repository(self, repository_name: str):
        repository_name = str(repository_name or "").strip()
        if not repository_name:
            raise ValueError("Repository name cannot be empty")
        return self.github.get_repo(f"{self.owner_name}/{repository_name}")

    def get_contents(
        self,
        repository_name: str,
        path: str = "",
        branch_name: Optional[str] = None,
    ):
        repo = self.get_repository(repository_name)
        return repo.get_contents(path, ref=branch_name)

    def get_file_content(
        self,
        repository_name: str,
        file_path: str,
        branch_name: Optional[str] = None,
    ) -> str:
        repo = self.get_repository(repository_name)
        file = repo.get_contents(file_path, ref=branch_name)
        if isinstance(file, list):
            raise ValueError(f"Path is a directory, not a file: {file_path}")
        return file.decoded_content.decode("utf-8")

    # =========================================================
    # REPOSITORY / BRANCH DISCOVERY
    # =========================================================

    def list_repositories(self, writable_only: bool = True) -> List[Dict[str, Any]]:
        repositories: List[Dict[str, Any]] = []

        for repo in self.user.get_repos(type="all"):
            permissions = getattr(repo, "permissions", None)
            can_push = (
                bool(getattr(permissions, "push", False))
                if permissions
                else False
            )

            if writable_only and not can_push:
                continue

            repositories.append(
                {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "default_branch": repo.default_branch,
                    "private": bool(repo.private),
                    "description": repo.description or "",
                    "can_push": can_push,
                }
            )

        repositories.sort(key=lambda item: item["name"].lower())
        return repositories

    def list_branches(self, repository_name: str) -> List[Dict[str, Any]]:
        repo = self.get_repository(repository_name)
        branches: List[Dict[str, Any]] = []

        for branch in repo.get_branches():
            branches.append(
                {
                    "name": branch.name,
                    "protected": bool(branch.protected),
                }
            )

        branches.sort(
            key=lambda item: (
                item["name"] != repo.default_branch,
                item["name"].lower(),
            )
        )
        return branches

    # =========================================================
    # BRANCH-WIDE TERRAFORM SCAN
    # =========================================================

    @staticmethod
    def _normalize_path(path: str) -> str:
        return str(path or "").strip().strip("/").replace("\\", "/")

    @classmethod
    def _is_skipped_path(cls, path: str) -> bool:
        parts = [part for part in cls._normalize_path(path).split("/") if part]
        return any(
            part.startswith(".") or part in cls.SKIP_DIRECTORIES
            for part in parts
        )

    def _branch_tree(self, repo, branch_name: str):
        branch = repo.get_branch(branch_name.strip())
        tree = repo.get_git_tree(branch.commit.sha, recursive=True)
        return tree

    def _read_blob(self, repo, blob_sha: str) -> str:
        blob = repo.get_git_blob(blob_sha)
        if getattr(blob, "encoding", None) == "base64":
            import base64

            return base64.b64decode(blob.content).decode("utf-8")
        return str(blob.content or "")

    def get_terraform_files(
        self,
        repository_name: str,
        branch_name: str,
    ) -> List[Dict[str, Any]]:
        """Return every .tf file anywhere in the selected branch."""
        repo = self.get_repository(repository_name)
        tree = self._branch_tree(repo, branch_name)

        if getattr(tree, "truncated", False):
            raise RuntimeError(
                "GitHub returned a truncated repository tree. "
                "The branch is too large for a complete recursive scan."
            )

        files: List[Dict[str, Any]] = []

        for item in tree.tree:
            path = self._normalize_path(getattr(item, "path", ""))
            item_type = getattr(item, "type", None)

            if item_type != "blob":
                continue
            if not path.lower().endswith(".tf"):
                continue
            if self._is_skipped_path(path):
                continue

            files.append(
                {
                    "path": path,
                    "name": path.rsplit("/", 1)[-1],
                    "directory": path.rsplit("/", 1)[0] if "/" in path else "",
                    "sha": getattr(item, "sha", ""),
                    "content": self._read_blob(repo, item.sha),
                }
            )

        files.sort(key=lambda item: item["path"].lower())
        return files

    def scan_terraform_branch(
        self,
        repository_name: str,
        branch_name: str,
    ) -> Dict[str, Any]:
        """
        Branch-wide metadata scan.

        This is intentionally content-oriented. It includes root-level
        Terraform files and Terraform files under arbitrary directories.
        It does not require folders named after resources or modules.
        """
        files = self.get_terraform_files(repository_name, branch_name)

        directories: Dict[str, Dict[str, Any]] = {}
        for file in files:
            directory = file["directory"]
            entry = directories.setdefault(
                directory,
                {
                    "name": directory.rsplit("/", 1)[-1] if directory else ".",
                    "path": directory,
                    "terraform_files": [],
                },
            )
            entry["terraform_files"].append(file["name"])

        terraform_directories = sorted(
            directories.values(),
            key=lambda item: item["path"].lower(),
        )

        return {
            "repository": repository_name,
            "branch": branch_name,
            "scan_mode": "branch-wide-recursive",
            "exists": True,
            "terraform_file_count": len(files),
            "terraform_files": [
                {
                    "path": file["path"],
                    "name": file["name"],
                    "directory": file["directory"],
                }
                for file in files
            ],
            "terraform_directories": terraform_directories,
            "module_count": len(terraform_directories),
            "modules": [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "terraform_files": sorted(item["terraform_files"]),
                }
                for item in terraform_directories
                if item["path"]
            ],
            "message": (
                f"Scanned {len(files)} Terraform file(s) across the entire "
                f"'{branch_name}' branch."
                if files
                else (
                    f"No Terraform .tf files were found anywhere on "
                    f"branch '{branch_name}'."
                )
            ),
            # Internal use by TargetRepositoryAnalyzer. Kept out of the UI
            # presentation path by the backend's response normalization.
            "_terraform_file_contents": files,
        }

    # Backward-compatible name used by the existing UI/backend.
    def list_existing_modules(
        self,
        repository_name: str,
        branch_name: str,
        modules_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Backward-compatible branch inventory API.

        `modules_root` is ignored for normal operation. The entire selected
        branch is scanned so root-level main.tf/variables.tf/outputs.tf and
        arbitrary Terraform directories are included.
        """
        return self.scan_terraform_branch(repository_name, branch_name)

    def inspect_module(
        self,
        repository_name: str,
        branch_name: str,
        module_name: str,
        modules_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspect a discovered Terraform directory by exact path/name."""
        inventory = self.scan_terraform_branch(repository_name, branch_name)
        wanted = str(module_name or "").strip().lower()

        matches = [
            module
            for module in inventory.get("modules", [])
            if str(module.get("name", "")).lower() == wanted
        ]

        if not matches:
            raise ValueError(
                f"Terraform directory '{module_name}' was not found on branch "
                f"'{branch_name}'."
            )

        return matches[0]

    # =========================================================
    # WORKING BRANCH MANAGEMENT
    # =========================================================

    def branch_exists(
        self,
        repository_name: str,
        branch_name: str,
    ) -> bool:
        repo = self.get_repository(repository_name)
        try:
            repo.get_branch(branch_name.strip())
            return True
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return False
            raise

    def validate_new_branch_name(
        self,
        repository_name: str,
        branch_name: str,
    ) -> Dict[str, Any]:
        branch_name = branch_name.strip()
        if not branch_name:
            return {
                "valid": False,
                "message": "Working branch name cannot be empty.",
            }

        if branch_name in {"main", "master"}:
            return {
                "valid": False,
                "message": "Use a new working branch instead of the base branch.",
            }

        if self.branch_exists(repository_name, branch_name):
            return {
                "valid": False,
                "message": f"Branch '{branch_name}' already exists.",
            }

        return {
            "valid": True,
            "message": f"Branch '{branch_name}' is available.",
        }

    def create_branch(
        self,
        repository_name: str,
        base_branch: str,
        new_branch: str,
    ) -> Dict[str, Any]:
        repo = self.get_repository(repository_name)
        base_branch = base_branch.strip()
        new_branch = new_branch.strip()

        if not new_branch:
            raise ValueError("Working branch name cannot be empty.")
        if new_branch == base_branch:
            raise ValueError("Working branch must be different from the base branch.")
        if self.branch_exists(repository_name, new_branch):
            raise ValueError(f"Branch '{new_branch}' already exists.")

        base = repo.get_branch(base_branch)
        ref = repo.create_git_ref(
            ref=f"refs/heads/{new_branch}",
            sha=base.commit.sha,
        )

        return {
            "repository": repository_name,
            "base_branch": base_branch,
            "branch": new_branch,
            "sha": ref.object.sha,
        }


if __name__ == "__main__":
    client = GitHubClient()
    repos = client.list_repositories()
    print(f"Writable repositories: {len(repos)}")
    for repo in repos:
        print(f"- {repo['full_name']} ({repo['default_branch']})")