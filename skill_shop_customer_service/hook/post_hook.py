from pathlib import Path
from utils.config_parser import load_md_config
BASE = Path(__file__).parent

class PostHookManager:
    def __init__(self):
        self.cfg = load_md_config(BASE / "hook_config.md")

    def run_hooks(self, ctx, reply_text: str):
        if self.cfg.get("enable_log_hook"):
            ctx.history_reply.append({
                "reply": reply_text,
                "intent": ctx.user_intent,
                "sentiment": ctx.user_sentiment
            })

def get_instance():
    return PostHookManager()