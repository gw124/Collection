import sys
import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.colors  
import os
import json
import requests
import urllib3
import shutil
from datetime import datetime, timedelta

# 关闭 requests 的 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= API 抓取配置 (硬编码，防止前端泄漏) =================
API_URL = "https://wgsh.hxwgame.cn/dish1/GetStockInfo"
API_TOKEN = "1dc16fb2-e2b7-4c37-8c9c-b65830f8b6be"

script_dir = os.path.dirname(os.path.abspath(__file__))
# 绝对物理隔离：后台只会读写这个文件，不污染其他脚本的数据
CSV_API_TARGET = os.path.join(script_dir, 'hxw_api_stock_data.csv')
STATUS_FILE = os.path.join(script_dir, 'api_status.json')
PREFS_FILE = os.path.join(script_dir, 'user_prefs.json')

def update_status(msg, is_error=False):
    """将后台抓取状态写入本地，供前端展示"""
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "time": (datetime.utcnow() + timedelta(hours=8)).strftime('%H:%M:%S'),
                "msg": msg,
                "error": is_error
            }, f, ensure_ascii=False)
    except Exception:
        pass

# ================= 🚀 核心一：24小时独立后台抓取进程 =================
def run_background_fetcher():
    print("🚀 后台数据抓取引擎已启动，脱离网页状态，正在 24 小时独立运行...")
    
    old_csv = os.path.join(script_dir, 'hxw_stock_data.csv')
    if not os.path.exists(CSV_API_TARGET) and os.path.exists(old_csv):
        try:
            shutil.copy(old_csv, CSV_API_TARGET)
            print("📦 成功将历史数据拷贝为 API 底座")
        except Exception as e:
            print(f"拷贝底座失败: {e}")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15",
        "Referer": "https://tmaservice.developer.toutiao.com/"
    }
    payload = {"platform": 1, "game": "p4", "token": API_TOKEN.strip()}
    
    while True:
        if API_URL.strip() and API_TOKEN.strip():
            try:
                res = requests.post(API_URL, json=payload, headers=headers, timeout=10, verify=False)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == 0:
                        stock_list = data.get("data", {}).get("list", [])
                        api_time_ms = data.get("time")
                        if api_time_ms:
                            current_time = datetime.utcfromtimestamp(api_time_ms / 1000.0) + timedelta(hours=8)
                        else:
                            current_time = datetime.utcnow() + timedelta(hours=8)
                        
                        new_rows = []
                        for item in stock_list:
                            name1 = item.get("name1")
                            name2 = item.get("name2")
                            price = item.get("price")
                            if name1 is not None and name2 is not None and price is not None:
                                new_rows.append({
                                    "时间": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "标的名称": f"{name1}-{name2}",
                                    "现价": price
                                })
                        
                        if new_rows:
                            new_df = pd.DataFrame(new_rows)
                            if os.path.exists(CSV_API_TARGET):
                                new_df.to_csv(CSV_API_TARGET, mode='a', header=False, index=False, encoding='utf-8')
                            else:
                                new_df.to_csv(CSV_API_TARGET, mode='w', header=True, index=False, encoding='utf-8-sig')
                            
                            update_status(f"成功入库 {len(new_rows)} 只股票最新价格", is_error=False)
                    else:
                        update_status(f"被游戏服务器拒绝: {data.get('msg', '未知')} (请检查Token)", is_error=True)
                else:
                    update_status(f"接口通信失败 HTTP {res.status_code}", is_error=True)
            except Exception as e:
                update_status(f"网络异常或连接超时: {str(e)}", is_error=True)
        
        # 动态智能读取前端设置的抓取频率 (最低保护为 5 秒)
        sleep_interval = 15
        try:
            if os.path.exists(PREFS_FILE):
                with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                    _pf = json.load(f)
                    sleep_interval = _pf.get("refresh_rate", 15)
        except Exception:
            pass
        
        time.sleep(max(5, sleep_interval))

