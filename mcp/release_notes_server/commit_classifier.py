"""
Commit categorization and customer impact detection.

This module analyzes commits to:
- Categorize by type (feature, fix, breaking, etc.)
- Detect breaking changes
- Identify customer-impacting changes
- Match against customer watchlist
"""
import re
import logging
from typing import Dict, List, Any, Set

logger = logging.getLogger(__name__)


# Conventional commit type mappings
CONVENTIONAL_COMMIT_TYPES = {
    'feat': 'feature',
    'feature': 'feature',
    'fix': 'bugfix',
    'bug': 'bugfix',
    'chore': 'chore',
    'refactor': 'refactor',
    'perf': 'performance',
    'performance': 'performance',
    'docs': 'documentation',
    'doc': 'documentation',
    'test': 'testing',
    'tests': 'testing',
    'style': 'chore',
    'build': 'chore',
    'ci': 'chore',
}

# Keyword heuristics for non-conventional commits
KEYWORD_PATTERNS = {
    'bugfix': ['fix', 'bug', 'patch', 'issue', 'resolve', 'correct'],
    'feature': ['add', 'new', 'feature', 'implement', 'support'],
    'performance': ['optimize', 'performance', 'faster', 'speed', 'improve'],
    'documentation': ['doc', 'docs', 'readme', 'comment', 'documentation'],
    'testing': ['test', 'tests', 'testing', 'spec', 'coverage'],
    'refactor': ['refactor', 'restructure', 'reorganize', 'clean'],
    'breaking': ['breaking', 'break', 'deprecated', 'remove', 'drop'],
}


def parse_conventional_commit(subject: str) -> Dict[str, Any]:
    """
    Parse conventional commit format: type(scope)!: description

    Args:
        subject: Commit subject line

    Returns:
        dict with type, scope, breaking, description
    """
    # Pattern: type(scope)!: description
    # or: type!: description
    # or: type: description
    pattern = r'^(\w+)(?:\(([^)]+)\))?(!)?\s*:\s*(.+)$'
    match = re.match(pattern, subject.strip())

    if match:
        commit_type = match.group(1).lower()
        scope = match.group(2) or None
        breaking_marker = match.group(3) == '!'
        description = match.group(4).strip()

        # Map to category
        category = CONVENTIONAL_COMMIT_TYPES.get(commit_type, 'other')

        return {
            'is_conventional': True,
            'type': commit_type,
            'scope': scope,
            'breaking_marker': breaking_marker,
            'description': description,
            'category': category
        }

    return {
        'is_conventional': False,
        'type': None,
        'scope': None,
        'breaking_marker': False,
        'description': subject,
        'category': None
    }


def detect_breaking_change(subject: str, body: str) -> bool:
    """
    Detect if commit is a breaking change.

    Args:
        subject: Commit subject
        body: Commit body

    Returns:
        True if breaking change detected
    """
    # Check for ! in subject (conventional commit marker)
    parsed = parse_conventional_commit(subject)
    if parsed['breaking_marker']:
        return True

    # Check for "BREAKING CHANGE:" in body
    body_lower = body.lower()
    breaking_patterns = [
        'breaking change:',
        'breaking:',
        'breaking-change:',
    ]

    for pattern in breaking_patterns:
        if pattern in body_lower:
            return True

    return False


def categorize_by_keywords(subject: str, body: str) -> str:
    """
    Categorize commit using keyword heuristics (fallback).

    Args:
        subject: Commit subject
        body: Commit body

    Returns:
        Category string
    """
    text = (subject + ' ' + body).lower()

    # Check each category's keywords
    for category, keywords in KEYWORD_PATTERNS.items():
        for keyword in keywords:
            if keyword in text:
                # Special handling for 'breaking' - don't use as primary category
                if category == 'breaking':
                    continue
                return category

    return 'other'


