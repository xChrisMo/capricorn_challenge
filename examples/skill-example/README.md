# Skill Example

Skills are reusable AI workflows that Claude can invoke automatically or be triggered by commands.

## What is a Skill?

Skills provide:
- Structured workflows for complex tasks
- Guards against common mistakes
- Reusable patterns across projects
- Context-aware automation

## Example Use Cases

- Code review workflows
- Test-driven development process
- Debugging systematic approach
- Architecture decision documentation
- Migration patterns

## Basic Structure

```json
// In plugin.json
{
  "skills": {
    "example-skill": {
      "description": "Example skill for demonstration",
      "prompt": "examples/skill-example/skill.md",
      "triggers": ["when user needs X"]
    }
  }
}
```

## Skill Prompt

The skill prompt should:
- Define when the skill applies
- Provide step-by-step workflow
- Include guards against mistakes
- Specify success criteria

## Learning from Superpowers

The superpowers plugin has excellent skill examples:
- `systematic-debugging` - 4-phase debugging process
- `test-driven-development` - RED-GREEN-REFACTOR cycle
- `code-reviewer` - Code review workflow

Study these for inspiration!

## Your Task

Build skills that:
- Encode best practices
- Prevent common mistakes
- Improve code quality
- Speed up development

## Resources

- [Skills Documentation](https://docs.claudecode.com/skills)
- [Superpowers Skills](https://github.com/colemanm/superpowers)
