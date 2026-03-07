import logging
import os
import time
import random
from typing import Optional

from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

logger = logging.getLogger(__name__)


class WebDriverManager:
    """WebDriver 管理器"""
    
    def __init__(self, config):
        self.config = config
        self.driver = None
    
    def initialize(self, headless: bool = False):
        """初始化 Selenium-Wire WebDriver"""
        logger.info("正在初始化 Selenium-Wire WebDriver...")
        
        # 配置 selenium-wire 以捕获请求
        wire_options = {
            'disable_capture': False,  # 启用请求捕获
            'disable_encoding': True,   # 禁用内容编码以便读取响应
        }
        
        ops = Options()
        ops.add_experimental_option("detach", not headless)
        ops.add_argument('--window-size=1280,800')
        ops.add_argument('--disable-blink-features=AutomationControlled')
        ops.add_argument('--no-proxy-server')
        ops.add_argument('--lang=zh-CN')
        ops.add_argument('--disable-gpu')
        ops.add_argument('--no-sandbox')
        ops.add_argument('--disable-dev-shm-usage')  # 解决 Docker/CI 环境内存问题

        ops.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 2. 只有在非 CI 环境才禁用这些 (CI环境有时候禁用 sandbox 会导致崩溃，但 try it)
        ops.add_argument('--no-sandbox')
        ops.add_argument('--disable-dev-shm-usage')
        
        # GitHub Actions 环境必须使用 headless 模式
        if headless or os.getenv('CI') == 'true':
            logger.info("检测到 CI 环境或 headless 模式，启用无头浏览器")
            ops.add_argument('--headless=new')  # 使用新的 headless 模式
            ops.add_argument('--disable-software-rasterizer')
        
        # 设置自定义 Chrome 路径
        if self.config.chrome_binary_path and os.path.exists(self.config.chrome_binary_path):
            logger.info(f"使用自定义 Chrome 路径: {self.config.chrome_binary_path}")
            ops.binary_location = self.config.chrome_binary_path
        
        try:
            # 在 CI 环境中，chromedriver 通常已安装在系统路径
            if os.getenv('CI') == 'true':
                logger.info("CI 环境中使用系统 ChromeDriver")
                self.driver = webdriver.Chrome(
                    options=ops,
                    seleniumwire_options=wire_options
                )
            else:
                # 本地环境使用项目目录中的 chromedriver
                local_driver_path = os.path.abspath("chromedriver.exe")
                if not os.path.exists(local_driver_path):
                    logger.error("未找到 chromedriver.exe，请确保文件在项目目录中")
                    return None
                
                logger.info(f"使用本地驱动: {local_driver_path}")
                service = Service(executable_path=local_driver_path)
                self.driver = webdriver.Chrome(
                    service=service,
                    options=ops,
                    seleniumwire_options=wire_options
                )
            
            if self.driver:
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """
                })

            logger.info("WebDriver 初始化成功")
            return self.driver
            
        except Exception as e:
            logger.error(f"WebDriver 初始化失败: {e}", exc_info=True)
            return None
    
    def close(self):
        """关闭 WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver 已关闭")