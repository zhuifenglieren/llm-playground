"""
Skill Harness - 渐进式执行调度器
负责 skill 的加载、渐进执行、状态管理与断点续跑
"""
import os
import json
from typing import Dict, Any, Optional
from .llm_client import LLMClient
from .skills import get_skill
from .utils import generate_filename


class SkillHarness:
    """Skill 执行 harness，支持渐进式分步执行"""

    def __init__(
        self,
        api_key: str,
        output_dir: str = "./output",
        naming_mode: str = "content"
    ):
        self.llm = LLMClient(api_key=api_key, model="qwen-max")
        self.output_dir = output_dir
        self.naming_mode = naming_mode
        os.makedirs(output_dir, exist_ok=True)
        self._state: Dict[str, Any] = {}

    def load_skill(self, skill_name: str) -> None:
        """加载指定 skill 并初始化状态"""
        self.skill = get_skill(skill_name, self.llm)
        self._state = {
            "skill_name": skill_name,
            "current_step_index": -1,
            "total_steps": len(self.skill.get_steps()),
            "context": {},
            "status": "initialized"
        }

    def get_status(self) -> Dict[str, Any]:
        """获取当前执行状态"""
        return {
            "skill": self._state.get("skill_name"),
            "current_step": self._state["current_step_index"],
            "total_steps": self._state["total_steps"],
            "step_names": self.skill.get_steps() if hasattr(self, 'skill') else [],
            "status": self._state["status"]
        }

    def next_step(self, context: Optional[Dict] = None) -> Dict[str, Any]:
        """执行下一步，支持传入补充上下文"""
        if not hasattr(self, 'skill'):
            raise RuntimeError("请先调用 load_skill 加载 skill")

        if self._state["status"] == "completed":
            return self._state

        next_idx = self._state["current_step_index"] + 1
        if next_idx >= self._state["total_steps"]:
            self._state["status"] = "completed"
            return self._state

        if context:
            self._state["context"].update(context)

        self._state["context"] = self.skill.execute_step(next_idx, self._state["context"])
        self._state["current_step_index"] = next_idx

        if next_idx == self._state["total_steps"] - 1:
            self._state["status"] = "completed"
        else:
            self._state["status"] = "running"

        return self._state.copy()

    def run_all(self, initial_context: Dict) -> Dict[str, Any]:
        """一次性执行所有步骤"""
        if not hasattr(self, 'skill'):
            raise RuntimeError("请先调用 load_skill 加载 skill")

        self._state["context"] = initial_context
        self._state["context"] = self.skill.run_full(initial_context)
        self._state["current_step_index"] = self._state["total_steps"] - 1
        self._state["status"] = "completed"
        return self._state.copy()

    def save_checkpoint(self, filename: str = None) -> str:
        """保存状态检查点，自动生成不重复文件名"""
        if filename is None:
            filename = generate_filename(
                prefix="checkpoint",
                suffix=".json",
                context=self._state.get("context", {}),
                mode=self.naming_mode
            )
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)
        return path

    def load_checkpoint(self, filename: str = "checkpoint.json") -> None:
        """从检查点恢复状态"""
        path = os.path.join(self.output_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            self._state = json.load(f)
        self.load_skill(self._state["skill_name"])
        self._state["current_step_index"] = self._state["current_step_index"]

    def export_output(self, filename: str = None) -> str:
        """导出最终HTML卡片，自动生成不重复文件名"""
        if "html_output" not in self._state["context"]:
            raise RuntimeError("尚未生成输出内容，请先执行完所有步骤")

        if filename is None:
            filename = generate_filename(
                prefix="weather_card",
                suffix=".html",
                context=self._state.get("context", {}),
                mode=self.naming_mode
            )

        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._state["context"]["html_output"])
        return path

    def get_context(self) -> Dict[str, Any]:
        """获取当前上下文数据"""
        return self._state.get("context", {}).copy()