"""
Release risk scoring and assessment.

This module calculates risk scores for releases based on:
- Breaking changes
- Customer-impacting commits
- Large commits
- Test coverage
- Other quality metrics
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# Risk level thresholds
RISK_LEVEL_LOW = 3
RISK_LEVEL_MODERATE = 6

# Scoring weights
BREAKING_CHANGE_POINTS = 2
CUSTOMER_IMPACT_POINTS = 1
CUSTOMER_IMPACT_CAP = 3
LARGE_COMMIT_POINTS = 1
LOW_COVERAGE_POINTS = 1
COVERAGE_THRESHOLD = 80.0


def calculate_release_risk(
    commits: List[Dict[str, Any]],
    ci_report: Optional[Dict[str, Any]] = None,
    customer_watchlist: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate risk score and level for a release.

    Scoring:
    - +2 per breaking change commit
    - +1 per customer-impacting commit (capped at +3 total)
    - +1 per large commit (>500 lines)
    - +1 if test coverage < 80%

    Risk levels:
    - low: score < 3
    - moderate: score 3-5
    - high: score >= 6

    Args:
        commits: List of categorized commits
        ci_report: Optional CI report dict
        customer_watchlist: Optional customer watchlist dict

    Returns:
        dict with score, level, factors
    """
    score = 0
    factors = []

    # Count breaking changes
    breaking_commits = [c for c in commits if c.get('is_breaking', False)]
    breaking_count = len(breaking_commits)

    if breaking_count > 0:
        points = breaking_count * BREAKING_CHANGE_POINTS
        score += points
        factors.append({
            'reason': f'{breaking_count} breaking change commit(s)',
            'points': points,
            'severity': 'high'
        })

    # Count customer-impacting commits
    customer_impact_commits = [
        c for c in commits
        if c.get('customer_impacts', {}).get('impact_count', 0) > 0
    ]
    customer_impact_count = len(customer_impact_commits)

    if customer_impact_count > 0:
        # Cap at CUSTOMER_IMPACT_CAP points
        points = min(customer_impact_count * CUSTOMER_IMPACT_POINTS, CUSTOMER_IMPACT_CAP)
        score += points
        factors.append({
            'reason': f'{customer_impact_count} customer-impacting commit(s)',
            'points': points,
            'severity': 'medium'
        })

        # Detail which features/paths were impacted
        all_features = set()
        all_paths = set()
        for commit in customer_impact_commits:
            impacts = commit.get('customer_impacts', {})
            all_features.update(impacts.get('matched_features', []))
            all_paths.update(impacts.get('matched_paths', []))

        if all_features:
            factors.append({
                'reason': f'Impacts features: {", ".join(sorted(all_features))}',
                'points': 0,
                'severity': 'info'
            })
        if all_paths:
            factors.append({
                'reason': f'Changes in high-risk paths: {", ".join(sorted(all_paths))}',
                'points': 0,
                'severity': 'info'
            })

    # Count large commits
    large_commits = [c for c in commits if c.get('is_large', False)]
    large_count = len(large_commits)

    if large_count > 0:
        points = large_count * LARGE_COMMIT_POINTS
        score += points
        factors.append({
            'reason': f'{large_count} large commit(s) (>500 lines)',
            'points': points,
            'severity': 'low'
        })

    # Check test coverage
    if ci_report:
        coverage_data = ci_report.get('coverage', {})
        line_coverage = coverage_data.get('line_percent')

        if line_coverage is not None:
            if line_coverage < COVERAGE_THRESHOLD:
                points = LOW_COVERAGE_POINTS
                score += points
                factors.append({
                    'reason': f'Test coverage below threshold ({line_coverage:.1f}% < {COVERAGE_THRESHOLD}%)',
                    'points': points,
                    'severity': 'medium'
                })

            # Also note coverage drops
            previous_coverage = coverage_data.get('previous', {}).get('line_percent')
            if previous_coverage is not None:
                coverage_drop = previous_coverage - line_coverage
                if coverage_drop > 5:
                    factors.append({
                        'reason': f'Coverage dropped {coverage_drop:.1f}% ({previous_coverage:.1f}% → {line_coverage:.1f}%)',
                        'points': 0,
                        'severity': 'warning'
                    })

        # Check for failed tests
        test_summary = ci_report.get('test_summary', {})
        failed_tests = test_summary.get('failed', 0)

        if failed_tests > 0:
            factors.append({
                'reason': f'{failed_tests} test(s) failing',
                'points': 0,
                'severity': 'critical'
            })

    # Determine risk level
    if score >= RISK_LEVEL_MODERATE:
        level = 'high'
    elif score >= RISK_LEVEL_LOW:
        level = 'moderate'
    else:
        level = 'low'

    logger.info(f"Calculated release risk: {level} (score: {score})")

    return {
        'score': score,
        'level': level,
        'factors': factors
    }


