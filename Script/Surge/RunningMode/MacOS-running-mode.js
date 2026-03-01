/**
 * Surge macOS 自动模式切换脚本 (Mac 专用版)
 *
 * ⚙️ 核心配置参数说明：
 *
 * 1. 可用的模式值 (用于 wifi 和 ethernet 字段):
 * - "RULE"   : 规则模式 (按照 Surge 配置文件分流，最常用)
 * - "DIRECT" : 全局直连 (相当于关闭代理，流量直连)
 * - "PROXY"  : 全局代理 (强制所有流量走代理节点)
 *
 * 2. 字段具体含义:
 * - wifi     : 【默认 Wi-Fi 策略】。当你连接的 Wi-Fi 名字**不**在 all_direct 或 all_proxy 列表中时，使用此模式。
 * - ethernet : 【有线/兜底策略】。当检测不到 Wi-Fi 名字时（例如插网线、或 Surge 未获得定位权限时），使用此模式。
 *
 * 3. 特殊名单:
 * - all_direct : 在这里的 Wi-Fi 名字，强制使用"全局直连"。
 * - all_proxy  : 在这里的 Wi-Fi 名字，强制使用"全局代理"。
 */

let config = {
  silence: false,      // true: 静默运行(不通知); false: 开启通知
  wifi: "RULE",        // 默认 Wi-Fi 下使用规则模式
  ethernet: "DIRECT",  // 有线网络下使用直连模式
  all_direct: [        // 强制直连的 Wi-Fi 列表 (比如公司的内网 Wi-Fi)
    "Company_WiFi", 
    "SuiYue"
  ], 
  all_proxy: [         // 强制全局代理的 Wi-Fi 列表 (比如必须翻墙的 Wi-Fi)
    "Starbucks_Free"
  ], 
};

// --- 以下为逻辑代码，无需修改 ---

const boxConfig = $persistentStore.read("surge_mac_running_mode");
if (boxConfig) {
  try {
    const parsed = JSON.parse(boxConfig);
    Object.assign(config, parsed);
    if (typeof config.silence === 'string') config.silence = JSON.parse(config.silence);
    if (typeof config.all_direct === 'string') config.all_direct = JSON.parse(config.all_direct);
    if (typeof config.all_proxy === 'string') config.all_proxy = JSON.parse(config.all_proxy);
  } catch (e) {
    console.log("配置读取失败: " + e);
  }
}

const MODE_NAMES = {
  RULE: "🚦规则模式",
  PROXY: "🚀全局代理",
  DIRECT: "🎯全局直连",
};

manager();
$done();

function manager() {
  let ssid = null;
  let mode;

  // macOS 获取 SSID 需要系统定位权限
  if ($network.wifi && $network.wifi.ssid) {
    ssid = $network.wifi.ssid;
  }

  if (ssid) {
    // 命中 Wi-Fi 逻辑
    mode = lookupSSID(ssid);
    console.log(`检测到 Wi-Fi: ${ssid}, 准备切换至: ${mode}`);
  } else {
    // 命中 有线/无SSID 逻辑
    mode = config.ethernet;
    console.log(`未检测到 SSID (可能有线网络)，准备切换至: ${mode}`);
  }

  const target = {
    RULE: "rule",
    PROXY: "global-proxy",
    DIRECT: "direct",
  }[mode];

  $surge.setOutboundMode(target);

  if (!config.silence) {
    notify(
      "💻 Surge Mac 网络切换",
      `当前网络：${ssid ? ssid : "🔌 有线网络/未知"}`,
      `已切换至 ${MODE_NAMES[mode]}`
    );
  }
}

function lookupSSID(ssid) {
  const map = {};
  (config.all_direct || []).forEach((id) => (map[id] = "DIRECT"));
  (config.all_proxy || []).forEach((id) => (map[id] = "PROXY"));

  // 优先匹配特殊列表，匹配不到则使用默认 wifi 配置
  return map[ssid] ? map[ssid] : config.wifi;
}

function notify(title, subtitle, content) {
  const NOTIFY_KEY = "surge_mac_last_notification";
  const uniqueStatus = `${subtitle}|${content}`;
  const lastStatus = $persistentStore.read(NOTIFY_KEY);

  if (lastStatus !== uniqueStatus) {
    $persistentStore.write(uniqueStatus, NOTIFY_KEY);
    $notification.post(title, subtitle, content);
  }
}
