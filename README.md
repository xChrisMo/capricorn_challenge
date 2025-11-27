# Release Notes Assistant

A production-ready Claude Code plugin that automates release note generation with intelligent risk assessment, QA integration, and customer impact analysis.

## Problem Statement

Manually creating release notes is tedious, error-prone, and often incomplete:

- **Developers** spend hours combing through git logs, categorizing commits, and writing summaries
- **Engineering leads** struggle to assess release risk without manually reviewing every change
- **QA teams** lack visibility into which commits might need extra testing
- **Customer Success/Support** don't know which customers or features are affected by changes
- **Product managers** need both technical details and customer-ready messaging

Traditional approaches fall short:
- Raw git logs are unstructured and hard to parse
- Manual categorization is inconsistent
- Risk assessment is subjective and often skipped
- Customer impact tracking requires tribal knowledge
- Creating two outputs (internal quality report + external release notes) doubles the work

This plugin solves these problems by automating the entire workflow from git history to polished release notes.

## Architecture

The plugin uses multiple Claude Code components working together:

```
┌─────────────────────────────────────────────────────────────────┐
│  User runs: /release-notes v1.0.0 v1.1.0                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Command (.claude/commands/release-notes.md)                    │
│  - Validates inputs                                             │
│  - Orchestrates workflow                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  MCP Server (mcp/release_notes_server/)                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Git History  │  │  CI Report   │  │  Watchlist   │          │
│  │   (commits)  │  │ (test/cov)   │  │ (customers)  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┴─────────────────┘                   │
│                           ↓                                     │
│         ┌──────────────────────────────────┐                    │
│         │  Categorization & Risk Scoring   │                    │
│         │  - Conventional commits parsing  │                    │
│         │  - Breaking change detection     │                    │
│         │  - Customer impact matching      │                    │
│         │  - Risk score calculation        │                    │
│         └─────────────┬────────────────────┘                    │
│                       ↓                                         │
│         ┌──────────────────────────────────┐                    │
│         │      Aggregator Module           │                    │
│         │  - Builds structured JSON        │                    │
│         │  - Groups commits by category    │                    │
│         │  - Aggregates customer impacts   │                    │
│         └─────────────┬────────────────────┘                    │
└───────────────────────┼──────────────────────────────────────────┘
                        ↓
              ┌──────────────────┐
              │  release_summary │
              │      (JSON)      │
              └────────┬─────────┘
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│  Skill (.claude/skills/release-notes.md)                        │
│  - Generates Developer Quality Report                           │
│  - Generates Customer Release Notes                             │
│  - Applies tone/style guidelines                                │
│  - Enforces guardrails (no hallucination)                       │
└─────────────────────────────────────────────────────────────────┘
                       ↓
         ┌──────────────────────────────┐
         │  📄 Release Quality Report   │
         │  📝 Customer Release Notes   │
         └──────────────────────────────┘
```

### Components

**1. MCP Server** (`mcp/release_notes_server/`)
- **Tools**: 3 MCP tools exposed via JSON-RPC 2.0
  - `get_git_history`: Fetches and parses git log with file statistics
  - `get_ci_report`: Loads CI/test results from JSON file
  - `get_customer_watchlist`: Loads customer impact configuration
- **Modules**: Pure Python (stdlib only, no dependencies)
  - `git_tools.py`: Git operations via subprocess
  - `commit_classifier.py`: Conventional commits + keyword heuristics
  - `risk_calculator.py`: Deterministic risk scoring (0-10+ scale)
  - `aggregator.py`: Data aggregation into structured JSON
  - `file_utils.py`: JSON file I/O with validation

**2. Command** (`.claude/commands/release-notes.md`)
- Entry point: `/release-notes <from_ref> <to_ref> [options]`
- Validates inputs (refs, options)
- Calls MCP tools to gather data
- Processes data through categorization and risk scoring
- Passes aggregated JSON to skill for output generation

**3. Main Skill** (`.claude/skills/release-notes.md`)
- Receives structured JSON from command
- Generates two outputs:
  - **Developer Quality Report**: Risk assessment, QA status, recommendations
  - **Customer Release Notes**: Clean, benefit-focused changelog
