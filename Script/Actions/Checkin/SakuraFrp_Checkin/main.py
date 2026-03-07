from config import Config
from automation import CheckInAutomation
import logging

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    try:
        # 加载配置
        config = Config.from_env()
        logger.info(f"使用账户: {config.sakurafrp_user}")
        
        # 执行自动签到
        automation = CheckInAutomation(config)
        automation.run()
        
    except ValueError as e:
        logger.error(f"配置错误: {e}")
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)


if __name__ == "__main__":
    main()