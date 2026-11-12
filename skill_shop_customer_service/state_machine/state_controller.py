from pathlib import Path
from utils.config_parser import load_md_config
BASE = Path(__file__).parent

class ShopStateMachine:
    def __init__(self):
        self.cfg = load_md_config(BASE / "sm_config.md")
        self.current_state = "STATE_INIT"

    def check_condition(self, cond: str, ctx):
        if cond == "has_order":
            return ctx.order_info.order_no is not None
        if cond == "no_order":
            return ctx.order_info.order_no is None
        if cond == "negative_emotion":
            return ctx.user_sentiment == "negative"
        if cond.startswith("intent="):
            target_intent = cond.split("=")[1]
            return ctx.user_intent == target_intent
        return False

    def run_transition(self, ctx):
        for rule in self.cfg["transition_rules"]:
            src, cond, dst = rule["from"], rule["condition"], rule["to"]
            if src == "*" or src == self.current_state:
                if self.check_condition(cond, ctx):
                    self.current_state = dst
                    break
        return self.current_state

def get_instance():
    return ShopStateMachine()