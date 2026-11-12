from pathlib import Path
from utils.config_parser import load_md_config
BASE = Path(__file__).parent

class ToolInvoker:
    def __init__(self):
        self.cfg = load_md_config(BASE / "tool_hook_config.md")
        self.enable_map = {t["tool_name"]:t["enable"] for t in self.cfg["tools"]}

    def invoke(self, ctx):
        intent = ctx.user_intent
        if intent == "INTENT_LOGISTICS" and self.enable_map["query_logistics_api"]:
            ctx.pending_task.append("query_logistics_api")
        if intent == "INTENT_REFUND" and self.enable_map["apply_refund_api"]:
            ctx.pending_task.append("apply_refund_api")

def get_instance():
    return ToolInvoker()