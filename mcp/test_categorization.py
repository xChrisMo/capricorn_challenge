#!/usr/bin/env python3
"""
Tests for commit categorization and risk scoring.
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.release_notes_server import commit_classifier, risk_calculator


def test_parse_conventional_commit():
    """Test conventional commit parsing."""
    print("Testing parse_conventional_commit...")

    # Standard conventional commit
    result = commit_classifier.parse_conventional_commit("feat: add new feature")
    assert result['is_conventional'] == True
    assert result['type'] == 'feat'
    assert result['category'] == 'feature'
    assert result['breaking_marker'] == False
    print("  ✓ Standard format parsed")

    # With scope
    result = commit_classifier.parse_conventional_commit("fix(auth): resolve login issue")
    assert result['is_conventional'] == True
    assert result['type'] == 'fix'
    assert result['scope'] == 'auth'
    assert result['category'] == 'bugfix'
    print("  ✓ Format with scope parsed")

    # Breaking change marker
    result = commit_classifier.parse_conventional_commit("feat!: breaking change")
    assert result['is_conventional'] == True
    assert result['breaking_marker'] == True
    print("  ✓ Breaking change marker detected")

    # Non-conventional
    result = commit_classifier.parse_conventional_commit("Add new feature")
    assert result['is_conventional'] == False
    assert result['category'] is None
    print("  ✓ Non-conventional format detected")

    print("✓ parse_conventional_commit test passed\n")


def test_detect_breaking_change():
    """Test breaking change detection."""
    print("Testing detect_breaking_change...")

    # Breaking marker in subject
    assert commit_classifier.detect_breaking_change("feat!: change", "") == True
    print("  ✓ Breaking marker detected in subject")

    # "BREAKING CHANGE:" in body
    assert commit_classifier.detect_breaking_change(
        "feat: change",
        "BREAKING CHANGE: API changed"
    ) == True
    print("  ✓ BREAKING CHANGE: detected in body")

    # No breaking change
    assert commit_classifier.detect_breaking_change("feat: add feature", "Normal change") == False
    print("  ✓ Non-breaking commit correctly identified")

    print("✓ detect_breaking_change test passed\n")


def test_categorize_by_keywords():
    """Test keyword-based categorization."""
    print("Testing categorize_by_keywords...")

    # Bugfix keywords
    assert commit_classifier.categorize_by_keywords("Fix bug in login", "") == 'bugfix'
    print("  ✓ Bugfix detected")

    # Feature keywords
    assert commit_classifier.categorize_by_keywords("Add new dashboard", "") == 'feature'
    print("  ✓ Feature detected")

    # Performance keywords
    assert commit_classifier.categorize_by_keywords("Optimize database queries", "") == 'performance'
    print("  ✓ Performance detected")

    # Documentation keywords
    assert commit_classifier.categorize_by_keywords("Update README", "") == 'documentation'
    print("  ✓ Documentation detected")

    # No match
    assert commit_classifier.categorize_by_keywords("Random commit", "") == 'other'
    print("  ✓ Other category for unmatched")

    print("✓ categorize_by_keywords test passed\n")


def test_match_customer_impacts():
    """Test customer impact matching."""
    print("Testing match_customer_impacts...")

    watchlist = {
        'watched_features': ['authentication', 'payment-processing'],
        'high_risk_paths': ['src/auth/', 'src/payment/'],
        'critical_customers': ['acme-corp', 'globex']
    }

    # Match feature in subject
    impacts = commit_classifier.match_customer_impacts(
        "Update authentication flow",
        "",
        [],
        watchlist
    )
    assert 'authentication' in impacts['matched_features']
    assert impacts['impact_count'] > 0
    print("  ✓ Feature matched in subject")

    # Match high-risk path
    impacts = commit_classifier.match_customer_impacts(
        "Update code",
        "",
        ['src/auth/login.py'],
        watchlist
    )
    assert 'src/auth/' in impacts['matched_paths']
    assert impacts['impact_count'] > 0
    print("  ✓ High-risk path matched")

    # Match customer in body
    impacts = commit_classifier.match_customer_impacts(
        "Fix issue",
        "Reported by acme-corp",
        [],
        watchlist
    )
    assert 'acme-corp' in impacts['matched_customers']
    assert impacts['impact_count'] > 0
    print("  ✓ Customer matched in body")

    # No matches
    impacts = commit_classifier.match_customer_impacts(
        "Random change",
        "",
        ['src/utils/helper.py'],
        watchlist
    )
    assert impacts['impact_count'] == 0
    print("  ✓ No false positives")

    print("✓ match_customer_impacts test passed\n")


def test_categorize_commit():
    """Test full commit categorization."""
    print("Testing categorize_commit...")

    watchlist = {
        'watched_features': ['authentication'],
        'high_risk_paths': ['src/auth/'],
        'critical_customers': []
    }

    # Feature commit
    commit = {
        'subject': 'feat: add user export',
        'body': 'Allows users to export data',
        'files_changed': [
            {'path': 'src/export.py', 'insertions': 100, 'deletions': 10}
        ]
    }

    result = commit_classifier.categorize_commit(commit, watchlist)
    assert result['category'] == 'feature'
    assert result['is_breaking'] == False
    assert result['is_large'] == False
    assert result['confidence'] == 'high'
    print("  ✓ Feature commit categorized")

    # Breaking change
    commit = {
        'subject': 'feat!: change API',
        'body': 'BREAKING CHANGE: API format changed',
        'files_changed': []
    }

    result = commit_classifier.categorize_commit(commit, watchlist)
    assert result['category'] == 'breaking'
    assert result['is_breaking'] == True
    print("  ✓ Breaking change detected")

    # Large commit
    commit = {
        'subject': 'refactor: restructure codebase',
        'body': '',
        'files_changed': [
            {'path': 'src/main.py', 'insertions': 300, 'deletions': 250}
        ]
    }

    result = commit_classifier.categorize_commit(commit, watchlist)
    assert result['is_large'] == True
    assert result['total_lines_changed'] == 550
    print("  ✓ Large commit detected")

    # Customer impact
    commit = {
        'subject': 'fix: authentication bug',
        'body': '',
        'files_changed': [
            {'path': 'src/auth/login.py', 'insertions': 5, 'deletions': 3}
        ]
    }

    result = commit_classifier.categorize_commit(commit, watchlist)
    assert result['customer_impacts']['impact_count'] > 0
    print("  ✓ Customer impact detected")

    print("✓ categorize_commit test passed\n")


def test_get_category_summary():
    """Test category summary statistics."""
    print("Testing get_category_summary...")

    commits = [
        {'category': 'feature', 'is_breaking': False, 'is_large': False, 'customer_impacts': {'impact_count': 0}},
        {'category': 'feature', 'is_breaking': False, 'is_large': True, 'customer_impacts': {'impact_count': 1}},
        {'category': 'bugfix', 'is_breaking': False, 'is_large': False, 'customer_impacts': {'impact_count': 0}},
        {'category': 'breaking', 'is_breaking': True, 'is_large': False, 'customer_impacts': {'impact_count': 1}},
    ]

    summary = commit_classifier.get_category_summary(commits)
    assert summary['total_commits'] == 4
    assert summary['category_counts']['feature'] == 2
    assert summary['category_counts']['bugfix'] == 1
    assert summary['breaking_changes'] == 1
    assert summary['large_commits'] == 1
    assert summary['customer_impact_commits'] == 2
    print("  ✓ Summary statistics correct")

    print("✓ get_category_summary test passed\n")


def test_calculate_release_risk():
    """Test risk score calculation."""
    print("Testing calculate_release_risk...")

    watchlist = {}

    # Low risk release
    commits = [
        {'category': 'feature', 'is_breaking': False, 'is_large': False, 'customer_impacts': {'impact_count': 0}},
        {'category': 'bugfix', 'is_breaking': False, 'is_large': False, 'customer_impacts': {'impact_count': 0}},
    ]

    result = risk_calculator.calculate_release_risk(commits, None, watchlist)
    assert result['level'] == 'low'
    assert result['score'] < 3
    print(f"  ✓ Low risk: score={result['score']}, level={result['level']}")

    # Moderate risk with breaking change
    commits = [
        {'category': 'breaking', 'is_breaking': True, 'is_large': False, 'customer_impacts': {'impact_count': 0}},
        {'category': 'feature', 'is_breaking': False, 'is_large': False, 'customer_impacts': {'impact_count': 1, 'matched_features': ['auth']}},
    ]

    result = risk_calculator.calculate_release_risk(commits, None, watchlist)
    assert result['level'] in ['moderate', 'low']
    assert result['score'] >= 3
    print(f"  ✓ Moderate risk: score={result['score']}, level={result['level']}")

    # High risk with multiple factors
    commits = [
        {'category': 'breaking', 'is_breaking': True, 'is_large': False, 'customer_impacts': {'impact_count': 1, 'matched_features': ['auth']}},
        {'category': 'breaking', 'is_breaking': True, 'is_large': True, 'customer_impacts': {'impact_count': 1, 'matched_features': ['payment']}},
        {'category': 'feature', 'is_breaking': False, 'is_large': False, 'customer_impacts': {'impact_count': 1, 'matched_features': ['billing']}},
    ]

    ci_report = {
        'coverage': {
            'line_percent': 75.0,
            'previous': {'line_percent': 85.0}
        },
        'test_summary': {
            'failed': 0
        }
    }

    result = risk_calculator.calculate_release_risk(commits, ci_report, watchlist)
    assert result['level'] == 'high'
    assert result['score'] >= 6
    print(f"  ✓ High risk: score={result['score']}, level={result['level']}")

    # Verify factors are returned
    assert len(result['factors']) > 0
    print(f"  ✓ Risk factors identified: {len(result['factors'])}")

    print("✓ calculate_release_risk test passed\n")


def test_get_risk_recommendations():
    """Test recommendation generation."""
    print("Testing get_risk_recommendations...")

    commits = [
        {'category': 'breaking', 'is_breaking': True, 'is_large': False, 'customer_impacts': {
            'impact_count': 1,
            'matched_features': ['auth'],
            'matched_paths': ['src/auth/']
        }},
    ]

    risk_assessment = {
        'score': 5,
        'level': 'moderate',
        'factors': []
    }

    ci_report = {
        'test_summary': {'failed': 2},
        'coverage': {'line_percent': 75.0}
    }

    recommendations = risk_calculator.get_risk_recommendations(
        risk_assessment,
        commits,
        ci_report
    )

    assert len(recommendations) > 0
    print(f"  ✓ Generated {len(recommendations)} recommendations")

    # Check for specific recommendations
    rec_text = ' '.join(recommendations).lower()
    assert 'breaking' in rec_text
    assert 'test' in rec_text or 'coverage' in rec_text
    print("  ✓ Recommendations are relevant to risk factors")

    print("✓ get_risk_recommendations test passed\n")


def test_integration():
    """Test full integration: categorize commits and calculate risk."""
    print("Testing full integration...")

    # Simulate real git history data
    commits = [
        {
            'sha': 'abc123',
            'subject': 'feat(auth): add OAuth support',
            'body': 'Implements OAuth 2.0 authentication flow',
            'files_changed': [
                {'path': 'src/auth/oauth.py', 'insertions': 150, 'deletions': 0}
            ]
        },
        {
            'sha': 'def456',
            'subject': 'fix: resolve payment processing bug',
            'body': 'Fixes issue reported by acme-corp',
            'files_changed': [
                {'path': 'src/payment/process.py', 'insertions': 10, 'deletions': 5}
            ]
        },
        {
            'sha': 'ghi789',
            'subject': 'feat!: remove deprecated API',
            'body': 'BREAKING CHANGE: Old API endpoints removed',
            'files_changed': [
                {'path': 'src/api/v1.py', 'insertions': 0, 'deletions': 300}
            ]
        },
    ]

    watchlist = {
        'watched_features': ['authentication', 'payment-processing'],
        'high_risk_paths': ['src/auth/', 'src/payment/'],
        'critical_customers': ['acme-corp']
    }

    # Categorize commits
    categorized = commit_classifier.categorize_commits(commits, watchlist)
    print(f"  ✓ Categorized {len(categorized)} commits")

    # Check categorization
    assert categorized[0]['category'] == 'feature'
    assert categorized[1]['category'] == 'bugfix'
    assert categorized[2]['category'] == 'breaking'
    print("  ✓ Categories assigned correctly")

    # Check customer impacts
    assert categorized[0]['customer_impacts']['impact_count'] > 0  # auth feature
    assert categorized[1]['customer_impacts']['impact_count'] > 0  # payment + customer mention
    print("  ✓ Customer impacts detected")

    # Get summary
    summary = commit_classifier.get_category_summary(categorized)
    print(f"  ✓ Summary: {summary['category_counts']}")

    # Calculate risk
    ci_report = {
        'coverage': {'line_percent': 85.0},
        'test_summary': {'failed': 0}
    }

    risk = risk_calculator.calculate_release_risk(categorized, ci_report, watchlist)
    print(f"  ✓ Risk: {risk['level']} (score: {risk['score']})")

    # Get recommendations
    recommendations = risk_calculator.get_risk_recommendations(risk, categorized, ci_report)
    print(f"  ✓ Recommendations: {len(recommendations)}")
    for rec in recommendations[:3]:
        print(f"    - {rec}")

    print("✓ Integration test passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Commit Categorization & Risk Scoring Tests")
    print("=" * 60)
    print()

    tests = [
        test_parse_conventional_commit,
        test_detect_breaking_change,
        test_categorize_by_keywords,
        test_match_customer_impacts,
        test_categorize_commit,
        test_get_category_summary,
        test_calculate_release_risk,
        test_get_risk_recommendations,
        test_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
