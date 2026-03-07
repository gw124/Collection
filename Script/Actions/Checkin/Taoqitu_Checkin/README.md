# 🐰 淘气兔自动签到脚本 (Taoqitu Auto Checkin)

基于 GitHub Actions 的自动签到脚本，专为 **淘气兔 (Taoqitu)** 网站设计。

![Python](https://img.shields.io/badge/Python-3.9-blue)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-green)
![License](https://img.shields.io/badge/License-MIT-orange)

## ✨ 功能特性

* **⚡️ 自动化执行**：每天北京时间 **08:30** 自动运行，无需人工干预。
* **🛡️ 强力防风控**：采用 **桌面端 Token 复用机制** + **Mac Chrome 指纹伪装**，完美绕过 IP 限制和 Cloudflare 验证。
* **🔧 灵活配置**：支持通过环境变量控制是否自动进行“流量抵消”。
* **推送通知**：目前脚本只打印日志，可在 Actions 页面查看详细运行结果。

---

## 🚀 快速开始

### 第一步：Fork 本仓库
点击右上角的 **Fork** 按钮，将本仓库克隆到你自己的 GitHub 账号下。

### 第二步：获取 USER_TOKEN (核心步骤)
由于网站风控严格，我们需要直接使用电脑浏览器上登录后的凭证（Token）。

1.  在电脑浏览器（推荐 Chrome/Edge）打开并登录 [淘气兔官网](https://vip.taoqitu.pro)。
    * **还没有账号？** [点此注册支持作者 (含邀请)](https://vip.taoqitu.pro/index.html?register=hvDi8r5s) 🚀
2.  按下 `F12` 打开开发者工具，点击 **网络 (Network)** 标签。
3.  点击页面上的“签到”按钮（或刷新页面）。
4.  在网络请求列表中找到 `sign` 或 `getUserInfo` 等请求。
5.  在右侧 **请求头 (Request Headers)** 中找到 **`Authorization`** 字段。
6.  复制那一长串字符（通常以 `eyJ...` 开头）。
    * ⚠️ **注意**：只复制 `eyJ` 开头的那串字符，**不要**包含 `Bearer ` 前缀。

### 第三步：配置 GitHub Secrets
1.  进入你 Fork 后的仓库页面。
2.  点击 **Settings** -> **Secrets and variables** -> **Actions**。
3.  点击 **New repository secret**，添加以下变量：

| Secret Name | 必填 | 说明 |
| :--- | :---: | :--- |
| `USER_TOKEN` | ✅ | **核心凭证**。填入上一步获取的 Authorization 字符串。 |
| `ENABLE_OFFSET`| ❌ | **流量抵消开关**。填 `true` 开启，填 `false` 关闭（默认关闭）。 |

### 第四步：启用 GitHub Actions
1.  点击仓库顶部的 **Actions** 标签。
2.  如果你看到一个绿色的按钮 "I understand my workflows, go ahead and enable them"，请点击它。
3.  在左侧选择 **Taoqitu Auto Checkin**。
4.  点击右侧的 **Run workflow** 手动触发一次测试。

---

## ⚙️ 进阶配置：流量抵消

脚本默认**只签到，不抵消流量**。如果你希望签到获得的流量自动抵消已用流量，请按以下步骤操作：

1.  前往 **Settings** -> **Secrets and variables** -> **Actions**。
2.  新建或修改 Secret：
    * **Name**: `ENABLE_OFFSET`
    * **Value**: `true`
3.  下次运行时，脚本将自动查询今日签到获得的流量并执行抵消。

---

## 📝 常见问题 (FAQ)

**Q: 运行日志显示 "未登录或登陆已过期" (403 Forbidden)？**
A: 这通常是因为 Token 失效或格式错误。
1. 请重新在电脑浏览器抓取最新的 Token。
2. 确保复制 Token 时没有多余的空格。
3. 确保你的 `USER_TOKEN` Secret 名字全大写，拼写正确。
4. 确保 Token 是从**电脑端**抓取的（脚本模拟的是 Mac 环境）。

**Q: 为什么我设置了 ENABLE_OFFSET 还是不抵消？**
A: 请检查：
1. 是否签到成功？（只有签到成功或显示“已签到”才会尝试抵消）。
2. `ENABLE_OFFSET` 的值是否为 `true`（小写）。
3. 当日是否有可抵消的流量记录。

---

## ⚠️ 免责声明

* 本脚本仅供学习和技术研究使用，请勿用于商业用途。
* 使用本脚本产生的任何后果（包括但不限于账号被封禁、数据丢失等）由使用者自行承担。
* 请支持正版，合理使用网站资源。
