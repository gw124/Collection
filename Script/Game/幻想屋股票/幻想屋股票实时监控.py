import requests
import json
import os
import time
import sys
import unicodedata
import csv
import random
import re
from datetime import datetime, timedelta

# ======================================================================
# 🌍 跨平台终端底层自适应初始化
# ======================================================================
# 【后台运行重要说明】：在群晖/青龙等无头环境中，无需初始化终端颜色引擎
if os.name == 'nt':
    os.system('chcp 65001 > nul')

for proxy_env in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(proxy_env, None)

# ================= 📖 保姆级说明书配置区 =================

# 📱 【Telegram 机器人推送配置】
# TG_TOKEN       : 你的 Telegram 机器人专属通信令牌 (在 TG 里通过 @BotFather 获取)
# TG_CHAT_ID     : 接收推送消息的终端 ID (可以是你的个人账号 ID，也可以是群组/频道 ID)
# ENABLE_TG_PUSH : 手机推送总开关
#   - True  -> 开启！不仅在终端显示，还会同步发送排版好的消息到你的手机 Telegram 上。
#   - False -> 关闭！只在电脑终端屏幕上显示，不发推送。
TG_TOKEN = "" 
TG_CHAT_ID = "" 
ENABLE_TG_PUSH = False       

# 🔌 【游戏接口与身份凭证】
API_URL = "https://wgsh.hxwgame.cn/dish1/GetStockInfo1Min" 
GAME_TOKEN = "1dc16fb2-e2b7-4c37-8c9c-b65830f8b6be" 

# ⏱ 【终端 UI 刷新与防错频率 (秒)】
POLL_INTERVAL = 20 

# 🧹 【每日自动重置时间 (逻辑交易日)】
# 绝对不能删！每天到达该时间点，自动清空昨天的连胜、极值、历史包袱，重新提取官方日开盘价！
RESET_TIME = "06:00"

# 👻 【群晖/青龙后台静默模式开关】
# - True  -> 后台模式。不再清屏，仅保留基础心跳日志防撑爆日志盘。精力全用来发 TG 通知！
# - False -> 前台模式。会在终端疯狂刷新彩色表格（适合在 Mac 上自己盯着看）。
HEADLESS_MODE = False

# ====================================================
# 🎛️ 【雷达面板显示开关】(打造你专属的极简界面)
# ====================================================
# True = 【显示】该列，False = 【隐藏】该列。
SHOW_EXTREMES    = True   # 【日内极低/极高】 记录今天的历史天花板和铁底，防追高必看！
SHOW_WIN_RATIO   = True   # 【净胜(连)】 累积净胜(当前连胜)，判断主力洗盘还是真跌！
SHOW_REL_DIFF    = True   # 【单轮涨跌】 刚刚这一分钟涨跌了多少，防飞刀核心指标！
SHOW_AVG_DIFF    = True   # 🌟 现在它代表【超短线真实动能(抓起爆)】
SHOW_RECENT_DIFF = True   # 【短线(大周期波段)】 
SHOW_CUM_DIFF    = True   # 【长线(超大周期趋势)】 
SHOW_PREDICT_TAG = True   # 【趋势预警】 大白话明牌提示(如：确认抄底、飞刀暴跌)，必须开启！

# ====================================================
# 🎛️ 【低价股过滤开关 (面板净化)】
# ====================================================
# 游戏后期有很多低价垃圾股，跳动频繁且绝对利润极低。
# 开启此功能，现价低于设定值的股票将从【终端屏幕】和【TG推送】中隐藏，保持版面清爽！
# ⚠️ 核心特性：隐藏的股票依然会在后台默默写入 hxw_stock_data.csv 数据库中，不影响数据收集。
ENABLE_PRICE_FILTER = True        # 低价股隐藏总开关 (True = 开启隐藏, False = 显示全盘)
MIN_PRICE_THRESHOLD = 30000       # 自定义隐藏门槛：现价低于此数字 (如 20000) 的股票将被面板隐藏

# ====================================================
# 🚀 【核心交易引擎配置】(基于真实数据波段优化)
# ====================================================

# 🚨 【引擎一：主升浪共振 (右侧追涨)】 
# 只有处于“全线喷发”且“底仓雄厚”状态的股票才会亮红。只要有一项指标没涨，红底立即取消！
ENABLE_SMART_ALERT = True    # 智能买进警报总开关 
SMART_ALERT_CON_WINS = 6     # 门槛一：必须【连续涨够】 6 轮，防早盘脉冲诱多骗炮。
SMART_ALERT_CUM_WINS = 0     # 门槛二：必须【累积净胜】 >= 0 局 (0代表不限制)。
ALERT_REQUIRE_REL = True     # 要求【单轮涨跌】当前这一分钟必须在涨 (>0)

# 🟢 【引擎二：极值反弹盲狙 (地狱级防飞刀专版)】 
# 专抓被暴砸深套后，真正企稳反弹的超级大妖股 (如星光码头)！
ENABLE_PREDICT_REBOUND = True     
REBOUND_CUM_DROP = -45.0          # 📉 深坑门槛：今天必须跌穿 -45% 才会纳入抄底雷达！(防无底洞)
REBOUND_CONFIRM_PCT = 6.0         # 🛡️ 防飞刀确认：触底后必须拉升超过 6% 才给[确认抄底]，否则提示等待！
REBOUND_CONFIRM_WINS = 4          # 🛡️ 连胜破局：必须连涨 4 轮才算趋势反转。

# 🐉 【引擎三：半山腰洗盘 / 龙回头】
# 专治“稳健牛”拉升后被恶意砸盘，洗完散户再次冲锋的信号！
ENABLE_PULLBACK_BUY = True        
PULLBACK_PEAK_MIN = 25.0          # 前提：该股今天曾是个大牛股（最高曾涨超 25%）
PULLBACK_DROP_PCT = 15.0          # 洗盘深度：从最高点回撤超过 15% 才会引起雷达注意。
PULLBACK_REBOUND_PCT = 4.0        # 结束信号：砸盘结束后，底部反弹超过 4.0%，提示 [🐉龙回头上车]！

