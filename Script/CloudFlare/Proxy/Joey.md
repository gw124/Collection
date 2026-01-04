# CFnew - 终端 v2.9

<div align="center" style="margin-bottom: 20px;">

**语言 / زبان:** [🇨🇳 中文](README.md) | [🇮🇷 فارسی](فارسی.md)

</div>

<div align="center">

**多协议支持 · 自定义路径 · 延迟测试优选**

[![Telegram](https://img.shields.io/badge/Telegram-交流群-blue?logo=telegram)](https://t.me/+ft-zI76oovgwNmRh)
[![Version](https://img.shields.io/badge/Version-2.9-green)]()
[![License](https://img.shields.io/badge/License-MIT-orange)]()

</div>

## ✨ v2.9 核心特性

- 🎭 **多协议支持** - VLESS + Trojan + xhttp，自由切换
- 🛤️ **自定义路径** - 告别UUID路径，自定义访问地址，支持多级路径
- ⚡ **延迟测试** - 内置IP延迟测试，自动获取机场码，多线程并发测试
- 🔄 **订阅转换** - 自定义转换服务，优选类型细粒度控制
- 🎯 **图形化管理** - KV存储，实时配置，无需重新部署
- 🚀 **API管理** - RESTful API，批量操作，动态更新
- 📱 **多客户端支持** - CLASH、SURGE、SING-BOX、LOON、QUANTUMULT X、V2RAY、Shadowrocket、STASH、NEKORAY、V2RAYNG
- 🚀 **应用唤醒** - 点击按钮自动唤醒对应客户端应用
- 🔍 **自动识别** - 根据User-Agent自动识别并返回对应格式
- 🌐 **多语言支持** - 支持中文和波斯语（伊朗语），根据浏览器语言自动切换

---

## 🆕 v2.9 更新内容

- 🌍 **地区筛选功能** - 在线优选结果支持按地区多选筛选，可选择美国、香港、日本、韩国、新加坡等多个地区，方便按需查看和添加。
- ⚡ **延迟筛选优化** - 新增"只显示延迟最快的10个"选项，自动按延迟排序并只显示速度最快的前10个结果，快速找到最优节点。
- ➕ **追加/替换模式** - 优选结果添加功能支持两种模式：追加模式（保留现有项并添加新项）和替换模式（清空后添加），更灵活地管理优选列表。
- 🎨 **结果展示优化** - 每个优选结果显示地区标签（如 [US]、[JP]），按延迟自动排序，筛选后实时更新显示。
- 🧩 **细节与文案优化** - 版本号更新为 v2.9，并对界面交互和用户体验做进一步优化。

---

### 配套工具

| 类型 | 描述 | 链接 |
| :--- | :--- | :--- |
|  **优选工具** | 根据自己的网络环境选择最适合的IP | https://github.com/byJoey/yx-tools/releases |
|  **文字教程** | 详细的部署与使用说明博客文章 | [https://joeyblog.net/yuanchuang/1146.html](https://joeyblog.net/yuanchuang/1146.html) |
|  **Workers视频教程** | 直观的操作演示和功能讲解 | https://www.youtube.com/watch?v=aYzTr8FafN4 |
|  **Pages视频教程** | 直观的操作演示和功能讲解 | https://www.youtube.com/watch?v=JhVxJChDL-E |
|  **Snippets视频教程** | 直观的操作演示和功能讲解 | https://www.youtube.com/watch?v=xeFeH3Akcu8 |

### 部署

加入了千呼万唤的订阅每15分钟自动优选一次

#### 🔧 基础配置
| 变量名 | 值 | 说明 |
| :--- | :--- | :--- |
| `u` | `你的 UUID` | **必需**。用于访问订阅和配置管理界面 |
| `p` | `proxyip` | **可选**。自定义ProxyIP地址和端口 |
| `s` | `你的SOCKS5地址` | **可选**。用于将所有出站流量通过 SOCKS5 代理转发，格式为 `user:pass@host:port` 或 `host:port` |
| `d` | `自定义路径` | **可选**。自定义订阅访问路径，支持多级路径，如 `/mypath` 或 `/path/to/sub`，不填则使用 UUID 路径。如果路径没有以 `/` 开头，会自动补上 |
| `wk` | `地区代码` | **可选**。手动指定Worker地区，如：`SG`、`HK`、`US`、`JP`等 |

#### 🎭 协议配置
| 变量名 | 值 | 说明 |
| :--- | :--- | :--- |
| `ev` | `yes/no` | **可选**。启用VLESS协议（默认启用） |
| `et` | `yes/no` | **可选**。启用Trojan协议（默认禁用） |
| `ex` | `yes/no` | **可选**。启用xhttp协议（默认禁用） |
| `tp` | `自定义密码` | **可选**。Trojan协议密码，留空则使用UUID |

#### 🎯 图形化配置（推荐）
- **KV存储配置**：在Workers中创建KV命名空间，绑定环境变量 `C`
- **访问界面**：部署后访问 `/{你的UUID}` 即可使用图形化配置管理
- **实时生效**：通过界面修改配置无需重新部署，立即生效

#### 🔧 高级控制
| 变量名 | 值 | 说明 |
| :--- | :--- | :--- |
| `yx` | `自定义优选IP/域名` | **可选**。支持节点命名，格式：`1.1.1.1:443#香港节点,8.8.8.8:53#Google DNS` |
| `yxURL` | `优选IP来源URL` | **可选**。自定义优选IP列表来源URL，留空则使用默认地址 |
| `scu` | `订阅转换地址` | **可选**。自定义订阅转换服务URL，默认：`https://url.v1.mk/sub` |
| `epd` | `yes/no` | **可选**。启用优选域名（默认启用） |
| `epi` | `yes/no` | **可选**。启用优选IP（默认启用） |
| `egi` | `yes/no` | **可选**。启用GitHub默认优选（默认启用） |
| `qj` | `no` | **可选**。降级控制，设置为`no`时启用降级模式：CF直连失败→SOCKS5连接→fallback地址 |
| `dkby` | `yes` | **可选**。TLS控制，设置为`yes`时只生成TLS节点，不生成非TLS节点（如80端口） |
| `yxby` | `yes` | **可选**。优选控制，设置为`yes`时关闭所有优选功能，只使用原生地址，不生成优选IP和域名节点 |
| `rm` | `no` | **可选**。地区匹配控制，设置为`no`时关闭地区智能匹配 |
| `ae` | `yes` | **可选**。API管理开关，设置为`yes`时允许通过API动态管理优选IP（默认关闭） |

#### 📦 KV存储设置（可选但推荐）
1. 在Cloudflare Workers中创建KV命名空间
2. 在Workers设置中绑定KV命名空间，变量名设为 `C`
3. 重新部署Workers
4. 访问 `/{你的UUID}` 即可使用图形化配置管理

#### 🔑 API快速开始
1. https://github.com/byJoey/yx-tools/releases 优选软件
2. **开启API功能**：访问 `/{UUID}` 或 `/{自定义路径}` → 找到"允许API管理"→ 选择"开启API管理"→ 保存
3. **添加单个IP**：
```bash
# 使用UUID路径
curl -X POST "https://your-worker.workers.dev/{UUID}/api/preferred-ips" \
  -H "Content-Type: application/json" \
  -d '{"ip": "1.2.3.4", "port": 443, "name": "香港节点"}'

# 使用自定义路径（如果设置了d变量）
curl -X POST "https://your-worker.workers.dev/{自定义路径}/api/preferred-ips" \
  -H "Content-Type: application/json" \
  -d '{"ip": "1.2.3.4", "port": 443, "name": "香港节点"}'
```
4. **批量添加IP**：
```bash
curl -X POST "https://your-worker.workers.dev/{UUID或自定义路径}/api/preferred-ips" \
  -H "Content-Type: application/json" \
  -d '[
    {"ip": "1.2.3.4", "port": 443, "name": "节点1"},
    {"ip": "5.6.7.8", "port": 8443, "name": "节点2"}
  ]'
```
5. **一键清空**：
```bash
curl -X DELETE "https://your-worker.workers.dev/{UUID或自定义路径}/api/preferred-ips" \
  -H "Content-Type: application/json" \
  -d '{"all": true}'
```

### 新功能

#### ⚡ 延迟测试功能（v2.7 起提供，v2.9 增强筛选）
- **内置测试工具**：无需外部软件，直接在配置页面测试IP延迟
- **多种IP来源**：
  - 手动输入：直接输入IP或域名，支持批量（逗号分隔）
  - CF随机IP：从Cloudflare IP段随机生成指定数量的IP
  - URL获取：从远程URL获取IP列表进行测试
- **多线程并发**：支持1-50线程并发测试，默认5线程
- **自动获取机场码**：测试成功后自动获取CF机场码（如SJC、LAX等）
- **中文机场名映射**：自动将机场码映射为中文名称（如SJC→圣何塞）
- **真实延迟计算**：自动扣除DNS+TLS握手时间，显示纯网络延迟
- **浏览器记忆**：所有设置（端口、线程数、IP来源、URL等）自动保存到浏览器
- **地区筛选**：支持按地区多选筛选结果，可选择特定地区的节点进行测试和添加
- **延迟筛选**：支持只显示延迟最快的10个结果，快速找到最优节点
- **追加/替换模式**：选中测试结果后支持追加到现有优选列表或替换整个列表，灵活管理优选节点

#### 🎭 多协议支持
- **VLESS协议**：默认启用，完整的VLESS支持
- **Trojan协议**：支持Trojan-WS-TLS，自定义密码或使用UUID
- **xhttp协议**：基于HTTP POST的伪装协议
- **协议混用**：支持同时启用多个协议，客户端自动识别
- **协议切换**：图形化界面一键启用/禁用协议
- **独立保存**：协议配置区域新增独立保存按钮，更方便快捷
- **密码管理**：Trojan支持自定义密码，留空自动使用UUID

#### 🛤️ 自定义路径（d变量）
- **路径自定义**：不再使用UUID作为路径，设置你喜欢的路径名
- **多级路径支持**：支持多级路径，如 `/path/to/sub`，灵活组织访问结构
- **自动补全**：如果路径没有以 `/` 开头，系统会自动补上
- **安全增强**：自定义路径后UUID路径自动禁用，提高隐蔽性
- **灵活访问**：`https://worker.dev/mypath/sub` 或 `https://worker.dev/path/to/sub/sub` 更简洁易记
- **动态切换**：通过图形界面随时修改访问路径
- **状态显示**：配置页面实时显示当前使用的路径类型

#### 🎯 图形化配置管理
- **KV存储支持**：使用Cloudflare KV存储持久化配置
- **图形化界面**：访问 `/{你的UUID}` 或 `/{自定义路径}` 即可使用配置管理界面
- **实时配置**：无需重新部署，配置立即生效
- **配置优先级**：KV配置 > 环境变量 > 默认值

#### 🌐 多语言支持
- **自动语言检测**：根据浏览器语言自动选择中文或波斯语
- **手动语言切换**：页面右上角提供语言选择器，可手动切换
- **持久化存储**：用户选择的语言会保存到浏览器，下次访问自动应用
- **RTL支持**：波斯语版本自动启用从右到左（RTL）布局
- **完整翻译**：所有界面文本、提示信息、按钮标签都已翻译

#### 🔄 订阅转换控制
- **自定义转换服务**：支持配置自定义订阅转换URL
- **优选类型控制**：细粒度控制优选域名、优选IP、GitHub优选
- **独立开关**：每种优选类型可单独启用/禁用
- **默认设置**：内置优选域名、优选IP、GitHub默认优选全部启用
- **实时更新**：修改配置后立即生效，无需重新部署

#### 🚀 API动态管理
- **API管理**：通过RESTful API动态管理优选IP，无需修改代码
- **批量上报**：支持一次性批量添加多个优选IP
- **一键清空**：支持清空所有优选IP，快速更新列表
- **安全开关**：默认关闭，需在图形界面手动开启API功能
- **自动合并**：API添加的IP与手动配置的yx变量自动合并
- **实时同步**：API添加的IP立即在配置页面显示
- **API端点**：
  - `GET /{UUID或路径}/api/preferred-ips` - 查询优选IP列表
  - `POST /{UUID或路径}/api/preferred-ips` - 添加优选IP（支持单个/批量）
  - `DELETE /{UUID或路径}/api/preferred-ips` - 删除优选IP（支持单个/全部）

#### 🌍 手动指定地区
- **地区选择**：支持手动指定Worker地区，覆盖自动检测
- **设置方式**：`wk=SG` 或通过图形化界面选择
- **支持地区**：US、SG、JP、HK、KR、DE、SE、NL、FI、GB 
- **智能显示**：系统状态会显示"手动指定地区"而非"自动检测"

#### 🏷️ 优选节点命名
- **自定义名称**：支持为优选节点设置自定义名称
- **格式支持**：`IP:端口#节点名称` 或 `IP:端口`（使用默认名称）
- **示例**：`1.1.1.1:443#香港节点,8.8.8.8:53#Google DNS`
- **默认格式**：未设置名称时自动生成 `自定义优选-IP:端口`

#### 📊 系统状态监控
- **实时检测**：显示Worker地区、检测方式、ProxyIP状态
- **智能匹配**：同地区 → 邻近地区 → 其他地区的选择逻辑
- **状态指示**：可视化显示系统运行状态和配置信息

#### 🔧 高级控制选项
- **地区匹配控制**：`rm=no` 关闭地区智能匹配
- **降级控制**：`qj=no` 启用降级模式（CF直连失败→SOCKS5→fallback）
- **TLS控制**：`dkby=yes` 只生成TLS节点，不生成非TLS节点
- **优选控制**：`yxby=yes` 关闭所有优选功能

#### 🎨 多客户端支持
- **10种客户端**：支持 CLASH、SURGE、SING-BOX、LOON、QUANTUMULT X、V2RAY、Shadowrocket、STASH、NEKORAY、V2RAYNG
- **自动转换**：根据客户端类型自动生成对应配置
- **一键获取**：图形化界面一键生成订阅链接
- **应用唤醒**：点击客户端按钮自动唤醒对应应用，无需手动复制链接
- **自动识别**：根据User-Agent自动识别客户端类型并返回对应格式
- **协议适配**：不同客户端自动适配最佳协议组合
- **ALPN支持**：所有TLS链接自动包含 `h3,h2,http/1.1` 协议协商

#### ⚡ 性能优化
- **智能优选**：每15分钟自动优选一次，保持最佳性能
- **容错机制**：多重备用方案，确保服务稳定性
- **缓存优化**：智能缓存机制，减少重复计算

### 致谢

  * 本项目基于 [zizifn/edgetunnel](https://github.com/zizifn/edgetunnel) 修改，感谢原作者的贡献。
  * 本项目内置ProxyIP部分  来自CM [[cmliu](https://github.com/cmliu)) ，感谢作者的贡献。
  * 本项目反代IP来着前端独苗kejiland  [[qwer-search](https://github.com/qwer-search)) ，感谢作者的贡献。
  * 本项目在线优选接口来自  [[白嫖哥](https://t.me/bestcfipas)) ，感谢作者的贡献。


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=byJoey/cfnew&type=Timeline)](https://www.star-history.com/#byJoey/cfnew&Timeline&LogScale)
