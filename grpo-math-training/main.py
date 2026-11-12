import torch
import argparse
from models.model_loader import ModelLoader
from data.math_dataset import MathDataset
from training.reward import MathReward
from training.grpo_trainer import GRPOTrainer
from evaluation.evaluator import Evaluator
from utils.config import TrainingConfig
import json
import os
import gc


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="GRPO数学能力训练")
    parser.add_argument("--model_name", type=str,
                        default="Qwen/Qwen1.5-0.5B-Chat",
                        help="模型名称")
    parser.add_argument("--train_samples", type=int, default=100,
                        help="训练样本数")
    parser.add_argument("--eval_samples", type=int, default=10,
                        help="评估样本数")
    parser.add_argument("--epochs", type=int, default=1,
                        help="训练轮数")
    parser.add_argument("--skip_train", action="store_true",
                        help="跳过训练，仅评估")
    parser.add_argument("--use_4bit", action="store_true",
                        help="使用4bit量化")
    parser.add_argument("--batch_size", type=int, default=1,
                        help="批次大小")
    parser.add_argument("--group_size", type=int, default=2,
                        help="每组采样数量")
    return parser.parse_args()


def clear_gpu_memory():
    """清理GPU内存"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()


def main():
    """主函数"""
    args = parse_args()

    # 加载配置
    config = TrainingConfig(
        model_name=args.model_name,
        train_samples=args.train_samples,
        eval_samples=args.eval_samples,
        num_epochs=args.epochs,
        use_4bit=args.use_4bit,
        batch_size=args.batch_size,
        group_size=args.group_size
    )

    print("=" * 60)
    print("GRPO数学能力强化训练系统")
    print("=" * 60)
    print(f"配置信息:")
    print(f"  模型: {config.model_name}")
    print(f"  训练样本: {config.train_samples}")
    print(f"  评估样本: {config.eval_samples}")
    print(f"  训练轮数: {config.num_epochs}")
    print(f"  批次大小: {config.batch_size}")
    print(f"  组大小: {config.group_size}")
    print(f"  使用4bit: {config.use_4bit}")
    print("=" * 60)

    # 1. 加载模型
    print("\n[1/5] 加载模型...")
    model_loader = ModelLoader(config.model_name, config.device)
    model, tokenizer = model_loader.load_model(config.use_4bit)

    # 打印模型信息
    model_info = model_loader.get_model_info()
    if model_info:
        print(f"模型信息:")
        for key, value in model_info.items():
            print(f"  {key}: {value}")

    # 2. 创建数据集
    print("\n[2/5] 创建数据集...")
    math_dataset = MathDataset()

    # 创建评估集
    eval_data = math_dataset.create_evaluation_set(config.eval_samples)
    print(f"创建评估集: {len(eval_data)} 道题目")
    print("\n评估题目:")
    for i, item in enumerate(eval_data, 1):
        print(f"  {i}. {item['question']} = {item['answer']}")

    # 3. 创建奖励函数和评估器
    print("\n[3/5] 初始化奖励函数和评估器...")
    reward_function = MathReward(
        answer_weight=config.answer_weight,
        format_weight=config.format_weight
    )

    evaluator = Evaluator(model, tokenizer, reward_function,
                          model_loader.device)

    # 4. 训练前评估
    print("\n[4/5] 训练前评估...")
    print("评估训练前的模型性能:")
    pre_train_results = evaluator.evaluate(eval_data)
    evaluator.print_results(pre_train_results, "训练前评估结果")

    # 清理GPU内存
    clear_gpu_memory()

    if not args.skip_train:
        # 创建训练数据集
        print("\n创建训练数据集...")
        train_dataset = math_dataset.generate_dataset(
            config.train_samples,
            operations=config.operations,
            num_range=config.num_range
        )
        print(f"创建训练集: {len(train_dataset)} 个样本")

        # 5. 训练模型
        print("\n[5/5] 开始GRPO训练...")
        trainer = GRPOTrainer(
            model=model,
            tokenizer=tokenizer,
            reward_function=reward_function,
            learning_rate=config.learning_rate,
            group_size=config.group_size,
            clip_epsilon=config.clip_epsilon,
            kl_coef=config.kl_coef,
            max_grad_norm=config.max_grad_norm,
            device=model_loader.device
        )

        # 开始训练（不再需要set_reference_model）
        trainer.train(
            dataset=train_dataset,
            num_epochs=config.num_epochs,
            batch_size=config.batch_size,
            save_path=config.save_path
        )

        # 清理GPU内存
        clear_gpu_memory()

        # 保存最终模型
        print("\n保存最终模型...")
        os.makedirs(config.final_model_path, exist_ok=True)
        try:
            model.save_pretrained(config.final_model_path)
            tokenizer.save_pretrained(config.final_model_path)
            print(f"最终模型已保存到: {config.final_model_path}")
        except Exception as e:
            print(f"保存模型时出错: {e}")

        # 训练后评估
        print("\n评估训练后的模型性能:")
        post_train_results = evaluator.evaluate(eval_data)
        evaluator.print_results(post_train_results, "训练后评估结果")

        # 对比结果
        print("\n" + "=" * 60)
        print("训练前后性能对比")
        print("=" * 60)
        print(f"{'指标':<20} {'训练前':<15} {'训练后':<15} {'提升':<15}")
        print("-" * 60)

        accuracy_improvement = post_train_results['accuracy'] - pre_train_results['accuracy']
        format_improvement = post_train_results['format_accuracy'] - pre_train_results['format_accuracy']
        reward_improvement = post_train_results['avg_reward'] - pre_train_results['avg_reward']

        print(f"{'答案准确率':<20} "
              f"{pre_train_results['accuracy']:.2%}        "
              f"{post_train_results['accuracy']:.2%}        "
              f"{accuracy_improvement:+.2%}")
        print(f"{'格式准确率':<20} "
              f"{pre_train_results['format_accuracy']:.2%}        "
              f"{post_train_results['format_accuracy']:.2%}        "
              f"{format_improvement:+.2%}")
        print(f"{'平均奖励':<20} "
              f"{pre_train_results['avg_reward']:.3f}        "
              f"{post_train_results['avg_reward']:.3f}        "
              f"{reward_improvement:+.3f}")
        print("=" * 60)

        # 保存评估结果
        results = {
            "config": {
                "model_name": config.model_name,
                "train_samples": config.train_samples,
                "eval_samples": config.eval_samples,
                "num_epochs": config.num_epochs,
                "batch_size": config.batch_size,
                "group_size": config.group_size,
                "learning_rate": config.learning_rate,
                "use_4bit": config.use_4bit
            },
            "pre_train": {
                "accuracy": pre_train_results['accuracy'],
                "format_accuracy": pre_train_results['format_accuracy'],
                "avg_reward": pre_train_results['avg_reward'],
                "correct_answers": pre_train_results['correct_answers'],
                "correct_format": pre_train_results['correct_format']
            },
            "post_train": {
                "accuracy": post_train_results['accuracy'],
                "format_accuracy": post_train_results['format_accuracy'],
                "avg_reward": post_train_results['avg_reward'],
                "correct_answers": post_train_results['correct_answers'],
                "correct_format": post_train_results['correct_format']
            },
            "improvement": {
                "accuracy": accuracy_improvement,
                "format_accuracy": format_improvement,
                "avg_reward": reward_improvement
            }
        }

        with open("evaluation_results.json", "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print("\n评估结果已保存到: evaluation_results.json")

    print("\n程序执行完成！")


if __name__ == "__main__":
    main()