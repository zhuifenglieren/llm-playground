import os
# 国内镜像前置配置
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
from src.utils import mkdir

# 需要下载的模型清单
MODEL_LIST = [
    {
        "name": "Qwen/Qwen1.5-0.5B-Chat",
        "save_dir": "./models/Qwen1.5-0.5B-Chat",
        "model_type": "llm"
    }
]

def download_all_models():
    print("===== 开始批量下载项目所需预训练模型 =====")
    for cfg in MODEL_LIST:
        model_name = cfg["name"]
        save_path = cfg["save_dir"]
        m_type = cfg["model_type"]

        mkdir(save_path)
        print(f"\n正在处理模型：{model_name}，保存路径：{save_path}")

        # 1. 下载分词器（移除timeout参数）
        print(f"1/2 下载 Tokenizer ...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.save_pretrained(save_path)
        print(f"Tokenizer 保存完成")

        # 2. 下载模型主体（移除timeout、torch_dtype等下载无关参数）
        print(f"2/2 下载 Model ...")
        if m_type == "encoder":
            model = AutoModel.from_pretrained(model_name)
        elif m_type == "llm":
            model = AutoModelForCausalLM.from_pretrained(model_name)
        else:
            raise ValueError("未知模型类型")

        model.save_pretrained(save_path)
        print(f"模型 {model_name} 完整保存至 {save_path}\n")

    print("="*60)
    print("全部模型下载完成！后续训练/测试直接读取本地离线文件")
    print("="*60)

if __name__ == "__main__":
    download_all_models()