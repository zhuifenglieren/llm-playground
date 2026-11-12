from loguru import logger
import os

def setup_logger():
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    # 运行日志
    logger.add(
        "logs/rag_runtime.log",
        rotation="500MB",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    # 评估独立日志
    logger.add(
        "logs/eval_result.log",
        rotation="200MB",
        encoding="utf-8",
        filter=lambda record: "EVAL" in record["extra"],
        format="{time:YYYY-MM-DD HH:mm:ss} | EVAL | {message}"
    )
    return logger

# 关键：实例化并导出 log 变量
log = setup_logger()