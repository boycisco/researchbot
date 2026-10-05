from dataclasses import dataclass, field
from typing import Optional, List


# Per-depth pipeline settings.
# These are defaults — tune them here, not inside the worker.
DEPTH_PROFILES = {
    "quick": {
        "max_queries":                        3,
        "max_search_results_per_query":       3,
        "max_sources_to_fetch":               6,    # fetch more
        "max_sources_to_verify":              3,    # verify top 3
        "max_claim_pairs":                   10,
        "min_confidence_for_key_findings":   60,
        "max_revisions":                      1,
    },
    "standard": {
        "max_queries":                        8,
        "max_search_results_per_query":       5,
        "max_sources_to_fetch":              12,    # fetch more
        "max_sources_to_verify":              5,    # verify top 5
        "max_claim_pairs":                   40,
        "min_confidence_for_key_findings":   70,
        "max_revisions":                      2,
    },
    "deep": {
        "max_queries":                       12,
        "max_search_results_per_query":       6,
        "max_sources_to_fetch":              20,
        "max_sources_to_verify":             10,
        "max_claim_pairs":                   80,
        "min_confidence_for_key_findings":   70,
        "max_revisions":                      3,
    },
    "exhaustive": {
        "max_queries":                       20,
        "max_search_results_per_query":       8,
        "max_sources_to_fetch":              40,
        "max_sources_to_verify":             20,
        "max_claim_pairs":                  150,
        "min_confidence_for_key_findings":   75,
        "max_revisions":                      3,
    },
}


@dataclass
class ResearchRequest:
    topic: str
    depth: str = "standard"          # quick, standard, deep, exhaustive
    recency: Optional[int] = None    # days, None = no limit
    max_sources: int = 20
    max_queries: int = 8
    language: str = "en"
    source_preferences: List[str] = field(default_factory=list)
    output_format: str = "telegram"  # telegram, markdown, json

    def __post_init__(self):
        allowed_depths = {"quick", "standard", "deep", "exhaustive"}
        if self.depth not in allowed_depths:
            raise ValueError(f"Invalid depth '{self.depth}'. Must be one of {allowed_depths}")

        if not self.topic or not self.topic.strip():
            raise ValueError("Topic cannot be empty")
        self.topic = self.topic.strip()

        if self.max_sources <= 0:
            self.max_sources = 20
        if self.max_queries <= 0:
            self.max_queries = 8

        self.source_preferences = [p.lower() for p in self.source_preferences]

        allowed_formats = {"telegram", "markdown", "json"}
        if self.output_format not in allowed_formats:
            self.output_format = "telegram"

    def profile(self) -> dict:
        """Return a copy of the pipeline settings for this request's depth."""
        return dict(DEPTH_PROFILES[self.depth])