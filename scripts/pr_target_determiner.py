#!/usr/bin/env python3
"""
PR Target Determination Module
================================

This module implements the business logic for determining whether to create a Pull Request (PR)
or update a personal Kanban board based on user input and note content analysis.

Author: Maestro DevOps Automation Team
License: MIT
"""

import re
import logging
from typing import Dict, Optional, TypedDict
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TargetAction(str, Enum):
    """Enumeration of possible target actions for the workflow."""
    CREATE_PR = "CREATE_PR"
    UPDATE_KANBAN = "UPDATE_KANBAN"


class PRTargetResult(TypedDict):
    """Type definition for the function return value."""
    target_action: str  # TargetAction enum value
    target_repo: str    # Repository name or "PERSONAL_KANBAN"


@dataclass
class VaguenessMetrics:
    """Metrics used to determine if content is too vague for a PR."""
    word_count: int
    has_technical_terms: bool
    has_actionable_verbs: bool
    has_code_references: bool
    specificity_score: float  # 0.0 to 1.0, higher is more specific


class ContentAnalyzer:
    """
    Analyzes raw note content to determine if it's specific enough for a PR.

    This class implements heuristics to detect vague, non-actionable content
    that should be routed to a personal Kanban board instead of a PR.
    """

    # Minimum word count for a PR-worthy note
    MIN_WORD_COUNT = 10

    # Minimum specificity score (0.0 to 1.0) for PR eligibility
    MIN_SPECIFICITY_SCORE = 0.3

    # Technical terms that indicate specific, actionable content
    TECHNICAL_TERMS = {
        'function', 'class', 'method', 'api', 'endpoint', 'database', 'schema',
        'test', 'bug', 'feature', 'refactor', 'optimize', 'deploy', 'build',
        'pipeline', 'workflow', 'integration', 'authentication', 'authorization',
        'kubernetes', 'docker', 'terraform', 'ci/cd', 'microservice', 'module'
    }

    # Actionable verbs indicating clear intent
    ACTIONABLE_VERBS = {
        'implement', 'fix', 'add', 'remove', 'update', 'refactor', 'optimize',
        'create', 'delete', 'modify', 'enhance', 'improve', 'resolve', 'debug',
        'deploy', 'migrate', 'upgrade', 'configure', 'setup', 'integrate'
    }

    # Patterns that indicate code references or technical specificity
    CODE_PATTERNS = [
        r'\b[a-z_]+\.[a-z_]+\(',           # Function calls: module.function()
        r'\b[A-Z][a-zA-Z]*\.[a-z_]+',      # Class methods: ClassName.method
        r'`[^`]+`',                         # Inline code: `code`
        r'```[\s\S]*?```',                  # Code blocks
        r'\b[a-z_]+/[a-z_]+\.py\b',        # File paths
        r'\b(GET|POST|PUT|DELETE|PATCH)\s+/', # HTTP methods
        r'\b\d+\.\d+\.\d+\b',              # Version numbers
    ]

    @classmethod
    def analyze_content(cls, content: str) -> VaguenessMetrics:
        """
        Analyzes content and returns metrics indicating its specificity.

        Args:
            content: The raw note content to analyze

        Returns:
            VaguenessMetrics object containing analysis results
        """
        if not content or not isinstance(content, str):
            logger.warning("Content is None or not a string, treating as vague")
            return VaguenessMetrics(
                word_count=0,
                has_technical_terms=False,
                has_actionable_verbs=False,
                has_code_references=False,
                specificity_score=0.0
            )

        content_lower = content.lower()
        words = content_lower.split()
        word_count = len(words)

        # Check for technical terms
        has_technical_terms = any(term in content_lower for term in cls.TECHNICAL_TERMS)

        # Check for actionable verbs
        has_actionable_verbs = any(verb in content_lower for verb in cls.ACTIONABLE_VERBS)

        # Check for code references using regex patterns
        has_code_references = any(
            re.search(pattern, content, re.IGNORECASE)
            for pattern in cls.CODE_PATTERNS
        )

        # Calculate specificity score (weighted combination of factors)
        score_components = []

        # Word count factor (logarithmic scale, caps at 100 words)
        if word_count > 0:
            word_score = min(word_count / 100.0, 1.0)
            score_components.append(word_score * 0.2)  # 20% weight

        # Technical terms factor
        if has_technical_terms:
            score_components.append(0.3)  # 30% weight

        # Actionable verbs factor
        if has_actionable_verbs:
            score_components.append(0.3)  # 30% weight

        # Code references factor
        if has_code_references:
            score_components.append(0.2)  # 20% weight

        specificity_score = sum(score_components)

        logger.debug(
            f"Content analysis: words={word_count}, tech={has_technical_terms}, "
            f"verbs={has_actionable_verbs}, code={has_code_references}, "
            f"score={specificity_score:.2f}"
        )

        return VaguenessMetrics(
            word_count=word_count,
            has_technical_terms=has_technical_terms,
            has_actionable_verbs=has_actionable_verbs,
            has_code_references=has_code_references,
            specificity_score=specificity_score
        )

    @classmethod
    def is_content_too_vague(cls, content: str) -> bool:
        """
        Determines if content is too vague for a PR.

        Primary criterion is specificity score, which weighs:
        - Technical terminology
        - Actionable verbs
        - Code references
        - Sufficient word count

        Content with high specificity (>= 0.3) is never considered vague,
        even if short (e.g., "Fix bug in API.authenticate()").

        Args:
            content: The raw note content to evaluate

        Returns:
            True if content is too vague, False if specific enough for a PR
        """
        metrics = cls.analyze_content(content)

        # Primary decision: specificity score
        # If score is high enough, content is specific regardless of length
        # This allows technical shorthand while filtering vague notes
        is_vague = metrics.specificity_score < cls.MIN_SPECIFICITY_SCORE

        if is_vague:
            logger.info(
                f"Content deemed too vague: {metrics.word_count} words, "
                f"{metrics.specificity_score:.2f} specificity score"
            )

        return is_vague


