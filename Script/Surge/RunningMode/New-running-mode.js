/**
 * Surge macOS/iOS 自动模式切换 (增强修复版)
 * 1. 修复 iOS 下因无 IPv4 导致脚本崩溃的问题
 * 2. 增加 try-catch 容错，防止脚本报错失效
 * 3. 优化 SSID 读取逻辑
 */

let config = {
  silence: false, // 是否静默运行 (不发通知)
  cellular: "RULE", // iOS 蜂窝数据下默认模式
  wifi: "RULE", // Wi-Fi 下默认模式
  ethernet: "DIRECT", // macOS 有线网络/无法获取 SSID 时的兜底模式
  all_direct: ["SuiYue", "303"], // 指定全局直连的 Wi-Fi 名字
  all_proxy: [], // 指定全局代理的 Wi-Fi 名字
};

// --- 下面一般无需修改 ---

const isLoon = typeof $loon !== "undefined";
const isSurge = typeof $httpClient !== "undefined" && !isLoon;
const MODE_NAMES = {
  RULE: "🚦规则模式",
  PROXY: "🚀全局代理",
  DIRECT: "🎯全局直连",
};

// 载入持久化配置
if (isSurge) {
  const boxConfig = $persistentStore.read("surge_running_mode");
  if (boxConfig) {
    try {
      const parsed = JSON.parse(boxConfig);
      Object.assign(config, parsed);
      if (typeof config.silence === 'string') config.silence = JSON.parse(config.silence);
    } catch (e) {
      console.log("配置读取失败，使用默认配置");
    }
  }
}

manager();
$done();

function manager() {
  try {
    let ssid = null;
    let mode = config.cellular; // 默认给一个初始值

    if (isSurge) {
      // 1. 安全获取网络信息 (核心修复点)
      // iOS 网络切换间隙 v4 可能为 undefined，直接读取 primaryAddress 会崩溃
      const v4_ip = ($network.v4 && $network.v4.primaryAddress) ? $network.v4.primaryAddress : null;
      
      // 2. 尝试获取 SSID
      if ($network.wifi && $network.wifi.ssid) {
        ssid = $network.wifi.ssid;
      }

      // 3. 逻辑判断
      if (ssid) {
        // 有 Wi-Fi 名，进行匹配
        mode = lookupSSID(ssid);
      } else {
        // 无 SSID 情况处理
        if (!v4_ip) {
          // 无 IP，可能是无网络或纯蜂窝数据切换中，保持默认 cellular 配置
          mode = config.cellular;
        } else {
          // 有 IP 但无 SSID：
          // macOS: 通常是有线网络 -> ethernet
          // iOS: 可能是未授权位置权限的 Wi-Fi，或者是蜂窝数据
          // 这里通过判断环境来区分
          // 注意：iOS 上如果没有位置权限，SSID 也是 null，会误判为 cellular，这是系统限制
           mode = config.cellular; // 简化逻辑，默认为蜂窝配置
        }
      }
      
      // 如果检测到是有线网络环境（通常指 macOS 且无 wifi），可覆盖为 ethernet
      // 但 JS 无法精准区分 Mac 有线和 iOS 蜂窝，通常建议 config.cellular 和 ethernet 设为一样，或者手动调整
      
      const target = {
        RULE: "rule",
        PROXY: "global-proxy",
        DIRECT: "direct",
      }[mode];

      // 4. 执行切换
      $surge.setOutboundMode(target);

      // 5. 发送通知
      if (!config.silence) {
        notify(
          `🤖 Surge 自动模式`,
          `当前网络：${ssid ? ssid : "蜂窝/有线/隐藏"}`,
          `已切换至 ${MODE_NAMES[mode]}`
        );
      }
    } else if (isLoon) {
        // Loon 逻辑保持不变
        const conf = JSON.parse($config.getConfig());
        ssid = conf.ssid;
        mode = ssid ? lookupSSID(ssid) : config.cellular;
        const target = { DIRECT: 0, RULE: 1, PROXY: 2 }[mode];
        $config.setRunningModel(target);
    }
  } catch (err) {
    console.log(`脚本运行错误: ${err}`);
  }
}

function lookupSSID(ssid) {
  const map = {};
  (config.all_direct || []).map((id) => (map[id] = "DIRECT"));
  (config.all_proxy || []).map((id) => (map[id] = "PROXY"));
  return map[ssid] ? map[ssid] : config.wifi;
}

function notify(title, subtitle, content) {
  const key = "running_mode_notified_subtitle";
  const last = $persistentStore.read(key);
  // 只有当网络环境（subtitle）发生变化时才通知，避免刷屏
  if (last !== subtitle) {
    $persistentStore.write(subtitle, key);
    $notification.post(title, subtitle, content);
  }
}