# 【架构黑科技】：判断是 Docker 后台启动抓取，还是 Streamlit 渲染前端
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetcher":
        run_background_fetcher()
        sys.exit(0) 


# ================= 🚀 核心二：Streamlit 网页渲染前端 =================
st.set_page_config(page_title="幻想屋股票大屏", layout="wide", initial_sidebar_state="expanded")

# 注入自定义CSS：隐藏全屏按钮，并将侧边栏的股票名称按钮强制左对齐，使其看起来像一个标准的文字列表
st.markdown(
    """
    <style>
    [data-testid="stStatusWidget"] {visibility: hidden;}
    button[title="View fullscreen"] { display: none !important; }
    div[data-testid="stSidebar"] div[data-testid="stButton"] button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding-left: 5px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("### 📈 幻想屋股票数据实时监控")

# 为配合高频抓取，将缓存生命周期下调至 2 秒
@st.cache_data(ttl=2)
def load_data():
    if not os.path.exists(CSV_API_TARGET):
        return None
    try:
        df = pd.read_csv(CSV_API_TARGET, encoding='utf-8-sig', on_bad_lines='skip').drop_duplicates()
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
        df['标的名称'] = df['标的名称'].map(STOCK_DICT).fillna(df['标的名称'])
        df = df.sort_values('时间')
        return df
    except Exception:
        return None

_temp_df = load_data()
all_stocks = _temp_df['标的名称'].unique().tolist() if _temp_df is not None else []

default_prefs = {
    "stocks": ["幻影物流", "星辰地产", "黎明餐馆"],
    "base_hour": 6,
    "filter_delisted": True,
    "delisted_threshold": 30,
    "history_days": 7,
    "show_extrema": True,
    "auto_refresh": True,
    "refresh_rate": 15,  # 默认加快到 15 秒
    "filter_low_price": False,
    "low_price_threshold": 10000
}

if os.path.exists(PREFS_FILE):
    try:
        with open(PREFS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k in default_prefs.keys():
                    if k in data:
                        default_prefs[k] = data[k]
    except Exception:
        pass

valid_saved_stocks = [s for s in default_prefs["stocks"] if s in all_stocks]
default_prefs["stocks"] = valid_saved_stocks if valid_saved_stocks else (all_stocks[:1] if all_stocks else [])

state_mapping = {
    "ui_stocks": "stocks",
    "ui_base_hour": "base_hour",
    "ui_filter_delisted": "filter_delisted",
    "ui_delisted_threshold": "delisted_threshold",
    "ui_history_days": "history_days",
    "ui_show_extrema": "show_extrema",
    "ui_auto_refresh": "auto_refresh",
    "ui_refresh_rate": "refresh_rate",
    "ui_filter_low_price": "filter_low_price",
    "ui_low_price_threshold": "low_price_threshold"
}

for ui_key, pref_key in state_mapping.items():
    if ui_key not in st.session_state:
        st.session_state[ui_key] = default_prefs[pref_key]

def save_prefs():
    current_prefs = {
        "stocks": st.session_state.ui_stocks,
        "base_hour": st.session_state.ui_base_hour,
        "filter_delisted": st.session_state.ui_filter_delisted,
        "delisted_threshold": st.session_state.ui_delisted_threshold,
        "history_days": st.session_state.ui_history_days,
        "show_extrema": st.session_state.ui_show_extrema,
        "auto_refresh": st.session_state.ui_auto_refresh,
        "refresh_rate": st.session_state.ui_refresh_rate,
        "filter_low_price": st.session_state.ui_filter_low_price,
        "low_price_threshold": st.session_state.ui_low_price_threshold
    }
    try:
        with open(PREFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_prefs, f, ensure_ascii=False)
    except Exception:
        pass

# ================= 提取最新单价并构建名称映射 =================
latest_prices_dict = {}
if _temp_df is not None and not _temp_df.empty:
    latest_prices_dict = _temp_df.drop_duplicates(subset=['标的名称'], keep='last').set_index('标的名称')['现价'].to_dict()

def format_stock_label(stock_name):
    price = latest_prices_dict.get(stock_name)
    if price is not None:
        return f"{stock_name} (¥{price:.2f})"
    return stock_name

# ================= 停牌/退市数据动态过滤 & 低价过滤 =================
active_stocks = all_stocks.copy()
if _temp_df is not None and not _temp_df.empty:
    if st.session_state.ui_filter_delisted:
        latest_times = _temp_df.groupby('标的名称')['时间'].max()
        global_max_time = latest_times.max()
        time_diffs = (global_max_time - latest_times).dt.total_seconds() / 60.0
        
        filtered_active = latest_times[time_diffs <= st.session_state.ui_delisted_threshold].index.tolist()
        active_stocks = [s for s in active_stocks if s in filtered_active]
        
    if st.session_state.ui_filter_low_price:
        threshold = st.session_state.ui_low_price_threshold
        filtered_price_active = [s for s, p in latest_prices_dict.items() if p >= threshold]
        active_stocks = [s for s in active_stocks if s in filtered_price_active]

current_valid_stocks = [s for s in st.session_state.ui_stocks if s in active_stocks]
if current_valid_stocks != st.session_state.ui_stocks:
    st.session_state.ui_stocks = current_valid_stocks

# ================= 侧边栏：自定义交互式股票列表 =================
st.sidebar.markdown("#### 🖱️ 股票选择面板")
st.sidebar.caption("👉 **单选**：直接点击股票名称\n👉 **多选**：勾选前面复选框")

def handle_check(s):
    is_checked = st.session_state[f"chk_{s}"]
    if is_checked and s not in st.session_state.ui_stocks:
        st.session_state.ui_stocks.append(s)
    elif not is_checked and s in st.session_state.ui_stocks:
        st.session_state.ui_stocks.remove(s)
    save_prefs()

def handle_click(s):
    st.session_state.ui_stocks = [s]
    save_prefs()

def select_all():
    st.session_state.ui_stocks = active_stocks.copy()
    save_prefs()

def clear_all():
    st.session_state.ui_stocks = []
    save_prefs()

for stock in active_stocks:
    st.session_state[f"chk_{stock}"] = (stock in st.session_state.ui_stocks)

col_a, col_b = st.sidebar.columns(2)
col_a.button("✅ 全选", on_click=select_all, use_container_width=True)
col_b.button("🗑️ 清空", on_click=clear_all, use_container_width=True)

with st.sidebar.container(height=450):
    for stock in active_stocks:
        col1, col2 = st.columns([0.15, 0.85])
        with col1:
            st.checkbox(" ", key=f"chk_{stock}", on_change=handle_check, args=(stock,), label_visibility="collapsed")
        with col2:
            st.button(format_stock_label(stock), key=f"btn_{stock}", on_click=handle_click, args=(stock,), type="tertiary", use_container_width=True)

st.sidebar.markdown("---")

# ================= 其他参数配置 =================
st.sidebar.markdown("#### ⚙️ 监控设置")

st.sidebar.toggle("🚫 过滤停牌/退市股票", key="ui_filter_delisted", on_change=save_prefs)
if st.session_state.ui_filter_delisted:
    st.sidebar.number_input("未更新剔除时间 (分钟)：", min_value=1, max_value=1440, step=1, key="ui_delisted_threshold", on_change=save_prefs)

st.sidebar.toggle("💰 过滤低价股票", key="ui_filter_low_price", on_change=save_prefs)
if st.session_state.ui_filter_low_price:
    st.sidebar.number_input("最低价格阈值：", min_value=0, max_value=9999999, step=1000, key="ui_low_price_threshold", on_change=save_prefs)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 📊 图表显示参数")

st.sidebar.number_input("历史显示天数：", min_value=1, max_value=9999, step=1, key="ui_history_days", on_change=save_prefs, help="设为 1 天即为当日日内监控，设为更大数字则显示历史累计趋势。")
st.sidebar.number_input("日内基准结算时间 (点)：", min_value=0, max_value=23, step=1, key="ui_base_hour", on_change=save_prefs)
st.sidebar.toggle("📌 显示最高/最低点标注", key="ui_show_extrema", on_change=save_prefs)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🔄 数据刷新控制")
st.sidebar.toggle("前端走势图自动刷新", key="ui_auto_refresh", on_change=save_prefs, help="关闭此开关可冻结图表，方便您分析走势。后台程序绝不受此影响，仍会持续记录数据。")
st.sidebar.number_input("⏱️ 更新与抓取频率 (秒)", min_value=5, max_value=300, step=5, key="ui_refresh_rate", on_change=save_prefs, help="调节此项可实现后台与前端双端变频。建议 10-15 秒。")

if not st.session_state.ui_stocks:
    st.info("👈 请在左侧面板选择或勾选至少一只股票进行监控。")
    st.info("🕒 初次部署或刚开启服务时，可能需要等待 1 分钟让后台完成首次抓取。")
    st.stop()


# 动态计算刷新频率：如果开启刷新则传入对应秒数，如果暂停则传 None (停止刷新)
refresh_interval = st.session_state.ui_refresh_rate if st.session_state.ui_auto_refresh else None

# ================= 核心渲染引擎 =================
@st.fragment(run_every=refresh_interval)
def render_main_dashboard():
    df = load_data()
    if df is None or df.empty:
        st.warning("🕒 正在等待后台引擎拉取首批数据...若长时间无反应，请检查 Token 是否有效。")
        return

    selected_stocks = st.session_state.ui_stocks
    base_hour = st.session_state.ui_base_hour
    history_days = st.session_state.ui_history_days
    show_extrema = st.session_state.ui_show_extrema 

    df_processed = df.copy()
    df_processed['交易日期'] = (df_processed['时间'] - timedelta(hours=base_hour)).dt.date

    latest_trade_day = df_processed['交易日期'].max()
    cutoff_date = latest_trade_day - timedelta(days=history_days - 1)
    filtered_df = df_processed[df_processed['交易日期'] >= cutoff_date].copy()
    
    if history_days == 1:
        st.subheader(f"📅 当前视图：{latest_trade_day} 日内分时监控 ({base_hour:02d}:00 基准)")
    else:
        st.subheader(f"📅 当前视图：最近 {history_days} 天历史累计趋势 ({base_hour:02d}:00 基准)")

    plot_df = filtered_df.copy()
    if not plot_df.empty:
        base_prices = {}
        for stock in selected_stocks:
            stock_data = plot_df[plot_df['标的名称'] == stock]
            if stock_data.empty: continue
            
            # 直接取本视图下，该股票最左侧(最早)出现的价格作为 0% 基准
            base_prices[stock] = stock_data.iloc[0]['现价']

        plot_df['Base'] = plot_df['标的名称'].map(base_prices)
        plot_df['涨跌幅(%)'] = (plot_df['现价'] - plot_df['Base']) / plot_df['Base'] * 100
    else:
        st.warning("⚠️ 当前筛选的时间范围内没有股票数据！")
        return

    fig = go.Figure()
    color_palette = plotly.colors.qualitative.Plotly

    for i, stock in enumerate(selected_stocks):
        group = plot_df[plot_df['标的名称'] == stock]
        if group.empty: continue

        if len(selected_stocks) == 1:
            line_color = '#e74c3c' if group.iloc[-1]['涨跌幅(%)'] >= 0 else '#2ecc71'
        else:
            line_color = color_palette[i % len(color_palette)]

        # 用标准 SVG 渲染，加入图例分组
        fig.add_trace(go.Scatter(
            uid=stock,
            x=group['时间'],
            y=group['涨跌幅(%)'],
            mode='lines',
            name=stock,
            legendgroup=stock, 
            line=dict(width=1.5, color=line_color),
            hovertemplate="<b>%{customdata[1]}</b><br>现价: %{customdata[0]:.2f}<br>涨跌幅: %{y:.2f}%<extra></extra>",
            customdata=group[['现价', '标的名称']]
        ))

        if show_extrema and len(group) > 1:
            max_idx = group['涨跌幅(%)'].idxmax()
            min_idx = group['涨跌幅(%)'].idxmin()
            
            max_row = group.loc[max_idx]
            min_row = group.loc[min_idx]

            fig.add_trace(go.Scatter(
                uid=f"{stock}_max",
                x=[max_row['时间']],
                y=[max_row['涨跌幅(%)']],
                mode='markers+text',
                legendgroup=stock, 
                marker=dict(size=6, color=line_color, symbol='circle'),
                text=[f"▲ 最高 {max_row['涨跌幅(%)']:.2f}%"],
                textposition="top center",
                textfont=dict(size=10, color=line_color),
                showlegend=False,
                hoverinfo='skip'
            ))

            fig.add_trace(go.Scatter(
                uid=f"{stock}_min",
                x=[min_row['时间']],
                y=[min_row['涨跌幅(%)']],
                mode='markers+text',
                legendgroup=stock, 
                marker=dict(size=6, color=line_color, symbol='circle'),
                text=[f"▼ 最低 {min_row['涨跌幅(%)']:.2f}%"],
                textposition="bottom center",
                textfont=dict(size=10, color=line_color),
                showlegend=False,
                hoverinfo='skip'
            ))

        last_row = group.iloc[-1]
        fig.add_trace(go.Scatter(
            uid=f"{stock}_label",
            x=[last_row['时间']],
            y=[last_row['涨跌幅(%)']],
            mode='text',
            legendgroup=stock, 
            text=[f" {last_row['标的名称'] if len(selected_stocks) > 1 else ''} <b>{last_row['现价']:.2f}</b> ({last_row['涨跌幅(%)']:+.2f}%)"],
            textposition="middle right",
            textfont=dict(size=11, color=line_color),
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        template="simple_white",  
        height=550,                
        hovermode="x unified",    
        dragmode="pan",         
        uirevision="live_dashboard", 
        spikedistance=-1,    
        hoverdistance=-1,
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.25)", 
            bordercolor="rgba(255, 255, 255, 0)",
            font=dict(color="#111111", size=13)
        ),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor='#f5f5f5',  
            gridwidth=1,
            tickformat="%m-%d %H:%M",
            linewidth=1,
            linecolor='#e0e0e0',  
            zeroline=False,
            showspikes=True,
            spikemode='across',
            spikedash='dash',
            spikecolor='#999999',
            spikethickness=1
        ),
        yaxis=dict(
            title=dict(text="累计涨跌幅 (%)", font=dict(size=12, color="#666666")),
            showgrid=True,
            gridcolor='#f5f5f5',
            gridwidth=1,
            linewidth=0,          
            zeroline=False,
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',  
            spikedash='dash',
            spikecolor='#999999',
            spikethickness=1
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title=""
        ),
        margin=dict(l=80, r=220, t=40, b=30)  
    )

    fig.add_hline(y=0, line_dash="dash", line_color="#cccccc", line_width=1, opacity=0.6)
    
    st.plotly_chart(fig, use_container_width=True, theme=None, config={
        'displaylogo': False, 
        'scrollZoom': True,
        'displayModeBar': True  
    })

    # === 可视化读取后台状态 ===
    status_msg = "暂无数据"
    status_color = "gray"
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                s_data = json.load(f)
                status_msg = f"{s_data.get('time', '')} | {s_data.get('msg', '')}"
                status_color = "red" if s_data.get('error') else "green"
        except Exception:
            pass

    st.markdown(
        f"<div style='font-size: 13px; color: {status_color};'>🔌 后台抓取引擎状态：{status_msg} (设定的轮询频率: {st.session_state.ui_refresh_rate}秒)</div>",
        unsafe_allow_html=True
    )
    
    if not st.session_state.ui_auto_refresh:
        st.info("⏸️ **图表已冻结**：当前前端不再自动拉取新走势，您可以安心缩放、隐藏分析走势。后台的 24 小时抓取进程依然在全速运转，重启开关即可查看最新数据。")

# 启动核心渲染
render_main_dashboard()