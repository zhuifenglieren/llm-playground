import shutil
import time
import json
from pathlib import Path
from utils.config_parser import load_md_config,dump_md_config

BASE = Path(__file__).parent
meta = load_md_config(BASE/"evolve_meta.md")
backup_root = Path(meta["backup_folder"])

class ConfigOperator:
    def __init__(self):
        backup_root.mkdir(exist_ok=True,parents=True)
        self.config_files = [
            "./intent/intent_config.md",
            "./state_machine/sm_config.md",
            "./rule/rule_config.md",
            "./reply_template/speech_config.md"
        ]

    def backup_all(self):
        stamp = str(int(time.time()))
        dest = backup_root / stamp
        dest.mkdir()
        for file_path in self.config_files:
            src = Path(file_path)
            if src.exists():
                shutil.copy2(src, dest / src.name)
        return stamp

    def apply_new_config(self, optimize_list):
        for item in optimize_list:
            target = Path(item["target_file"])
            data = item["new_content"]
            if isinstance(data,str):
                data = json.loads(data)
            remark = "# 自动进化更新配置\n# 优化原因:"+item["optimize_reason"]
            dump_md_config(target,data,head_comment=remark)

    def roll_back(self, stamp:str):
        restore_dir = backup_root / stamp
        for subfile in restore_dir.iterdir():
            shutil.copy2(subfile, Path("./") / subfile.name)

def get_instance():
    return ConfigOperator()