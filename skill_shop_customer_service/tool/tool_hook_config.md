# 工具钩子配置

```json
{
    "tools":[
        {"tool_name":"query_order_api","enable":true},
        {"tool_name":"query_logistics_api","enable":true},
        {"tool_name":"apply_refund_api","enable":true}
    ],
    "system_hooks":["log_hook","risk_detect_hook"],
    "optimize_slot":{"custom_tool_dir":"./tool/custom_tools/"}
}