# 意图识别配置
> 可由自进化引擎自动修改关键词、权重、识别阈值
> version:v1.0

```json
{
    "intent_list": [
        {"intent_name":"INTENT_GOODS_INFO","alias":["商品咨询","参数","规格"],"weight":1,"semantic_threshold":0.65},
        {"intent_name":"INTENT_STOCK_QUERY","alias":["有没有货","库存"],"weight":1},
        {"intent_name":"INTENT_FREIGHT","alias":["运费","包邮"],"weight":1},
        {"intent_name":"INTENT_COUPON","alias":["优惠","优惠券","满减"],"weight":1},
        {"intent_name":"INTENT_URGE_DELIVER","alias":["催发货","什么时候发货"],"weight":2},
        {"intent_name":"INTENT_MODIFY_ADDRESS","alias":["修改收货地址"],"weight":2},
        {"intent_name":"INTENT_LOGISTICS","alias":["物流","快递到哪了"],"weight":2},
        {"intent_name":"INTENT_REFUND","alias":["退款","仅退款"],"weight":3},
        {"intent_name":"INTENT_RETURN_GOODS","alias":["退货退款"],"weight":3},
        {"intent_name":"INTENT_DAMAGE_COMPENSATE","alias":["破损","损坏","赔偿"],"weight":4},
        {"intent_name":"INTENT_COMPLAIN","alias":["投诉","不满意"],"weight":5},
        {"intent_name":"INTENT_MANUAL_SERVICE","alias":["转人工","人工客服"],"weight":6},
        {"intent_name":"INTENT_NONE","alias":[],"weight":0.5}
    ],
    "optimize_slot":{"embedding_model":null,"custom_keyword_file":null}
}