# Release Notes Plugin for Claude Code

A production-ready Claude Code plugin that generates comprehensive release notes with risk assessment, QA integration, and customer impact analysis.

## Overview

This plugin helps development teams ship quality releases by:

- 📊 **Analyzing git history** between any two refs (tags, branches, SHAs)
- 🏷️ **Categorizing commits** automatically (features, fixes, breaking changes, etc.)
- ⚠️ **Calculating release risk** based on change types, size, and test coverage
- 🎯 **Identifying customer impacts** using a configurable watchlist
- ✅ **Integrating QA data** from CI/CD reports
- 📝 **Generating two outputs**:
  - Developer-focused quality report with risk assessment
  - Customer-facing release notes ready to publish

## Architecture

The plugin uses multiple Claude Code components working together:

1. **MCP Server** (`mcp/release_notes_server/`): Python JSON-RPC server with 3 tools
   - `get_git_history`: Fetch and parse git log data
   - `get_ci_report`: Load CI/test results from JSON
   - `get_customer_watchlist`: Load customer impact watchlist

2. **Command** (`.claude/commands/release-notes.md`): Slash command `/release-notes <from> <to>`

3. **Skill** (`.claude/skills/release-notes.md`): Orchestrates data gathering and note generation

4. **Python Modules** (stdlib only, no dependencies):
   - `git_tools.py`: Git operations via subprocess
   - `commit_classifier.py`: Categorization and impact detection
   - `risk_calculator.py`: Risk scoring and recommendations
   - `aggregator.py`: Data aggregation into structured JSON
   - `file_utils.py`: JSON file I/O with validation

## Quick Start

### 1. Install the MCP Server

From your repository root:

```bash
# The MCP server is ready to use - no installation needed!
# It uses only Python standard library (no pip install required)
```

### 2. Configure Claude Code

Add the MCP server to your Claude Code configuration:

```json
{
  "mcpServers": {
    "release-notes-server": {
      "command": "python",
      "args": ["-m", "mcp.release_notes_server.server"],
      "cwd": "/path/to/capricorn_challenge"
    }
  }
}
```

### 3. Set Up Configuration Files (Optional)

The plugin works without configuration files but is more powerful with them:

```bash
# Copy example files to your repo root
cp examples/ci_report.example.json ci_report.json
cp examples/customer_watchlist.example.json customer_watchlist.json

# Edit them to match your project
```

**ci_report.json**: Test results, coverage, build status
**customer_watchlist.json**: Critical customers, watched features, high-risk paths

### 4. Generate Release Notes

In Claude Code, use the slash command:

```
/release-notes v1.0.0 v1.1.0
```

Or with branch names:

```
/release-notes main release-candidate
```

Or with commit references:

```
/release-notes HEAD~10 HEAD
```

## Usage Examples

### Basic Usage

```
/release-notes v1.2.0 v1.3.0
```

Claude will:
1. Fetch git history between the refs
2. Categorize all commits
3. Calculate release risk
4. Generate both developer and customer-facing notes

### With QA Integration

1. Export your CI results to `ci_report.json`:
   ```json
   {
     "test_summary": {"total": 150, "passed": 148, "failed": 2},
     "coverage": {"line_percent": 85.5},
     "build_status": "unstable"
   }
   ```

2. Run the command:
   ```
   /release-notes v1.2.0 HEAD
   ```

3. Claude will include QA status in risk calculation and flag failing tests

### With Customer Impact Tracking

1. Define your watchlist in `customer_watchlist.json`:
   ```json
   {
     "critical_customers": ["acme-corp", "globex"],
     "watched_features": ["authentication", "payment-processing"],
     "high_risk_paths": ["src/auth/", "src/payment/"]
   }
   ```

2. Run the command - Claude will flag any commits affecting these areas

## Configuration Files

### ci_report.json (Optional)

Provides CI/test data for risk assessment:

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
    "previous": {"line_percent": 87.0}
  },
  "build_status": "unstable",
  "failed_tests": [
    {
      "name": "test_authentication",
      "file": "tests/test_auth.py",
      "error": "AssertionError: ..."
    }
  ]
}
```

**Graceful degradation**: If missing, plugin continues without QA data.

### customer_watchlist.json (Optional)

Defines what to watch for customer impact:

```json
{
  "critical_customers": ["customer-id-1", "customer-id-2"],
  "watched_features": ["authentication", "payment-processing"],
  "high_risk_paths": ["src/payment/", "src/auth/"],
  "breaking_change_keywords": ["BREAKING", "deprecated"]
}
```

**Graceful degradation**: If missing, uses sensible defaults.

## Risk Scoring

The plugin calculates a risk score (0-10+) based on:

- **+2 points** per breaking change commit
- **+1 point** per customer-impacting commit (capped at +3)
- **+1 point** per large commit (>500 lines changed)
- **+1 point** if test coverage < 80%

**Risk Levels**:
- 🟢 **LOW** (score < 3): Standard QA process
- 🟡 **MODERATE** (score 3-5): Extra attention on flagged areas
- 🔴 **HIGH** (score ≥ 6): Consider splitting release, use feature flags

## Commit Categorization

Commits are automatically categorized using:

1. **Conventional Commits** (preferred): `type(scope): description`
   - `feat:` → Feature
   - `fix:` → Bugfix
   - `perf:` → Performance
   - `docs:` → Documentation
   - `test:` → Testing
   - `refactor:` → Refactor
   - `chore:` → Chore

2. **Keyword Heuristics** (fallback): Analyzes commit message text
   - "fix", "bug" → Bugfix
   - "add", "new" → Feature
   - "optimize", "performance" → Performance
   - etc.

3. **Breaking Change Detection**:
   - `!` marker in type: `feat!:`
   - `BREAKING CHANGE:` in commit body

## Output Examples

### Developer Quality Report

```markdown
# Release Quality Report: v1.2.0 → v1.3.0

