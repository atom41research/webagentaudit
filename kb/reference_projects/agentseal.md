# AgentSeal

AI agent security validation toolkit for evaluating whether AI agents can be compromised.

## Purpose

Two main functions:
- **Machine Security Scanning** (`agentseal guard`): Auto-discovers and audits 17 AI agents on a system for malware, credential theft, prompt injection vulnerabilities, configuration issues. No API keys required.
- **Agent Vulnerability Testing** (`agentseal scan`): Sends 191+ attack probes to assess resistance to security exploits, generating a trust score (0-100).

## Architecture

Dual-language implementation (Python via PyPI, JavaScript/TypeScript via npm).

### Probe Categories

**Extraction Attacks (82 probes):** Trick agents into revealing system prompts
- Direct prompts asking to disclose instructions
- Encoding tricks (Base64, ROT13, hex)
- Persona hijacking
- Indirect methods (echo, hypotheticals)

**Injection Attacks (109 probes):** Override agent behavior
- Conflicting directives in user input
- Boundary testing between system/user prompts
- Safety guideline circumvention
- Unintended action execution

**Advanced (Pro tier):**
- MCP Tool Poisoning (+45 probes)
- RAG Poisoning (+28 probes)
- Multimodal Attacks (+13 probes)
- Behavioral Genome Mapping (~105 probes)

## Key Design Patterns

### Probe-Response Loop
1. Send structured attack probes to target
2. Collect responses
3. Evaluate via **deterministic pattern matching** (NOT AI judge)
4. Generate reproducible, consistent results

### Data Structures

**ScanReport:**
- `trust_score`: 0-100
- `trust_level`: categorical
- `score_breakdown`: { extraction, injection }
- `results`: ProbeResult[]

**ProbeResult categories:** Blocked, Partial, Leaked

**Severity levels:** CRITICAL, HIGH, MEDIUM, LOW

### Integration Points
- Direct Model APIs (OpenAI, Anthropic)
- Local Models (Ollama)
- HTTP Endpoints
- LiteLLM Proxy
- MCP Servers
- Skills/Rules Files

## Key Takeaways for webllm

1. Deterministic pattern matching (no AI judge) ensures reproducibility
2. Probe categories are well-defined and extensible
3. Trust score aggregation from individual probe results
4. Severity classification at probe level
5. Multiple channel types for reaching the LLM
