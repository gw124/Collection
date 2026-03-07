# Acck.io 自动签到脚本 🚀

![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-brightgreen)
![Cloudflare WARP](https://img.shields.io/badge/Network-WARP%20Proxy-orange)

这是一个基于 **Python** 和 **GitHub Actions** 构建的全自动多账号签到工具。专门针对目标网站的 Cloudflare 拦截机制进行了优化，内置了本地 WARP 代理功能，完美绕过机房 IP 风控，实现真正的“无人值守”每日自动签到。

## ✨ 核心功能

* **🤖 彻底解放双手**：依托 GitHub Actions，每天定时自动运行，无需本地电脑开机。
* **🛡️ 独家防封控技术**：每次签到前自动调用并重启 Cloudflare WARP 客户端，强制全局网络和 DNS 走本地 Socks5 代理，模拟真实用户 IP。
* **👥 多账号无缝支持**：支持配置多个账号，账号之间自动间隔执行，并重新分配干净的出口 IP。
* **🔒 隐私安全保护**：运行日志深度脱敏，隐藏账号真实名称和完整 IP 地址，即便日志泄露也绝对安全。
* **📊 状态精准识别**：自动判断“今日已签到”状态，并实时抓取展示账户当前 AC 币余额。

---

## 🛠️ 快速部署指南

只需 3 分钟，即可拥有属于你自己的自动签到流。

### 第一步：准备仓库
为了保护你的账号密码安全，**强烈建议创建一个 Private (私有) 仓库**，然后将本项目的 `checkin.py` 和 `.github/workflows/sign.yml` 上传到你的仓库中。

### 第二步：配置账号密码 (Secrets)
1. 进入你的 GitHub 仓库，点击顶部菜单栏的 **Settings** (设置)。
2. 在左侧导航栏找到 **Secrets and variables** -> **Actions**。
3. 点击绿色的 **New repository secret** 按钮。
4. **Name** 填入：`ACCOUNTS`
5. **Secret** 填入你的账号密码。
   * **格式说明**：账号和密码之间用 `----` 分隔，不同账号之间用英文逗号 `,` 分隔。
   * **填写示例**：
     ```text
     user1@gmail.com----Password123!,user2@qq.com----MyPass456
     ```
6. 点击 **Add secret** 保存。

### 第三步：手动运行测试
1. 点击仓库顶部菜单栏的 **Actions**。
2. 在左侧找到 **每日自动化签到 (WARP防封版)** 并点击。
3. 点击右侧的 **Run workflow** 下拉菜单，再点击绿色的 **Run workflow** 按钮。
4. 等待约 1-2 分钟，点击进入运行日志，查看是否显示 `🎉 [账号X] 签到成功！`。

---

## ⏰ 修改定时任务时间 (可选)

默认配置为**每天北京时间早上 8:30** 自动运行。如果你想修改时间，请编辑 `.github/workflows/sign.yml` 文件中的 `cron` 表达式：

```yaml
  schedule:
    # 这里的格式是 UTC 时间。
    # 北京时间 = UTC时间 + 8小时。
    # 例如：'30 0 * * *' 代表 UTC 00:30，即北京时间 08:30。
    - cron: '30 0 * * *'
