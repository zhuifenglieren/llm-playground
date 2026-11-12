import json
import time
import uuid
from pathlib import Path
from utils.config_parser import load_md_config

BASE = Path(__file__).parent
evolve_cfg = load_md_config(BASE / "evolve_meta.md")

class MetricCollector:
    def __init__(self):
        self.buffer = []
        self.trigger_num = evolve_cfg["sample_trigger_count"]

    def collect(self, ctx, token_in:int, token_out:int, cost_ms:int):
        record = {
            "rid": str(uuid.uuid4()),
            "sid": ctx.session_id,
            "round": ctx.dialogue_round,
            "intent": ctx.user_intent,
            "sentiment": ctx.user_sentiment,
            "task_list": ctx.pending_task,
            "input_token": token_in,
            "output_token": token_out,
            "sum_token": token_in + token_out,
            "latency_ms": cost_ms,
            "timestamp": time.time()
        }
        self.buffer.append(record)
        raw_path = Path(evolve_cfg["raw_session_log"])
        raw_path.mkdir(exist_ok=True, parents=True)
        with open(raw_path / (record["rid"]+".json"),"w",encoding="utf‑8") as f:
            json.dump(record,f,indent=2,ensure_ascii=False)

    def is_ready_evolve(self):
        return len(self.buffer) >= self.trigger_num

    def pop_samples(self):
        samples = self.buffer.copy()
        self.buffer.clear()
        return samples

def get_instance():
    return MetricCollector()