# 📈 【引擎四：长短均线金叉 (大级别左侧反转)】 
# 过滤短线噪音，看大周期级别的反转共振！
ENABLE_PREDICT_CROSS = True       
CROSS_SHORT_MA = 15               # 短期均线 (如：15分钟)
CROSS_LONG_MA = 60                # 长期均线 (如：60分钟)。15上穿60即为大金叉！

# ⚡ 【引擎五：动能加速度起爆 (超短线潜伏)】 
# 主力资金突然涌入，涨幅瞬间放大，抓起涨先手！
ENABLE_PREDICT_ACCEL = True       
PREDICT_ACCEL_THRESHOLD = 2.0     # 加速度阈值：一分钟内突飙 2% 以上，触发[突然飙升]警报！
PREDICT_MAX_WINS = 2              # 连胜必须 <= 2 轮才预警 (超过了说明已经起飞，归引擎一管)。

# 🌊 【引擎六：道氏波浪形态追踪 (绝杀防腰斩)】
# 记录上一个波浪顶点。突破前高=主升浪；无法突破前高=破位暴跌！
ENABLE_WAVE_TRACKING = True       
WAVE_CONFIRM_DROP_PCT = 5.0       # 确认波峰：从局部最高点回撤超过 5%，雷达就会死死记住那个高点！

# ====================================================
# 🛡️ 【三大空头防守引擎配置】(逃顶 / 抓崩盘)
# ====================================================
ENABLE_ESCAPE_TOP = True          # 🟦 [高位见顶] 逃顶警报
ESCAPE_CUM_PROFIT = 15.0          # 前提：长线累积涨幅已超过 15.0%
ESCAPE_REL_DROP = -2.5            # 触发：一分钟内突然被爆砸 -2.5% 报警 (过滤小幅回踩噪音)

ENABLE_DEATH_CROSS = True         # 🧊 [由涨转跌] 短线下穿长线的死叉预警
ENABLE_WATERFALL = True           # 🟤 [断崖暴跌] 瀑布式踩踏预警
WATERFALL_ACCEL_THRESHOLD = -2.0  # 触发：向下加速度超越 -2.0%，大出货开始！

# ====================================================
# ⭐ 【自选股专属配置】
# ====================================================
# 把你最关心的股票名字填在这里，只写纯名字即可。
FAVORITES = [
   "黎明酒馆", 
]

# FAV_STYLE : 🌟 自选股的高亮模式 (严格二选一)
#   "name" : 仅名称变青色 (低调护眼)
#   "bg"   : 铺满高级背景色并强制白字 (极其显眼)
FAV_STYLE = "name" 

# FAV_BG_COLOR : 背景颜色选择 (仅在 FAV_STYLE = "bg" 时生效)
FAV_BG_COLOR = "gray"

# FAV_PIN_TOP : 自选股霸榜特权？
# True = 无视涨跌，永远置顶；False = 和其他股票一起排队。
FAV_PIN_TOP = True 

# ====================================================
# 📊 【大盘核心排序与分界线配置】
# ====================================================
# SORT_METHOD:
#   "ratio" : (推荐) 按【涨幅比(连胜)】排。谁近期连击强排最前。
#   "cum" / "recent" / "percent" : 按指定的长短线百分比排。
SORT_METHOD = "ratio" 

# RATIO_SORT_BY : 🌟 涨幅比排序优先级开关
#   "consecutive" : 连续优先，短线爆发看括号内的连胜次数。
#   "cumulative"  : 累积优先，看重中长线波段底仓。
RATIO_SORT_BY = "consecutive"     

# ====================================================
# 📈 【量化计算指标参数设置】 (1分钟 = 1轮。超大周期战略重构)
# ====================================================
# 💡 注意：1440轮代表24小时，雷达具有史诗级全局视野。
MICRO_COUNT = 5      # 🎯 【超短动能】过去 5 分钟的真实动能，抓刚起爆的拐点！
RECENT_COUNT = 720   # 🌊 【大波段】过去 12 小时的中长线波段涨跌。
CUM_COUNT = 1440     # 🦅 【超宏观】过去 24 小时的大周期趋势 (如果周期是48H，可改为2880)。

# 🎨 【终端红绿色彩开关】
# True = 开启数字随涨跌变色 (正红负绿)，False = 关闭变色 (全白显示)。
# 强烈建议全部保持 True，方便一眼看穿全盘情绪！
COLOR_PERCENT = True   # 【总涨跌】列是否随涨跌变色
COLOR_REL = True       # 【单轮涨跌】列是否随涨跌变色
COLOR_AVG = True       # 【超短】列是否随涨跌变色 (代表最近5分钟动能红绿)
COLOR_RECENT = True    # 【短线】列是否随涨跌变色 (代表最近12小时趋势红绿)
COLOR_CUM = True       # 【长线】列是否随涨跌变色 (代表最近24小时趋势红绿)