- Enforces strict guardrails against hallucination
- Handles missing data gracefully

**4. Helper Skill** (`.claude/skills/release-notes-guide.md`)
- Activates when users ask about release notes
- Guides users to the correct command
- Helps identify appropriate git refs
- Explains options and expected output

## Installation & Setup

### Prerequisites

- Claude Code with MCP support
- Python 3.8+ (for MCP server)
- Git repository

### Installation

1. **Clone or copy this plugin** to your project directory

2. **Configure Claude Code** by adding the plugin configuration to your Claude Code settings:

   The plugin includes a `plugin.json` that configures:
   - MCP server: `release-notes-server`
   - Command: `/release-notes`
   - Skills: `release-notes` and `release-notes-guide`

   Claude Code will automatically load the configuration from `plugin.json`.

3. **Verify the MCP server** can be started:
   ```bash
   python -m mcp.release_notes_server.server
   # Should wait for JSON-RPC messages on stdin (press Ctrl+C to exit)
   ```

4. **(Optional) Configure CI report and watchlist**:
   ```bash
   # Copy example files
   cp examples/ci_report.example.json ci_report.json
   cp examples/customer_watchlist.example.json customer_watchlist.json

   # Edit them for your project
   ```

### Configuration Files

**`ci_report.json` (optional)** - Provides test and coverage data:
```json
{
  "test_summary": {
    "total": 150,
    "passed": 148,
    "failed": 2,
    "skipped": 0
  },
  "coverage": {
    "line_percent": 85.5,
    "branch_percent": 78.0
  },
  "build_status": "unstable",
  "failed_tests": [...]
}
```

**`customer_watchlist.json` (optional)** - Defines impact tracking:
```json
{
  "critical_customers": ["acme-corp", "globex"],
  "watched_features": ["authentication", "payment-processing"],
  "high_risk_paths": ["src/auth/", "src/payment/"],
  "breaking_change_keywords": ["BREAKING", "deprecated"]
}
```

**Graceful degradation**: The plugin works without these files but provides richer analysis when they're present.

## Usage

### Basic Usage

Generate release notes between two git refs:

```bash
/release-notes v1.0.0 v1.1.0
```

This will:
1. Fetch all commits between the refs
2. Categorize each commit (feature, bugfix, breaking, etc.)
3. Calculate release risk score
4. Generate both developer and customer-facing outputs

### Advanced Usage

**Compare branches:**
```bash
/release-notes main release-candidate
```

**Recent commits:**
```bash
/release-notes HEAD~10 HEAD
```

**With custom CI report path:**
```bash
/release-notes v2.0.0 v2.1.0 --ci-report build/test-results.json
```

**With custom watchlist:**
```bash
/release-notes v1.5.0 HEAD --watchlist config/production-watchlist.json
```

**Include enablement brief for CS/Support:**
```bash
/release-notes v3.0.0 v3.1.0 --enablement
```

### Options

- `--ci-report PATH`: Path to CI report JSON (default: `./ci_report.json`)
- `--watchlist PATH`: Path to customer watchlist JSON (default: `./customer_watchlist.json`)
- `--enablement`: Generate additional internal brief for Customer Success/Support teams

### Finding Git Refs

Not sure which refs to use? Try:

```bash
# List tags
git tag --list

# List branches
git branch -a

# View recent commits
git log --oneline -20
```

Or just ask the `release-notes-guide` skill for help!

## Demo

### Example Run

Let's generate release notes for commits between `v1.3.0` and `v1.4.0`:

```
/release-notes v1.3.0 v1.4.0
```

### Output: Release Quality Report

