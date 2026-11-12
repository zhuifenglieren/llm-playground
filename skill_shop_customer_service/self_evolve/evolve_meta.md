# LLM‑SelfEvolve 全局参数

```json
{
    "enable_self_evolve": true,
    "sample_trigger_count":15,
    "eval_sample_size":10,
    "max_evolution_daily":20,
    "token_warning":1200,
    "latency_warn_ms":800,
    "min_intent_accuracy":0.75,
    "auto_rollback":true,
    "backup_folder":"./self_evolve/config_backup/",
    "raw_session_log":"./logs/raw_session/",
    "compare_log":"./logs/evolve_compare/",
    "chart_save":"./logs/chart/"
}