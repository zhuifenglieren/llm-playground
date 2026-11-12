from pathlib import Path
from utils.config_parser import load_md_config
BASE = Path(__file__).parent

class RuleManager:
    def __init__(self):
        self.cfg = load_md_config(BASE / "rule_config.md")

    def conversation_limit_check(self, ctx):
        if ctx.dialogue_round >= self.cfg["manual_transfer_round"]:
            ctx.user_intent = "INTENT_MANUAL_SERVICE"

def get_instance():
    return RuleManager()