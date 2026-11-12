# 网店客服 Skill 元信息
skill_name: OnlineShopCustomerSkill
skill_id: skill‑008‑shop‑service
version: v2.1‑md‑config‑self‑evolve
description: 分文件职责隔离、渐进式按需加载、MD格式配置文件、LLM自动进化优化token耗时与准确率
enable_progressive_load: true
enable_self_evolve: true
module_ttl: 120
max_dialogue_round: 30
work_hour_range: ["08:00","23:00"]

## 懒加载文件寻址映射
path_map:
  context: ./context/session_context.py
  intent: ./intent/intent_detector.py
  statemachine: ./state_machine/state_controller.py
  rule: ./rule/rule_manager.py
  tool: ./tool/tool_invoker.py
  speech: ./reply_template/speech_engine.py
  hook: ./hook/post_hook.py
  evolve_collector: ./self_evolve/evolve_collector.py
  evolve_agent: ./self_evolve/evolve_llm_agent.py
  evolve_operator: ./self_evolve/evolve_config_operator.py
  evolve_logger: ./self_evolve/evolve_logger.py

## 可进化的配置文件列表
evolvable_config_files:
  - ./intent/intent_config.md
  - ./state_machine/sm_config.md
  - ./rule/rule_config.md
  - ./reply_template/speech_config.md