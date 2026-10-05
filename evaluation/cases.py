"""
Curated research questions used to evaluate the pipeline.

Each case has:
  id         — stable identifier for diffing across runs
  question   — what gets sent to the pipeline
  category   — what kind of question this is (used for reporting)
  depth      — quick / standard / deep / exhaustive
  notes      — what a "good" outcome looks like (informational, not graded yet)
"""

CASES = [
    {
        "id": "simple-factual",
        "question": "What is the boiling point of water at sea level?",
        "category": "simple_factual",
        "depth": "quick",
        "notes": "Should be a single, uncontroversial number (100°C / 212°F).",
    },
    {
        "id": "scientific",
        "question": "Is intermittent fasting effective for weight loss?",
        "category": "scientific",
        "depth": "standard",
        "notes": "Expect moderate-to-high confidence, several studies cited, "
                 "and caveats about adherence and long-term effects.",
    },
    {
        "id": "historical",
        "question": "What caused the 2008 financial crisis?",
        "category": "historical",
        "depth": "standard",
        "notes": "Well-documented. Expect multiple sources and coherent causal narrative.",
    },
    {
        "id": "controversial",
        "question": "Does remote work increase or decrease productivity?",
        "category": "controversial",
        "depth": "standard",
        "notes": "Expect genuine disagreement in the sources. The answer should "
                 "reflect both sides rather than pick one.",
    },
    {
        "id": "ambiguous",
        "question": "Is coffee good for you?",
        "category": "ambiguous",
        "depth": "standard",
        "notes": "Vague by design. The analysis stage should narrow it. "
                 "Answer should hedge appropriately.",
    },
    {
        "id": "conflicting-sources",
        "question": "Do vitamin D supplements reduce the severity of COVID-19?",
        "category": "conflicting_sources",
        "depth": "deep",
        "notes": "Genuinely mixed evidence in the literature. Expect the "
                 "different_context classifier to fire.",
    },
    {
        "id": "current-events",
        "question": "What is the current state of nuclear fusion research?",
        "category": "current_events",
        "depth": "standard",
        "notes": "Recent developments. Sources should be reasonably recent.",
    },
    {
        "id": "no-useful-sources",
        "question": "What was the exact agenda of the private meeting held "
                    "in the town of Xyzzyplugh on 2019-03-14?",
        "category": "no_useful_sources",
        "depth": "quick",
        "notes": "Deliberately unanswerable. The pipeline should fail cleanly "
                 "(no verified sources) rather than invent an answer.",
    },
]