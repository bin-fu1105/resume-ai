from pathlib import Path

from services.errors import ClaudeServiceError


def load_prompt(prompts_dir: Path, prompt_name: str) -> str:
    """Load a prompt file and inject shared recruiter rules when requested."""
    prompt_path = prompts_dir / prompt_name
    if not prompt_path.is_file():
        raise ClaudeServiceError(f"Prompt file not found: {prompt_path}")

    template = prompt_path.read_text(encoding="utf-8")
    if "<<<SHARED_RULES>>>" not in template:
        return template

    shared_path = prompts_dir / "shared_rules.txt"
    if not shared_path.is_file():
        raise ClaudeServiceError(f"Prompt file not found: {shared_path}")

    shared_rules = shared_path.read_text(encoding="utf-8").strip()
    return template.replace("<<<SHARED_RULES>>>", shared_rules)
