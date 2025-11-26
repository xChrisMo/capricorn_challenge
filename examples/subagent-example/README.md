# Subagent Example

Subagents are specialized AI agents that handle specific tasks autonomously.

## What is a Subagent?

Subagents provide:
- Autonomous task execution
- Specialized capabilities
- Parallel processing
- Focused expertise

## Example Use Cases

- Code review agent
- Test generation agent
- Documentation writer
- Bug investigator
- Performance analyzer
- Migration executor

## Basic Structure

```json
// In plugin.json
{
  "subagents": {
    "example-agent": {
      "description": "Example subagent for demonstration",
      "prompt": "examples/subagent-example/agent.md",
      "tools": ["Read", "Write", "Grep", "Bash"]
    }
  }
}
```

## Subagent Prompt

The subagent prompt should:
- Define the agent's role and expertise
- Specify what tools it can use
- Provide clear success/failure criteria
- Include error handling strategies

## Learning from Superpowers

The superpowers plugin has excellent subagent examples:
- `code-reviewer` - Reviews code against requirements
- `css-variables-migrator` - Executes batch migrations
- Other specialized agents

## Your Task

Build subagents that:
- Handle specific, well-defined tasks
- Work autonomously
- Have clear success criteria
- Provide useful feedback

## Key Considerations

**Autonomy**: Subagent should complete tasks without constant user input

**Reporting**: Should report progress and results clearly

**Error Handling**: Should handle failures gracefully

**Tools**: Should have appropriate tools for the task

## Resources

- [Subagents Documentation](https://docs.claudecode.com/subagents)
- [Task Tool Documentation](https://docs.claudecode.com/tools/task)
