#!/usr/bin/env python3
"""
Unit Tests for PR Target Determiner Module
===========================================

Comprehensive test suite covering all business logic paths, edge cases,
and error conditions for the determine_pr_target() function.

Run with: python -m pytest test_pr_target_determiner.py -v
Or: python test_pr_target_determiner.py
"""

import unittest
import logging
from typing import Dict

# Import the module under test
from pr_target_determiner import (
    determine_pr_target,
    ContentAnalyzer,
    VaguenessMetrics,
    TargetAction,
    validate_repository_name
)

# Disable logging during tests for cleaner output
logging.disable(logging.CRITICAL)


class TestRepositoryNameValidation(unittest.TestCase):
    """Test cases for repository name validation."""

    def test_valid_repo_names(self):
        """Test that valid repository names are accepted."""
        valid_names = [
            "my-repo",
            "MyRepo",
            "my_repo",
            "repo.name",
            "repo-123",
            "a",  # Single character is valid
            "A1-b2.c3_d4",  # Mixed valid characters
            "repo" * 25,  # 100 chars (at limit)
        ]
        for name in valid_names:
            with self.subTest(name=name):
                self.assertTrue(
                    validate_repository_name(name),
                    f"Expected {name!r} to be valid"
                )

    def test_invalid_repo_names(self):
        """Test that invalid repository names are rejected."""
        invalid_names = [
            "",  # Empty string
            ".repo",  # Starts with dot
            "-repo",  # Starts with hyphen
            "repo name",  # Contains space
            "repo/name",  # Contains slash
            "repo@name",  # Contains @
            "repo#name",  # Contains #
            "repo$name",  # Contains $
            "a" * 101,  # 101 chars (over limit)
            None,  # None value
        ]
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(
                    validate_repository_name(name),
                    f"Expected {name!r} to be invalid"
                )


class TestContentAnalyzer(unittest.TestCase):
    """Test cases for content vagueness analysis."""

    def test_empty_content(self):
        """Test analysis of empty or None content."""
        test_cases = [None, "", "   ", "\n\t"]
        for content in test_cases:
            with self.subTest(content=content):
                metrics = ContentAnalyzer.analyze_content(content)
                self.assertEqual(metrics.word_count, 0)
                self.assertFalse(metrics.has_technical_terms)
                self.assertFalse(metrics.has_actionable_verbs)
                self.assertFalse(metrics.has_code_references)
                self.assertEqual(metrics.specificity_score, 0.0)

    def test_vague_content(self):
        """Test that vague content is correctly identified."""
        vague_texts = [
            "some ideas",
            "maybe later",
            "thinking about stuff",
            "todo",
            "notes",
        ]
        for text in vague_texts:
            with self.subTest(text=text):
                self.assertTrue(
                    ContentAnalyzer.is_content_too_vague(text),
                    f"Expected {text!r} to be vague"
                )

    def test_specific_content(self):
        """Test that specific technical content is not flagged as vague."""
        specific_texts = [
            "Implement OAuth2 authentication flow with JWT tokens for user-service API endpoints",
            "Fix critical bug in payment processing service where transactions fail silently",
            "Refactor UserService.authenticate() method to use async/await pattern",
            "Add integration tests for the new microservice deployment pipeline",
            "Update database schema to include user_roles table with foreign key constraints",
        ]
        for text in specific_texts:
            with self.subTest(text=text):
                self.assertFalse(
                    ContentAnalyzer.is_content_too_vague(text),
                    f"Expected {text!r} to be specific enough"
                )

    def test_technical_terms_detection(self):
        """Test detection of technical terminology."""
        content = "Implement function to refactor the API endpoint with authentication"
        metrics = ContentAnalyzer.analyze_content(content)
        self.assertTrue(metrics.has_technical_terms)
        self.assertGreater(metrics.specificity_score, 0.3)

    def test_actionable_verbs_detection(self):
        """Test detection of actionable verbs."""
        content = "Fix the bug and implement the new feature"
        metrics = ContentAnalyzer.analyze_content(content)
        self.assertTrue(metrics.has_actionable_verbs)

    def test_code_references_detection(self):
        """Test detection of code-like patterns."""
        test_cases = [
            ("Call module.function() to process data", True),
            ("Update ClassName.method implementation", True),
            ("Modify `config.yaml` settings", True),
            ("Fix bug in user_service/api.py", True),
            ("Implement GET /api/users endpoint", True),
            ("Upgrade to version 2.3.1", True),
            ("Regular text without code", False),
        ]
        for content, should_detect in test_cases:
            with self.subTest(content=content):
                metrics = ContentAnalyzer.analyze_content(content)
                self.assertEqual(
                    metrics.has_code_references,
                    should_detect,
                    f"Code detection failed for: {content!r}"
                )

    def test_specificity_score_calculation(self):
        """Test that specificity scores are calculated correctly."""
        # Minimal content
        minimal = ContentAnalyzer.analyze_content("hi")
        self.assertLess(minimal.specificity_score, 0.3)

        # Rich technical content
        rich = ContentAnalyzer.analyze_content(
            "Implement OAuth2 authentication using UserService.authenticate() "
            "method in backend/auth/service.py with integration tests"
        )
        self.assertGreater(rich.specificity_score, 0.5)


