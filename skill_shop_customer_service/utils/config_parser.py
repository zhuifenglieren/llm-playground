import re
import json
from pathlib import Path

def load_md_config(file_path: Path):
    """读取md文件，抓取第一个json代码块并返回字典"""
    text = file_path.read_text(encoding="utf-8")
    pattern = r'```(?:json)\s*\n(.*?)\n```'
    res = re.search(pattern, text, re.DOTALL)
    if not res:
        raise RuntimeError(f"{file_path} 找不到JSON代码块")
    json_str = res.group(1)
    return json.loads(json_str)


def dump_md_config(file_path: Path, config_data: dict, head_comment: str = ""):
    """写入配置到markdown json代码块，自进化引擎更新配置时调用"""
    json_text = json.dumps(config_data, ensure_ascii=False, indent=4)
    md_content = f"{head_comment}\n```json\n{json_text}\n```\n"
    file_path.write_text(md_content, encoding="utf-8")