# 🌟 【股票名称翻译字典】 
STOCK_DICT = {
    "10000-10001": "幻想屋工作室", "1011-2005": "夏威酒馆", "1017-2028": "晨星烘培", "1007-2007": "星辰商会",
    "1027-2019": "银河航运", "1016-2030": "星耀广告", "1014-2004": "星光农园", "1028-2025": "迷雾地产",
    "1020-2014": "风铃餐馆", "1006-2008": "丰收畜牧", "1026-2015": "翡翠旅店", "1018-2009": "弧光典当",
    "1001-2022": "四季保险", "1012-2026": "月光娱乐", "1013-2029": "宝石酿酒", "1009-2012": "花舞仓储",
    "1015-2013": "慧光食品", "1004-2002": "彩虹银行", "1010-2027": "幻影咖啡", "1003-2005": "星露酒馆",
    "1031-2028": "暮色烘培", "1022-2010": "暮光公会", "1005-2020": "晨露矿场", "1011-2024": "夏威物流",
    "1023-2016": "星尘渔业", "1021-2012": "极光仓储", "1032-2003": "珊瑚汽车", "1025-2023": "琥珀电力",
    "1016-2032": "星耀机械", "1002-2030": "绿野广告", "1018-2021": "弧光机车", "1014-2018": "星光码头",
    "1007-2025": "星辰地产", "1022-2026": "暮光娱乐", "1019-2009": "冬星典当", "1008-2015": "梦幻旅店",
    "1030-2014": "黎明餐馆", "1012-2011": "月光市场", "1029-2020": "钻石矿场", "1017-2022": "晨星保险",
    "1026-2004": "翡翠农园", "1024-2007": "水晶商会", "1010-2024": "幻影物流", "1028-2014": "迷雾餐馆",
    "1015-2029": "慧光酿酒", "1027-2001": "银河炼金", "1014-2013": "星光食品", "1013-2027": "宝石咖啡",
    "1032-2028": "珊瑚烘焙", "1006-2005": "丰收酒馆", "1026-2028": "翡翠烘焙", "1030-2005": "黎明酒馆",
    "1025-2028": "琥珀烘焙", "1020-2005": "风铃酒馆", "1011-2003": "夏威汽车", "1005-2008": "晨露畜牧",
    "1029-2011": "钻石市场", "1008-2019": "梦幻航运", "1010-2015": "幻影旅店", "1003-2017": "星露医院",
    "1009-2010": "花舞公会", "1021-2030": "极光广告", "1016-2024": "星耀物流", "1030-2006": "黎明工坊",
    "1029-2012": "钻石仓储", "1022-2031": "暮光安保", "1001-2020": "四季矿场", "1012-2016": "月光渔业",
    "1019-2003": "冬星汽车", "1002-2010": "绿野公会", "1023-2021": "星尘机车", "1009-2014": "花舞餐馆",
    "1018-2022": "弧光保险", "1024-2013": "水晶食品", "1028-2026": "迷雾娱乐", "1004-2025": "彩虹地产",
    "1014-2012": "星光仓储", "1007-2023": "星辰电力", "1017-2027": "晨星咖啡", "1013-2031": "宝石安保",
    "1029-2018": "钻石码头", "1011-2009": "夏威典当", "1005-2004": "昙霞农原", "1008-2020": "梦幻矿场",
    "1016-2003": "星耀汽车", "1031-2001": "暮色炼金", "1027-2005": "银河酒馆", "1001-2010": "四季公会",
    "1002-2029": "绿野酿酒", "1019-2030": "冬星广告", "1012-2032": "月光机械", "1032-2012": "珊瑚仓储",
    "1020-2019": "风铃航运", "1006-2017": "丰收医院", "1021-2028": "极光烘焙",
}

# 💾 【退出时清理缓存 (状态重置开关)】
# - True  -> 每次退出脚本，都会删掉雷达的历史记忆。
# - False -> 退出保留！重启时无缝衔接大周期的累积、极值和波峰数据 (强烈推荐)。
CLEAR_STATE_ON_EXIT = False

# 💾 【本地数据挖掘引擎 (隐形记录器)】
# 开启后，会在脚本目录自动生成 CSV 文件，记录每一跳数据，供你后期复盘！
ENABLE_DATA_LOGGER = True           
LOG_FILE_NAME = "hxw_stock_data.csv" 
LOG_RETAIN_DAYS = 0                  # 0 = 永久保留数据，不自动清理。

# ================= 📖 核心配置区结束 =====================

PAYLOAD = {"platform": 1, "game": "p4", "token": GAME_TOKEN}

def get_random_headers():
    user_agents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"]
    return {"Content-Type": "application/json", "User-Agent": random.choice(user_agents)}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "stock_state.json")

# 颜色代码
C_RED = '\033[91m'
C_GREEN = '\033[92m'
C_YELLOW = '\033[93m'
C_CYAN = '\033[96m'
C_WHITE = '\033[97m'
C_RESET = '\033[0m'

C_BG_STYLE   = '\033[48;5;238m\033[97m' if FAV_BG_COLOR == "gray" else '\033[44m\033[97m'
C_BG_ALERT   = '\033[41m\033[97m'
C_BG_REBOUND = '\033[42m\033[97m'
C_BG_CROSS   = '\033[45m\033[97m'
C_BG_ACCEL   = '\033[43m\033[30m'
C_BG_ESCAPE  = '\033[44;1m\033[97m'
C_BG_DEATH   = '\033[46m\033[97m'
C_BG_WATERFALL = '\033[100m\033[97m'

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def get_raw_width(text):
    clean_text = ANSI_ESCAPE.sub('', str(text))
    width = 0
    for char in clean_text:
        if unicodedata.east_asian_width(char) in ('F', 'W'): width += 2
        else: width += 1
    return width

