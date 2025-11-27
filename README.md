# Release Notes Assistant

A Claude Code plugin that automates release note generation with intelligent risk assessment, QA integration, and customer impact analysis from git history.

## Problem

Manual release notes are tedious, error-prone, and incomplete:

- **Developers** spend hours combing through git logs and categorizing commits inconsistently
- **Engineering leads** struggle to assess release risk without reviewing every change manually
- **Customer Success/Support** lack visibility into which customers or features are affected by changes
- **QA teams** need to know which commits require extra testing attention

Traditional approaches rely on subjective risk assessment, tribal knowledge for customer impact, and creating separate outputs for different audiences doubles the work.

## How It Works (Architecture)

The plugin combines multiple Claude Code components:

**MCP Server** (`release-notes-server`): Provides 3 tools that fetch git history, load CI reports, and read customer watchlists. Includes modules for git operations, commit categorization (Conventional Commits + heuristics), risk scoring, and data aggregation.

**Command** (`/release-notes`): Entry point that validates inputs, calls MCP tools, processes data through categorization and risk scoring, and passes aggregated JSON to the skill.

**Main Skill** (`release-notes`): Receives structured JSON and generates two outputs—a developer quality report with risk assessment and customer-facing release notes with benefit-focused messaging.

**Helper Skill** (`release-notes-guide`): Provides conversational guidance when users ask about release notes, helps identify git refs, and explains command options.

**Data Flow:**

```
git history + CI report + customer watchlist
                ↓
        MCP server (analysis)
    ┌──────────────────────┐
    │ - categorization     │
    │ - risk scoring       │
    │ - impact detection   │
    │ - aggregation        │
    └──────────┬───────────┘
               ↓
    release summary (JSON)
               ↓
    release-notes skill
               ↓
┌──────────────────────────────┐
│ Developer Quality Report     │
│ - Risk assessment            │
│ - QA snapshot                │
│ - Customer impacts           │
│ - Action items               │
└──────────────────────────────┘
┌──────────────────────────────┐
│ Customer Release Notes       │
│ - Features                   │
│ - Bug fixes                  │
│ - Breaking changes           │
│ - Known issues               │
└──────────────────────────────┘
```

## Setup

**Requirements:**
- Python 3.8+
- Git repository
- Claude Code with MCP support

**Installation:**

The plugin includes `plugin.json` which configures the MCP server, command, and skills. Claude Code loads this automatically.

Verify the MCP server starts correctly:
```bash
python -m mcp.release_notes_server.server
```

**Optional configuration files:**

`ci_report.json` - Test results and coverage data (plugin degrades gracefully if missing)

`customer_watchlist.json` - Critical customers, watched features, high-risk paths (uses defaults if missing)

Copy and edit example files:
```bash
cp examples/ci_report.example.json ci_report.json
cp examples/customer_watchlist.example.json customer_watchlist.json
```

## Usage

Basic usage between two git refs:

```bash
/release-notes v1.0.0 v1.1.0
```

Compare branches:
```bash
/release-notes main release-candidate
```

With custom paths and enablement brief:
```bash
/release-notes v2.0.0 v2.1.0 \
  --ci-report ./ci_report.json \
  --watchlist ./customer_watchlist.json \
  --enablement
```

Recent commits:
```bash
/release-notes HEAD~10 HEAD
```

The command analyzes commits between refs, categorizes each commit (feature, bugfix, breaking change, etc.), calculates a risk score based on change type and size, integrates QA data from CI reports, checks customer watchlist for impact detection, and generates both a developer quality report and customer-facing release notes.

**Options:**
- `--ci-report PATH`: Custom path to CI report JSON (default: `./ci_report.json`)
- `--watchlist PATH`: Custom path to customer watchlist JSON (default: `./customer_watchlist.json`)
- `--enablement`: Generate internal brief for Customer Success/Support teams

## Example Output (High Level)

**Release Quality Report** includes:
- Risk assessment with score (0-10+ scale) and level (LOW/MODERATE/HIGH)
- Risk factors: breaking changes, customer impacts, large commits, low coverage
- Change summary by category with counts
- QA snapshot: build status, test results, coverage trends, failed tests
- Customer impact analysis: affected features, high-risk paths, customer mentions
- Actionable recommendations based on risk level

**Customer Release Notes** includes:
- Summary of key changes
- New features (benefit-focused, not technical)
- Bug fixes (impact-focused)
- Performance improvements
- Breaking changes with migration guidance
- Known issues and quality status

Both outputs are generated from actual git data with strict guardrails against hallucination.

## Limitations & Future Improvements

- **CI integration**: Currently requires manual JSON export; could integrate directly with GitHub Actions, CircleCI, Jenkins
- **Issue tracking**: No automatic linking to Jira/GitHub issues; could include issue context and resolved tickets
- **Enablement subagent**: The `--enablement` flag is documented but would benefit from a specialized subagent for customer success materials
- **Template customization**: Fixed output format; could support custom templates and multiple output formats (GitHub, Confluence, email)
- **Historical analysis**: No trend analysis across releases; could compare risk to historical averages and flag unusual patterns

## AI Assistance

Claude (LLM) was used throughout development for:
- Architecture design and validation of component boundaries
- Boilerplate code generation for MCP server, tools, and test suites
- Comprehensive test case creation and documentation

Human guidance provided:
- Strategic architecture decisions and constraints
- Risk scoring algorithm design and factor weighting
- Output tone and structure requirements
- Debugging complex issues (e.g., two-pass git log parsing)
- Quality standards and when to iterate vs. ship

The plugin demonstrates effective human-AI collaboration: AI provided development speed and thoroughness, while human judgment ensured it solved the right problem correctly.

## Credits

Built with Claude Code for the Capricorn Challenge.

Author: ChrisMo
