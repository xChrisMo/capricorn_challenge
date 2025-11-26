#!/usr/bin/env python3
"""
Tests for release summary aggregation.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.release_notes_server import aggregator


def test_build_window_metadata():
    """Test window metadata extraction."""
    print("Testing _build_window_metadata...")

    git_history = {
        'from_ref': 'v1.0.0',
        'to_ref': 'v1.1.0',
        'from_sha': 'abc123',
        'to_sha': 'def456',
        'stats': {
            'total_commits': 15,
            'total_files_changed': 42,
            'total_insertions': 1200,
            'total_deletions': 300,
            'authors': ['Alice', 'Bob'],
            'date_range': {
                'first_commit_date': '2024-01-10T08:00:00Z',
                'last_commit_date': '2024-01-15T18:30:00Z'
            }
        }
    }

    window = aggregator._build_window_metadata(git_history)

    assert window['from_ref'] == 'v1.0.0'
    assert window['to_ref'] == 'v1.1.0'
    assert window['commit_count'] == 15
    assert window['files_changed'] == 42
    assert len(window['authors']) == 2
    print("  ✓ Window metadata extracted correctly")

    print("✓ _build_window_metadata test passed\n")


def test_group_commits_by_category():
    """Test commit grouping by category."""
    print("Testing _group_commits_by_category...")

    commits = [
        {
            'sha': 'abc123',
            'author': 'Alice',
            'date': '2024-01-15T10:00:00Z',
            'subject': 'feat: add feature',
            'body': 'Description',
            'category': 'feature',
            'files_changed': [],
            'total_lines_changed': 100,
            'is_large': False,
            'customer_impacts': {'impact_count': 1}
        },
        {
            'sha': 'def456',
            'author': 'Bob',
            'date': '2024-01-14T10:00:00Z',
            'subject': 'fix: bug fix',
            'body': '',
            'category': 'bugfix',
            'files_changed': [],
            'total_lines_changed': 10,
            'is_large': False,
            'customer_impacts': {'impact_count': 0}
        },
        {
            'sha': 'ghi789',
            'author': 'Alice',
            'date': '2024-01-16T10:00:00Z',
            'subject': 'feat!: breaking',
            'body': 'BREAKING CHANGE',
            'category': 'breaking',
            'files_changed': [],
            'total_lines_changed': 50,
            'is_large': False,
            'customer_impacts': {'impact_count': 0}
        }
    ]

    categories = aggregator._group_commits_by_category(commits)

    assert len(categories['features']) == 1
    assert len(categories['bugfixes']) == 1
    assert len(categories['breaking']) == 1
    assert categories['features'][0]['sha'] == 'abc123'
    assert categories['features'][0]['customer_impact'] == True
    print("  ✓ Commits grouped correctly by category")

    # Check sorting within each category (newest first)
    for category_name, category_commits in categories.items():
        if category_commits:  # Only check non-empty categories
            dates = [c['date'] for c in category_commits]
            assert dates == sorted(dates, reverse=True), f"Category {category_name} not sorted by date"
    print("  ✓ Commits sorted by date within each category (newest first)")

    print("✓ _group_commits_by_category test passed\n")


def test_build_qa_snapshot():
    """Test QA snapshot building."""
    print("Testing _build_qa_snapshot...")

    # With CI report
    ci_report = {
        'build_status': 'success',
        'test_summary': {
            'total': 150,
            'passed': 148,
            'failed': 2,
            'skipped': 0,
            'flaky': 1
        },
        'coverage': {
            'line_percent': 85.5,
            'branch_percent': 78.2,
            'threshold': {
                'line_percent': 80.0,
                'branch_percent': 75.0
            }
        },
        'failed_tests': [
            {'name': 'test_auth', 'file': 'test_auth.py', 'error': 'Failed'},
            {'name': 'test_payment', 'file': 'test_payment.py', 'error': 'Timeout'}
        ],
        'duration_seconds': 120
    }

    snapshot = aggregator._build_qa_snapshot(ci_report)

    assert snapshot['available'] == True
    assert snapshot['build_status'] == 'success'
    assert snapshot['test_summary']['total'] == 150
    assert snapshot['test_summary']['failed'] == 2
    assert snapshot['coverage']['line_percent'] == 85.5
    assert len(snapshot['failed_tests']) == 2
    print("  ✓ QA snapshot built with CI data")

    # Without CI report
    snapshot = aggregator._build_qa_snapshot(None)
    assert snapshot['available'] == False
    assert snapshot['build_status'] == 'unknown'
    print("  ✓ QA snapshot handles missing CI data")

    print("✓ _build_qa_snapshot test passed\n")


def test_aggregate_customer_impacts():
    """Test customer impact aggregation."""
    print("Testing _aggregate_customer_impacts...")

    commits = [
        {
            'sha': 'abc123',
            'subject': 'Update auth',
            'category': 'feature',
            'customer_impacts': {
                'impact_count': 2,
                'matched_features': ['authentication'],
                'matched_customers': ['acme-corp'],
                'matched_paths': ['src/auth/']
            }
        },
        {
            'sha': 'def456',
            'subject': 'Fix payment',
            'category': 'bugfix',
            'customer_impacts': {
                'impact_count': 1,
                'matched_features': ['payment-processing'],
                'matched_customers': [],
                'matched_paths': ['src/payment/']
            }
        },
        {
            'sha': 'ghi789',
            'subject': 'Update docs',
            'category': 'documentation',
            'customer_impacts': {
                'impact_count': 0,
                'matched_features': [],
                'matched_customers': [],
                'matched_paths': []
            }
        }
    ]

    watchlist = {
        'watched_features': ['authentication', 'payment-processing'],
        'critical_customers': ['acme-corp', 'globex'],
        'high_risk_paths': ['src/auth/', 'src/payment/']
    }

    impacts = aggregator._aggregate_customer_impacts(commits, watchlist)

    assert impacts['available'] == True
    assert impacts['summary']['total_impacted_commits'] == 2
    assert impacts['summary']['features_impacted'] == 2
    assert impacts['summary']['customers_mentioned'] == 1
    assert impacts['summary']['high_risk_paths_changed'] == 2
    print("  ✓ Customer impacts aggregated correctly")

    # Check by_feature
    assert 'authentication' in impacts['by_feature']
    assert len(impacts['by_feature']['authentication']) == 1
    assert impacts['by_feature']['authentication'][0]['sha'] == 'abc123'
    print("  ✓ Impacts grouped by feature")

    # Check by_customer
    assert 'acme-corp' in impacts['by_customer']
    assert len(impacts['by_customer']['acme-corp']) == 1
    print("  ✓ Impacts grouped by customer")

    # Check by_path
    assert 'src/auth/' in impacts['by_path']
    assert 'src/payment/' in impacts['by_path']
    print("  ✓ Impacts grouped by path")

    # Without watchlist
    impacts = aggregator._aggregate_customer_impacts(commits, None)
    assert impacts['available'] == False
    print("  ✓ Handles missing watchlist")

    print("✓ _aggregate_customer_impacts test passed\n")


def test_build_release_summary():
    """Test full release summary building."""
    print("Testing build_release_summary...")

    git_history = {
        'from_ref': 'v1.0.0',
        'to_ref': 'v1.1.0',
        'from_sha': 'abc123',
        'to_sha': 'def456',
        'stats': {
            'total_commits': 3,
            'total_files_changed': 10,
            'total_insertions': 200,
            'total_deletions': 50,
            'authors': ['Alice', 'Bob'],
            'date_range': {
                'first_commit_date': '2024-01-10T08:00:00Z',
                'last_commit_date': '2024-01-15T18:30:00Z'
            }
        }
    }

    categorized_commits = [
        {
            'sha': 'abc123',
            'author': 'Alice',
            'date': '2024-01-15T10:00:00Z',
            'subject': 'feat: add feature',
            'body': 'Description',
            'category': 'feature',
            'files_changed': [],
            'total_lines_changed': 100,
            'is_large': False,
            'customer_impacts': {
                'impact_count': 1,
                'matched_features': ['authentication'],
                'matched_customers': [],
                'matched_paths': []
            }
        },
        {
            'sha': 'def456',
            'author': 'Bob',
            'date': '2024-01-14T10:00:00Z',
            'subject': 'fix: bug fix',
            'body': '',
            'category': 'bugfix',
            'files_changed': [],
            'total_lines_changed': 10,
            'is_large': False,
            'customer_impacts': {'impact_count': 0}
        }
    ]

    risk = {
        'score': 3,
        'level': 'moderate',
        'factors': [
            {'reason': 'Customer impacts', 'points': 1, 'severity': 'medium'}
        ]
    }

    ci_report = {
        'build_status': 'success',
        'test_summary': {
            'total': 100,
            'passed': 100,
            'failed': 0,
            'skipped': 0
        },
        'coverage': {
            'line_percent': 85.0,
            'branch_percent': 80.0
        }
    }

    watchlist = {
        'watched_features': ['authentication'],
        'critical_customers': [],
        'high_risk_paths': []
    }

    # Use fixed datetime for testing
    test_time = datetime(2024, 1, 16, 9, 0, 0)

    summary = aggregator.build_release_summary(
        git_history,
        ci_report,
        watchlist,
        categorized_commits,
        risk,
        now=test_time
    )

    # Validate structure
    assert 'window' in summary
    assert 'risk' in summary
    assert 'categories' in summary
    assert 'qaSnapshot' in summary
    assert 'customerImpacts' in summary
    assert 'generatedAt' in summary
    print("  ✓ Summary has all required sections")

    # Validate window
    assert summary['window']['commit_count'] == 3
    assert summary['window']['from_ref'] == 'v1.0.0'
    print("  ✓ Window metadata correct")

    # Validate risk
    assert summary['risk']['level'] == 'moderate'
    assert summary['risk']['score'] == 3
    print("  ✓ Risk assessment included")

    # Validate categories
    assert len(summary['categories']['features']) == 1
    assert len(summary['categories']['bugfixes']) == 1
    print("  ✓ Categories populated")

    # Validate QA snapshot
    assert summary['qaSnapshot']['available'] == True
    assert summary['qaSnapshot']['build_status'] == 'success'
    print("  ✓ QA snapshot included")

    # Validate customer impacts
    assert summary['customerImpacts']['available'] == True
    assert summary['customerImpacts']['summary']['total_impacted_commits'] == 1
    print("  ✓ Customer impacts aggregated")

    # Validate timestamp
    assert summary['generatedAt'] == '2024-01-16T09:00:00Z'
    print("  ✓ Timestamp generated")

    print("✓ build_release_summary test passed\n")


def test_format_release_summary_markdown():
    """Test markdown formatting."""
    print("Testing format_release_summary_markdown...")

    # Create minimal summary
    summary = {
        'window': {
            'from_ref': 'v1.0.0',
            'to_ref': 'v1.1.0',
            'commit_count': 5,
            'authors': ['Alice', 'Bob'],
            'files_changed': 20,
            'insertions': 300,
            'deletions': 50,
            'first_commit_date': '2024-01-10T08:00:00Z',
            'last_commit_date': '2024-01-15T18:30:00Z'
        },
        'risk': {
            'score': 3,
            'level': 'moderate',
            'factors': [
                {'reason': 'Test factor', 'points': 3, 'severity': 'medium'}
            ]
        },
        'categories': {
            'features': [
                {'sha': 'abc123', 'subject': 'Add feature', 'date': '2024-01-15T10:00:00Z'}
            ],
            'bugfixes': [],
            'breaking': [],
            'performance': [],
            'documentation': [],
            'testing': [],
            'chores': [],
            'refactors': [],
            'other': []
        },
        'qaSnapshot': {
            'available': True,
            'build_status': 'success',
            'test_summary': {
                'total': 100,
                'passed': 100,
                'failed': 0,
                'skipped': 0
            },
            'coverage': {
                'line_percent': 85.0,
                'branch_percent': 80.0
            }
        },
        'customerImpacts': {
            'available': False,
            'summary': {}
        },
        'generatedAt': '2024-01-16T09:00:00Z'
    }

    markdown = aggregator.format_release_summary_markdown(summary)

    # Check for expected sections
    assert '# Release Summary' in markdown
    assert '## Overview' in markdown
    assert '## Risk Assessment' in markdown
    assert '## Changes by Category' in markdown
    assert '## QA Snapshot' in markdown
    assert 'v1.0.0 → v1.1.0' in markdown
    print("  ✓ Markdown contains all sections")

    # Check for data
    assert '5' in markdown  # commit count
    assert 'Alice, Bob' in markdown  # authors
    assert 'moderate' in markdown or 'MODERATE' in markdown  # risk level
    print("  ✓ Markdown contains correct data")

    print("✓ format_release_summary_markdown test passed\n")


def test_integration_with_real_structure():
    """Test with realistic data structure."""
    print("Testing integration with realistic data...")

    # Simulate real data from all components
    git_history = {
        'from_ref': 'HEAD~3',
        'to_ref': 'HEAD',
        'from_sha': '7bb3aea7',
        'to_sha': '741f283',
        'commits': [],  # Will be categorized separately
        'stats': {
            'total_commits': 4,
            'total_files_changed': 27,
            'total_insertions': 3279,
            'total_deletions': 71,
            'authors': ['Claude', 'chrismo'],
            'date_range': {
                'first_commit_date': '2024-01-10T08:00:00Z',
                'last_commit_date': '2024-01-15T18:30:00Z'
            }
        }
    }

    categorized_commits = [
        {
            'sha': '741f283',
            'author': 'Claude',
            'email': 'noreply@anthropic.com',
            'date': '2024-01-15T18:30:00Z',
            'subject': 'Add commit categorization and risk scoring',
            'body': 'Implement intelligent commit analysis',
            'category': 'feature',
            'files_changed': [],
            'total_lines_changed': 1108,
            'is_large': True,
            'is_breaking': False,
            'customer_impacts': {
                'impact_count': 2,
                'matched_features': ['git', 'testing'],
                'matched_customers': [],
                'matched_paths': ['mcp/release_notes_server/']
            },
            'confidence': 'high'
        }
    ]

    risk = {
        'score': 4,
        'level': 'moderate',
        'factors': [
            {'reason': '1 customer-impacting commit(s)', 'points': 1, 'severity': 'medium'},
            {'reason': 'Impacts features: git, testing', 'points': 0, 'severity': 'info'},
            {'reason': '1 large commit(s) (>500 lines)', 'points': 1, 'severity': 'low'}
        ]
    }

    ci_report = None  # Not available

    watchlist = {
        'watched_features': ['git', 'testing', 'server'],
        'critical_customers': [],
        'high_risk_paths': ['mcp/release_notes_server/']
    }

    summary = aggregator.build_release_summary(
        git_history,
        ci_report,
        watchlist,
        categorized_commits,
        risk
    )

    # Validate
    assert summary['window']['commit_count'] == 4
    assert summary['risk']['level'] == 'moderate'
    assert len(summary['categories']['features']) == 1
    assert summary['qaSnapshot']['available'] == False
    assert summary['customerImpacts']['available'] == True
    print("  ✓ Realistic data processed correctly")

    # Format as markdown
    markdown = aggregator.format_release_summary_markdown(summary)
    assert len(markdown) > 0
    print("  ✓ Markdown generated successfully")

    # Print sample output
    print("\n--- Sample Markdown Output ---")
    print(markdown[:500] + "...")
    print("--- End Sample ---\n")

    print("✓ Integration test passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Release Summary Aggregator Tests")
    print("=" * 60)
    print()

    tests = [
        test_build_window_metadata,
        test_group_commits_by_category,
        test_build_qa_snapshot,
        test_aggregate_customer_impacts,
        test_build_release_summary,
        test_format_release_summary_markdown,
        test_integration_with_real_structure,
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
