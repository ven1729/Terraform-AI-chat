from app.modules.catalog import ModuleCatalog


class AISelector:
    """
    Deterministic approved-module selector.

    The LLM decides what the user asked for.
    This class selects only from modules present in modules.json.
    It does not invent module names.
    """

    PRIMARY_SCORE = 200
    PRIMARY_TAG_SCORE = 100
    SUPPORTING_SCORE = 50
    SUMMARY_SCORE = 10
    RESOURCE_SCORE = 20

    def __init__(self):
        self.catalog = ModuleCatalog()

    def select_modules(self, plan):
        primary_services = {
            str(service).lower()
            for service in plan.get("primary_services", [])
        }

        supporting_services = {
            str(service).lower()
            for service in plan.get("supporting_services", [])
        }

        recommendations = []

        for module in self.catalog.get_all_modules():
            module_name = str(module.get("name", "")).lower()

            tags = {
                str(tag).lower()
                for tag in module.get("tags", [])
            }

            summary = str(
                module.get("summary", "")
            ).lower()

            score = 0
            reasons = []

            # Primary services
            for service in primary_services:
                if service == module_name:
                    score += self.PRIMARY_SCORE
                    reasons.append(f"primary:{service}")

                if service in tags:
                    score += self.PRIMARY_TAG_SCORE
                    reasons.append(f"primary-tag:{service}")

                if service and service in summary:
                    score += self.SUMMARY_SCORE
                    reasons.append(f"summary:{service}")

            # Supporting services
            for service in supporting_services:
                if service in tags:
                    score += self.SUPPORTING_SCORE
                    reasons.append(f"support:{service}")

                if service and service in summary:
                    score += self.SUMMARY_SCORE
                    reasons.append(f"summary-support:{service}")

            # Resource-type evidence
            for resource in module.get("resources", []):
                resource_type = str(
                    resource.get("type", "")
                ).lower()

                for service in primary_services | supporting_services:
                    normalized = service.replace("-", "").replace("_", "")
                    resource_normalized = (
                        resource_type
                        .replace("-", "")
                        .replace("_", "")
                    )

                    if normalized and normalized in resource_normalized:
                        score += self.RESOURCE_SCORE
                        reasons.append(
                            f"resource:{resource_type}"
                        )

            if score > 0:
                recommendations.append({
                    "module": module_name,
                    "score": score,
                    "summary": module.get("summary", ""),
                    "dependencies": module.get("dependencies", []),
                    "reasons": sorted(set(reasons)),
                })

        recommendations.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return recommendations

    def select_primary_and_supporting(self, plan):
        recommendations = self.select_modules(plan)

        primary = set(
            str(x).lower()
            for x in plan.get("primary_services", [])
        )
        supporting = set(
            str(x).lower()
            for x in plan.get("supporting_services", [])
        )

        selected = []

        for item in recommendations:
            name = item["module"].lower()

            # Look up catalog metadata so a supporting concept such as
            # "networking" can select a module named "vnet".
            module = self.catalog.get_module(name)
            tags = {
                str(tag).lower()
                for tag in (module or {}).get("tags", [])
            }

            if name in primary or tags.intersection(primary):
                item["selection_type"] = "primary"
                selected.append(item)
                continue

            if name in supporting or tags.intersection(supporting):
                item["selection_type"] = "supporting"
                selected.append(item)

        # Preserve all recommendations for display, while
        # selected_modules contains only directly relevant approved modules.
        return {
            "recommendations": recommendations,
            "selected_modules": selected,
        }