def validate_repository_name(repo_name: str) -> bool:
    """
    Validates that a repository name follows GitHub naming conventions.

    Args:
        repo_name: The repository name to validate

    Returns:
        True if valid, False otherwise
    """
    if not repo_name or not isinstance(repo_name, str):
        return False

    # GitHub repo names: alphanumeric, hyphens, underscores, dots
    # Cannot start with a dot or hyphen
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$'
    is_valid = bool(re.match(pattern, repo_name))

    if not is_valid:
        logger.warning(f"Invalid repository name format: {repo_name}")

    return is_valid


def determine_pr_target(
    raw_notes_content: Optional[str],
    user_designated_target_repo: Optional[str]
) -> PRTargetResult:
    """
    Determines the target action and repository for workflow routing.

    This function implements the core business logic for deciding whether to:
    1. Create a Pull Request in a designated repository
    2. Update a personal Kanban board for vague or exploratory notes

    **Business Logic:**

    Priority 1 - Targeted PR Creation:
        If `user_designated_target_repo` is provided AND content is specific enough,
        route to PR creation workflow for that repository.

    Priority 2 - Kanban Update (Fallback):
        If no target repo is provided OR content is too vague/exploratory,
        route to personal Kanban update workflow.

    **Vagueness Detection:**
    Content is considered "too vague" if it:
        - Contains fewer than 10 words
        - Has a specificity score < 0.3 (based on technical terms, actionable verbs, code references)
        - Lacks clear technical context or actionable intent

    Args:
        raw_notes_content: The raw text content from user notes (can be None/empty)
        user_designated_target_repo: The explicitly designated target repository name
                                     (can be None/empty)

    Returns:
        PRTargetResult dictionary with:
            - target_action: "CREATE_PR" or "UPDATE_KANBAN"
            - target_repo: Repository name or "PERSONAL_KANBAN"

    Raises:
        ValueError: If inputs violate critical constraints (e.g., invalid repo name format)

    Examples:
        >>> determine_pr_target(
        ...     "Fix authentication bug in user service module",
        ...     "my-data-backend"
        ... )
        {'target_action': 'CREATE_PR', 'target_repo': 'my-data-backend'}

        >>> determine_pr_target(
        ...     "some ideas",
        ...     None
        ... )
        {'target_action': 'UPDATE_KANBAN', 'target_repo': 'PERSONAL_KANBAN'}

        >>> determine_pr_target(
        ...     "Implement OAuth2 authentication flow with JWT tokens for user-service API",
        ...     "auth-backend"
        ... )
        {'target_action': 'CREATE_PR', 'target_repo': 'auth-backend'}
    """
    logger.info("=" * 70)
    logger.info("PR Target Determination - Starting Analysis")
    logger.info("=" * 70)

    # Normalize inputs: treat empty strings as None
    if raw_notes_content is not None and not raw_notes_content.strip():
        raw_notes_content = None
        logger.debug("Empty notes content normalized to None")

    if user_designated_target_repo is not None and not user_designated_target_repo.strip():
        user_designated_target_repo = None
        logger.debug("Empty target repo normalized to None")

    # Log inputs for audit trail
    logger.info(f"Input - Target Repo: {user_designated_target_repo or 'NOT PROVIDED'}")
    logger.info(f"Input - Content Length: {len(raw_notes_content) if raw_notes_content else 0} chars")

    # =========================================================================
    # DECISION LOGIC - Priority 1: Validate target repository if provided
    # =========================================================================
    if user_designated_target_repo is not None:
        if not validate_repository_name(user_designated_target_repo):
            error_msg = (
                f"Invalid repository name: '{user_designated_target_repo}'. "
                f"Must follow GitHub naming conventions (alphanumeric, hyphens, "
                f"underscores, dots; max 100 chars)."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"✓ Valid repository name: {user_designated_target_repo}")

    # =========================================================================
    # DECISION LOGIC - Priority 2: Check content vagueness if repo is targeted
    # =========================================================================
    content_is_vague = False
    if raw_notes_content is not None:
        content_is_vague = ContentAnalyzer.is_content_too_vague(raw_notes_content)
    else:
        content_is_vague = True  # No content = vague
        logger.info("No content provided - treating as vague")

    # =========================================================================
    # DECISION LOGIC - Priority 3: Routing decision
    # =========================================================================

    # CASE 1: User designated target repo AND content is specific enough
    if user_designated_target_repo is not None and not content_is_vague:
        logger.info("✓ DECISION: CREATE_PR (designated repo + specific content)")
        logger.info(f"→ Target Repository: {user_designated_target_repo}")
        logger.info("=" * 70)

        return PRTargetResult(
            target_action=TargetAction.CREATE_PR.value,
            target_repo=user_designated_target_repo
        )

    # CASE 2: No target repo OR content too vague → Kanban update
    reason_parts = []
    if user_designated_target_repo is None:
        reason_parts.append("no target repo")
    if content_is_vague:
        reason_parts.append("vague content")

    reason = " + ".join(reason_parts)
    logger.info(f"✓ DECISION: UPDATE_KANBAN ({reason})")
    logger.info("→ Target: PERSONAL_KANBAN")
    logger.info("=" * 70)

    return PRTargetResult(
        target_action=TargetAction.UPDATE_KANBAN.value,
        target_repo="PERSONAL_KANBAN"
    )


