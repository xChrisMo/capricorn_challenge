---
description: Generate release notes and a release quality report from a range of commits
arguments:
  from_ref:
    description: Starting git ref (tag, branch, or SHA)
    required: true
  to_ref:
    description: Ending git ref (tag, branch, or SHA)
    required: true
options:
  ci-report:
    description: Path to CI report JSON file
    default: ./ci_report.json
  watchlist:
    description: Path to customer watchlist JSON file
    default: ./customer_watchlist.json
  enablement:
    description: Also generate an internal enablement brief for CS/Support
    type: boolean
dependencies:
  - mcp_server: release-notes-server
custom: true
---

You are a command handler for `/release-notes`.

When the user runs:

`/release-notes <from_ref> <to_ref> [--ci-report PATH] [--watchlist PATH] [--enablement]`

follow this workflow:

## 1. Validate Inputs

- Ensure `from_ref` and `to_ref` are provided.
- If they are identical, explain the problem and show a usage example instead of continuing.
- If refs are missing, show usage:
  ```
  Usage: /release-notes <from_ref> <to_ref> [options]

  Examples:
    /release-notes v1.0.0 v1.1.0
    /release-notes main release-candidate
    /release-notes HEAD~10 HEAD
    /release-notes v2.0.0 HEAD --enablement
  ```

## 2. Gather Raw Data via MCP Tools

Call these MCP tools from the `release-notes-server`:

```python
# Get git history
git_history = get_git_history(
    from_ref=<from_ref>,
    to_ref=<to_ref>,
    include_diffs=False,
    max_commits=200
)

# Get CI report (optional - may return None)
ci_report = get_ci_report(
    report_path=<--ci-report option or default>
)

# Get customer watchlist (always returns valid structure with defaults)
watchlist = get_customer_watchlist(
    watchlist_path=<--watchlist option or default>
)
```

**Error Handling:**
- Invalid refs: Explain error, suggest `git tag --list` or `git branch -a`
- Not a git repo: Explain, suggest running from repository root
- Empty commit range: Confirm refs are in correct order (older first)
- MCP server not running: Explain how to configure/start it

## 3. Enrich and Aggregate

Process the data using the MCP server's Python modules:

```python
from mcp.release_notes_server import commit_classifier, risk_calculator, aggregator

# Categorize commits with customer impact detection
categorized_commits = commit_classifier.categorize_commits(
    git_history['commits'],
    watchlist
)

# Calculate release risk score
risk = risk_calculator.calculate_release_risk(
    categorized_commits,
    ci_report,
    watchlist
)

# Build comprehensive release summary
release_summary = aggregator.build_release_summary(
    git_history,
    ci_report,
    watchlist,
    categorized_commits,
    risk
)
```

This produces a `release_summary` JSON object with:
- `window`: Git history metadata (refs, SHAs, commits, dates, stats)
- `risk`: Risk score, level (LOW/MODERATE/HIGH), factors
- `categories`: Commits grouped by type (features, bugfixes, breaking, etc.)
- `qaSnapshot`: Build status, tests, coverage, failures
- `customerImpacts`: Affected features, customers, paths
- `generatedAt`: ISO timestamp

## 4. Generate Human Output via the `release-notes` Skill

Pass the `release_summary` JSON to the `release-notes` skill, which will generate:

1. **Developer-Facing Release Quality Report**
   - Risk assessment with score and factors
   - Change summary by category
   - QA snapshot (tests, coverage, failures)
   - Customer impact analysis
   - Actionable recommendations

2. **Customer-Facing Release Notes**
   - Summary of key changes
   - New features (benefit-focused)
   - Bug fixes (impact-focused)
   - Performance improvements
   - Breaking changes with migration guidance
   - Known issues and quality status

The skill follows strict guardrails:
- Only describes changes present in the data
- Never invents features or metrics
- Handles missing data gracefully
- Uses appropriate tone for each audience

## 5. Optional: Enablement Brief

If `--enablement` flag is provided:
- Generate an additional internal brief for Customer Success/Support teams
- Focus on customer value, business impact, and talking points
- Keep it non-technical and business-focused
- Include under heading: `# Enablement Brief`

## 6. Output Format

Always produce:

1. **Context Header**
   ```markdown
   # Release Analysis: {from_ref} → {to_ref}

   Analyzed {count} commits from {first_date} to {last_date}
   {Note about missing QA/watchlist data if applicable}
   ```

2. **Release Quality Report** (from skill)
3. **Customer Release Notes** (from skill)
4. **Enablement Brief** (if requested)

## Error Handling & Guardrails

**Missing Data:**
- If `ci_report` is None: Note "QA data not available - risk assessment based on commits only"
- If watchlist has defaults only: Note "Using default watchlist - no project-specific customer tracking"
- Continue with available data - don't fail

**Invalid Input:**
- Malformed refs: Explain and suggest valid examples
- Identical refs: "No commits between identical refs"
- Reversed refs: Detect and suggest correct order
- MCP errors: Provide clear troubleshooting steps

**Never:**
- Invent commits or changes
- Guess at missing metrics
- Hide quality concerns or risks
- Generate output without running the analysis

## Examples

**Basic usage:**
```
/release-notes v1.2.0 v1.3.0
```

**With custom paths:**
```
/release-notes main HEAD --ci-report build/test-results.json
```

**Full analysis with enablement brief:**
```
/release-notes v2.0.0 v2.1.0 --enablement
```

**Recent commits:**
```
/release-notes HEAD~20 HEAD
```

## Success Criteria

A successful execution should:
- ✅ Fetch real data from git, CI, and watchlist
- ✅ Categorize all commits accurately
- ✅ Calculate risk score with clear factors
- ✅ Generate both developer and customer outputs
- ✅ Provide actionable recommendations
- ✅ Handle missing data gracefully
- ✅ Be honest about quality concerns