def get_risk_recommendations(
    risk_assessment: Dict[str, Any],
    commits: List[Dict[str, Any]],
    ci_report: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Generate actionable recommendations based on risk assessment.

    Args:
        risk_assessment: Risk assessment dict from calculate_release_risk
        commits: List of categorized commits
        ci_report: Optional CI report dict

    Returns:
        List of recommendation strings
    """
    recommendations = []
    level = risk_assessment['level']

    # Breaking changes
    breaking_commits = [c for c in commits if c.get('is_breaking', False)]
    if breaking_commits:
        recommendations.append(
            f'⚠️  Review {len(breaking_commits)} breaking change(s) with stakeholders'
        )
        recommendations.append(
            '📝 Update migration guide and changelog with breaking changes'
        )

    # Customer impacts
    customer_impact_commits = [
        c for c in commits
        if c.get('customer_impacts', {}).get('impact_count', 0) > 0
    ]
    if customer_impact_commits:
        recommendations.append(
            f'📢 Notify customer success about {len(customer_impact_commits)} impactful change(s)'
        )

    # High-risk paths
    high_risk_commits = [
        c for c in commits
        if c.get('customer_impacts', {}).get('matched_paths')
    ]
    if high_risk_commits:
        recommendations.append(
            '🔍 Extra QA attention on auth, payment, or billing flows'
        )

    # Large commits
    large_commits = [c for c in commits if c.get('is_large', False)]
    if large_commits:
        recommendations.append(
            f'👀 Manual review of {len(large_commits)} large commit(s) for hidden issues'
        )

    # CI issues
    if ci_report:
        failed_tests = ci_report.get('test_summary', {}).get('failed', 0)
        if failed_tests > 0:
            recommendations.append(
                f'🚨 Fix {failed_tests} failing test(s) before release'
            )

        coverage = ci_report.get('coverage', {}).get('line_percent')
        if coverage and coverage < COVERAGE_THRESHOLD:
            recommendations.append(
                f'📊 Improve test coverage (currently {coverage:.1f}%, target {COVERAGE_THRESHOLD}%)'
            )

    # General recommendations based on risk level
    if level == 'high':
        recommendations.append(
            '⏸️  Consider splitting this release into smaller, lower-risk releases'
        )
        recommendations.append(
            '🎯 Use feature flags for gradual rollout of high-risk changes'
        )
    elif level == 'moderate':
        recommendations.append(
            '✅ Standard QA process with extra attention to flagged areas'
        )

    return recommendations


def summarize_risk_by_category(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarize risk factors by commit category.

    Args:
        commits: List of categorized commits

    Returns:
        dict with risk breakdown by category
    """
    category_risk = {}

    for commit in commits:
        category = commit.get('category', 'other')

        if category not in category_risk:
            category_risk[category] = {
                'count': 0,
                'breaking': 0,
                'customer_impact': 0,
                'large': 0,
            }

        category_risk[category]['count'] += 1

        if commit.get('is_breaking'):
            category_risk[category]['breaking'] += 1

        if commit.get('customer_impacts', {}).get('impact_count', 0) > 0:
            category_risk[category]['customer_impact'] += 1

        if commit.get('is_large'):
            category_risk[category]['large'] += 1

    return category_risk
