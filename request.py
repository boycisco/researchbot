from dataclasses import dataclass, field
from typing import Optional, List

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
        # Validate depth
        allowed_depths = {"quick", "standard", "deep", "exhaustive"}
        if self.depth not in allowed_depths:
            raise ValueError(f"Invalid depth '{self.depth}'. Must be one of {allowed_depths}")

        # Basic topic validation
        if not self.topic or not self.topic.strip():
            raise ValueError("Topic cannot be empty")
        self.topic = self.topic.strip()

        # Ensure max_sources and max_queries are positive integers
        if self.max_sources <= 0:
            self.max_sources = 20
        if self.max_queries <= 0:
            self.max_queries = 8

        # Normalize source_preferences to lowercase
        self.source_preferences = [p.lower() for p in self.source_preferences]

        # Validate output_format
        allowed_formats = {"telegram", "markdown", "json"}
        if self.output_format not in allowed_formats:
            self.output_format = "telegram"