class TestDeterminePRTarget(unittest.TestCase):
    """Test cases for the main determine_pr_target() function."""

    def test_case_1_targeted_pr_with_specific_content(self):
        """
        CASE 1: User provides target repo AND content is specific.
        Expected: CREATE_PR to designated repo
        """
        result = determine_pr_target(
            raw_notes_content="Implement OAuth2 authentication flow with JWT tokens for user-service API",
            user_designated_target_repo="auth-backend"
        )

        self.assertEqual(result["target_action"], TargetAction.CREATE_PR.value)
        self.assertEqual(result["target_repo"], "auth-backend")

    def test_case_2_no_repo_vague_content(self):
        """
        CASE 2: No target repo AND content is vague.
        Expected: UPDATE_KANBAN
        """
        result = determine_pr_target(
            raw_notes_content="some ideas",
            user_designated_target_repo=None
        )

        self.assertEqual(result["target_action"], TargetAction.UPDATE_KANBAN.value)
        self.assertEqual(result["target_repo"], "PERSONAL_KANBAN")

    def test_case_3_no_repo_specific_content(self):
        """
        CASE 3: No target repo BUT content is specific.
        Expected: UPDATE_KANBAN (repo designation takes precedence)
        """
        result = determine_pr_target(
            raw_notes_content="Fix critical bug in payment processing service where transactions fail silently",
            user_designated_target_repo=None
        )

        self.assertEqual(result["target_action"], TargetAction.UPDATE_KANBAN.value)
        self.assertEqual(result["target_repo"], "PERSONAL_KANBAN")

    def test_case_4_repo_provided_vague_content(self):
        """
        CASE 4: Target repo provided BUT content is vague.
        Expected: UPDATE_KANBAN (content vagueness overrides repo)
        """
        result = determine_pr_target(
            raw_notes_content="maybe later",
            user_designated_target_repo="my-repo"
        )

        self.assertEqual(result["target_action"], TargetAction.UPDATE_KANBAN.value)
        self.assertEqual(result["target_repo"], "PERSONAL_KANBAN")

    def test_case_5_empty_content_with_repo(self):
        """
        CASE 5: Target repo provided BUT content is empty/None.
        Expected: UPDATE_KANBAN (no actionable content)
        """
        test_cases = [None, "", "   ", "\n\t"]
        for content in test_cases:
            with self.subTest(content=content):
                result = determine_pr_target(
                    raw_notes_content=content,
                    user_designated_target_repo="test-repo"
                )

                self.assertEqual(result["target_action"], TargetAction.UPDATE_KANBAN.value)
                self.assertEqual(result["target_repo"], "PERSONAL_KANBAN")

    def test_case_6_technical_content_with_code(self):
        """
        CASE 6: Highly technical content with code references.
        Expected: CREATE_PR (high specificity score)
        """
        result = determine_pr_target(
            raw_notes_content=(
                "Refactor UserService.authenticate() method to use async/await pattern. "
                "Update tests in user_service_test.py and modify api/v1/auth endpoint"
            ),
            user_designated_target_repo="backend-services"
        )

        self.assertEqual(result["target_action"], TargetAction.CREATE_PR.value)
        self.assertEqual(result["target_repo"], "backend-services")

    def test_both_inputs_none(self):
        """
        Edge case: Both inputs are None.
        Expected: UPDATE_KANBAN
        """
        result = determine_pr_target(
            raw_notes_content=None,
            user_designated_target_repo=None
        )

        self.assertEqual(result["target_action"], TargetAction.UPDATE_KANBAN.value)
        self.assertEqual(result["target_repo"], "PERSONAL_KANBAN")

    def test_invalid_repo_name_raises_error(self):
        """
        Error case: Invalid repository name format.
        Expected: ValueError raised
        """
        invalid_repos = [".bad-repo", "-bad-repo", "bad/repo", "bad repo"]

        for repo in invalid_repos:
            with self.subTest(repo=repo):
                with self.assertRaises(ValueError) as context:
                    determine_pr_target(
                        raw_notes_content="Fix the bug",
                        user_designated_target_repo=repo
                    )

                self.assertIn("Invalid repository name", str(context.exception))

    def test_whitespace_normalization(self):
        """
        Test that whitespace-only strings are normalized to None.
        """
        result = determine_pr_target(
            raw_notes_content="   ",
            user_designated_target_repo="  "
        )

        # Both should be treated as None -> UPDATE_KANBAN
        self.assertEqual(result["target_action"], TargetAction.UPDATE_KANBAN.value)

    def test_case_insensitive_content_analysis(self):
        """
        Test that content analysis works regardless of case.
        """
        # Uppercase technical terms should still be detected
        result = determine_pr_target(
            raw_notes_content="IMPLEMENT OAUTH2 AUTHENTICATION FOR API ENDPOINT",
            user_designated_target_repo="auth-service"
        )

        self.assertEqual(result["target_action"], TargetAction.CREATE_PR.value)

    def test_multiple_repositories_different_content(self):
        """
        Test routing to different repositories based on content.
        """
        test_scenarios = [
            {
                "content": "Add Docker deployment configuration for Kubernetes cluster",
                "repo": "devops-infra",
                "expected_action": TargetAction.CREATE_PR.value
            },
            {
                "content": "Update user authentication microservice with new OAuth provider",
                "repo": "auth-backend",
                "expected_action": TargetAction.CREATE_PR.value
            },
            {
                "content": "Refactor database migration scripts for production deployment",
                "repo": "data-backend",
                "expected_action": TargetAction.CREATE_PR.value
            }
        ]

        for scenario in test_scenarios:
            with self.subTest(repo=scenario["repo"]):
                result = determine_pr_target(
                    raw_notes_content=scenario["content"],
                    user_designated_target_repo=scenario["repo"]
                )

                self.assertEqual(result["target_action"], scenario["expected_action"])
                self.assertEqual(result["target_repo"], scenario["repo"])


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests simulating real-world usage patterns."""

    def test_developer_workflow_sequence(self):
        """
        Simulate a developer's workflow over multiple notes.
        """
        # Morning: Vague brainstorming note
        result1 = determine_pr_target("thinking about architecture", None)
        self.assertEqual(result1["target_action"], TargetAction.UPDATE_KANBAN.value)

        # Mid-day: Specific implementation task
        result2 = determine_pr_target(
            "Implement rate limiting middleware using Redis for API gateway",
            "api-gateway"
        )
        self.assertEqual(result2["target_action"], TargetAction.CREATE_PR.value)
        self.assertEqual(result2["target_repo"], "api-gateway")

        # Afternoon: Bug fix with technical details
        result3 = determine_pr_target(
            "Fix memory leak in ConnectionPool.acquire() method causing server crashes",
            "database-connector"
        )
        self.assertEqual(result3["target_action"], TargetAction.CREATE_PR.value)
        self.assertEqual(result3["target_repo"], "database-connector")

    def test_boundary_conditions(self):
        """Test behavior at threshold boundaries."""
        # Content right at word count threshold (10 words)
        exactly_10_words = " ".join(["word"] * 10)
        result = determine_pr_target(exactly_10_words, "test-repo")
        # Should be vague (no technical terms)
        self.assertEqual(result["target_action"], TargetAction.UPDATE_KANBAN.value)

        # 10 words with technical terms
        technical_10_words = "implement fix refactor api database function test deploy build optimize"
        result2 = determine_pr_target(technical_10_words, "test-repo")
        # Should pass (technical terms boost score)
        self.assertEqual(result2["target_action"], TargetAction.CREATE_PR.value)


def run_tests():
    """Run all tests with verbose output."""
    # Re-enable logging for test run
    logging.disable(logging.NOTSET)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRepositoryNameValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestContentAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestDeterminePRTarget))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    import sys
    sys.exit(run_tests())