```markdown
# Release Quality Report: v1.3.0 → v1.4.0

## Overview
- **Commits**: 23
- **Authors**: Alice, Bob, Charlie
- **Files Changed**: 47
- **Lines**: +1,234 -567
- **Date Range**: 2024-01-10 to 2024-01-28

## Risk Assessment: 🟡 MODERATE
- **Score**: 4

**Risk Factors:**
- ⚠️ 1 breaking change commit(s) (+2 points)
- ⚡ 2 customer-impacting commit(s) (+2 points)
- 📌 Impacts features: authentication, payment-processing

**Recommendations:**
- Review breaking changes with stakeholders before release
- Notify Customer Success about impacted features
- Extra QA attention on authentication and payment flows
- Consider feature flags for breaking changes

## Change Summary
- 23 commits total
  - 5 features
  - 12 bugfixes
  - 1 breaking change
  - 3 performance improvements
  - 2 documentation updates

**Breaking Changes:**
- feat!: migrate OAuth to v2.0 endpoints (da3f4b2)

**Large Commits** (>500 lines):
- refactor: restructure payment processing module (2a1c5f8)

## QA Snapshot
- **Build**: ⚠️ UNSTABLE
- **Tests**: 148/150 passed (2 failed)
- **Coverage**: 82.3% (↓ 2.1% from previous)

**Failed Tests:**
1. `test_oauth_token_refresh` - tests/test_auth.py
   - TimeoutError: OAuth service did not respond within 5s
2. `test_bulk_payment_processing` - tests/test_payment.py
   - AssertionError: Expected 200 transactions, processed 198

## Customer Impact Analysis
- **Affected Features**: authentication, payment-processing
- **High-Risk Paths**: src/auth/, src/payment/
- **Customer Mentions**: acme-corp mentioned in 1 commit

**Impacts by Feature:**
- authentication: 3 commits (1 breaking, 2 fixes)
- payment-processing: 2 commits (1 feature, 1 perf)

## Action Items Before Release
1. 🔴 **Critical**: Fix failing OAuth test or document known issue
2. 🟡 **Important**: Investigate payment test failure (2 missing transactions)
3. 🟡 **Important**: Prepare migration guide for OAuth v2.0 changes
4. 🟢 **Recommended**: Notify acme-corp about authentication improvements
5. 🟢 **Recommended**: Update coverage to meet 85% threshold
```

### Output: Customer Release Notes

```markdown
# Release Notes: v1.4.0

## Summary
- Upgraded to OAuth 2.0 for improved security (requires migration)
- Enhanced payment processing speed by 40%
- Fixed 12 bugs including critical authentication issues

## New Features

**Improved Payment Processing**
You can now process bulk payments up to 40% faster. Large payment batches that previously took several minutes now complete in under a minute, improving cash flow management and reducing processing delays.

**Enhanced Dashboard Analytics**
The dashboard now shows real-time payment status updates and includes new filtering options to help you track transactions more effectively.

**API Rate Limiting**
New intelligent rate limiting prevents accidental overuse while maintaining full throughput for normal operations. You'll see clearer error messages if limits are reached.

## Bug Fixes

- Fixed timeout errors when refreshing authentication tokens during long sessions
- Resolved issue where bulk export would occasionally miss recent transactions
- Corrected timezone handling in scheduled payment processing
- Fixed memory leak in webhook notification system
- Improved error messages throughout the payment workflow

## Performance & Reliability

- **40% faster** payment processing for bulk operations
- Reduced memory usage by 25% during peak loads
- Improved webhook delivery reliability to 99.9%

## Breaking Changes

⚠️ **OAuth 2.0 Migration Required**

We've upgraded our authentication system to OAuth 2.0 for enhanced security and better compliance with industry standards.

**What changed:**
- Legacy OAuth 1.0 endpoints are deprecated and will be removed in v1.5.0
- New OAuth 2.0 endpoints provide better security and token refresh capabilities

**Migration steps:**
1. Update your OAuth client configuration to use the new v2.0 endpoints
2. Test authentication flows in your staging environment
3. Update production integrations before May 1st, 2024

See our [OAuth 2.0 Migration Guide](docs/oauth-migration.md) for detailed instructions.

## Known Issues & Quality

- **Build**: Currently unstable due to 2 failing tests
- **Test Coverage**: 82.3% (target: 85%)
- **Known Issues**:
  - OAuth token refresh occasionally times out under heavy load (investigating)
  - Bulk payment processing may miss 1-2% of transactions in batches >500 (fix coming in v1.4.1)

We recommend thorough testing in staging before deploying this release to production.

## Customer Impact

**Authentication System**: If you're using OAuth integration, please review the migration guide. The changes improve security but require configuration updates.

**Payment Processing**: High-volume payment users will see significant performance improvements. If you process more than 100 transactions daily, expect faster processing times.
```