# =============================================================================
# CLI Interface (for standalone testing)
# =============================================================================

def main():
    """Command-line interface for testing the function."""
    import sys
    import json

    print("\n" + "=" * 70)
    print("PR Target Determiner - Standalone Test Mode")
    print("=" * 70 + "\n")

    # Example test cases
    test_cases = [
        {
            "name": "Case 1: Specific PR with designated repo",
            "content": "Implement OAuth2 authentication flow with JWT tokens for user-service API endpoints",
            "repo": "auth-backend"
        },
        {
            "name": "Case 2: Vague content, no repo",
            "content": "some ideas",
            "repo": None
        },
        {
            "name": "Case 3: Specific content, no repo",
            "content": "Fix critical bug in payment processing service where transactions fail silently",
            "repo": None
        },
        {
            "name": "Case 4: Vague content, designated repo",
            "content": "maybe later",
            "repo": "my-repo"
        },
        {
            "name": "Case 5: Empty content",
            "content": "",
            "repo": "test-repo"
        },
        {
            "name": "Case 6: Technical content with code references",
            "content": "Refactor UserService.authenticate() method to use async/await pattern. Update tests in user_service_test.py",
            "repo": "backend-services"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{test['name']}")
        print("-" * 70)
        print(f"Content: {test['content']!r}")
        print(f"Repo: {test['repo']!r}")
        print()

        result = determine_pr_target(
            raw_notes_content=test['content'],
            user_designated_target_repo=test['repo']
        )

        print(f"\nResult: {json.dumps(result, indent=2)}")
        print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
