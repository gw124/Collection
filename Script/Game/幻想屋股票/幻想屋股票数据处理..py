import pandas as pd
import os
import requests
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from datetime import timedelta, datetime

# ================= 配置区域 =================

# --- 1. 数据处理参数 ---
RETENTION_DAYS = 7        # 数据保留天数：设置为 7，仅处理最近 7 天，设为 0 则处理全量
CHART_SIZE_WIDTH = 30      # 图表宽度：单位英寸，10 是宽屏标准
CHART_SIZE_HEIGHT = 10     # 图表高度：单位英寸，5 是较优高度

# --- 2. 存储与合并开关 ---
MERGE_DOCS = True         # 文档合并：True 将历史数据写入同一个大 CSV，False 按天拆分多个 CSV
MERGE_CHARTS = False      # 走势图合并：True 将指定天数内的走势连成一张大图，False 按天拆分独立绘图
CLEAR_OLD_CHARTS = False  # 清理旧图：True 每次运行前清空走势图文件夹，False 保留历史图片

# --- 3. Telegram 推送配置 ---
TG_TOKEN = "8348595310:AAHt5YAYIn_e7g-BB9ZSvsHKxbXzjkeklPo"
TG_CHAT_ID = "-5198807667"

# --- 4. 推送控制开关 ---
PUSH_DOCS = False             # 是否推送 CSV 文档 (按天拆分模式下会推送昨日文档)
PUSH_PREV_DAY_ONLY = True    # 是否推送“前一日”走势图 (通常配合 06:00 定时使用)
PUSH_CURRENT_CHART = True     # 是否推送“今日/最新”走势图 (06:05 后运行自动推送)
PUSH_ALL_CHARTS = False       # 是否推送所有走势图 (慎用，可能触发频率限制)

# --- 5. 【新增】指定推送白名单 ---
ENABLE_TARGET_PUSH = False     # 白名单总开关：True 启用下方名单，False 临时关闭(变回全量推送)
PUSH_TARGET_STOCKS = ["幻影物流", "珊瑚烘焙", "翡翠烘焙", "黎明酒馆", "风铃酒馆"]

# ===========================================

