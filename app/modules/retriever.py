from difflib import SequenceMatcher

from modules.catalog import ModuleCatalog


class ModuleRetriever:

    def __init__(self):

        self.catalog = ModuleCatalog()

    def list_modules(self):

        return self.catalog.list_modules()

    def get_module_count(self):

        return self.catalog.get_module_count()

    def recommend(
        self,
        requirement,
        top_n=5
    ):

        requirement = requirement.lower()

        results = []

        for module in self.catalog.catalog[
            "modules"
        ]:

            score = 0
            reasons = []

            #
            # tags
            #
            for tag in module.get(
                "tags",
                []
            ):

                if tag in requirement:

                    score += 50

                    reasons.append(
                        f"tag:{tag}"
                    )

            #
            # summary
            #
            summary = module.get(
                "summary",
                ""
            ).lower