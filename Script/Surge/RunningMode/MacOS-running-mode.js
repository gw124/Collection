/**
 * Surge macOS 自动模式切换脚本 (Mac 专用版)
 * * 功能：
 * 1. 自动识别 Wi-Fi SSID 并切换指定模式。
 * 2. 自动识别 有线网络 (Ethernet) 并切换指定模式。
 * * 配置说明：
 * - wifi: 默认 Wi-Fi 下的模式 (当 Wi-Fi 名字不在特殊列表中时)
 * - ethernet: 有线网络 (或未识别到 SSID) 下的模式
 * - all_direct: 指定强制直连的 Wi-Fi 名称列表
 * - all_proxy: 指定强制代理的 Wi-Fi 名称列表
 */

let config = {
  silence: false, // 是否静默运行 (true 则不弹窗通知)
  wifi: "RULE",   // 默认 Wi-Fi 模式
  ethernet: "DIRECT", // macOS 有线网络/无法获取 SSID 时的模式
  all_direct: ["SuiYue", "303", "Office-Wifi"], // 指定全局直连的 Wi-Fi
  all_proxy: [], // 指定全局代理的 Wi-Fi
};

// --- 以下为逻辑代码，通常无需修改 ---

// 尝试从持久化存储读取用户覆盖配置 (BoxJS 等)
const boxConfig = $persistentStore.read("surge_mac_running_mode");
if (boxConfig) {
  try {
    const parsed = JSON.parse(boxConfig);
    Object.assign(config, parsed);
    // 类型转换修复
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

  // 获取 SSID (macOS 必须开启定位权限给 Surge 才能获取 SSID，否则会视为 Ethernet)
  if ($network.wifi && $network.wifi.ssid) {
    ssid = $network.wifi.ssid;
  }

  // 核心逻辑判断
  if (ssid) {
    // 场景 1: 连接了 Wi-Fi
    mode = lookupSSID(ssid);
    console.log(`检测到 Wi-Fi: ${ssid}, 匹配模式: ${mode}`);
  } else {
    // 场景 2: 无 SSID，视为 macOS 有线网络 (Ethernet)
    mode = config.ethernet;
    console.log(`未检测到 SSID，切换至有线网络配置: ${mode}`);
  }

  const target = {
    RULE: "rule",
    PROXY: "global-proxy",
    DIRECT: "direct",
  }[mode];

  // 执行 Surge 模式切换
  $surge.setOutboundMode(target);

  // 发送通知
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
  // 构建查找表
  (config.all_direct || []).forEach((id) => (map[id] = "DIRECT"));
  (config.all_proxy || []).forEach((id) => (map[id] = "PROXY"));

  // 如果 SSID 在列表中，返回对应模式；否则返回默认 Wi-Fi 模式
  return map[ssid] ? map[ssid] : config.wifi;
}

function notify(title, subtitle, content) {
  // 简单的防抖逻辑：只有当"当前网络"或"切换的模式"发生变化时才通知
  // 这里使用 subtitle (网络名) + content (模式) 作为 key
  const NOTIFY_KEY = "surge_mac_last_notification";
  const uniqueStatus = `${subtitle}|${content}`;
  const lastStatus = $persistentStore.read(NOTIFY_KEY);

  if (lastStatus !== uniqueStatus) {
    $persistentStore.write(uniqueStatus, NOTIFY_KEY);
    $notification.post(title, subtitle, content);
  }
}
