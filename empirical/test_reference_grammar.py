#!/usr/bin/env python3
"""Unit tests for the syntactic candidate-reference grammar."""

from __future__ import annotations

import unittest

from collect_argocd_repository import non_overlapping_matches


class ReferenceGrammarTests(unittest.TestCase):
    def test_local_hash_reference(self) -> None:
        self.assertEqual(non_overlapping_matches("Fixes #123")[0]["repository"], "argoproj/argo-cd")

    def test_scoped_reference(self) -> None:
        item = non_overlapping_matches("See owner/repository#456")[0]
        self.assertEqual((item["repository"], item["number"]), ("owner/repository", 456))

    def test_full_issue_url(self) -> None:
        item = non_overlapping_matches("https://github.com/owner/repository/issues/789")[0]
        self.assertEqual((item["repository"], item["number"]), ("owner/repository", 789))

    def test_full_url_is_not_duplicated(self) -> None:
        self.assertEqual(len(non_overlapping_matches("https://github.com/owner/repository/issues/789")), 1)

    def test_plain_number_is_excluded(self) -> None:
        self.assertEqual(non_overlapping_matches("related to 123"), [])

    def test_jira_token_is_excluded(self) -> None:
        self.assertEqual(non_overlapping_matches("ARGO-123"), [])

    def test_pull_request_url_is_excluded(self) -> None:
        self.assertEqual(non_overlapping_matches("https://github.com/owner/repository/pull/123"), [])

    def test_template_placeholder_is_excluded(self) -> None:
        self.assertEqual(non_overlapping_matches("Fixes [ISSUE #]"), [])


if __name__ == "__main__":
    unittest.main()
