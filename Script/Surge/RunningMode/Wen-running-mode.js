/**
 * Surge Mac 自动模式切换 (调试版)
 * 特性：增加延迟执行，防止网络未就绪导致判断失败
 */

// ================= 配置区域 =================
const config = {
  // 指定必须【全局直连】的 WiFi 名称 (精确匹配)
  all_direct: ["SuiYue", "303", "Company_Guest"],
  
  // 指定必须【全局代理】的 WiFi 名称
  all_proxy: [],
  
  // 默认 Wifi 下的模式 (RULE / DIRECT / PROXY)
  wifi_default: "RULE",
  
  // 有线网络/无法获取SSID时的模式 (通常建议 DIRECT 或 RULE)
  wired_default: "DIRECT" 
};
// ===========================================

const MODE_NAMES = {
  rule: "🚦规则模式",
  "global-proxy": "🚀全局代理",
  direct: "🎯全局直连"
};

// 延迟 3000 毫秒 (3秒) 执行，确保 Wi-Fi 已经获取到 IP
setTimeout(run, 3000);

function run() {
  // 1. 检查是否为 Surge
  if (typeof $surge === "undefined") {
    console.log("❌ 不是 Surge 环境，停止运行");
    $done();
    return;
  }

  // 2. 获取网络状态
  const v4_ip = $network.v4.primaryAddress;
  const ssid = $network.wifi ? $network.wifi.ssid : null;

  console.log(`[调试日志]当前 IP: ${v4_ip}, SSID: ${ssid}`);

  // 3. 核心逻辑判断
  let targetMode = "rule"; // 默认为规则模式
  let reason = "";

  if (ssid) {
    // === 情况 A: 连接了 Wi-Fi ===
    if (config.all_direct.includes(ssid)) {
      targetMode = "direct";
      reason = `匹配到直连 Wi-Fi: ${ssid}`;
    } else if (config.all_proxy.includes(ssid)) {
      targetMode = "global-proxy";
      reason = `匹配到代理 Wi-Fi: ${ssid}`;
    } else {
      targetMode = config.wifi_default.toLowerCase();
      if(targetMode === "proxy") targetMode = "global-proxy"; // 修正配置写法差异
      reason = `未知 Wi-Fi (${ssid})，使用默认配置`;
    }
  } else {
    // === 情况 B: 没有 Wi-Fi (通常是有线网 或 没给定位权限) ===
    if (v4_ip) {
      // 有 IP 但没 SSID -> 认为是有线网络
      targetMode = config.wired_default.toLowerCase();
      reason = "检测到有线网络 (或未获取到 SSID)";
    } else {
      // 既没 IP 也没 SSID -> 无网络
      console.log("❌ 当前无网络连接，不做改变");
      $done();
      return;
    }
  }

  // 4. 执行切换
  // 获取当前模式进行对比，避免重复操作
  $surge.setOutboundMode(targetMode);
  
  // 5. 发送通知和日志
  const logMsg = `模式: ${MODE_NAMES[targetMode]} | 原因: ${reason}`;
  console.log(`✅ 切换成功: ${logMsg}`);
  
  $notification.post(
    "运行模式自动切换", 
    `当前网络: ${ssid || "有线/蜂窝"}`, 
    `已切换至: ${MODE_NAMES[targetMode]}`
  );

  $done();
}
