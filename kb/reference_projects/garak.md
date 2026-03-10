# NVIDIA Garak

LLM vulnerability scanner that probes for failure modes including hallucination, data leakage, prompt injection, misinformation, toxicity, and jailbreaks.

## Architecture: Five Plugin Categories

Garak's core architecture is built on 5 plugin types, each with a base class in `garak/<type>/base.py`:

### 1. Probes (`garak/probes/`)
Generate interactions with LLMs to elicit problematic behavior. Each probe defines:
- Attack prompts to send
- Primary detector (what to look for in responses)
- Extended detectors (additional analysis)

### 2. Detectors (`garak/detectors/`)
Identify when LLMs exhibit failure modes. Analyze probe responses for:
- Pattern matches
- Semantic content
- Behavioral indicators

### 3. Generators (`garak/generators/`)
Interface with different LLM targets. Supported:
- Hugging Face (local and API)
- OpenAI, Cohere, Groq
- AWS Bedrock, Replicate
- Custom REST endpoints
- GGML/llama.cpp
- NVIDIA NIM

### 4. Harnesses (`garak/harnesses/`)
Structure the testing workflow. Default "probewise harness":
- Instantiates probes
- Uses probe's `primary_detector` and `extended_detectors`
- Orchestrates send→receive→detect flow

### 5. Evaluators (`garak/evaluators/`)
Report assessment results. Output:
- Debug log (`garak.log`)
- Detailed JSONL report per run
- Hit log tracking discovered vulnerabilities

## Key Design Patterns

- **Base class inheritance**: Each plugin category has `base.py` with ABC. Concrete implementations extend it.
- **Probe-Detector coupling**: Probes declare which detectors to use via attributes
- **Generator abstraction**: All LLM targets implement same interface regardless of provider
- **Plugin discovery**: Modules are discovered by convention (file naming in plugin directories)

## Key Takeaways for webllm

1. Clean separation of concerns: probes generate, detectors analyze, generators connect
2. Harness pattern for orchestrating the workflow
3. Base class per plugin category enables extensibility
4. Probe-detector relationship (probe knows which detectors to use)
5. Generator = our LlmChannel concept
