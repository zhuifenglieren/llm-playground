import time
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from utils.config_parser import load_md_config

BASE = Path(__file__).parent
meta = load_md_config(BASE/"evolve_meta.md")

class EvolveLogger:
    def __init__(self):
        self.compare_dir = Path(meta["compare_log"])
        self.chart_dir = Path(meta["chart_save"])
        self.compare_dir.mkdir(exist_ok=True,parents=True)
        self.chart_dir.mkdir(exist_ok=True,parents=True)

    def calc_statistics(self, sample_arr):
        df = pd.DataFrame(sample_arr)
        avg_token = float(df["sum_token"].mean())
        avg_latency = float(df["latency_ms"].mean())
        negative = len(df[df["sentiment"]=="negative"])
        negative_rate = negative / len(df)
        return {
            "sample_count": len(sample_arr),
            "avg_sum_token": avg_token,
            "avg_response_ms": avg_latency,
            "negative_user_rate": round(negative_rate, 4)
        }

    def save_compare_log(self, backup_id, before, after, optimize_plan):
        out_data = {
            "evolve_timestamp": int(time.time()),
            "backup_stamp": backup_id,
            "metrics_before": before,
            "metrics_after": after,
            "optimize_detail": optimize_plan
        }
        save_path = self.compare_dir / f"evolve_{backup_id}.json"
        with open(save_path,"w",encoding="utf‑8") as fp:
            json.dump(out_data,fp,indent=2,ensure_ascii=False)
        self.draw_chart(before,after,backup_id)
        return out_data

    def draw_chart(self, before, after, stamp):
        labels = ["平均总Token","平均耗时ms","负面情绪率×1000"]
        b_vals = [before["avg_sum_token"], before["avg_response_ms"], before["negative_user_rate"]*1000]
        a_vals = [after["avg_sum_token"], after["avg_response_ms"], after["negative_user_rate"]*1000]
        x = list(range(len(labels)))
        plt.figure(figsize=(8, 5))
        plt.bar([i-0.2 for i in x], b_vals, width=0.4, label="优化前")
        plt.bar([i+0.2 for i in x], a_vals, width=0.4, label="优化后")
        plt.xticks(x, labels)
        plt.legend()
        plt.title(f"Self‑Evolve指标对比 stamp={stamp}")
        plt.savefig(self.chart_dir / f"chart_{stamp}.png")
        plt.close()

def get_instance():
    return EvolveLogger()