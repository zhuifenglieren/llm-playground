from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class OrderInfo:
    order_no: Optional[str] = None
    goods_name: Optional[str] = None
    pay_amount: Optional[float] = None
    logistics_no: Optional[str] = None
    order_status: Optional[str] = None

@dataclass
class DialogueContext:
    session_id: str
    user_openid: str
    dialogue_round: int = 0
    user_intent: Optional[str] = None
    order_info: OrderInfo = field(default_factory=OrderInfo)
    user_sentiment: str = "neutral"
    history_reply: List[Dict[str, Any]] = field(default_factory=list)
    pending_task: List[str] = field(default_factory=list)
    custom_params: Dict[str, Any] = field(default_factory=dict)

    def reset(self):
        self.dialogue_round = 0
        self.user_intent = None
        self.pending_task.clear()

def get_instance():
    return None