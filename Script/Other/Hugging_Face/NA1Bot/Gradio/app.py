#!/usr/bin/env python3
import os
import threading
import time
import gradio as gr
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from collections import deque
from datetime import datetime
import requests
from urllib.parse import unquote

# ============== 环境变量 ==============
PANEL_NA1_COOKIES = os.environ.get("PANEL_NA1_COOKIES", "")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
TG_API = os.environ.get("TG_API", "https://api.telegram.org")
PROJECT_URL = os.environ.get("PROJECT_URL", "")

# ============== 共享状态 ==============
worker_status = {
    "coins": 0, "checks": 0, "status": "waiting", "afk": False,
    "multiplier": 1, "active_users": 0, "session_coins": 0,
    "coins_per_minute": 1, "initial_coins": 0, "napoints": 0,
    "start_time": None, "keepalive": None
}
log_queue = deque(maxlen=100)

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_queue.append(line)

# ============== 保活 ==============
def add_keepalive_task():
    if not PROJECT_URL:
        add_log("[KEEP] ⏭️ 未设置 PROJECT_URL")
        worker_status['keepalive'] = 'skipped'
        return
    add_log(f"[KEEP] 🔄 添加保活...")
    try:
        r = requests.post("https://trans.ct8.pl/add-url", json={"url": PROJECT_URL}, timeout=30)
        worker_status['keepalive'] = 'success' if r.status_code == 200 else 'failed'
        add_log(f"[KEEP] {'✅ 成功' if r.status_code == 200 else '❌ 失败'}")
    except Exception as e:
        worker_status['keepalive'] = 'failed'
        add_log(f"[KEEP] ❌ {e}")

# ============== Worker ==============
class AFKWorker:
    def __init__(self):
        self.session = requests.Session()
        self.base = "https://panel.na1.host"
        self.xsrf = None
        self.coins = self.initial = 0
        self._init_session()
    
    def _init_session(self):
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0", "Accept": "application/json",
            "Referer": self.base, "Origin": self.base
        })
        for item in PANEL_NA1_COOKIES.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                self.session.cookies.set(k.strip(), v.strip(), domain="panel.na1.host")
                if k.strip() == "XSRF-TOKEN":
                    self.xsrf = unquote(v.strip())
    
    def _h(self):
        return {"X-XSRF-TOKEN": self.xsrf} if self.xsrf else {}
    
    def _upd(self, r):
        for c in r.cookies:
            self.session.cookies.set(c.name, c.value, domain="panel.na1.host")
            if c.name == "XSRF-TOKEN": self.xsrf = unquote(c.value)
    
    def tg(self, msg):
        if TG_BOT_TOKEN and TG_CHAT_ID:
            try: requests.post(f"{TG_API}/bot{TG_BOT_TOKEN}/sendMessage", data={"chat_id": TG_CHAT_ID, "text": msg}, timeout=10)
            except: pass
    
    def login(self):
        try:
            r = self.session.get(f"{self.base}/api/client", headers=self._h(), timeout=30)
            self._upd(r)
            return r.status_code == 200
        except: return False
    
    def wallet(self):
        try:
            r = self.session.get(f"{self.base}/api/client/account/wallet", headers=self._h(), timeout=30)
            self._upd(r)
            if r.status_code == 200:
                d = r.json()
                self.coins = d.get('coins', 0)
                worker_status['coins'] = self.coins
                worker_status['napoints'] = d.get('napoints', 0)
                return True
        except: pass
        return False
    
    def join(self):
        try:
            r = self.session.post(f"{self.base}/api/client/account/afk/join", headers=self._h(), timeout=30)
            self._upd(r)
            return r.status_code in [200, 409]
        except: return False
    
    def status(self):
        try:
            r = self.session.get(f"{self.base}/api/client/account/afk/status", headers=self._h(), timeout=30)
            self._upd(r)
            if r.status_code == 200:
                d = r.json()
                worker_status.update({
                    'active_users': d.get('active_users', 0),
                    'multiplier': d.get('multiplier', 1),
                    'coins_per_minute': d.get('coins_per_minute', 1),
                    'session_coins': d.get('session', {}).get('coins_earned', 0),
                    'afk': True
                })
                return True
        except: pass
        return False
    
    def run(self):
        worker_status['start_time'] = time.time()
        add_log("🎮 NA1 AFK Bot 启动中...")
        add_keepalive_task()
        
        if not self.login():
            worker_status['status'] = 'cookie_expired'
            add_log("❌ Cookie 已过期")
            self.tg("❌ Cookie 已过期")
            return
        add_log("✅ 登录成功")
        
        self.wallet()
        self.initial = worker_status['initial_coins'] = self.coins
        add_log(f"💰 初始: {self.coins}")
        
        self.join()
        self.status()
        add_log(f"📊 在线 {worker_status['active_users']} 人 | {worker_status['multiplier']}x")
        
        worker_status['status'] = 'running'
        self.tg(f"✅ AFK 启动 | 💰 {self.coins}")
        last_tg = time.time()
        
        while worker_status['status'] == 'running':
            time.sleep(60)
            worker_status['checks'] += 1
            n = worker_status['checks']
            
            if self.status():
                add_log(f"[{n:03d}] 👥{worker_status['active_users']} ⚡{worker_status['multiplier']}x +{worker_status['session_coins']}")
            
            if n % 5 == 0:
                old = self.coins
                self.wallet()
                add_log(f"[SYNC] 💰{self.coins} (+{self.coins-old})")
            
            if n % 30 == 0: self.join()
            
            if time.time() - last_tg >= 3600:
                last_tg = time.time()
                self.tg(f"📊 {self.coins} (+{self.coins-self.initial})")

