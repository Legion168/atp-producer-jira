import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class JiraConfig:
    base_url: str
    email: str
    api_token: str


def get_jira_config() -> JiraConfig:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    api_token = os.getenv("JIRA_API_TOKEN", "")
    if not base_url or not email or not api_token:
        # Leave values empty; UI will prompt user to fill.
        pass
    return JiraConfig(base_url=base_url, email=email, api_token=api_token)
