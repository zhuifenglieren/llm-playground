# GRPO数学能力强化训练系统 - 使用指南


1. 安装依赖

pip install -r requirements.txt

2. 基础训练

python main.py --train_samples 1000 --eval_samples 10 --epochs 3

3. 跳过训练（仅评估）

python main.py --skip_train

4. 使用自定义模型

python main.py --model_name "path/to/your/model"

5. 参数说明

参数	说明	默认值
--model_name	模型名称或路径	Qwen/Qwen1.5-0.5B-Chat
--train_samples	训练样本数	1000
--eval_samples	评估样本数	10
--epochs	训练轮数	3
--skip_train	跳过训练	False

6. 输出文件

checkpoints/ - 训练检查点

final_model/ - 最终模型

evaluation_results.json - 评估结果