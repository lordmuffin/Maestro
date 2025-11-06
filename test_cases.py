"""
Test Cases for Maestro Evaluation Framework
Golden test suite with human-scored examples for validation
"""

from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum


class TestDifficulty(Enum):
    """Difficulty levels for test cases."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TestCategory(Enum):
    """Categories of test cases."""
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    CODE = "code"
    INSTRUCTION_FOLLOWING = "instruction_following"
    EDGE_CASE = "edge_case"


@dataclass
class TestCase:
    """
    Structured test case with human evaluation for validation.

    Attributes:
        id: Unique identifier for the test case
        category: Category of the test case (factual, analytical, creative, code)
        prompt: The prompt text to evaluate
        expected_elements: Key points that should be covered in a good response
        human_scores: Manual scores assigned by human evaluators (1-5 scale)
        difficulty: Difficulty level of the test case
        notes: Additional notes or context about the test case
    """
    id: str
    category: TestCategory
    prompt: str
    expected_elements: List[str]
    human_scores: Dict[str, float]
    difficulty: TestDifficulty
    notes: str = ""


# Golden Test Suite - Sample test cases across different categories
# These serve as baseline examples - expand to 50-100 for production use

GOLDEN_TEST_SUITE = [
    # Factual Knowledge Tests
    TestCase(
        id="TC001",
        category=TestCategory.FACTUAL,
        prompt="Explain the key differences between TCP and UDP protocols in computer networking.",
        expected_elements=[
            "Connection-oriented vs connectionless",
            "Reliability guarantees",
            "Speed tradeoffs",
            "Use case examples",
            "Header size differences"
        ],
        human_scores={
            "Factual Accuracy": 5.0,
            "Completeness": 4.5,
            "Clarity & Coherence": 4.5,
            "Relevance to Query": 5.0,
            "Appropriate Detail Level": 4.0,
        },
        difficulty=TestDifficulty.MEDIUM,
        notes="Standard networking question - tests fundamental technical knowledge"
    ),

    TestCase(
        id="TC002",
        category=TestCategory.FACTUAL,
        prompt="What are the main causes of the 2008 financial crisis?",
        expected_elements=[
            "Subprime mortgage crisis",
            "Housing bubble collapse",
            "Financial deregulation",
            "Complex financial instruments (CDOs, MBS)",
            "Credit rating failures",
            "Lehman Brothers collapse"
        ],
        human_scores={
            "Factual Accuracy": 5.0,
            "Completeness": 4.0,
            "Clarity & Coherence": 4.5,
            "Relevance to Query": 5.0,
            "Logical Consistency": 5.0,
        },
        difficulty=TestDifficulty.MEDIUM,
        notes="Tests historical and economic knowledge"
    ),

    # Analytical/Reasoning Tests
    TestCase(
        id="TC003",
        category=TestCategory.ANALYTICAL,
        prompt="Analyze the advantages and disadvantages of remote work for both employees and employers.",
        expected_elements=[
            "Employee benefits (flexibility, work-life balance)",
            "Employee challenges (isolation, distractions)",
            "Employer benefits (cost savings, talent access)",
            "Employer challenges (management, culture)",
            "Balanced perspective"
        ],
        human_scores={
            "Logical Consistency": 4.5,
            "Completeness": 4.5,
            "Clarity & Coherence": 4.5,
            "Relevance to Query": 5.0,
            "Actionability": 4.0,
        },
        difficulty=TestDifficulty.MEDIUM,
        notes="Tests analytical thinking and balanced reasoning"
    ),

    TestCase(
        id="TC004",
        category=TestCategory.ANALYTICAL,
        prompt="Compare the environmental impact of electric vehicles versus traditional gasoline cars, considering the full lifecycle.",
        expected_elements=[
            "Manufacturing emissions",
            "Battery production impact",
            "Electricity source considerations",
            "Operational emissions",
            "End-of-life recycling",
            "Lifecycle analysis perspective"
        ],
        human_scores={
            "Factual Accuracy": 4.5,
            "Logical Consistency": 5.0,
            "Completeness": 4.5,
            "Clarity & Coherence": 4.5,
            "Appropriate Detail Level": 4.5,
        },
        difficulty=TestDifficulty.HARD,
        notes="Complex multi-factor analysis requiring nuanced understanding"
    ),

    # Creative/Generative Tests
    TestCase(
        id="TC005",
        category=TestCategory.CREATIVE,
        prompt="Write a compelling elevator pitch for a startup that uses AI to help small businesses optimize their inventory management.",
        expected_elements=[
            "Problem statement",
            "Solution overview",
            "Unique value proposition",
            "Target market",
            "Call to action",
            "Concise format (30-60 seconds)"
        ],
        human_scores={
            "Clarity & Coherence": 4.5,
            "Completeness": 4.0,
            "Relevance to Query": 5.0,
            "Actionability": 4.5,
            "Appropriate Detail Level": 4.5,
        },
        difficulty=TestDifficulty.MEDIUM,
        notes="Tests creative writing and business communication"
    ),

    # Code Tests
    TestCase(
        id="TC006",
        category=TestCategory.CODE,
        prompt="Write a Python function that finds the longest palindromic substring in a given string. Include proper error handling and docstrings.",
        expected_elements=[
            "Correct algorithm implementation",
            "Edge case handling (empty string, single char)",
            "Proper docstring",
            "Error handling",
            "Efficient approach",
            "Example usage"
        ],
        human_scores={
            "Functional Correctness": 5.0,
            "Adherence to Specs": 5.0,
            "Efficiency/Performance": 4.0,
            "Readability & Style": 4.5,
            "Error Handling/Robustness": 4.5,
        },
        difficulty=TestDifficulty.MEDIUM,
        notes="Classic algorithm problem - tests coding fundamentals"
    ),

    TestCase(
        id="TC007",
        category=TestCategory.CODE,
        prompt="Create a TypeScript class for a rate limiter that allows N requests per time window. Include unit tests.",
        expected_elements=[
            "Class structure",
            "Rate limiting logic",
            "Time window handling",
            "Request tracking",
            "TypeScript types",
            "Unit tests",
            "Documentation"
        ],
        human_scores={
            "Functional Correctness": 4.5,
            "Adherence to Specs": 5.0,
            "Efficiency/Performance": 4.5,
            "Readability & Style": 4.5,
            "Error Handling/Robustness": 4.5,
        },
        difficulty=TestDifficulty.HARD,
        notes="Complex system design problem with testing requirements"
    ),

    # Instruction Following Tests
    TestCase(
        id="TC008",
        category=TestCategory.INSTRUCTION_FOLLOWING,
        prompt="List exactly 5 books about artificial intelligence, published after 2018. Format: Title (Year) by Author. Include a one-sentence description for each.",
        expected_elements=[
            "Exactly 5 books",
            "All about AI",
            "All published after 2018",
            "Correct format (Title (Year) by Author)",
            "One-sentence description per book",
            "Factual accuracy"
        ],
        human_scores={
            "Factual Accuracy": 4.5,
            "Relevance to Query": 5.0,
            "Completeness": 5.0,
            "Appropriate Detail Level": 5.0,
            "Clarity & Coherence": 4.5,
        },
        difficulty=TestDifficulty.EASY,
        notes="Tests precise instruction following and formatting"
    ),

    # Edge Cases
    TestCase(
        id="TC009",
        category=TestCategory.EDGE_CASE,
        prompt="Explain quantum computing to a 10-year-old without using technical jargon.",
        expected_elements=[
            "Simple analogies",
            "Age-appropriate language",
            "Avoidance of technical terms",
            "Engaging explanation",
            "Core concept coverage"
        ],
        human_scores={
            "Clarity & Coherence": 5.0,
            "Relevance to Query": 5.0,
            "Appropriate Detail Level": 5.0,
            "Completeness": 4.0,
            "Actionability": 4.5,
        },
        difficulty=TestDifficulty.HARD,
        notes="Tests ability to adjust complexity and audience awareness"
    ),

    TestCase(
        id="TC010",
        category=TestCategory.EDGE_CASE,
        prompt="What would happen if you tried to divide by zero in different programming languages? Be comprehensive.",
        expected_elements=[
            "Multiple languages covered (Python, Java, JavaScript, C++, etc.)",
            "Specific error types",
            "Behavior differences",
            "IEEE 754 floating point considerations",
            "Integer vs float division",
            "Practical implications"
        ],
        human_scores={
            "Factual Accuracy": 5.0,
            "Completeness": 5.0,
            "Logical Consistency": 5.0,
            "Appropriate Detail Level": 4.5,
            "Clarity & Coherence": 4.5,
        },
        difficulty=TestDifficulty.HARD,
        notes="Tests depth of technical knowledge across multiple domains"
    ),
]


def get_test_cases_by_category(category: TestCategory) -> List[TestCase]:
    """Filter test cases by category."""
    return [tc for tc in GOLDEN_TEST_SUITE if tc.category == category]


def get_test_cases_by_difficulty(difficulty: TestDifficulty) -> List[TestCase]:
    """Filter test cases by difficulty."""
    return [tc for tc in GOLDEN_TEST_SUITE if tc.difficulty == difficulty]


def get_test_case_by_id(test_id: str) -> TestCase:
    """Get a specific test case by ID."""
    for tc in GOLDEN_TEST_SUITE:
        if tc.id == test_id:
            return tc
    raise ValueError(f"Test case with ID {test_id} not found")


# Statistics about the test suite
def get_test_suite_stats() -> Dict[str, int]:
    """Get statistics about the test suite composition."""
    stats = {
        "total": len(GOLDEN_TEST_SUITE),
        "by_category": {},
        "by_difficulty": {}
    }

    for category in TestCategory:
        count = len(get_test_cases_by_category(category))
        if count > 0:
            stats["by_category"][category.value] = count

    for difficulty in TestDifficulty:
        count = len(get_test_cases_by_difficulty(difficulty))
        if count > 0:
            stats["by_difficulty"][difficulty.value] = count

    return stats
