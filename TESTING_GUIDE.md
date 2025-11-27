# Testing Guide for Release Notes Plugin

## Summary of Test Results

**Unit Tests**: ✅ 36/37 tests passing (98% pass rate)
- MCP Server Protocol: 4/5 tests passing
- Git Integration: 7/7 tests passing
- Categorization & Risk: 9/9 tests passing
- Aggregation: 7/7 tests passing
- File I/O: 9/9 tests passing

**MCP Server Manual Test**: ✅ All 3 integration tests passing

## How to Test the Plugin in Claude Code

### Option 1: Test Locally (Development Mode)

#### Step 1: Configure Claude Code

Add this to your Claude Code MCP server configuration (usually in settings):

```json
{
  "mcpServers": {
    "release-notes-server": {
      "command": "python",
      "args": ["-m", "mcp.release_notes_server"],
      "cwd": "/home/user/capricorn_challenge"
    }
  }
}
```

#### Step 2: Restart Claude Code

After adding the configuration, restart Claude Code to load the MCP server.

#### Step 3: Test the Command

In a git repository, try running:

```
/release-notes HEAD~5 HEAD
```

This should:
1. Call the MCP server to fetch git history
2. Categorize all 5 commits
3. Calculate risk score
4. Generate both developer and customer-facing release notes

#### Step 4: Test with Options

Try with custom paths:

```
/release-notes v1.0.0 v1.1.0 --ci-report ./ci_report.json --watchlist ./customer_watchlist.json
```

### Option 2: Test with Example Data

#### Create Sample CI Report:

```bash
cat > ci_report.json <<'EOF'
{
  "test_summary": {
    "total": 150,
    "passed": 145,
    "failed": 5,
    "skipped": 0
  },
  "coverage": {
    "line_percent": 75.5,
    "branch_percent": 68.2
  },
  "build_status": "unstable",
  "failed_tests": [
    {
      "name": "test_authentication",
      "file": "tests/test_auth.py",
      "error": "AssertionError: Expected 200, got 401"
    }
  ]
}
EOF
```

#### Create Sample Watchlist:

```bash
cat > customer_watchlist.json <<'EOF'
{
  "critical_customers": ["important-customer", "enterprise-client"],
  "watched_features": ["authentication", "payment", "api"],
  "high_risk_paths": ["src/auth/", "src/payment/"]
}
EOF
```

#### Run the Command:

```
/release-notes HEAD~10 HEAD --ci-report ./ci_report.json --watchlist ./customer_watchlist.json
```

### Option 3: Test the MCP Server Directly

You can test the MCP server without Claude Code:

```bash
# Run the manual test script
python test_mcp_manual.py

# Or start the server interactively
python -m mcp.release_notes_server
```

Then send JSON-RPC requests via stdin.

## Expected Output

When you run `/release-notes`, you should see:

### 1. Release Quality Report (Developer-Facing)

```markdown
# Release Quality Report: v1.0.0 → v1.1.0

## Overview
- Commits: 23
- Authors: Alice, Bob
- Files Changed: 47
- Lines: +1,234 -567

## Risk Assessment: 🟡 MODERATE
- Score: 4

Risk Factors:
- ⚠️ 1 breaking change commit(s) (+2 points)
- ⚡ 2 customer-impacting commit(s) (+2 points)

Recommendations:
- Review breaking changes with stakeholders
- Notify Customer Success about impacted features
- Extra QA attention on authentication flows

## Change Summary
- Features: 5
- Bug fixes: 12
- Breaking changes: 1
- Performance: 3

## QA Snapshot
- Build: UNSTABLE
- Tests: 145/150 passed (5 failed)
- Coverage: 75.5%

## Customer Impact Analysis
- Affected features: authentication, payment
- High-risk paths: src/auth/
```

### 2. Customer Release Notes

```markdown
# Release Notes: v1.1.0

## Summary
- 23 commits with 5 new features and 12 bug fixes
- One breaking change requires migration
- See details below

## New Features
- New OAuth 2.0 authentication flow
- Batch payment processing
- API rate limiting improvements

## Bug Fixes
- Fixed authentication timeout issues
- Resolved payment processing errors
- Corrected timezone handling

## Breaking Changes
⚠️ OAuth 1.0 endpoints deprecated
Migration steps: [...]

## Known Issues
- Build currently unstable (5 failing tests)
- Test coverage below target (75.5% < 80%)
```

## Troubleshooting

### MCP Server Won't Start

Check the server manually:
```bash
python -m mcp.release_notes_server
# Should wait for input without errors
```

### Command Not Found

Make sure:
1. `plugin.json` exists in repository root
2. `.claude/commands/release-notes.md` exists
3. Claude Code has been restarted

### No Output from Command

Check Claude Code logs for errors. The MCP server logs to stderr, so check:
```bash
# Run the server with logging visible
python -m mcp.release_notes_server 2>&1 | tee server.log
```

### Invalid Refs

Make sure you're in a git repository with the refs you're trying to compare:
```bash
git tag --list    # List available tags
git branch -a     # List available branches
git log --oneline -20  # See recent commits
```

## Performance Testing

For large repositories:

```bash
# Test with many commits (should complete in <5 seconds)
/release-notes HEAD~100 HEAD

# Test with branch comparison (might take longer)
/release-notes main develop
```

The optimizations ensure O(n) performance even with 100+ commits.

## What's Working

✅ Git history fetching (tags, branches, SHAs, relative refs)
✅ Commit categorization (Conventional Commits + heuristics)
✅ Risk scoring (0-10+ scale with clear factors)
✅ CI report integration (graceful degradation if missing)
✅ Customer watchlist (impact detection)
✅ Dual output generation (developer + customer notes)
✅ Performance optimizations (single-pass accumulators, set operations)

## Next Steps

1. **Merge the PR** on GitHub to get optimizations on main
2. **Install the plugin** in Claude Code following Step 1 above
3. **Test in a real repository** with actual releases
4. **Customize** `ci_report.json` and `customer_watchlist.json` for your project
5. **Generate real release notes** for your next release!

## Support

If you encounter issues:
1. Check this guide's Troubleshooting section
2. Run the test suite: `./run_all_tests.sh`
3. Test the MCP server manually: `python test_mcp_manual.py`
4. Check Claude Code logs for errors
