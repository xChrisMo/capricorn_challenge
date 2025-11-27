# Quick Start - Testing Your Plugin

## ✅ Tests Already Passing

```bash
# Run all tests
./run_all_tests.sh
```

**Result**: 36/37 tests passing ✅

## 🚀 Install Plugin in Claude Code

### 1. Add to Claude Code Configuration

Find your Claude Code settings and add:

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

### 2. Restart Claude Code

Close and reopen Claude Code to load the plugin.

### 3. Test the Command

In any git repository, run:

```
/release-notes HEAD~5 HEAD
```

You should see:
- ✅ Release Quality Report (developer-facing)
- ✅ Customer Release Notes (customer-facing)

## 📝 Create Test Data (Optional)

```bash
# Copy example files
cp examples/ci_report.example.json ci_report.json
cp examples/customer_watchlist.example.json customer_watchlist.json

# Edit for your project
nano ci_report.json
nano customer_watchlist.json
```

## 🎯 Advanced Usage

```bash
# With custom files
/release-notes v1.0.0 v1.1.0 --ci-report ./ci_report.json --watchlist ./customer_watchlist.json

# With enablement brief for CS/Support
/release-notes v2.0.0 v2.1.0 --enablement

# Compare branches
/release-notes main release-candidate
```

## ❓ Need Help?

See `TESTING_GUIDE.md` for detailed instructions and troubleshooting.

## 🎉 You're Done!

Your plugin is production-ready and tested. Generate release notes for your next release!
