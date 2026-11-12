"""
主入口程序
支持多轮对话式信息收集，输入错误不退出，输入 exit 可主动退出
校验通过后执行完整卡片生成流程，支持连续多次查询
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.harness import SkillHarness
from src.utils import load_config, get_api_key


def validate_location(context: dict) -> tuple[bool, str]:
    """校验解析出的地点与时间是否有效"""
    location = context.get("location", {})
    city = location.get("city", "").strip()
    date_desc = location.get("date_desc", "").strip()
    days = location.get("forecast_days", 0)

    if not city or len(city) < 2:
        return False, "未识别到有效城市名称，请输入具体城市名（如：北京、上海）"
    if not date_desc or days < 1:
        return False, "未识别到有效时间，请输入日期（如今天、未来3天）"
    return True, "信息校验通过"


def main():
    # 加载配置
    config = load_config("config/config.yaml")
    dashscope_key = get_api_key(config, "dashscope_api_key")

    if not dashscope_key:
        print("❌ 错误：未配置 DASHSCOPE_API_KEY")
        print("请设置环境变量或在 config/config.yaml 中填写通义千问密钥")
        sys.exit(1)

    # 初始化执行引擎
    output_dir = config.get("skill", {}).get("output_dir", "./output")
    naming_mode = config.get("output", {}).get("naming_mode", "content")

    harness = SkillHarness(
        api_key=dashscope_key,
        output_dir=output_dir,
        naming_mode=naming_mode
    )

    print("=" * 45)
    print("          天气预报卡片生成系统")
    print("  输入查询生成天气卡片，输入 exit 可退出程序")
    print("=" * 45 + "\n")

    # 多轮对话主循环：输入错误不退出，直到用户主动退出
    while True:
        user_input = input("请输入天气查询（如：成都未来3天天气）: ").strip()

        # 退出指令：支持 exit/quit/退出 多种写法
        if user_input.lower() in {"exit", "quit", "退出"}:
            print("\n👋 程序已退出，感谢使用")
            break

        if not user_input:
            print("⚠️  输入不能为空，请重新输入\n")
            continue

        # 每次新查询重置状态，避免上一次上下文残留
        harness.load_skill("weather_card")
        status = harness.get_status()

        try:
            # ========== 第一步：解析输入并前置校验 ==========
            harness.next_step({"user_input": user_input})
            ctx = harness.get_context()
            valid, msg = validate_location(ctx)

            # 校验不通过：提示后回到输入循环，不执行后续步骤
            if not valid:
                print(f"⚠️  {msg}\n")
                continue

            loc = ctx["location"]
            print(f"\n✅ 信息确认：城市={loc['city']}，时段={loc['date_desc']}（共{loc['forecast_days']}天）")

            # ========== 校验通过：执行剩余步骤生成卡片 ==========
            print("\n" + "-" * 45)
            print("       开始生成天气卡片")
            print("-" * 45)

            for i in range(1, status["total_steps"]):
                step_name = status["step_names"][i]
                print(f"\n▶ 执行步骤 {i+1}/{status['total_steps']}: {step_name}")
                harness.next_step()
                ctx = harness.get_context()

                if i == 1:
                    w = ctx["weather_data"]
                    print(f"  ✓ 已获取 {w['city']} 共{len(w['daily'])}天真实预报数据")
                elif i == 2:
                    print(f"  ✓ 卡片文案与建议生成完成")
                elif i == 3:
                    print(f"  ✓ 天蓝色主题HTML卡片渲染完成")

                # 每步自动保存检查点
                harness.save_checkpoint()

            # 导出最终文件
            output_path = harness.export_output()
            print("\n" + "=" * 45)
            print("       🎉 卡片生成完成")
            print("=" * 45)
            print(f"命名模式：{naming_mode}")
            print(f"卡片路径：{os.path.abspath(output_path)}")
            print("用浏览器打开该文件即可查看天气卡片效果\n")

        except ValueError as e:
            # 业务类错误：城市不存在、参数非法等
            print(f"\n❌ 处理失败：{str(e)}")
            print("请检查输入的城市名称是否正确，重新输入\n")
        except Exception as e:
            # 兜底异常：网络错误、API异常等
            print(f"\n❌ 发生错误：{str(e)}")
            print("请检查网络连接后重试，或输入 exit 退出\n")


if __name__ == "__main__":
    main()