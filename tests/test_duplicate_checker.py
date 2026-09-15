import os

from dotenv import load_dotenv

from app.catalog.catalog import ModuleCatalog
from app.target.analyzer import TargetRepositoryAnalyzer
from app.target.duplicate_checker import DuplicateChecker


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# LOAD APPROVED MODULE CATALOG
# =========================================================

catalog = ModuleCatalog()


# =========================================================
# TARGET REPOSITORY CONFIGURATION
# =========================================================

repository = os.getenv("TARGET_REPO")

if not repository:
    raise ValueError(
        "TARGET_REPO is not configured in .env"
    )

branch = os.getenv(
    "TARGET_BRANCH",
    "main",
)


# =========================================================
# ANALYZE TARGET REPOSITORY
# =========================================================

print()
print("Analyzing target repository...")

analyzer = TargetRepositoryAnalyzer(
    repository_name=repository,
    branch_name=branch,
)

target_analysis = analyzer.analyze()


# =========================================================
# DISPLAY TARGET SUMMARY
# =========================================================

print()
print(
    f"Repository: "
    f"{target_analysis['repository']}"
)

print(
    f"Branch: "
    f"{target_analysis['branch']}"
)

print(
    f"Terraform files: "
    f"{len(target_analysis['files'])}"
)

print(
    f"Module directories: "
    f"{len(target_analysis['module_directories'])}"
)

print(
    f"Resources: "
    f"{len(target_analysis['resources'])}"
)


# =========================================================
# SIMULATE SELECTED MODULES
# =========================================================

selected_modules = [
    {"module": "vnet"},
    {"module": "aks"},
    {"module": "storage"},
]


print()
print("Selected modules:")

for module in selected_modules:
    print(
        f"  - {module['module']}"
    )


# =========================================================
# RUN DUPLICATE CHECK
# =========================================================

checker = DuplicateChecker(
    catalog
)

decisions = checker.check(
    selected_modules,
    target_analysis,
)


# =========================================================
# DISPLAY DECISIONS
# =========================================================

print()
print("=" * 60)
print("CREATE / REUSE / REVIEW")
print("=" * 60)

for decision in decisions:

    print()

    print(
        f"Module   : "
        f"{decision['module']}"
    )

    print(
        f"Decision : "
        f"{decision['decision']}"
    )

    print(
        f"Reason   : "
        f"{decision['reason']}"
    )

    # Existing module call
    if "existing_module" in decision:

        existing = decision[
            "existing_module"
        ]

        print(
            f"Existing module: "
            f"{existing}"
        )

    # Existing module directory
    if "existing_module_directory" in decision:

        directory = decision[
            "existing_module_directory"
        ]

        print(
            f"Existing directory: "
            f"{directory}"
        )

    # Existing resources
    if "existing_resources" in decision:

        print(
            "Existing resources:"
        )

        for resource in decision[
            "existing_resources"
        ]:

            print(
                f"  - "
                f"{resource['type']}."
                f"{resource['name']}"
                f" "
                f"({resource.get('file')})"
            )


# =========================================================
# SUMMARY
# =========================================================

summary = checker.summarize(
    decisions
)

print()
print("=" * 60)
print("DECISION SUMMARY")
print("=" * 60)

print(
    f"CREATE : {summary['CREATE']}"
)

print(
    f"REUSE  : {summary['REUSE']}"
)

print(
    f"REVIEW : {summary['REVIEW']}"
)

print()
print("Duplicate check complete.")