def send_tg_msg(text, file_path=None):
    """发送消息或文件到 Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/send{'Document' if file_path else 'Message'}"
        data = {'chat_id': TG_CHAT_ID, 'caption': text} if file_path else {'chat_id': TG_CHAT_ID, 'text': text}
        files = {'document': open(file_path, 'rb')} if file_path else None
        requests.post(url, data=data, files=files, timeout=10)
    except Exception as e:
        print(f"推送失败: {e}")

def get_font_prop():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_dir, 'SourceHanSansSC-Regular.otf')
    return fm.FontProperties(fname=font_path) if os.path.exists(font_path) else None

my_font = get_font_prop()

def draw_and_save_chart(group, stock_name, title_date_str, chart_path):
    """独立的绘图函数，包含防文字遮挡逻辑"""
    base_price = group.iloc[0]['现价']
    group['pct'] = (group['现价'] - base_price) / base_price * 100
    
    plt.figure(figsize=(CHART_SIZE_WIDTH, CHART_SIZE_HEIGHT), dpi=120)
    plt.style.use('seaborn-v0_8-whitegrid')
    line_color = '#e74c3c' if group.iloc[-1]['pct'] >= 0 else '#2ecc71'
    plt.plot(group['时间'], group['pct'], color=line_color, linewidth=1.5, marker='o', markersize=2)
    plt.axhline(0, color='gray', linestyle='--', alpha=0.5)
    
    bg_bbox = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8)
    plt.text(group['时间'].iloc[0], 0, f" Base: {base_price:.2f}", color='gray', va='top', ha='left', fontweight='bold', fontsize=9, bbox=bg_bbox)

    max_row = group.loc[group['现价'].idxmax()]
    min_row = group.loc[group['现价'].idxmin()]
    
    plt.annotate(f"Top: {max_row['现价']:.2f} ({max_row['pct']:+.2f}%)", xy=(max_row['时间'], max_row['pct']), xytext=(0, 12), textcoords='offset points', ha='center', color='red', fontweight='bold', fontsize=9, bbox=bg_bbox)
    plt.annotate(f"Bottom: {min_row['现价']:.2f} ({min_row['pct']:+.2f}%)", xy=(min_row['时间'], min_row['pct']), xytext=(0, -15), textcoords='offset points', ha='center', color='green', fontweight='bold', fontsize=9, bbox=bg_bbox)
    plt.annotate(f"Now: {group.iloc[-1]['现价']:.2f} ({group.iloc[-1]['pct']:+.2f}%)", xy=(group.iloc[-1]['时间'], group.iloc[-1]['pct']), xytext=(8, 10), textcoords='offset points', ha='left', color=line_color, fontweight='bold', fontsize=10, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=line_color, lw=1, alpha=0.9))

    if my_font:
        plt.title(f"{stock_name} ({title_date_str}) - 涨跌幅监控", fontproperties=my_font, fontsize=14)
        plt.ylabel("涨跌幅 (%)", fontproperties=my_font)
    else:
        plt.title(f"{stock_name} ({title_date_str}) - Monitor", fontsize=14)
        
    plt.xticks(rotation=30, fontsize=9)
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, 'hxw_stock_data.csv')
    if not os.path.exists(input_file): return

    df = pd.read_csv(input_file, encoding='utf-8-sig', on_bad_lines='skip').drop_duplicates()
    df['时间'] = pd.to_datetime(df['时间'], errors='coerce')
    df = df.dropna(subset=['标的名称', '现价'])
    
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
        "1025-2028": "琥珀烘焙", "1020-2005": "风铃酒馆", "1011-2003": "夏威汽车", 
    }
    df['标的名称'] = df['标的名称'].map(STOCK_DICT).fillna(df['标的名称'])
    df['交易日期'] = (df['时间'] - timedelta(hours=6)).dt.date
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    current_time = datetime.now()
    
    data_folder = os.path.join(script_dir, '幻想屋股票数据')
    chart_folder = os.path.join(script_dir, '幻想屋股票走势图')
    os.makedirs(data_folder, exist_ok=True)
    os.makedirs(chart_folder, exist_ok=True)

    # ================= 1. 清理旧走势图 =================
    if CLEAR_OLD_CHARTS:
        for filename in os.listdir(chart_folder):
            file_path = os.path.join(chart_folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"清理文件失败 {file_path}: {e}")

    # ================= 2. 文档保存逻辑 =================
    for stock_name, stock_group in df.groupby('标的名称'):
        stock_group = stock_group.sort_values('时间')
        safe_name = "".join([c for c in str(stock_name) if c.isalnum() or c in (' ', '_', '-')]).strip()
        
        if MERGE_DOCS:
            stock_group.to_csv(os.path.join(data_folder, f"{safe_name}.csv"), index=False, encoding='utf-8-sig')
        else:
            for trade_date, daily_group in stock_group.groupby('交易日期'):
                csv_path = os.path.join(data_folder, f"{safe_name}_{trade_date}.csv")
                daily_group.to_csv(csv_path, index=False, encoding='utf-8-sig')
                if PUSH_DOCS and trade_date == yesterday:
                    send_tg_msg(f"昨日文档: {safe_name}", file_path=csv_path)

    # ================= 3. 走势图生成与推送逻辑 =================
    if RETENTION_DAYS > 0:
        cutoff_date = df['交易日期'].max() - timedelta(days=RETENTION_DAYS - 1)
        df_chart = df[df['交易日期'] >= cutoff_date]
    else:
        df_chart = df

    if MERGE_CHARTS:
        # --- 合并走势图模式 ---
        for stock_name, group in df_chart.groupby('标的名称'):
            group = group.sort_values('时间')
            safe_name = "".join([c for c in str(stock_name) if c.isalnum() or c in (' ', '_', '-')]).strip()
            chart_path = os.path.join(chart_folder, f"{safe_name}_综合走势.png")
            date_label = f"最近{RETENTION_DAYS}天" if RETENTION_DAYS > 0 else "全量历史"
            
            draw_and_save_chart(group, stock_name, date_label, chart_path)
            
            # 检查白名单开关逻辑
            is_target = (not ENABLE_TARGET_PUSH) or (not PUSH_TARGET_STOCKS) or (stock_name in PUSH_TARGET_STOCKS)
            if is_target:
                if PUSH_CURRENT_CHART and (current_time.hour > 6 or (current_time.hour == 6 and current_time.minute > 5)):
                    send_tg_msg(f"综合走势监控: {stock_name} ({date_label})", file_path=chart_path)
                elif PUSH_ALL_CHARTS:
                    send_tg_msg(f"全景图: {stock_name}", file_path=chart_path)

    else:
        # --- 按天拆分模式 ---
        for (stock_name, trade_date), group in df_chart.groupby(['标的名称', '交易日期']):
            group = group.sort_values('时间')
            safe_name = "".join([c for c in str(stock_name) if c.isalnum() or c in (' ', '_', '-')]).strip()
            chart_path = os.path.join(chart_folder, f"{safe_name}_{trade_date}.png")
            
            draw_and_save_chart(group, stock_name, str(trade_date), chart_path)
            
            # 检查白名单开关逻辑
            is_target = (not ENABLE_TARGET_PUSH) or (not PUSH_TARGET_STOCKS) or (stock_name in PUSH_TARGET_STOCKS)
            if is_target:
                if PUSH_CURRENT_CHART and trade_date == today and (current_time.hour > 6 or (current_time.hour == 6 and current_time.minute > 5)):
                    send_tg_msg(f"今日实时监控: {stock_name} (最新)", file_path=chart_path)
                if PUSH_PREV_DAY_ONLY and trade_date == yesterday:
                    send_tg_msg(f"昨日回顾: {stock_name} ({trade_date})", file_path=chart_path)
                if PUSH_ALL_CHARTS and trade_date != today:
                    send_tg_msg(f"历史数据: {stock_name} ({trade_date})", file_path=chart_path)

    print("同步处理完成。")

if __name__ == "__main__":
    main()