def match_customer_impacts(
    subject: str,
    body: str,
    file_paths: List[str],
    watchlist: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Match commit against customer watchlist.

    Args:
        subject: Commit subject
        body: Commit body
        file_paths: List of changed file paths
        watchlist: Customer watchlist dict

    Returns:
        dict with matched_features, matched_paths, impact_count
    """
    text = (subject + ' ' + body).lower()

    matched_features = []
    matched_paths = []

    # Match watched features in text
    watched_features = watchlist.get('watched_features', [])
    for feature in watched_features:
        feature_lower = feature.lower()
        if feature_lower in text:
            matched_features.append(feature)

    # Match high-risk paths in changed files
    high_risk_paths = watchlist.get('high_risk_paths', [])
    for changed_file in file_paths:
        for risk_path in high_risk_paths:
            if changed_file.startswith(risk_path):
                if risk_path not in matched_paths:
                    matched_paths.append(risk_path)

    # Match critical customers mentioned in text
    matched_customers = []
    critical_customers = watchlist.get('critical_customers', [])
    for customer in critical_customers:
        customer_lower = customer.lower()
        if customer_lower in text:
            matched_customers.append(customer)

    impact_count = len(matched_features) + len(matched_paths) + len(matched_customers)

    return {
        'matched_features': matched_features,
        'matched_paths': matched_paths,
        'matched_customers': matched_customers,
        'impact_count': impact_count
    }


def categorize_commit(commit: Dict[str, Any], watchlist: Dict[str, Any]) -> Dict[str, Any]:
    """
    Categorize a single commit and detect customer impacts.

    Adds the following fields to the commit:
    - category: str (feature, bugfix, breaking, performance, etc.)
    - is_breaking: bool
    - is_large: bool (>500 lines changed)
    - customer_impacts: dict with matched features/paths/customers
    - confidence: str (high, medium, low)

    Args:
        commit: Commit dict from git_history
        watchlist: Customer watchlist dict

    Returns:
        Enriched commit dict with categorization fields
    """
    subject = commit.get('subject', '')
    body = commit.get('body', '')
    files_changed = commit.get('files_changed', [])

    # Calculate total lines changed
    total_insertions = sum(f.get('insertions', 0) for f in files_changed)
    total_deletions = sum(f.get('deletions', 0) for f in files_changed)
    total_lines_changed = total_insertions + total_deletions

    # Parse conventional commit format
    parsed = parse_conventional_commit(subject)

    # Determine category
    if parsed['is_conventional'] and parsed['category']:
        category = parsed['category']
        confidence = 'high'
    else:
        # Fallback to keyword matching
        category = categorize_by_keywords(subject, body)
        confidence = 'medium' if category != 'other' else 'low'

    # Detect breaking changes
    is_breaking = detect_breaking_change(subject, body)

    # Override category if breaking change
    if is_breaking:
        category = 'breaking'
        confidence = 'high'

    # Check if large commit
    is_large = total_lines_changed > 500

    # Match customer impacts
    file_paths = [f['path'] for f in files_changed]
    customer_impacts = match_customer_impacts(subject, body, file_paths, watchlist)

    # Add categorization fields to commit
    enriched_commit = commit.copy()
    enriched_commit.update({
        'category': category,
        'is_breaking': is_breaking,
        'is_large': is_large,
        'customer_impacts': customer_impacts,
        'confidence': confidence,
        'total_lines_changed': total_lines_changed,
    })

    return enriched_commit


def categorize_commits(
    commits: List[Dict[str, Any]],
    watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Categorize a list of commits.

    Args:
        commits: List of commit dicts from git_history
        watchlist: Customer watchlist dict

    Returns:
        List of enriched commit dicts with categorization
    """
    categorized = []

    for commit in commits:
        enriched = categorize_commit(commit, watchlist)
        categorized.append(enriched)

    logger.info(f"Categorized {len(categorized)} commits")

    # Log category distribution
    category_counts = {}
    for commit in categorized:
        cat = commit['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1

    logger.debug(f"Category distribution: {category_counts}")

    return categorized


def get_category_summary(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics for categorized commits.

    Args:
        commits: List of categorized commits

    Returns:
        dict with counts per category, breaking changes, customer impacts
    """
    category_counts = {}
    breaking_count = 0
    large_count = 0
    customer_impact_commits = 0
    total_customer_impacts = 0

    for commit in commits:
        # Count by category
        category = commit.get('category', 'other')
        category_counts[category] = category_counts.get(category, 0) + 1

        # Count breaking changes
        if commit.get('is_breaking'):
            breaking_count += 1

        # Count large commits
        if commit.get('is_large'):
            large_count += 1

        # Count customer impacts
        impacts = commit.get('customer_impacts', {})
        impact_count = impacts.get('impact_count', 0)
        if impact_count > 0:
            customer_impact_commits += 1
            total_customer_impacts += impact_count

    return {
        'total_commits': len(commits),
        'category_counts': category_counts,
        'breaking_changes': breaking_count,
        'large_commits': large_count,
        'customer_impact_commits': customer_impact_commits,
        'total_customer_impacts': total_customer_impacts,
    }
