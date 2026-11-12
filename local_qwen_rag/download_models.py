import os
from modelscope import snapshot_download

os.environ["MODELSCOPE_SYMLINK_FILES_IN_ROOT_ENABLED"] = "false"

MODEL_DOWNLOAD_LIST = [
    {
        "ms_repo_id": "sentence-transformers/all-MiniLM-L6-v2",
        "local_save_dir": "./models/all-MiniLM-L6-v2"
    },
    # 替换为兼容版Qwen1.5-0.5B-Chat
    {
        "ms_repo_id": "qwen/Qwen1.5-0.5B-Chat",
        "local_save_dir": "./models/Qwen1.5-0.5B-Chat"
    }
]

def download_model_from_modelscope():
    print("===== ModelScope国内模型下载 =====")
    for item in MODEL_DOWNLOAD_LIST:
        repo_id = item["ms_repo_id"]
        save_path = item["local_save_dir"]
        print(f"\n开始下载：{repo_id} → {save_path}")
        snapshot_download(
            model_id=repo_id,
            local_dir=save_path,
            revision="master"
        )
        print(f"✅ {repo_id} 下载完成")
    print("\n🎉 全部模型文件完整下载完毕")

if __name__ == "__main__":
    download_model_from_modelscope()