## Reflection

### What This Plugin Does Well

**1. Zero Dependencies**
- Uses only Python standard library
- No pip installs, no version conflicts
- Easy to deploy and maintain

**2. Graceful Degradation**
- Works without CI reports or watchlist files
- Provides sensible defaults when data is missing
- Never fails due to optional inputs

**3. Deterministic Risk Scoring**
- Clear, repeatable algorithm
- Transparent factors (breaking changes, size, coverage, customer impact)
- Actionable recommendations based on risk level

**4. Dual Audience Output**
- Internal quality report for engineering decisions
- External release notes for customers
- Different tone and focus for each

**5. Production-Ready Error Handling**
- Comprehensive test suite (37 tests)
- Detailed error messages with suggestions
- Proper logging at all levels

**6. Real Git Integration**
- Parses actual git log data (no hallucination)
- Handles large commit ranges efficiently
- Supports tags, branches, SHAs, relative refs (HEAD~N)

### What Could Be Improved With More Time

**1. Dedicated Enablement Subagent**
Currently the `--enablement` flag is documented but would benefit from a specialized subagent that:
- Focuses on competitive positioning
- Generates customer success talking points
- Creates technical enablement materials
- Tailors messaging for different customer segments

**2. Deeper CI Integration**
- Direct integration with CI systems (GitHub Actions, CircleCI, Jenkins)
- Automatic retrieval of test results without manual JSON export
- Trend analysis across multiple releases
- Performance regression detection

**3. Issue Tracker Integration**
- Link commits to Jira/GitHub issues automatically
- Include issue context in release notes
- Track which issues are resolved in each release
- Generate "closed issues" sections automatically

**4. Template Customization**
- Allow projects to define custom release note templates
- Support multiple output formats (GitHub, Confluence, Email)
- Configurable risk thresholds per project
- Custom categorization rules

**5. Historical Analysis**
- Compare current release risk to historical averages
- Identify trends (increasing test failures, declining coverage)
- Suggest optimal release cadence based on commit patterns
- Flag unusual patterns (massive commits, long gaps)

**6. Interactive Refinement**
- Allow users to edit categorization in-context
- Provide suggestions for better commit messages
- Let users override risk assessments with justification
- Save custom classifications for future releases

### How AI Assisted Development

**Architecture Design**
- Claude helped validate the problem statement and proposed solution
- Provided suggestions for component boundaries and data flow
- Recommended JSON schemas and API structures
- Identified edge cases and error scenarios

**Code Generation**
- Wrote boilerplate for MCP server, tools, and test suites
- Generated initial implementations for git parsing and JSON I/O
- Created comprehensive test cases
- Produced documentation and usage examples

**Human Guidance Required**
- Overall architecture decisions (which components, how they interact)
- Risk scoring algorithm design (what factors, how to weight them)
- Output tone and structure (developer vs customer voice)
- Debugging complex issues (git log parsing, two-pass algorithm)
- Quality standards (test coverage, error handling depth)

**The Balance**
AI excelled at:
- Rapid prototyping and iteration
- Comprehensive test coverage
- Documentation completeness
- Following established patterns

Humans provided:
- Strategic direction and constraints
- Domain expertise (release management pain points)
- Quality judgment (when good enough vs needs refinement)
- Creative problem-solving (the two-pass git log parsing fix)

The plugin is a collaboration: AI provided speed and thoroughness, human judgment ensured it solved the right problem the right way.

---

## License

MIT License - see LICENSE file for details

## Credits

Built with Claude Code for the Capricorn Challenge submission.

Author: ChrisMo