def auto_start():
    if not PANEL_NA1_COOKIES:
        add_log("❌ 未设置 PANEL_NA1_COOKIES")
        worker_status['status'] = 'no_cookie'
        add_keepalive_task()
        return
    AFKWorker().run()

threading.Thread(target=auto_start, daemon=True).start()

# ============== FastAPI ==============
app = FastAPI()

@app.get("/")
def health():
    s = worker_status
    return JSONResponse({
        "status": "ok",
        "coins": s['coins'],
        "earned": s['coins'] - s.get('initial_coins', 0),
        "checks": s['checks'],
        "worker": s['status'],
        "afk": s['afk']
    })

# ============== Gradio ==============
def make_page():
    s = worker_status
    total = s['coins'] - s.get('initial_coins', 0)
    
    rt = "--"
    if s.get('start_time'):
        m = (time.time() - s['start_time']) / 60
        rt = f"{m:.0f}分" if m < 60 else f"{m/60:.1f}时"
    
    status_map = {
        "running": ("🟢", "运行中", "#10b981", "#ecfdf5"),
        "waiting": ("🟡", "启动中", "#f59e0b", "#fffbeb"),
        "no_cookie": ("🔴", "未配置", "#ef4444", "#fef2f2"),
        "cookie_expired": ("🔴", "已过期", "#ef4444", "#fef2f2"),
    }
    s_icon, s_text, s_color, s_bg = status_map.get(s['status'], ("⚪", s['status'], "#6b7280", "#f3f4f6"))
    
    ka_map = {
        "success": ("🛡️", "保活", "#3b82f6", "#eff6ff"),
        "failed": ("⚠️", "失败", "#ef4444", "#fef2f2"),
        "skipped": ("⏭️", "跳过", "#6b7280", "#f3f4f6"),
        None: ("⏳", "等待", "#f59e0b", "#fffbeb"),
    }
    k_icon, k_text, k_color, k_bg = ka_map.get(s.get('keepalive'), ("⏳", "等待", "#f59e0b", "#fffbeb"))
    
    logs = "\n".join(log_queue) if log_queue else "⏳ 等待日志..."
    
    return f'''
<div class="container">
    <div class="header">
        <div class="logo">🎮 NA1 AFK</div>
        <div class="badge" style="background:{s_bg};color:{s_color}">{s_icon} {s_text}</div>
        <div class="badge" style="background:{k_bg};color:{k_color}">{k_icon} {k_text}</div>
        <div class="stats-row">
            <span>💰 <b>{s['coins']:,}</b></span>
            <span>📈 <b class="green">+{total:,}</b></span>
            <span>👥 <b>{s.get('active_users', 0)}</b></span>
            <span>⚡ <b>{s.get('multiplier', 1)}x</b></span>
            <span>⏱️ <b>{rt}</b></span>
        </div>
    </div>
    
    <div class="main">
        <div class="card logs-card">
            <div class="card-title">📋 日志 <span class="sub">#{s['checks']}</span></div>
            <div class="logs">{logs}</div>
        </div>
        
        <div class="sidebar">
            <div class="card">
                <div class="card-title">📊 统计</div>
                <div class="stat-grid">
                    <div class="stat-item"><div class="stat-val">{s['coins']:,}</div><div class="stat-label">金币</div></div>
                    <div class="stat-item"><div class="stat-val green">+{total:,}</div><div class="stat-label">收益</div></div>
                    <div class="stat-item"><div class="stat-val blue">+{s.get('session_coins', 0)}</div><div class="stat-label">会话</div></div>
                    <div class="stat-item"><div class="stat-val">{s.get('coins_per_minute', 1)}</div><div class="stat-label">/分钟</div></div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">⚙️ 环境变量配置</div>
                <div class="config-table">
                    <div class="config-row header-row">
                        <span class="config-name">变量名</span>
                        <span class="config-desc">说明</span>
                    </div>
                    <div class="config-row">
                        <code>PANEL_NA1_COOKIES</code>
                        <span>登录 Cookie <b class="req">必填</b></span>
                    </div>
                    <div class="config-row">
                        <code>PROJECT_URL</code>
                        <span>保活链接 <b class="opt">可选</b></span>
                    </div>
                    <div class="config-row">
                        <code>TG_BOT_TOKEN</code>
                        <span>TG 机器人 <b class="opt">可选</b></span>
                    </div>
                    <div class="config-row">
                        <code>TG_CHAT_ID</code>
                        <span>TG 聊天 ID <b class="opt">可选</b></span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">🔗 获取保活链接</div>
                <div class="help-steps">
                    <div class="step"><span class="step-num">1</span>打开你的 Space 页面</div>
                    <div class="step"><span class="step-num">2</span>点击右上角 <b>⋮</b> 菜单按钮</div>
                    <div class="step"><span class="step-num">3</span>选择 <b>Embed this Space</b></div>
                    <div class="step"><span class="step-num">4</span>复制 <b>Direct URL</b></div>
                    <div class="url-example">
                        <code>https://用户名-项目名.hf.space</code>
                    </div>
                    <div class="tip">
                        💡 设置 <code>PROJECT_URL</code> 环境变量后自动启用保活，防止 Space 休眠
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>'''

