# Surge 运行模式自动切换 (Auto Running Mode)

这是一个 Surge 脚本模块集合，用于根据当前的网络环境（Wi-Fi SSID、有线网络、蜂窝数据）自动切换 Surge 的运行模式（规则模式、全局直连、全局代理）。

针对不同设备的特性，本项目提供了 **macOS** 和 **iOS** 两个专用版本。

---

## 📥 安装 (Installation)

请根据您的设备类型，复制对应的模块链接地址到 Surge 中安装。

| 平台 | 特性说明 | 模块链接 (点击复制) |
| :--- | :--- | :--- |
| **macOS** | ✅ 适配有线网络 (Ethernet)<br>✅ 修复定位权限导致的 SSID 获取失败 | `https://raw.githubusercontent.com/gw124/Collection/refs/heads/main/Script/Surge/RunningMode/MacOS-running-mode.sgmodule` |
| **iOS** | ✅ 适配蜂窝数据 (Cellular)<br>✅ 针对移动端省电优化 | `https://raw.githubusercontent.com/gw124/Collection/refs/heads/main/Script/Surge/RunningMode/IOS-running-mode.sgmodule` |

> **一键安装链接 (需已安装 Surge):**
> * [安装 macOS 版](surge:///install-module?url=https://raw.githubusercontent.com/gw124/Collection/refs/heads/main/Script/Surge/RunningMode/MacOS-running-mode.sgmodule)
> * [安装 iOS 版](surge:///install-module?url=https://raw.githubusercontent.com/gw124/Collection/refs/heads/main/Script/Surge/RunningMode/IOS-running-mode.sgmodule)

---

## ⚙️ 配置说明 (Configuration)

安装模块后，右键/长按编辑模块，修改脚本顶部的 `config` 对象即可自定义逻辑。

### 1. 通用参数
| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `wifi` | 字符串 | **默认 Wi-Fi 模式**<br>当 Wi-Fi 名称未在下方特殊列表中时使用的模式。 |
| `all_direct` | 数组 | **强制直连列表**<br>在此列表中的 Wi-Fi 将强制切换为“全局直连”。<br>例如: `["Company-WiFi", "Home-5G"]` |
| `all_proxy` | 数组 | **强制代理列表**<br>在此列表中的 Wi-Fi 将强制切换为“全局代理”。 |

### 2. 平台特有参数
* **macOS 版专用**:
    * `ethernet`: **有线/兜底模式**。当使用网线连接或无法获取 SSID 时使用的模式（默认为 `DIRECT`）。
* **iOS 版专用**:
    * `cellular`: **蜂窝数据模式**。当使用 4G/5G 数据流量时使用的模式（默认为 `RULE`）。

### 3. 模式代码值
* `"RULE"` : 🚦 规则模式
* `"DIRECT"` : 🎯 全局直连
* `"PROXY"` : 🚀 全局代理

---

## ⚠️ 注意事项 (Notes)

###  macOS 用户必读
Surge Mac 需要 **定位服务权限** 才能获取当前连接的 Wi-Fi 名称 (SSID)。
1.  前往 `系统设置` -> `隐私与安全性` -> `定位服务`。
2.  确保 **Surge** 已被勾选。
3.  *如果不授予权限，脚本将无法读取 SSID，默认判定为“有线网络”并执行 `ethernet` 策略。*

### 📱 iOS 用户
首次运行脚本时，可能会弹出通知权限请求，建议允许，以便接收模式切换的通知提醒。
