"""
Release summary aggregation.

This module combines data from git history, categorization, risk scoring,
CI reports, and customer watchlist into a single structured output for
the release-notes skill.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


def build_release_summary(
    git_history: Dict[str, Any],
    ci_report: Optional[Dict[str, Any]],
    customer_watchlist: Optional[Dict[str, Any]],
    categorized_commits: List[Dict[str, Any]],
    risk: Dict[str, Any],
    now: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Build a comprehensive release summary from all data sources.

    This function aggregates:
    - Git history metadata (refs, dates, commit counts)
    - Categorized commits grouped by type
    - Risk assessment with factors and recommendations
    - QA/CI snapshot (test results, coverage)
    - Customer impact analysis

    Args:
        git_history: Git history dict from get_git_history
        ci_report: Optional CI report dict
        customer_watchlist: Optional customer watchlist dict
        categorized_commits: List of commits with categorization fields
        risk: Risk assessment dict from calculate_release_risk
        now: Optional timestamp for generatedAt (defaults to now)

    Returns:
        Structured release summary dict ready for skill consumption
    """
    if now is None:
        now = datetime.utcnow()

    # Extract window metadata
    window = _build_window_metadata(git_history)

    # Group commits by category
    categories = _group_commits_by_category(categorized_commits)

    # Build QA snapshot
    qa_snapshot = _build_qa_snapshot(ci_report)

    # Aggregate customer impacts
    customer_impacts = _aggregate_customer_impacts(
        categorized_commits,
        customer_watchlist
    )

    # Build final summary
    summary = {
        'window': window,
        'risk': risk,
        'categories': categories,
        'qaSnapshot': qa_snapshot,
        'customerImpacts': customer_impacts,
        'generatedAt': now.strftime('%Y-%m-%dT%H:%M:%SZ')
    }

    logger.info(f"Built release summary: {window['commit_count']} commits, risk: {risk['level']}")

    return summary


