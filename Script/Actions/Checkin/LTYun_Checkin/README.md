# LTYun 自动签到脚本

基于 GitHub Actions 构建的 LTYun 全自动多账号签到脚本，集成图形验证码识别与 WARP 动态 IP 切换防封控机制。

## ✨ 核心功能

- **全自动签到**：每天定时执行（默认北京时间早上 9:00），彻底解放双手。
- **多账号支持**：支持配置多个账号，按顺序自动轮询签到。
- **本地验证码秒破**：内置 `ddddocr` 本地无感识别图形验证码，识别率极高，无需对接付费的第三方打码平台。
- **WARP IP 切换 (防风控)**：每次切换账号签到前，自动重启 Cloudflare WARP 更换出口 IP，有效规避同 IP 多账号请求触发的网站风控策略。
- **隐私脱敏日志**：默认强制开启匿名模式，Actions 运行日志仅输出 `[账户1]`、`[账户2]` 以及高度脱敏后的 IP 地址段，即使公开仓库也不怕真实邮箱和资产隐私泄露。

## 🚀 部署教程 (GitHub Actions)

只需简单几步，即可白嫖 GitHub 提供的服务器实现全自动签到。

### 1. Fork 本仓库
点击本页面右上角的 `Fork` 按钮，将本项目复制到你的个人账号下。

### 2. 配置账号信息 (Secrets)
进入你 Fork 后的个人仓库，依次点击页面顶部的 `Settings` -> 左侧边栏的 `Secrets and variables` -> `Actions`。
点击绿色的 `New repository secret` 按钮，添加以下核心变量：

- **Name**（变量名）: `ACCOUNTS`
- **Secret**（变量值）: 填写你的签到账号密码。
  
  **支持的格式如下（多账号用换行或 `&` 符号隔开）：**
  > # 基础格式：账号,密码
  > user1@gmail.com,password123
  > user2@test.com,pwd456
  > 
  > # 或者带自定义名称格式：名称:账号,密码
  > 大号:user1@gmail.com,password123&小号:user2@test.com,pwd456
  
  *(注：即使你在配置中写了“大号”、“小号”，只要未专门关闭匿名模式，公开日志中依然会安全地显示为“账户1”、“账户2”)*
### 3. 开启 Actions 权限
切换到仓库顶部的 `Actions` 标签页，如果你看到一个绿色的按钮提示 `I understand my workflows, go ahead and enable them`，点击它以允许工作流运行。

### 4. 手动触发测试
在 `Actions` 页面左侧列表中选择 `Auto Sign-in with WARP`，点击右侧的 `Run workflow` 下拉菜单，再点击绿色的 `Run workflow` 按钮手动运行一次。
等待一两分钟后，点击进入运行记录，查看输出日志，出现 `🎉 签到成功` 即代表配置完美通关！

---

## ⚙️ 进阶配置 (可选)

如果你是私有仓库，或者不在乎日志公开，想要在日志中明确显示你设置的**真实自定义名称**，可以在 Secrets 中新增一个变量来关闭匿名保护：
- **Name**: `ANONYMOUS_MODE`
- **Secret**: `false`

## 💻 本地运行 (Linux/macOS)

如果你希望在本地设备或个人 VPS 上运行此脚本：
1. 确保系统已安装 Python 3.9 左右的版本，并已正确安装配置 `cloudflare-warp` 客户端。
2. 安装项目依赖库（需锁定兼容版本）：
   `pip install requests "ddddocr==1.4.3" "Pillow<10.0.0" "numpy<2.0.0"`
3. 导入环境变量并执行脚本：
   `export ACCOUNTS="你的账号,你的密码"`
   `python sign.py`

## ⚠️ 免责声明

本项目仅供编程学习与交流使用，请勿用于商业用途或进行恶意高频并发请求。因使用本脚本产生的任何后果由使用者自行承担，与开发者无关。
