from pathlib import Path
from utils.config_parser import load_md_config

BASE = Path(__file__).parent

class IntentDetector:
    def __init__(self):
        self.config = load_md_config(BASE / "intent_config.md")
        self.intent_data = self.config["intent_list"]

    def detect(self, user_query: str, ctx):
        text = user_query.lower().strip()
        matched_intent = "INTENT_NONE"
        max_weight = 0
        for item in self.intent_data:
            for keyword in item["alias"]:
                if keyword in text and item["weight"] > max_weight:
                    max_weight = item["weight"]
                    matched_intent = item["intent_name"]
        ctx.user_intent = matched_intent
        bad_words = ["生气","很差","垃圾","恼火","投诉"]
        for w in bad_words:
            if w in text:
                ctx.user_sentiment = "negative"
                break
        return matched_intent

def get_instance():
    return IntentDetector()