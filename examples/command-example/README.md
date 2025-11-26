# Command Example

Commands are slash commands that users can invoke in Claude Code (e.g., `/review-code`).

## What is a Command?

Commands provide:
- Quick access to common tasks
- Structured prompts for specific workflows
- Shortcuts for repetitive operations

## Example Use Cases

- `/review-pr` - Review pull request changes
- `/generate-tests` - Generate tests for selected code
- `/explain-error` - Explain an error message
- `/refactor` - Suggest refactorings
- `/doc-update` - Update documentation

## Basic Structure

```json
// In plugin.json
{
  "commands": {
    "example-command": {
      "description": "Example command that does something useful",
      "prompt": "examples/command-example/prompt.md"
    }
  }
}
```

## Command Prompt

The `prompt.md` file contains the instructions Claude receives when the command is invoked.

## Variables

Commands can access:
- `{{selection}}` - Currently selected text
- `{{fileName}}` - Current file name
- `{{filePath}}` - Current file path
- Custom variables defined in your command

## Your Task

Build commands that solve real problems:
- What tasks do you do repeatedly?
- What could be automated with AI?
- What would save time?

## Resources

- [Command Documentation](https://docs.claudecode.com/commands)
- [Command Examples](https://github.com/anthropics/claude-code/tree/main/examples/commands)
