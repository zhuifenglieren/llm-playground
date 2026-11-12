from pathlib import Path
from utils.config_parser import load_md_config
BASE = Path(__file__).parent

class SpeechEngine:
    def __init__(self):
        self.cfg = load_md_config(BASE / "speech_config.md")
        self.tpl = self.cfg["template"]
        self.default_style = "standard"

    def generate_reply(self, ctx):
        style = "comfort" if ctx.user_sentiment == "negative" else self.default_style
        intent = ctx.user_intent
        if ctx.dialogue_round <= 1:
            return self.tpl["welcome"][style]
        if intent == "INTENT_URGE_DELIVER":
            orderid = ctx.order_info.order_no if ctx.order_info.order_no else "未知订单"
            return self.tpl["urge_deliver"][self.default_style].replace("{{order_no}}",orderid)
        if intent == "INTENT_MANUAL_SERVICE":
            return self.tpl["to_manual"][self.default_style]
        if ctx.user_sentiment == "negative":
            return self.tpl["negative_comfort"][style]
        return "请问还需要什么帮助？"

def get_instance():
    return SpeechEngine()