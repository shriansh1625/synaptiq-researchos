"""Prompt template loader for agent prompts."""

from __future__ import annotations

from dataclasses import dataclass

from app.prompts.brief_template import (
    BRIEF_FEW_SHOT,
    BRIEF_INSTRUCTIONS,
    BRIEF_PROMPT_VERSION,
    BRIEF_SYSTEM,
)
from app.prompts.comparative_template import (
    COMPARATIVE_FEW_SHOT,
    COMPARATIVE_INSTRUCTIONS,
    COMPARATIVE_PROMPT_VERSION,
    COMPARATIVE_SYSTEM,
)
from app.prompts.discovery_template import (
    DISCOVERY_FEW_SHOT,
    DISCOVERY_INSTRUCTIONS,
    DISCOVERY_PROMPT_VERSION,
    DISCOVERY_SYSTEM,
)
from app.prompts.gap_template import (
    GAP_FEW_SHOT,
    GAP_INSTRUCTIONS,
    GAP_PROMPT_VERSION,
    GAP_SYSTEM,
)
from app.prompts.verification_template import (
    VERIFICATION_FEW_SHOT,
    VERIFICATION_INSTRUCTIONS,
    VERIFICATION_PROMPT_VERSION,
    VERIFICATION_SYSTEM,
)


@dataclass(frozen=True)
class PromptTemplate:
    """Versioned prompt template."""

    name: str
    version: str
    system: str
    instructions: str
    few_shot: str

    def render(self, **variables: object) -> str:
        """Render prompt with runtime variables."""
        sections = [
            self.system,
            self.instructions,
            self.few_shot,
        ]
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            rendered = str(value)
            sections = [section.replace(placeholder, rendered) for section in sections]
        return "\n\n".join(sections)


def load_prompt(name: str, version: str | None = None) -> PromptTemplate:
    """Load a named prompt template."""
    templates = {
        "discovery": (
            DISCOVERY_PROMPT_VERSION,
            DISCOVERY_SYSTEM,
            DISCOVERY_INSTRUCTIONS,
            DISCOVERY_FEW_SHOT,
        ),
        "verification": (
            VERIFICATION_PROMPT_VERSION,
            VERIFICATION_SYSTEM,
            VERIFICATION_INSTRUCTIONS,
            VERIFICATION_FEW_SHOT,
        ),
        "comparative": (
            COMPARATIVE_PROMPT_VERSION,
            COMPARATIVE_SYSTEM,
            COMPARATIVE_INSTRUCTIONS,
            COMPARATIVE_FEW_SHOT,
        ),
        "gap": (
            GAP_PROMPT_VERSION,
            GAP_SYSTEM,
            GAP_INSTRUCTIONS,
            GAP_FEW_SHOT,
        ),
        "brief": (
            BRIEF_PROMPT_VERSION,
            BRIEF_SYSTEM,
            BRIEF_INSTRUCTIONS,
            BRIEF_FEW_SHOT,
        ),
        "executive_brief": (
            BRIEF_PROMPT_VERSION,
            BRIEF_SYSTEM,
            BRIEF_INSTRUCTIONS,
            BRIEF_FEW_SHOT,
        ),
    }
    if name in templates:
        prompt_version, system, instructions, few_shot = templates[name]
        return PromptTemplate(
            name=name,
            version=version or prompt_version,
            system=system,
            instructions=instructions,
            few_shot=few_shot,
        )
    msg = f"Unknown prompt template: {name}"
    raise ValueError(msg)
