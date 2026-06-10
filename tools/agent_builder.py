import os
from typing import List
from tools.project_paths import project_path_str


def create_agent_scaffold(name: str, capabilities: List[str], target_dir: str = "agents") -> str:
    """Create a simple agent scaffold under agents/<name>/ and return the path.

    This creates:
    - main.py (entrypoint with run())
    - README.md describing required permissions
    - requirements.txt
    - .env and config.example.env
    """
    safe_name = name.replace(" ", "_").lower()
    agent_path = project_path_str(target_dir, safe_name)
    os.makedirs(agent_path, exist_ok=True)

    caps_str = ', '.join(capabilities)
    main_py = f'''# Auto-generated agent: {name}
import os

from tools.instruction_loader import compose_system_prompt

SYSTEM_PROMPT = compose_system_prompt(
    "You are an auto-generated TOM agent. Follow the shared repo instruction stack and return concise, verified outputs.",
    "{safe_name}",
    include_ui=True,
)

def run():
    print("Agent {{name}} started")
    # Capabilities: {caps_str}
    # Shared instruction stack is loaded through tools.instruction_loader.
    # TODO: implement the agent's logic here

if __name__ == "__main__":
    run()
'''

    readme = f"""# {name}

This agent was scaffolded by TOM. Capabilities requested: {', '.join(capabilities)}.

The scaffold is pre-wired to use the shared instruction stack from:
- `CLAUDE.md`
- `AGENTS.md`
- `skills/SKILL.md` when the agent generates any visible artifact

Before running:
- Review `config.example.env` and populate real credentials.
- Confirm permissions and credentials with the user before connecting to external services (Instagram, email providers, etc.).
"""

    reqs = """# Minimal requirements for the scaffolded agent
requests
"""

    config_example = """# Example environment variables
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.2:latest
# OLLAMA_TIMEOUT_SECONDS=45
# TASK_TIMEOUT_SECONDS=75
# EMAIL_ADDRESS=you@example.com
# GMAIL_CREDENTIALS_FILE=C:\\path\\to\\client_secret.json
# GMAIL_TOKEN_FILE=C:\\path\\to\\gmail_token.json
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# IMAP_HOST=imap.gmail.com
# IMAP_PORT=993
# VOICE_INPUT_ENABLED=true
# VOICE_OUTPUT_ENABLED=true
# VOICE_SPEAK_TIMEOUT_SECONDS=8
# FEEDBACK_MAX_LOOPS=5
# VOICE_RATE=175
# VOICE_VOLUME=1.0
"""

    with open(os.path.join(agent_path, 'main.py'), 'w', encoding='utf-8') as f:
        f.write(main_py)

    with open(os.path.join(agent_path, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme)

    with open(os.path.join(agent_path, 'requirements.txt'), 'w', encoding='utf-8') as f:
        f.write(reqs)

    with open(os.path.join(agent_path, 'config.example.env'), 'w', encoding='utf-8') as f:
        f.write(config_example)

    with open(os.path.join(agent_path, '.env'), 'w', encoding='utf-8') as f:
        f.write(config_example)

    return agent_path
