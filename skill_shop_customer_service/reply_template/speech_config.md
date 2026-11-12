# 回复话术模板配置

```json
{
    "style_list":["standard","sweet","brief","comfort","formal"],
    "template":{
        "welcome":{"standard":"您好，很高兴为您服务，可以告诉我您需要办理什么业务？"},
        "urge_deliver":{"standard":"非常抱歉让您等候，这边马上催促仓库尽快发出您的订单，订单编号 {{order_no}}"},
        "negative_comfort":{"comfort":"十分理解您糟糕的体验，我们会认真处理您的诉求"},
        "to_manual":{"standard":"现已为您转接人工客服，请耐心等候"}
    },
    "optimize_slot":{"goods_speech":null,"ab_test_group":null,"multi_lang":null}
}