---
name: llm-call
description: Call a configured LLM model directly through the local script using provider settings from config.yaml. Use this skill when the user wants a raw model call, prompt test, provider/model comparison, or asks to send text to a specific GPT/Claude/Gemini model. Do not use it for normal Mavis agent execution.
---

# LLM Call

Replace `<skill_dir>` with the actual skill path shown by the loader.

## Procedure

1. Read the user's target model and prompt.
2. **Always pass `--model provider/model`**. If the user didn't name a specific model, pick a sensible default or run `--list` first to check available models.
3. Pass `--system`, `--max-tokens`, `--temperature`, `--stream`, or `--config` only when the task clearly requires them.
4. The script auto-detects config.yaml from the parent data dir hint when available, falling back to `~/.mavis/config.yaml`. Use `--config` when calling a non-default profile explicitly.
5. Return the model output directly. If the call fails, summarize the provider or config error without inventing a fallback.

## Protocol mapping

- `@ai-sdk/anthropic` -> `messages`
- `@ai-sdk/openai` -> `chat/completions`
- `@ai-sdk/google` -> `models/{model}:generateContent`

## Examples

```bash
python3 <skill_dir>/scripts/llm_call.py --model anthropic/claude-sonnet-4-6 --prompt "Explain this in one sentence"
python3 <skill_dir>/scripts/llm_call.py --model gemini/gemini-2.5-pro --system "Be brief" --prompt "Summarize this"
python3 <skill_dir>/scripts/llm_call.py --list
```

## Failure handling

- If config.yaml is missing or incomplete, say which provider or credential is missing.
- If the requested model is not configured, ask the user to choose from configured models.
- If the HTTP request fails, surface the provider error; do not silently retry with another model.