def _build_window_metadata(git_history: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract window metadata from git history.

    Args:
        git_history: Git history dict

    Returns:
        Window metadata dict
    """
    stats = git_history.get('stats', {})
    date_range = stats.get('date_range', {})

    return {
        'from_ref': git_history.get('from_ref'),
        'to_ref': git_history.get('to_ref'),
        'from_sha': git_history.get('from_sha'),
        'to_sha': git_history.get('to_sha'),
        'commit_count': stats.get('total_commits', 0),
        'first_commit_date': date_range.get('first_commit_date') if date_range else None,
        'last_commit_date': date_range.get('last_commit_date') if date_range else None,
        'authors': stats.get('authors', []),
        'files_changed': stats.get('total_files_changed', 0),
        'insertions': stats.get('total_insertions', 0),
        'deletions': stats.get('total_deletions', 0)
    }


def _group_commits_by_category(commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group commits by category.

    Args:
        commits: List of categorized commits

    Returns:
        Dict mapping category names to lists of commits
    """
    # Initialize all categories
    categories = {
        'breaking': [],
        'features': [],
        'bugfixes': [],
        'performance': [],
        'documentation': [],
        'testing': [],
        'chores': [],
        'refactors': [],
        'other': []
    }

    # Map category names to output keys
    category_map = {
        'breaking': 'breaking',
        'feature': 'features',
        'bugfix': 'bugfixes',
        'performance': 'performance',
        'documentation': 'documentation',
        'testing': 'testing',
        'chore': 'chores',
        'refactor': 'refactors',
        'other': 'other'
    }

    for commit in commits:
        category = commit.get('category', 'other')
        output_key = category_map.get(category, 'other')

        # Simplify commit for output (remove redundant fields)
        simplified_commit = {
            'sha': commit['sha'],
            'author': commit['author'],
            'date': commit['date'],
            'subject': commit['subject'],
            'body': commit.get('body', ''),
            'files_changed_count': len(commit.get('files_changed', [])),
            'lines_changed': commit.get('total_lines_changed', 0),
            'is_large': commit.get('is_large', False),
            'customer_impact': commit.get('customer_impacts', {}).get('impact_count', 0) > 0,
            'customer_impacts': commit.get('customer_impacts', {})
        }

        categories[output_key].append(simplified_commit)

    # Sort commits in each category by date (newest first)
    for category_commits in categories.values():
        category_commits.sort(
            key=lambda c: c.get('date', ''),
            reverse=True
        )

    return categories


def _build_qa_snapshot(ci_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build QA snapshot from CI report.

    Args:
        ci_report: Optional CI report dict

    Returns:
        QA snapshot dict
    """
    if not ci_report:
        return {
            'available': False,
            'build_status': 'unknown',
            'test_summary': None,
            'coverage': None,
            'failed_tests': []
        }

    test_summary = ci_report.get('test_summary', {})
    coverage = ci_report.get('coverage', {})
    failed_tests = ci_report.get('failed_tests', [])

    return {
        'available': True,
        'build_status': ci_report.get('build_status', 'unknown'),
        'test_summary': {
            'total': test_summary.get('total', 0),
            'passed': test_summary.get('passed', 0),
            'failed': test_summary.get('failed', 0),
            'skipped': test_summary.get('skipped', 0),
            'flaky': test_summary.get('flaky', 0)
        } if test_summary else None,
        'coverage': {
            'line_percent': coverage.get('line_percent'),
            'branch_percent': coverage.get('branch_percent'),
            'threshold': coverage.get('threshold', {}),
            'previous': coverage.get('previous', {})
        } if coverage else None,
        'failed_tests': [
            {
                'name': test.get('name'),
                'file': test.get('file'),
                'error': test.get('error')
            }
            for test in failed_tests[:10]  # Limit to first 10
        ],
        'duration_seconds': ci_report.get('duration_seconds')
    }


def _aggregate_customer_impacts(
    commits: List[Dict[str, Any]],
    customer_watchlist: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate customer impact data.

    Args:
        commits: List of categorized commits
        customer_watchlist: Optional customer watchlist dict

    Returns:
        Customer impact summary dict
    """
    if not customer_watchlist:
        return {
            'available': False,
            'summary': {},
            'by_feature': {},
            'by_customer': {},
            'by_path': {}
        }

    # Aggregate by feature
    by_feature = defaultdict(list)
    # Aggregate by customer
    by_customer = defaultdict(list)
    # Aggregate by high-risk path
    by_path = defaultdict(list)

    # Track all impacted items
    all_features = set()
    all_customers = set()
    all_paths = set()

    for commit in commits:
        impacts = commit.get('customer_impacts', {})

        # Features
        for feature in impacts.get('matched_features', []):
            by_feature[feature].append({
                'sha': commit['sha'],
                'subject': commit['subject'],
                'category': commit.get('category', 'other')
            })
            all_features.add(feature)

        # Customers
        for customer in impacts.get('matched_customers', []):
            by_customer[customer].append({
                'sha': commit['sha'],
                'subject': commit['subject'],
                'category': commit.get('category', 'other')
            })
            all_customers.add(customer)

        # Paths
        for path in impacts.get('matched_paths', []):
            by_path[path].append({
                'sha': commit['sha'],
                'subject': commit['subject'],
                'category': commit.get('category', 'other')
            })
            all_paths.add(path)

    # Count impacted commits
    impacted_commits = [
        c for c in commits
        if c.get('customer_impacts', {}).get('impact_count', 0) > 0
    ]

    return {
        'available': True,
        'summary': {
            'total_impacted_commits': len(impacted_commits),
            'features_impacted': len(all_features),
            'customers_mentioned': len(all_customers),
            'high_risk_paths_changed': len(all_paths)
        },
        'by_feature': dict(by_feature),
        'by_customer': dict(by_customer),
        'by_path': dict(by_path),
        'watched_features': customer_watchlist.get('watched_features', []),
        'critical_customers': customer_watchlist.get('critical_customers', []),
        'high_risk_paths': customer_watchlist.get('high_risk_paths', [])
    }


def format_release_summary_markdown(summary: Dict[str, Any]) -> str:
    """
    Format release summary as markdown for quick viewing.

    This is a helper function for debugging/previewing.
    The actual release notes generation happens in the skill.

    Args:
        summary: Release summary dict

    Returns:
        Markdown-formatted summary
    """
    lines = []

    # Header
    window = summary['window']
    lines.append(f"# Release Summary: {window['from_ref']} → {window['to_ref']}")
    lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append(f"- **Commits**: {window['commit_count']}")
    lines.append(f"- **Authors**: {', '.join(window['authors'])}")
    lines.append(f"- **Files Changed**: {window['files_changed']}")
    lines.append(f"- **Lines**: +{window['insertions']} -{window['deletions']}")
    lines.append(f"- **Date Range**: {window['first_commit_date']} to {window['last_commit_date']}")
    lines.append("")

    # Risk
    risk = summary['risk']
    risk_emoji = {'low': '🟢', 'moderate': '🟡', 'high': '🔴'}.get(risk['level'], '⚪')
    lines.append(f"## Risk Assessment: {risk_emoji} {risk['level'].upper()}")
    lines.append(f"- **Score**: {risk['score']}")
    lines.append("")
    if risk['factors']:
        lines.append("**Factors:**")
        for factor in risk['factors']:
            severity_emoji = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '⚡',
                'low': 'ℹ️',
                'info': '📌',
                'warning': '⚠️'
            }.get(factor['severity'], '•')
            lines.append(f"- {severity_emoji} {factor['reason']} (+{factor['points']} points)")
        lines.append("")

    # Categories
    lines.append("## Changes by Category")
    categories = summary['categories']
    for cat_name, commits in categories.items():
        if commits:
            emoji = {
                'breaking': '💥',
                'features': '✨',
                'bugfixes': '🐛',
                'performance': '⚡',
                'documentation': '📚',
                'testing': '🧪',
                'chores': '🔧',
                'refactors': '♻️'
            }.get(cat_name, '•')
            lines.append(f"### {emoji} {cat_name.title()} ({len(commits)})")
            for commit in commits[:5]:  # Show first 5
                lines.append(f"- {commit['subject']} ({commit['sha'][:8]})")
            if len(commits) > 5:
                lines.append(f"- ... and {len(commits) - 5} more")
            lines.append("")

    # QA Snapshot
    qa = summary['qaSnapshot']
    if qa['available']:
        lines.append("## QA Snapshot")
        lines.append(f"- **Build Status**: {qa['build_status']}")
        if qa['test_summary']:
            ts = qa['test_summary']
            lines.append(f"- **Tests**: {ts['passed']}/{ts['total']} passed, {ts['failed']} failed")
        if qa['coverage']:
            cov = qa['coverage']
            lines.append(f"- **Coverage**: {cov['line_percent']:.1f}% line, {cov['branch_percent']:.1f}% branch")
        lines.append("")

    # Customer Impacts
    impacts = summary['customerImpacts']
    if impacts['available'] and impacts['summary']['total_impacted_commits'] > 0:
        lines.append("## Customer Impacts")
        s = impacts['summary']
        lines.append(f"- **Impacted Commits**: {s['total_impacted_commits']}")
        lines.append(f"- **Features Affected**: {s['features_impacted']}")
        if s['customers_mentioned'] > 0:
            lines.append(f"- **Customers Mentioned**: {s['customers_mentioned']}")
        lines.append("")

        if impacts['by_feature']:
            lines.append("**By Feature:**")
            for feature, commits in impacts['by_feature'].items():
                lines.append(f"- {feature}: {len(commits)} commit(s)")
            lines.append("")

    # Footer
    lines.append(f"*Generated at {summary['generatedAt']}*")

    return '\n'.join(lines)
