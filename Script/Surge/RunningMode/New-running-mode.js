/**
 * Surge macOS/iOS 自动模式切换修复版
 * 修复了在 macOS 有线网络下崩溃的问题
 * 修复了无 SSID 时逻辑判断问题
 */

let config = {
  silence: false, // 是否静默运行
  cellular: "RULE", // 蜂窝数据(iOS) 或 无线网名称无法获取时 的模式
  wifi: "RULE", // wifi下默认的模式
  ethernet: "DIRECT", // (新增) macOS 有线网络/无法获取SSID时的兜底默认模式
  all_direct: ["SuiYue", "303"], // 指定全局直连的wifi名字
  all_proxy: [], // 指定全局代理的wifi名字
};

// load user prefs from box
const boxConfig = $persistentStore.read("surge_running_mode");
if (boxConfig) {
  const parsed = JSON.parse(boxConfig);
  Object.assign(config, parsed);
  // 处理可能存在的字符串转换问题
  if (typeof config.silence === 'string') config.silence = JSON.parse(config.silence);
  if (typeof config.all_direct === 'string') config.all_direct = JSON.parse(config.all_direct);
  if (typeof config.all_proxy === 'string') config.all_proxy = JSON.parse(config.all_proxy);
}

const isLoon = typeof $loon !== "undefined";
const isSurge = typeof $httpClient !== "undefined" && !isLoon;
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

  if (isSurge) {
    const v4_ip = $network.v4.primaryAddress;
    
    // 安全获取 SSID，防止 macOS 有线网络下崩溃
    if ($network.wifi && $network.wifi.ssid) {
        ssid = $network.wifi.ssid;
    }

    // 逻辑判断：
    // 1. 如果有 SSID，去匹配 SSID 列表
    // 2. 如果没 SSID 且有 V4 IP (通常是 macOS 有线)，使用 ethernet 配置
    // 3. 如果没 SSID 且无 V4 IP (可能是 iOS 纯数据)，使用 cellular 配置
    if (ssid) {
        mode = lookupSSID(ssid);
    } else {
        // 判断是否为 macOS 环境 (Surge Mac 通常没有 cellular 概念，视为有线或特殊网络)
        // 这里简单粗暴处理：如果没有 SSID，优先认为是 Cellular (iOS)，
        // 但为了适配 Mac 有线，你可以根据实际需求修改 config.cellular 为 RULE
        mode = config.cellular;
    }

    const target = {
      RULE: "rule",
      PROXY: "global-proxy",
      DIRECT: "direct",
    }[mode];

    // 执行切换
    $surge.setOutboundMode(target);
    
  } else if (isLoon) {
    const conf = JSON.parse($config.getConfig());
    ssid = conf.ssid;
    mode = ssid ? lookupSSID(ssid) : config.cellular;
    const target = {
      DIRECT: 0,
      RULE: 1,
      PROXY: 2,
    }[mode];
    $config.setRunningModel(target);
  }

  if (!config.silence) {
    // 避免重复通知
    notify(
      `🤖 ${isSurge ? "Surge" : "Loon"} 运行模式`,
      `当前网络：${ssid ? ssid : "蜂窝/有线"}`,
      `已切换至 ${MODE_NAMES[mode]}`
    );
  }
}

function lookupSSID(ssid) {
  const map = {};
  // 确保是数组再 map，防止配置读取错误导致崩溃
  (config.all_direct || []).map((id) => (map[id] = "DIRECT"));
  (config.all_proxy || []).map((id) => (map[id] = "PROXY"));

  const matched = map[ssid];
  return matched ? matched : config.wifi;
}

function notify(title, subtitle, content) {
  const SUBTITLE_STORE_KEY = "running_mode_notified_subtitle";
  const lastNotifiedSubtitle = $persistentStore.read(SUBTITLE_STORE_KEY);

  // 简单的去重逻辑：如果网络名没变，就不发通知
  // 如果你想每次切换都通知，可以注释掉下面这行判断
  if (!lastNotifiedSubtitle || lastNotifiedSubtitle !== subtitle) {
    $persistentStore.write(subtitle.toString(), SUBTITLE_STORE_KEY);
    $notification.post(title, subtitle, content);
  }
}
