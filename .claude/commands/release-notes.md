---
description: Generate release notes between two git refs with risk assessment
---

Generate comprehensive release notes for the commits between `{{arg1}}` and `{{arg2}}`.

Use the `release-notes` skill to:
1. Fetch git history between the refs
2. Load QA/CI data and customer watchlist
3. Categorize commits and calculate risk
4. Generate both a developer-focused quality report and customer-ready release notes

The refs can be tags, branches, or SHAs (e.g., `v1.0.0`, `main`, `HEAD~5`).
