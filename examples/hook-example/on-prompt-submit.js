/**
 * Example Hook: onPromptSubmit
 *
 * This hook runs before a user's prompt is sent to Claude.
 * Use it to validate, enhance, or modify prompts.
 */

module.exports = async (context) => {
  const { prompt, metadata } = context;

  // Example: Check for common issues
  if (shouldEnhancePrompt(prompt)) {
    // Add helpful context
    const enhancedPrompt = enhancePrompt(prompt, metadata);

    return {
      ...context,
      prompt: enhancedPrompt,
      metadata: {
        ...metadata,
        enhanced: true,
      },
    };
  }

  // Return context unchanged
  return context;
};

function shouldEnhancePrompt(prompt) {
  // Your logic here
  // Example: Check if prompt is too vague
  return prompt.length < 10;
}

function enhancePrompt(prompt, metadata) {
  // Your enhancement logic here
  // Example: Add context from current file
  return `${prompt}\n\nContext: Working in file ${metadata.currentFile}`;
}

/**
 * Your Implementation Ideas:
 *
 * - Add project-specific context automatically
 * - Validate prompt before sending
 * - Check for sensitive information
 * - Add common requirements automatically
 * - Track prompt patterns for analytics
 */
