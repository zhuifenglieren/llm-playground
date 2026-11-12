# 状态机流转配置
> 自动进化可调整状态跳转条件

```json
{
    "state_enum":["STATE_INIT","STATE_PRE_SALE","STATE_AFTER_SALE","STATE_WAIT_USER_MATERIAL","STATE_RUN_TASK","STATE_FINISH","STATE_MANUAL_TRANSFER"],
    "transition_rules":[
        {"from":"STATE_INIT","condition":"has_order","to":"STATE_AFTER_SALE"},
        {"from":"STATE_INIT","condition":"no_order","to":"STATE_PRE_SALE"},
        {"from":"*","condition":"negative_emotion","to":"STATE_MANUAL_TRANSFER"},
        {"from":"*","condition":"intent=INTENT_MANUAL_SERVICE","to":"STATE_MANUAL_TRANSFER"}
    ],
    "optimize_slot":{"custom_rule_file":null,"state_timeout":null}
}