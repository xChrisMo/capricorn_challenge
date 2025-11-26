# Hook Example

Hooks allow you to automate workflows at specific points in the Claude Code lifecycle.

## What are Hooks?

Hooks provide:
- Automated workflow triggers
- Lifecycle event handling
- Process validation
- Automated checks

## Available Hooks

- `onSessionStart` - When Claude Code session starts
- `onFileChange` - When a file is modified
- `onToolCall` - Before/after tool execution
- `onPromptSubmit` - Before user prompt is sent
- `onResponse` - After Claude responds

## Example Use Cases

- **Pre-commit checks** - Validate code before committing
- **Auto-formatting** - Format code on save
- **Test running** - Run tests after changes
- **Linting** - Check code quality
- **Documentation updates** - Update docs when code changes
- **Notification** - Alert on specific events

## Basic Structure

```json
// In plugin.json
{
  "hooks": {
    "onPromptSubmit": {
      "script": "examples/hook-example/on-prompt-submit.js"
    }
  }
}
```

## Hook Script

```javascript
module.exports = async (context) => {
  // context contains:
  // - prompt: The user's prompt
  // - files: Changed files
  // - tools: Available tools
  // - metadata: Additional info

  // Perform your automation
  // Return modified context or block execution
};
```

## Your Task

Build hooks that:
- Automate repetitive tasks
- Enforce quality standards
- Prevent common mistakes
- Improve workflow efficiency

## Best Practices

**Performance**: Hooks should be fast
- Don't block on long operations
- Use async operations wisely
- Cache results when possible

**User Experience**: Hooks should be helpful, not annoying
- Provide clear feedback
- Allow bypassing if needed
- Don't interrupt unnecessarily

**Reliability**: Hooks should be robust
- Handle errors gracefully
- Don't break the workflow
- Fail safely

## Resources

- [Hooks Documentation](https://docs.claudecode.com/hooks)
- [Hook Examples](https://github.com/anthropics/claude-code/tree/main/examples/hooks)
