# Example Command Prompt

This file is executed when the user runs `/example-command`.

## Instructions

You are helping the user with [describe what this command does].

The user has provided:
- File: {{fileName}}
- Selection: {{selection}}

## Your Task

1. Analyze the provided code/text
2. [Specific instructions for what Claude should do]
3. Provide clear, actionable output

## Output Format

Present your response in a clear format:
- Summary of findings
- Specific recommendations
- Code examples if applicable

## Example

If the user selects this function:
```typescript
function calculate(x, y) {
  return x + y;
}
```

You might respond with:
- **Analysis**: Simple addition function
- **Suggestions**: Add type annotations, JSDoc comment
- **Improved Code**:
```typescript
/**
 * Adds two numbers together
 * @param x First number
 * @param y Second number
 * @returns Sum of x and y
 */
function calculate(x: number, y: number): number {
  return x + y;
}
```

---

**Remember**: This is just an example. Your actual command should solve a real problem!
