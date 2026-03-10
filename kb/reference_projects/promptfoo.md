# Promptfoo

CLI and library for evaluating and stress-testing LLM applications. Enables systematic testing of prompts and models.

## Key Capabilities

- Automated evaluation of prompts against test cases with multiple models
- Red teaming and vulnerability scanning
- Side-by-side model comparison (OpenAI, Anthropic, Azure, Bedrock, Ollama, etc.)
- CI/CD integration for deployment pipeline compliance
- Code scanning for LLM security issues in PRs

## Architecture

### Providers
Abstract interface for different LLM APIs. Allows consistent testing across Claude, GPT, Gemini, Llama without reconfiguration. This is analogous to our LlmChannel concept.

### Test Cases
Declarative configuration-based structure:
- Input prompts
- Expected outputs / evaluation criteria
- Target models
- Assertion rules for pass/fail

### Assertions & Grading
Built-in evaluators that automatically assess LLM outputs against defined metrics. Types include:
- Exact match
- Contains/regex
- Semantic similarity
- Custom functions
- LLM-as-judge

### Configuration
YAML/JSON-driven test definitions. Developer-friendly: live reload, result caching, 100% local execution.

## Key Takeaways for webllm

1. Provider abstraction pattern = our LlmChannel
2. Declarative test/probe configuration could be a future extension
3. Multiple assertion types (deterministic + AI-based) for flexibility
4. Config-driven approach useful for non-developer users
5. CI/CD integration pattern for continuous monitoring