CSS = """
/* 隐藏 HuggingFace 顶部栏 */
#huggingface-space-header { display: none !important; }
footer { display: none !important; }

.gradio-container { background: #f8fafc !important; padding: 0 !important; }

.container { max-width: 1100px; margin: 0 auto; padding: 16px; font-family: system-ui, sans-serif; }

.header { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: white; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 12px; flex-wrap: wrap; }
.logo { font-size: 16px; font-weight: 700; color: #1e293b; }
.badge { display: inline-flex; align-items: center; gap: 5px; padding: 5px 10px; border-radius: 16px; font-size: 12px; font-weight: 600; }
.stats-row { display: flex; gap: 14px; margin-left: auto; font-size: 13px; color: #64748b; flex-wrap: wrap; }
.stats-row b { color: #1e293b; }
.stats-row .green { color: #10b981; }

.main { display: grid; grid-template-columns: 1fr 320px; gap: 12px; }
@media (max-width: 800px) { .main { grid-template-columns: 1fr; } }

.card { background: white; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
.card-title { padding: 10px 14px; font-size: 13px; font-weight: 600; color: #374151; border-bottom: 1px solid #e5e7eb; display: flex; }
.card-title .sub { margin-left: auto; color: #9ca3af; font-weight: 400; }

.logs { padding: 12px; font-family: 'SF Mono', Consolas, monospace; font-size: 11px; line-height: 1.8; color: #475569; background: #f8fafc; height: 500px; overflow-y: auto; white-space: pre-wrap; }

.sidebar { display: flex; flex-direction: column; gap: 12px; }

.stat-grid { display: grid; grid-template-columns: 1fr 1fr; }
.stat-item { padding: 12px; text-align: center; border-bottom: 1px solid #e5e7eb; }
.stat-item:nth-child(odd) { border-right: 1px solid #e5e7eb; }
.stat-item:nth-last-child(-n+2) { border-bottom: none; }
.stat-val { font-size: 20px; font-weight: 700; color: #1e293b; }
.stat-val.green { color: #10b981; }
.stat-val.blue { color: #3b82f6; }
.stat-label { font-size: 10px; color: #9ca3af; text-transform: uppercase; }

/* 配置表格 */
.config-table { padding: 0; }
.config-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid #f1f5f9; font-size: 11px; }
.config-row:last-child { border-bottom: none; }
.config-row.header-row { background: #f8fafc; font-weight: 600; color: #64748b; font-size: 10px; }
.config-row code { background: #f1f5f9; padding: 3px 6px; border-radius: 4px; font-size: 10px; color: #1e293b; font-family: 'SF Mono', Consolas, monospace; }
.config-row .req { color: #ef4444; font-size: 9px; }
.config-row .opt { color: #6b7280; font-size: 9px; }
.config-name { font-weight: 600; }
.config-desc { color: #64748b; }

/* 帮助步骤 */
.help-steps { padding: 12px; }
.step { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 12px; color: #475569; }
.step-num { width: 20px; height: 20px; background: #3b82f6; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; flex-shrink: 0; }
.step b { color: #1e293b; }

.url-example { margin: 10px 0; padding: 8px 12px; background: #f1f5f9; border-radius: 6px; border-left: 3px solid #3b82f6; }
.url-example code { font-size: 11px; color: #3b82f6; font-family: 'SF Mono', Consolas, monospace; word-break: break-all; }

.tip { margin-top: 10px; padding: 10px 12px; background: #fffbeb; border-radius: 6px; font-size: 11px; color: #92400e; line-height: 1.5; }
.tip code { background: #fef3c7; padding: 2px 5px; border-radius: 3px; font-size: 10px; color: #92400e; }
"""

with gr.Blocks(title="NA1 AFK", css=CSS, theme=gr.themes.Soft()) as gradio_app:
    html = gr.HTML(make_page)
    gr.Timer(5).tick(make_page, outputs=html)

app = gr.mount_gradio_app(app, gradio_app, path="/na1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)