## Risk Assessment: 🟡 MODERATE (Score: 4)

**Risk Factors:**
- ⚠️ 1 breaking change commit(s) (+2 points)
- ⚡ 2 customer-impacting commit(s) (+2 points)
- 📌 Impacts features: authentication, payment-processing

**Recommendations:**
- Review breaking changes with stakeholders
- Notify customer success about impactful changes
- Extra QA attention on auth and payment flows

## Change Summary
- 15 commits total
- 3 features
- 8 bugfixes
- 1 breaking change
- 2 performance improvements
- 1 documentation update

## QA Snapshot
- Build: ⚠️ UNSTABLE
- Tests: 148/150 passed (2 failed)
- Coverage: 85.5% (↓ 1.5% from previous)

**Failed Tests:**
1. test_authentication_timeout (tests/test_auth.py)
2. test_payment_processing (tests/test_payment.py)

## Customer Impact Analysis
**Affected Features:** authentication, payment-processing
**High-Risk Changes:** src/auth/, src/payment/
**Customer Mentions:** acme-corp (1 commit)

---

[Detailed commit breakdown by category...]
```

### Customer-Facing Release Notes

```markdown
# Release Notes: v1.3.0

## New Features

- **OAuth Authentication**: You can now sign in using Google and GitHub accounts
- **Batch Export**: Export multiple reports at once with the new batch export feature
- **Dark Mode**: Toggle dark mode in user settings

## Bug Fixes

- Fixed timeout errors when processing large payment transactions
- Resolved issue where email notifications were not being sent
- Corrected timezone handling in scheduled reports

## Improvements

- Faster dashboard loading (40% improvement)
- Improved error messages throughout the application
- Enhanced mobile responsiveness for reports

## Breaking Changes

⚠️ **API Authentication**: The deprecated `/api/v1/auth` endpoint has been removed.
Please migrate to `/api/v2/auth`. See our [migration guide](link) for details.

## Known Issues

- Large file uploads (>100MB) may timeout - fix coming in v1.3.1
```

## Testing

The plugin includes comprehensive test suites:

```bash
# Test MCP server protocol
python mcp/test_server.py

# Test git operations
python mcp/test_git_integration.py

# Test categorization and risk scoring
python mcp/test_categorization.py

# Test aggregation
python mcp/test_aggregator.py

# Test file I/O
python mcp/test_file_utils.py

# Run all tests
python -m pytest mcp/
```

## Development

### Project Structure

```
capricorn_challenge/
├── mcp/
│   ├── release_notes_server/
│   │   ├── server.py              # JSON-RPC MCP server
│   │   ├── tools.py               # MCP tool handlers
│   │   ├── errors.py              # Exception hierarchy
│   │   ├── git_tools.py           # Git operations
│   │   ├── commit_classifier.py   # Categorization logic
│   │   ├── risk_calculator.py     # Risk scoring
│   │   ├── aggregator.py          # Data aggregation
│   │   └── file_utils.py          # JSON file I/O
│   ├── test_server.py
│   ├── test_git_integration.py
│   ├── test_categorization.py
│   ├── test_aggregator.py
│   └── test_file_utils.py
├── .claude/
│   ├── commands/
│   │   └── release-notes.md       # Slash command
│   └── skills/
│       └── release-notes.md       # Skill orchestrator
├── examples/
│   ├── ci_report.example.json
│   └── customer_watchlist.example.json
└── README.md
```

### Design Principles

- **No external dependencies**: Python stdlib only
- **Graceful degradation**: Works without config files
- **Production-ready**: Comprehensive error handling and logging
- **Testable**: 40+ automated tests
- **Efficient**: Minimal git operations, smart caching

## Troubleshooting

### "Git repository not found"

Ensure you're running from a git repository:
```bash
git status  # Should show branch info
```

### "Invalid ref"

Check that your refs exist:
```bash
git tag --list        # List tags
git branch -a         # List branches
```

### "MCP server not responding"

Verify MCP server configuration in Claude Code settings and restart Claude Code.

### "No commits between refs"

Ensure refs are in correct order (older ref first):
```bash
# Correct
/release-notes v1.0.0 v1.1.0

# Incorrect (reversed)
/release-notes v1.1.0 v1.0.0
```

## Contributing

This plugin was built as a Claude Code challenge submission. For issues or improvements:

1. Check existing issues
2. Ensure tests pass: `python mcp/test_*.py`
3. Follow existing code style (stdlib only, no external deps)
4. Add tests for new features

## License

[Your chosen license]

## Credits

Built with Claude Code using:
- MCP (Model Context Protocol)
- Claude Agent SDK
- Git log parsing
- Python standard library