def align_cell(colored_text, raw_text, width, align='right'):
    w = get_raw_width(raw_text)
    pad = ' ' * max(0, width - w)
    if align == 'left': return colored_text + pad
    elif align == 'right': return pad + colored_text
    else: return ' ' * (len(pad)//2) + colored_text + ' ' * (len(pad) - len(pad)//2)

def format_num(val):
    if val > 99999999: return f"{val:.2e}"
    return f"{val:.2f}"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {
        "basePrices": {}, "last_raw_prices": {}, "last_valid_prices": {}, "last_rel_diff": {}, 
        "historyPct": {}, "historyPrices": {}, "cumulative_wins": {}, "consecutive_wins": {}, 
        "logical_date": "", "daily_max_pct": {}, "daily_min_pct": {},
        "wave_peaks": {}, "wave_tracking": {}
    }

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f: json.dump(state, f, ensure_ascii=False, indent=2)

def send_tg_msg(text):
    if not ENABLE_TG_PUSH: return
    try: 
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        if HEADLESS_MODE: print(f"[{datetime.now().strftime('%H:%M:%S')}] TG发送失败: {e}")

def get_color(val):
    return C_RED if val > 0 else C_GREEN if val < 0 else ""

def safe_sleep(duration):
    time.sleep(duration)

def cleanup_old_csv_logs(csv_path, retain_days):
    if retain_days <= 0 or not os.path.exists(csv_path): return
    try:
        cutoff_time = datetime.now() - timedelta(days=retain_days)
        rows_to_keep = []
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
                rows_to_keep.append(header)
            except StopIteration: return 
            for row in reader:
                if not row: continue
                try:
                    row_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    if row_time >= cutoff_time: rows_to_keep.append(row)
                except ValueError: rows_to_keep.append(row)
        with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(rows_to_keep)
    except Exception as e: pass

def main():
    state = load_state()
    basePrices, last_raw_prices, last_valid_prices = state.get("basePrices", {}), state.get("last_raw_prices", {}), state.get("last_valid_prices", {})
    last_rel_diff, historyPct, historyPrices = state.get("last_rel_diff", {}), state.get("historyPct", {}), state.get("historyPrices", {})
    cumulative_wins, consecutive_wins, daily_max_pct, daily_min_pct = state.get("cumulative_wins", {}), state.get("consecutive_wins", {}), state.get("daily_max_pct", {}), state.get("daily_min_pct", {})
    
    # 获取波浪引擎的状态字典
    wave_peaks = state.get("wave_peaks", {})
    wave_tracking = state.get("wave_tracking", {})

    print(f"🚀 [幻想屋战术监控雷达] 正在启动... 当前运行模式: {'【后台静默模式】' if HEADLESS_MODE else '【前台交互模式】'}")

    if ENABLE_DATA_LOGGER and LOG_RETAIN_DAYS > 0:
        csv_path = os.path.join(SCRIPT_DIR, LOG_FILE_NAME)
        cleanup_old_csv_logs(csv_path, LOG_RETAIN_DAYS)

    try:
        while True:
            if not HEADLESS_MODE: os.system('clear' if os.name == 'posix' else 'cls')
                
            reset_h, reset_m = map(int, RESET_TIME.split(':'))
            current_logical_date = (datetime.now() - timedelta(hours=reset_h, minutes=reset_m)).strftime('%Y-%m-%d')
            
            # --- 换日重置机制 ---
            if state.get("logical_date") != current_logical_date:
                basePrices.clear(); last_raw_prices.clear(); last_valid_prices.clear()
                last_rel_diff.clear(); historyPct.clear(); historyPrices.clear()
                cumulative_wins.clear(); consecutive_wins.clear()
                daily_max_pct.clear(); daily_min_pct.clear()
                wave_peaks.clear(); wave_tracking.clear()  # 清空旧的波浪记忆
                
                state["logical_date"] = current_logical_date
                state["needs_snapshot"] = True
                save_state(state)
                if HEADLESS_MODE: print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 触发换日重置，准备捕获官方开盘价。")
                
                if ENABLE_DATA_LOGGER and LOG_RETAIN_DAYS > 0:
                    csv_path = os.path.join(SCRIPT_DIR, LOG_FILE_NAME)
                    cleanup_old_csv_logs(csv_path, LOG_RETAIN_DAYS)

            if not HEADLESS_MODE: print(f"📡 正在拉取大盘核心数据... (按Ctrl+C安全退出)")
            
            no_cache_url = f"{API_URL}?_t={int(time.time() * 1000)}"
            try:
                resp = requests.post(no_cache_url, json=PAYLOAD, headers=get_random_headers(), timeout=20)
                data = resp.json()
            except Exception as e:
                if HEADLESS_MODE: print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ 网络请求错误: {e}")
                safe_sleep(5)
                continue

            stock_list = data.get("data", {}).get("list", [])
            if not stock_list:
                safe_sleep(10)
                continue

            current_prices = { f"{str(s.get('name1', '')).strip()}-{str(s.get('name2', '')).strip()}": float(s.get('price', 0)) for s in stock_list }
            
            if state.get("needs_snapshot"):
                basePrices = {}
                for s in stock_list:
                    s_id = f"{str(s.get('name1', '')).strip()}-{str(s.get('name2', '')).strip()}"
                    official_daily_price = float(s.get('dailyPrice', current_prices[s_id]))
                    basePrices[s_id] = official_daily_price
                
                state["basePrices"] = basePrices
                state["needs_snapshot"] = False
                save_state(state)
                if HEADLESS_MODE: print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 今日官方开盘基准价已锁定！")

            is_first_run = (len(last_valid_prices) == 0)
            is_valid_update = (current_prices != last_raw_prices)
            
            # 🎯 核心修复：根据你的最大周期，动态分配数组内存，防止溢出死机！
            max_history_len = max(CUM_COUNT, RECENT_COUNT, MICRO_COUNT, CROSS_LONG_MA) + 10

            if is_valid_update:
                if is_first_run:
                    last_valid_prices = current_prices.copy()
                    for s_id, price in current_prices.items(): historyPrices[s_id] = [price]
                else:
                    for s in stock_list:
                        s_id = f"{str(s.get('name1', '')).strip()}-{str(s.get('name2', '')).strip()}"
                        c_price = current_prices[s_id]
                        prev_valid = last_valid_prices.get(s_id)
                        if prev_valid and prev_valid > 0:
                            rel_diff = ((c_price - prev_valid) / prev_valid) * 100
                            last_rel_diff[s_id] = rel_diff
                            if rel_diff > 0:
                                cumulative_wins[s_id] = cumulative_wins.get(s_id, 0) + 1
                                consecutive_wins[s_id] = max(consecutive_wins.get(s_id, 0) + 1, 1)
                            elif rel_diff < 0:
                                cumulative_wins[s_id] = cumulative_wins.get(s_id, 0) - 1
                                consecutive_wins[s_id] = min(consecutive_wins.get(s_id, 0) - 1, -1)
                            if s_id not in historyPct: historyPct[s_id] = []
                            historyPct[s_id].append(rel_diff)
                            if len(historyPct[s_id]) > max_history_len: historyPct[s_id].pop(0)
                        if s_id not in historyPrices: historyPrices[s_id] = []
                        historyPrices[s_id].append(c_price)
                        if len(historyPrices[s_id]) > max_history_len: historyPrices[s_id].pop(0) 
                        last_valid_prices[s_id] = c_price
                last_raw_prices = current_prices.copy()
            
            time_str = datetime.now().strftime('%H:%M:%S')

            columns_def = [
                ("标的名称", 14, 'left'), 
                ("基准价", 11, 'right'), 
                ("现价", 11, 'right'), 
                ("总涨跌", 10, 'right')
            ]
            if SHOW_EXTREMES: columns_def.append(("极低/极高", 14, 'right'))
            if SHOW_WIN_RATIO: columns_def.append(("净胜(连)", 11, 'right'))
            if SHOW_REL_DIFF: columns_def.append(("单轮", 8, 'right'))
            if SHOW_AVG_DIFF: columns_def.append(("超短", 8, 'right'))
            if SHOW_RECENT_DIFF: columns_def.append(("短线", 8, 'right'))
            if SHOW_CUM_DIFF: columns_def.append(("长线", 8, 'right'))
            if SHOW_PREDICT_TAG: columns_def.append(("趋势预警", 18, 'left'))

            h_cols = []
            for name, width, align in columns_def:
                h_cols.append(align_cell(name, name, width, align))
            h_str = "| " + " | ".join(h_cols) + " |"
            t_width = get_raw_width(h_str)
            sep_line = "-" * t_width

            if not HEADLESS_MODE:
                print(f"\n{'=' * t_width}")
                print(f"📉 幻想屋战术雷达 (V5大周期狙击版) | ⏱ {time_str}")
                print(f"{'=' * t_width}")
                print(h_str)
                print(sep_line)

            tg_msg = f"📈 <b>幻想屋股票实时推送</b>\n⏱ {time_str}\n" + "━" * 15 + "\n"
            results_list = []

            for s in stock_list:
                s_id = f"{str(s.get('name1', '')).strip()}-{str(s.get('name2', '')).strip()}"
                c_price = current_prices[s_id]
                b_price = basePrices.get(s_id, float(s.get('dailyPrice', c_price)))
                diff_percent = ((c_price - b_price) / b_price * 100) if b_price > 0 else 0.0
                rel_diff = last_rel_diff.get(s_id, 0.0)
                
                # ====================================================
                # 🎛️ 低价股过滤判断
                # ====================================================
                is_hidden = False
                if ENABLE_PRICE_FILTER and c_price < MIN_PRICE_THRESHOLD:
                    is_hidden = True
                
                if is_valid_update and not is_first_run:
                    if s_id not in daily_max_pct or diff_percent > daily_max_pct[s_id]: daily_max_pct[s_id] = diff_percent
                    if s_id not in daily_min_pct or diff_percent < daily_min_pct[s_id]: daily_min_pct[s_id] = diff_percent
                
                max_pct_val = daily_max_pct.get(s_id, diff_percent)
                min_pct_val = daily_min_pct.get(s_id, diff_percent)
                range_pct = max_pct_val - min_pct_val
                pos = ((diff_percent - min_pct_val) / range_pct * 100) if range_pct > 2 else 50.0 
                
                cum_score = cumulative_wins.get(s_id, 0)
                con_score = consecutive_wins.get(s_id, 0)
                
                hp_list = historyPrices.get(s_id, [])
                
                if len(hp_list) > MICRO_COUNT:
                    micro_price = hp_list[-(MICRO_COUNT + 1)]
                    avg_percent = ((c_price - micro_price) / micro_price) * 100 if micro_price > 0 else 0.0
                else:
                    micro_price = hp_list[0] if len(hp_list) > 0 else c_price
                    avg_percent = ((c_price - micro_price) / micro_price) * 100 if micro_price > 0 else 0.0

                recent_diff = ((c_price - hp_list[-(RECENT_COUNT + 1)]) / hp_list[-(RECENT_COUNT + 1)] * 100) if len(hp_list) > RECENT_COUNT and hp_list[-(RECENT_COUNT + 1)] > 0 else (((c_price - hp_list[0]) / hp_list[0] * 100) if len(hp_list) > 1 and hp_list[0] > 0 else 0.0)
                cum_diff = ((c_price - hp_list[-(CUM_COUNT + 1)]) / hp_list[-(CUM_COUNT + 1)] * 100) if len(hp_list) > CUM_COUNT and hp_list[-(CUM_COUNT + 1)] > 0 else (((c_price - hp_list[0]) / hp_list[0] * 100) if len(hp_list) > 1 and hp_list[0] > 0 else 0.0)

                # ====================================================
                # 🌊 引擎六：道氏波浪形态追踪算法
                # ====================================================
                is_wave_breakout, is_wave_downtrend = False, False
                if ENABLE_WAVE_TRACKING:
                    w_peak = wave_peaks.get(s_id, 0.0)
                    w_trk = wave_tracking.get(s_id, {"local_max": c_price})
                    
                    if c_price > w_trk["local_max"]:
                        w_trk["local_max"] = c_price
                        if w_peak > 0 and c_price > w_peak * 1.01: 
                            is_wave_breakout = True
                    elif c_price < w_trk["local_max"] * (1 - WAVE_CONFIRM_DROP_PCT / 100.0):
                        confirmed_peak = w_trk["local_max"]
                        if w_peak > 0 and confirmed_peak < w_peak * 0.99:
                            is_wave_downtrend = True
                        
                        wave_peaks[s_id] = confirmed_peak
                        w_trk["local_max"] = c_price 
                        
                    wave_tracking[s_id] = w_trk

                # ====================================================
                # 🛡️ 预判引擎
                # ====================================================
                term_tag_raw = "[中线观望]"
                term_tag_col = ""
                tg_alert = ""

                bounce_from_bottom = diff_percent - min_pct_val
                drawdown_from_peak = max_pct_val - diff_percent
                is_pullback_rebound = False
                
                if ENABLE_PULLBACK_BUY and max_pct_val >= PULLBACK_PEAK_MIN:
                    if drawdown_from_peak >= PULLBACK_DROP_PCT:
                        if rel_diff > 0 and con_score >= 1 and (bounce_from_bottom >= PULLBACK_REBOUND_PCT or rel_diff > PULLBACK_REBOUND_PCT/2):
                            is_pullback_rebound = True
                            term_tag_raw = "[龙回头上车]"
                            term_tag_col = f"{C_GREEN}[龙回头上车]{C_RESET}"
                        elif rel_diff <= 0:
                            term_tag_raw = "[主力洗盘中]"
                            term_tag_col = f"{C_YELLOW}[主力洗盘中]{C_RESET}"

                if not is_pullback_rebound:
                    if diff_percent <= REBOUND_CUM_DROP or con_score <= -25:
                        if rel_diff <= 0:
                            term_tag_raw = "[飞刀暴跌]"
                            term_tag_col = f"{C_YELLOW}[飞刀暴跌]{C_RESET}"
                        else:
                            if bounce_from_bottom >= REBOUND_CONFIRM_PCT or con_score >= REBOUND_CONFIRM_WINS:
                                term_tag_raw = "[确认抄底]"
                                term_tag_col = f"{C_GREEN}[确认抄底]{C_RESET}"
                            else:
                                diff_needed = max(0, REBOUND_CONFIRM_PCT - bounce_from_bottom)
                                term_tag_raw = f"[距反弹差{diff_needed:.1f}%]" 
                                term_tag_col = f"{C_YELLOW}{term_tag_raw}{C_RESET}"
                    
                    elif pos <= 10.0 and range_pct > 15.0: 
                        if rel_diff <= 0:
                            if diff_percent <= -40.0:
                                term_tag_raw = "[深坑建仓区]"
                                term_tag_col = f"{C_YELLOW}[深坑建仓区]{C_RESET}"
                            else:
                                term_tag_raw = "[底部摩擦]"
                                term_tag_col = f"{C_YELLOW}[底部摩擦]{C_RESET}"
                        else:
                            if bounce_from_bottom >= REBOUND_CONFIRM_PCT or con_score >= REBOUND_CONFIRM_WINS:
                                term_tag_raw = "[极值反弹]"
                                term_tag_col = f"{C_GREEN}[极值反弹]{C_RESET}"
                            else:
                                diff_needed = max(0, REBOUND_CONFIRM_PCT - bounce_from_bottom)
                                term_tag_raw = f"[距反弹差{diff_needed:.1f}%]" 
                                term_tag_col = f"{C_YELLOW}{term_tag_raw}{C_RESET}"
                    
                    elif diff_percent >= 50.0 or con_score >= 18:
                        term_tag_raw = "[极高随时崩]"
                        term_tag_col = f"{C_CYAN}[极高随时崩]{C_RESET}"
                    elif pos >= 90.0 and range_pct > 20.0:
                        term_tag_raw = "[涨到头了]"
                        term_tag_col = f"{C_CYAN}[涨到头了]{C_RESET}"

                is_smart_alert, is_predict_rebound, is_predict_cross, is_predict_accel = False, False, False, False
                is_escape_top, is_death_cross, is_waterfall = False, False, False

                if ENABLE_SMART_ALERT and (con_score >= SMART_ALERT_CON_WINS) and (cum_score >= SMART_ALERT_CUM_WINS):
                    is_smart_alert = True
                    if ALERT_REQUIRE_REL and rel_diff <= 0: is_smart_alert = False
                
                if not is_smart_alert and ENABLE_ESCAPE_TOP and cum_diff >= ESCAPE_CUM_PROFIT and rel_diff <= ESCAPE_REL_DROP: is_escape_top = True
                if not is_smart_alert and not is_escape_top:
                    if ENABLE_DEATH_CROSS and len(hp_list) >= CROSS_LONG_MA + 1:
                        curr_s_ma = sum(hp_list[-CROSS_SHORT_MA:]) / CROSS_SHORT_MA
                        curr_l_ma = sum(hp_list[-CROSS_LONG_MA:]) / CROSS_LONG_MA
                        prev_s_ma = sum(hp_list[-(CROSS_SHORT_MA+1):-1]) / CROSS_SHORT_MA
                        prev_l_ma = sum(hp_list[-(CROSS_LONG_MA+1):-1]) / CROSS_LONG_MA
                        if prev_s_ma >= prev_l_ma and curr_s_ma < curr_l_ma and rel_diff < 0: is_death_cross = True
                    if ENABLE_WATERFALL and len(hp_list) >= 2 and rel_diff < 0:
                        prev_rel_diff = ((hp_list[-2] - hp_list[-3]) / hp_list[-3] * 100) if len(hp_list) >= 3 else 0.0
                        if (rel_diff - prev_rel_diff) <= WATERFALL_ACCEL_THRESHOLD: is_waterfall = True
                
                if is_wave_downtrend:
                    term_tag_raw = "[高点降低!撤退]"
                    term_tag_col = f"{C_CYAN}[高点降低!撤退]{C_RESET}"
                elif is_wave_breakout:
                    term_tag_raw = "[突破前高!主升]"
                    term_tag_col = f"{C_RED}[突破前高!主升]{C_RESET}"

                clean_name = STOCK_DICT.get(s_id, s_id).strip().replace("💼", "")
                is_fav = clean_name in FAVORITES
                
                r_cols = []
                name_str_raw = clean_name
                name_str_col = f"{C_CYAN}{name_str_raw}{C_RESET}" if is_fav and FAV_STYLE == "name" else name_str_raw
                r_cols.append(align_cell(name_str_col, name_str_raw, columns_def[0][1], columns_def[0][2]))

                base_str = format_num(b_price)
                r_cols.append(align_cell(base_str, base_str, columns_def[1][1], columns_def[1][2]))
                
                curr_str = format_num(c_price)
                r_cols.append(align_cell(curr_str, curr_str, columns_def[2][1], columns_def[2][2]))
                
                diff_str_raw = f"{diff_percent:+.1f}%"
                diff_str_col = f"{get_color(diff_percent)}{diff_str_raw}{C_RESET}" if COLOR_PERCENT and diff_percent != 0 else diff_str_raw
                r_cols.append(align_cell(diff_str_col, diff_str_raw, columns_def[3][1], columns_def[3][2]))

                col_idx = 4
                if SHOW_EXTREMES:
                    ext_str = f"{min_pct_val:.0f}/{max_pct_val:+.0f}"
                    r_cols.append(align_cell(ext_str, ext_str, columns_def[col_idx][1], columns_def[col_idx][2]))
                    col_idx += 1
                
                if SHOW_WIN_RATIO:
                    ratio_str_raw = f"{cum_score:+d}({con_score:+d})"
                    ratio_str_col = f"{cum_score:+d}({get_color(con_score)}{con_score:+d}{C_RESET})" if con_score != 0 else ratio_str_raw
                    r_cols.append(align_cell(ratio_str_col, ratio_str_raw, columns_def[col_idx][1], columns_def[col_idx][2]))
                    col_idx += 1

                if SHOW_REL_DIFF:
                    rel_str_raw = f"{rel_diff:+.1f}%"
                    rel_str_col = f"{get_color(rel_diff)}{rel_str_raw}{C_RESET}" if COLOR_REL and rel_diff != 0 else rel_str_raw
                    r_cols.append(align_cell(rel_str_col, rel_str_raw, columns_def[col_idx][1], columns_def[col_idx][2]))
                    col_idx += 1

                if SHOW_AVG_DIFF:
                    avg_str_raw = f"{avg_percent:+.1f}%"
                    avg_str_col = f"{get_color(avg_percent)}{avg_str_raw}{C_RESET}" if COLOR_AVG and avg_percent != 0 else avg_str_raw
                    r_cols.append(align_cell(avg_str_col, avg_str_raw, columns_def[col_idx][1], columns_def[col_idx][2]))
                    col_idx += 1

                if SHOW_RECENT_DIFF:
                    rec_str_raw = f"{recent_diff:+.1f}%"
                    rec_str_col = f"{get_color(recent_diff)}{rec_str_raw}{C_RESET}" if COLOR_RECENT and recent_diff != 0 else rec_str_raw
                    r_cols.append(align_cell(rec_str_col, rec_str_raw, columns_def[col_idx][1], columns_def[col_idx][2]))
                    col_idx += 1

                if SHOW_CUM_DIFF:
                    cum_str_raw = f"{cum_diff:+.1f}%"
                    cum_str_col = f"{get_color(cum_diff)}{cum_str_raw}{C_RESET}" if COLOR_CUM and cum_diff != 0 else cum_str_raw
                    r_cols.append(align_cell(cum_str_col, cum_str_raw, columns_def[col_idx][1], columns_def[col_idx][2]))
                    col_idx += 1
                
                bg_color = None
                if is_wave_downtrend: bg_color = C_BG_ESCAPE
                elif is_wave_breakout: bg_color = C_BG_ALERT
                elif is_smart_alert: bg_color = C_BG_ALERT
                elif is_escape_top: bg_color = C_BG_ESCAPE
                elif is_waterfall: bg_color = C_BG_WATERFALL
                elif is_death_cross: bg_color = C_BG_DEATH
                elif is_predict_rebound: bg_color = C_BG_REBOUND
                elif is_predict_cross: bg_color = C_BG_CROSS
                elif is_predict_accel: bg_color = C_BG_ACCEL
                elif is_pullback_rebound: bg_color = C_BG_REBOUND 
                elif is_fav and FAV_STYLE == "bg": bg_color = C_BG_STYLE

                if bg_color:
                    clean_row = [ANSI_ESCAPE.sub('', c) for c in r_cols]
                    line_str_raw = " | ".join(clean_row)
                    if SHOW_PREDICT_TAG:
                        p_col = align_cell(term_tag_raw, term_tag_raw, columns_def[-1][1], columns_def[-1][2])
                        line_str_raw += f" | {p_col}"
                    term_line = f"{bg_color}| {line_str_raw} |{C_RESET}"
                else:
                    line_str_col = " | ".join(r_cols)
                    if SHOW_PREDICT_TAG:
                        tag_col = term_tag_col if term_tag_col else term_tag_raw
                        p_col = align_cell(tag_col, term_tag_raw, columns_def[-1][1], columns_def[-1][2])
                        line_str_col += f" | {p_col}"
                    term_line = f"| {line_str_col} |"

                # ====================================================
                # 🎯 TG 推送标签绝对优先级组装
                # ====================================================
                if is_wave_downtrend: tg_alert = "🚨[高点降低!撤退]"
                elif is_wave_breakout: tg_alert = "🚀[突破前高!主升]"
                elif is_smart_alert: tg_alert = "🔥[强势连涨]"
                elif is_escape_top: tg_alert = "🚨[高位砸盘]"
                elif is_waterfall: tg_alert = "🟤[断崖暴跌]"
                elif is_death_cross: tg_alert = "🧊[由涨转跌]"
                elif is_predict_rebound: tg_alert = "🟢[确认抄底]"
                elif is_predict_cross: tg_alert = "📈[止跌回升]"
                elif is_predict_accel: tg_alert = "⚡[突然飙升]"
                
                if tg_alert == "":
                    if "[龙回头" in term_tag_raw: tg_alert = "🐉[洗盘结束/龙回头]"
                    elif "[确认抄底]" in term_tag_raw: tg_alert = "🟢[确认抄底]"
                    elif "距反弹差" in term_tag_raw or "[飞刀" in term_tag_raw: tg_alert = "🔪[飞刀暴跌]"
                    elif "[极高随时崩" in term_tag_raw: tg_alert = "🚨[极高随时崩]"
                    elif "[涨到头了]" in term_tag_raw: tg_alert = "⚠️[涨到头了]"
                    elif "[深坑建仓区]" in term_tag_raw: tg_alert = "🛒[深坑建仓区]"

                fav_icon = "⭐" if is_fav else "🔸"
                tg_line = f"{fav_icon} <b>{clean_name}</b> {tg_alert}\n"
                tg_data = f"<code>现价:{str(int(c_price)):<5} | 总涨:{diff_percent:+.1f}%"
                if SHOW_REL_DIFF: tg_data += f" | 单轮:{rel_diff:+.1f}%"
                if SHOW_EXTREMES: tg_data += f" | 极值:{min_pct_val:.0f}/{max_pct_val:+.0f}"
                tg_data += "</code>\n"
                tg_line += tg_data

                results_list.append({
                    "name": clean_name, "is_fav": is_fav, "ratio_cum": cum_score, "ratio_con": con_score,
                    "sort_val": con_score if RATIO_SORT_BY == "consecutive" else cum_score,
                    "term_line": term_line, "tg_line": tg_line,
                    "c_price": c_price, "diff_percent": diff_percent, "rel_diff": rel_diff,
                    "cum_score": cum_score, "con_score": con_score, "avg_percent": avg_percent,
                    "recent_diff": recent_diff, "cum_diff": cum_diff, "term_tag_raw": term_tag_raw,
                    "is_hidden": is_hidden
                })

            results_list.sort(key=lambda x: (0 if FAV_PIN_TOP and x["is_fav"] else 1, -x["sort_val"]))
            cross_fav, cross_zero = False, False
            displayed_count = 0
            
            for idx, item in enumerate(results_list):
                # 🎯 核心逻辑：如果是低价被过滤的股票，直接跳过 UI 渲染和 TG 推送，但数据已被保留在结果列表中供 CSV 使用
                if item.get("is_hidden"): 
                    continue
                
                if FAV_PIN_TOP and not item["is_fav"] and not cross_fav:
                    if not HEADLESS_MODE and displayed_count > 0: print(f"{C_CYAN}{sep_line}{C_RESET}")
                    cross_fav = True
                    tg_msg += f"〰️〰️〰️ <b>自选股分割线</b> 〰️〰️〰️\n"

                if not (FAV_PIN_TOP and item["is_fav"]) and item["sort_val"] < 0 and not cross_zero:
                    if not HEADLESS_MODE and displayed_count > 0: print(sep_line)
                    cross_zero = True
                    tg_msg += f"〰️〰️〰️ <b>涨跌分界线</b> 〰️〰️〰️\n"
                
                if not HEADLESS_MODE: print(item["term_line"])
                tg_msg += item["tg_line"]
                displayed_count += 1

            if not HEADLESS_MODE:
                print(f"{'=' * t_width}")
                print(f" [🌊新增战法：道氏波浪形态追踪]")
                print(f" 🚀 {C_RED}[突破前高!主升]{C_RESET} : 突破上一轮波峰！主升浪确认，有底仓死拿，无底仓追涨！")
                print(f" 🚨 {C_CYAN}[高点降低!撤退]{C_RESET} : 反弹未能突破上一轮波峰！主力撤退，逢高必空/清仓！")
                print(f"{'-' * t_width}")
                print(f" [🐉进阶战法：龙回头与洗盘判断]")
                print(f" 前提：今天曾大涨过 {PULLBACK_PEAK_MIN}%，随后被主力砸盘回撤超过 {PULLBACK_DROP_PCT}%。此时：")
                print(f" {C_YELLOW}[主力洗盘中]{C_RESET} : 还在跌，忍住别买。")
                print(f" {C_GREEN}[龙回头上车]{C_RESET} : 洗盘结束！反弹超过 {PULLBACK_REBOUND_PCT}%，第二波主升浪开启！")
                print(f"{'-' * t_width}")
                print(f" [🪤防飞刀与大资金建仓图鉴]")
                print(f" {C_YELLOW}[飞刀暴跌]{C_RESET}     : 只要这一分钟还在下跌，坚决不碰！")
                print(f" {C_YELLOW}[深坑建仓区]{C_RESET}   : (大资金专属) 跌穿-40%且处于横盘摩擦区，适合左侧轻仓吸筹！")
                print(f" {C_YELLOW}[距反弹差 X%]{C_RESET}  : 刚止跌，但反弹没超过 {REBOUND_CONFIRM_PCT}%，再等等！")
                print(f" {C_GREEN}[确认抄底]{C_RESET}     : 满足反弹幅度 或 满足 {REBOUND_CONFIRM_WINS} 连胜，且正在上涨，进场！")
                print(f"{'=' * t_width}")
                print(" [做多提示]: 🔴红底(强势连涨) | 🟢绿底(跌透反弹/龙回头) | 📈紫底(止跌回升) | ⚡黄底(突然飙升)")
                print(" [做空提示]: 🟦蓝底(高位砸盘) | 🟤灰底(断崖暴跌) | 🧊青底(由涨转跌)")
                print(f"{'=' * t_width}")
                        
            if ENABLE_DATA_LOGGER and is_valid_update:
                csv_path = os.path.join(SCRIPT_DIR, LOG_FILE_NAME)
                file_exists = os.path.exists(csv_path)
                try:
                    with open(csv_path, mode='a', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["时间", "标的名称", "现价", "总涨跌", "单轮涨跌", "累积净胜", "当前连胜", f"{MICRO_COUNT}轮超短", f"{RECENT_COUNT}轮短线", f"{CUM_COUNT}轮长线", "趋势预警"])
                        for item in results_list:
                            writer.writerow([
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                item["name"],
                                item["c_price"],
                                f"{item['diff_percent']:.2f}%",
                                f"{item['rel_diff']:.2f}%",
                                item["cum_score"],
                                item["con_score"],
                                f"{item['avg_percent']:.2f}%",
                                f"{item['recent_diff']:.2f}%",
                                f"{item['cum_diff']:.2f}%",
                                item["term_tag_raw"]
                            ])
                except Exception as log_e:
                    if HEADLESS_MODE: print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 数据历史日志写入失败: {log_e}")

            if ENABLE_TG_PUSH:
                if HEADLESS_MODE: print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 发现行情变动，正在推送 Telegram...")
                send_tg_msg(tg_msg)
            elif ENABLE_TG_PUSH and not is_valid_update and HEADLESS_MODE:
                if time.time() % 3600 < POLL_INTERVAL:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 触发心跳检测，向 TG 推送存活报告...")
                    send_tg_msg("🤖 【幻想屋雷达】心跳检测：后台守护进程运行正常，大盘目前无变动。")

            state["basePrices"], state["last_raw_prices"], state["last_valid_prices"] = basePrices, last_raw_prices, last_valid_prices
            state["last_rel_diff"], state["historyPct"], state["historyPrices"] = last_rel_diff, historyPct, historyPrices
            state["cumulative_wins"], state["consecutive_wins"], state["daily_max_pct"], state["daily_min_pct"] = cumulative_wins, consecutive_wins, daily_max_pct, daily_min_pct
            
            state["wave_peaks"], state["wave_tracking"] = wave_peaks, wave_tracking
            
            save_state(state)

            server_time_ms = data.get("time", 0)
            next_trend_time_ms = data.get("data", {}).get("nextTrendTime", 0)
            if next_trend_time_ms > 0 and server_time_ms > 0:
                wait_ms = next_trend_time_ms - server_time_ms
                if wait_ms > 0:
                    sleep_time = (wait_ms / 1000.0) + 0.5
                    if HEADLESS_MODE: print(f"[{datetime.now().strftime('%H:%M:%S')}] 等待下一轮服务器跳动: {sleep_time:.1f} 秒")
                    safe_sleep(sleep_time)
                    continue
            safe_sleep(POLL_INTERVAL)

    except KeyboardInterrupt: 
        if not HEADLESS_MODE: print(f"\n{C_GREEN}✅ 监控安全关闭。{C_RESET}")
    except Exception as e:
        if HEADLESS_MODE: print(f"[{datetime.now().strftime('%H:%M:%S')}] 💥 致命错误，进程崩溃: {e}")

if __name__ == "__main__": main()