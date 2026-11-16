import sqlite3, os, secrets, datetime, random, string
from datetime import timedelta
from flask import Flask, request, redirect, session, send_from_directory

app = Flask(__name__)
app.secret_key = "tim-shop-final-2026"
app.permanent_session_lifetime = timedelta(days=30)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def db():
    c = sqlite3.connect("shop.db")
    c.row_factory = sqlite3.Row
    return c

def safe(row, key, default=""):
    try:
        v = row[key]
        return v if v is not None else default
    except:
        return default

def parse_price(v):
    try:
        s = str(v).replace(',','').strip()
        if '-' in s:
            s = s.split('-')[0].strip()
        if s == '' or s == '-': return 0
        return float(s)
    except:
        return 0

def fmt_price(v):
    try:
        f = float(v)
        if f == int(f): return str(int(f))
        return str(f)
    except:
        return "0"

def init():
    c = db()
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, coin REAL DEFAULT 0, role TEXT DEFAULT 'user', avatar TEXT DEFAULT '', date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS zones(id INTEGER PRIMARY KEY, name TEXT, icon TEXT DEFAULT '🔥', order_num INTEGER DEFAULT 0, img TEXT DEFAULT '')")
    c.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, zone_id INTEGER, name TEXT, price REAL, desc TEXT, img TEXT DEFAULT '', stock TEXT DEFAULT '', date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS variants(id INTEGER PRIMARY KEY, product_id INTEGER, name TEXT, price REAL, stock TEXT DEFAULT '', date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY, logo TEXT DEFAULT '', banner TEXT DEFAULT '', shop_name TEXT DEFAULT 'tim SHOP', promptpay TEXT DEFAULT '', truemoney_phone TEXT DEFAULT '', auto_check INTEGER DEFAULT 1)")
    c.execute("CREATE TABLE IF NOT EXISTS topups(id INTEGER PRIMARY KEY, username TEXT, amount REAL, method TEXT, slip TEXT DEFAULT '', envelope_link TEXT DEFAULT '', phone TEXT DEFAULT '', status TEXT DEFAULT 'pending', date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS credit_codes(id INTEGER PRIMARY KEY, code TEXT UNIQUE, amount REAL, used_by TEXT DEFAULT '', used INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS agent_keys(id INTEGER PRIMARY KEY, code TEXT UNIQUE, discount INTEGER DEFAULT 10, days INTEGER DEFAULT 30, price REAL DEFAULT 0, created_by TEXT DEFAULT 'admin', used_by TEXT DEFAULT '', used INTEGER DEFAULT 0, date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS agents(id INTEGER PRIMARY KEY, username TEXT UNIQUE, discount INTEGER DEFAULT 10, expire TEXT, date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, username TEXT, product_name TEXT, qty INTEGER, total REAL, codes TEXT, date TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, type TEXT, username TEXT, amount REAL, message TEXT, detail TEXT, link TEXT, is_read INTEGER DEFAULT 0, date TEXT)")
    for tbl, col, sql in [
        ("zones","img","ALTER TABLE zones ADD COLUMN img TEXT DEFAULT ''"),
        ("zones","order_num","ALTER TABLE zones ADD COLUMN order_num INTEGER DEFAULT 0"),
        ("settings","auto_check","ALTER TABLE settings ADD COLUMN auto_check INTEGER DEFAULT 1"),
    ]:
        try:
            cols = [r[1] for r in c.execute(f"PRAGMA table_info({tbl})").fetchall()]
            if col not in cols: c.execute(sql)
        except: pass
    if not c.execute("SELECT * FROM settings WHERE id=1").fetchone():
        c.execute("INSERT INTO settings(id,logo,banner,shop_name,promptpay,truemoney_phone,auto_check) VALUES(1,'','','tim SHOP','','',1)")
    if not c.execute("SELECT * FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users(username,password,coin,role,avatar,date) VALUES('admin','1234',999999,'owner','',?)", (str(datetime.datetime.now()),))
    if c.execute("SELECT COUNT(*) FROM zones").fetchone()[0]==0:
        c.execute("INSERT INTO zones(name,icon,order_num,img) VALUES('FREE FRIE AD','🔥',1,'')")
        c.execute("INSERT INTO zones(name,icon,order_num,img) VALUES('FREEFRIE IOS','⚡',2,'')")
        c.execute("INSERT INTO zones(name,icon,order_num,img) VALUES('FREEFRIE PC','💻',3,'')")
        c.execute("INSERT INTO zones(name,icon,order_num,img) VALUES('FREEFRIE IOS และ AD','📱',4,'')")
        c.execute("INSERT INTO zones(name,icon,order_num,img) VALUES('โปรแกรม ROV','⚔️',5,'')")
        c.execute("INSERT INTO zones(name,icon,order_num,img) VALUES('ไก่ได้เวล','🐔',6,'')")
        zid = c.execute("SELECT id FROM zones WHERE order_num=1").fetchone()[0]
        c.execute("INSERT INTO products(zone_id,name,price,desc,img,stock,date) VALUES(?, 'โปรแกรม tim', 59, 'ลื่นๆ ใช้งานง่าย', '', 'TIM-001\\nTIM-002', ?)", (zid, str(datetime.datetime.now())))
        pid = c.execute("SELECT id FROM products WHERE name='โปรแกรม tim'").fetchone()[0]
        for n,p in [("1 ชั่วโมง",19),("1 วัน",59),("3 วัน",129),("7 วัน",249),("30 วัน",599)]:
            c.execute("INSERT INTO variants(product_id,name,price,stock,date) VALUES(?,?,?,?,?)", (pid, n, p, "TIM-001\\nTIM-002", str(datetime.datetime.now())))
    c.commit(); c.close()

def cur():
    if 'uid' not in session: return None
    c = db(); u = c.execute("SELECT * FROM users WHERE id=?", (session['uid'],)).fetchone(); c.close(); return u
def get_setting():
    c = db(); s = c.execute("SELECT * FROM settings WHERE id=1").fetchone(); c.close(); return s
def add_notify(type_, username, amount, message, detail="", link="/admin"):
    c = db(); c.execute("INSERT INTO notifications(type,username,amount,message,detail,link,is_read,date) VALUES(?,?,?,?,?,?,0,?)", (type_, username, amount, message, detail, link, str(datetime.datetime.now()))); c.commit(); c.close()
def unread_count():
    c = db()
    try: n = c.execute("SELECT COUNT(*) FROM notifications WHERE is_read=0").fetchone()[0]
    except: n = 0
    c.close(); return n

def base(body):
    u = cur(); st = get_setting()
    shop_name = safe(st,'shop_name','tim SHOP'); logo = safe(st,'logo','')
    logo_html = f"<img src='/uploads/{logo}' style='width:36px;height:36px;border-radius:50%;object-fit:cover'>" if logo else "<span style='font-size:22px'>🔥</span>"
    if u:
        av = safe(u,'avatar','')
        avh = f"<img src='/uploads/{av}' style='width:32px;height:32px;border-radius:50%;object-fit:cover'>" if av else "👤"
        user_btn = f"<a href='/profile' style='display:flex;align-items:center;gap:6px;color:#fff'>{avh} {u['username']} 💰 {int(u['coin'])}</a>"
        side_user = f"<div style='color:#fff'>👤 <b>{u['username']}</b><br><a href='/profile' style='color:#2f7bff'>ดูโปรไฟล์ ></a> | <a href='/logout' style='color:#ff5555'>ออกจากระบบ</a></div>"
    else:
        user_btn = "<a href='/login' style='color:#fff'>เข้าสู่ระบบ</a>"
        side_user = "<a href='/register' style='color:#fff'>👤 <b>สมัครสมาชิก</b> สร้างบัญชีใหม่ ></a><br><a href='/login' style='color:#fff'>🔑 <b>เข้าสู่ระบบ</b> เข้าสู่บัญชีของคุณ ></a>"
    bell = ""
    if u and u['role'] in ['owner','admin']:
        un = unread_count()
        badge = f"<span id='bell-badge' style='background:#ef4444;color:#fff;font-size:10px;padding:2px 6px;border-radius:20px;position:absolute;top:-6px;right:-6px'>{un}</span>" if un>0 else "<span id='bell-badge' style='display:none'></span>"
        bell = f"<a href='/notifications' style='position:relative;font-size:20px'>🔔{badge}</a>"
    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{shop_name}</title>
<style>
*{{box-sizing:border-box}}body{{background:#0b0e13;color:#fff;font-family:sans-serif;margin:0}}a{{color:#2f7bff;text-decoration:none}}
.top{{background:#0f1218;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100;border-bottom:1px solid #1e293b}}
.sidebar{{position:fixed;top:0;left:-300px;width:280px;height:100vh;background:#0f1218;z-index:200;transition:.3s;padding:16px;border-right:1px solid #222;overflow-y:auto}}
.sidebar.open{{left:0}}.overlay{{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;z-index:150}}.overlay.show{{display:block}}
.menu-item{{display:block;padding:14px 12px;border-radius:12px;color:#fff;margin:4px 0}}.menu-item.active{{background:#2f6bff;color:#fff}}
.box{{background:#14181f;border:1px solid #1e293b;border-radius:16px;padding:16px;margin:12px 0}}
input,select,textarea{{width:100%;padding:12px;background:#1a1f2a;border:1px solid #2a3342;color:#fff;border-radius:10px;margin:6px 0}}button{{background:#2f6bff;color:#fff;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;width:100%;margin-top:6px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.card{{background:#14181f;border:1px solid #1e293b;border-radius:14px;padding:10px;text-align:center;display:flex;flex-direction:column}}
.card img{{width:100%;height:110px;object-fit:cover;border-radius:10px}}
.card h3{{font-size:14px;line-height:1.3;min-height:36px;display:flex;align-items:center;justify-content:center;margin:8px 0}}
.stat{{background:#14181f;border:1px solid #1e293b;border-radius:16px;padding:14px;text-align:center}}.stat b{{color:#2f7bff;font-size:22px}}
.snowflake{{position:fixed;top:-20px;color:#fff;user-select:none;pointer-events:none;z-index:9999;animation:fall linear infinite;opacity:.9;text-shadow:0 0 8px #fff}}@keyframes fall{{0%{{transform:translateY(-20px)}}100%{{transform:translateY(110vh) translateX(60px) rotate(360deg)}}}}
.scroll-x{{display:flex;gap:10px;overflow-x:auto;padding:6px 0}}.scroll-x::-webkit-scrollbar{{display:none}}.latest-item{{min-width:220px;background:#0f1218;border:1px solid #1e293b;border-radius:12px;padding:10px;display:flex;gap:8px;align-items:center}}
.marquee{{overflow:hidden;white-space:nowrap;color:#888;font-size:12px;padding:8px 0}}.marquee span{{display:inline-block;padding-left:100%;animation:marq 18s linear infinite}}@keyframes marq{{from{{transform:translateX(0)}}to{{transform:translateX(-100%)}}}}
.hero-btn{{flex:1;padding:13px;border-radius:12px;font-weight:bold;text-align:center;display:block}}
.zone-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.zone-card{{border:1px solid #2f7bff;border-radius:14px;overflow:hidden;background:#000;display:block}}
.zone-card img{{width:100%;height:auto;object-fit:contain;display:block}}
.zone-name{{padding:8px;background:#111;text-align:center;font-size:13px;font-weight:bold;color:#fff}}
.variant-label{{display:flex;justify-content:space-between;align-items:center;background:#111;border:1px solid #333;padding:12px;border-radius:12px;margin:6px 0;cursor:pointer}}
.variant-label.active{{border-color:#2f7bff;background:#1a2a4a}}
@media(max-width:500px){{.zone-grid{{grid-template-columns:repeat(3,1fr);gap:8px}}.zone-name{{font-size:11px;padding:6px}}.grid{{grid-template-columns:repeat(2,1fr);gap:8px}}.card img{{height:95px}}}}
</style></head><body>
<div class='overlay' id='overlay' onclick='toggleMenu()'></div>
<div class='sidebar' id='sidebar'>
  <div style='display:flex;justify-content:space-between;align-items:center'><div style='display:flex;align-items:center;gap:8px'>{logo_html}<div><b>{shop_name}</b><br><span style='font-size:12px;color:#888'>ร้านค้าออนไลน์</span></div></div><span onclick='toggleMenu()' style='font-size:20px;cursor:pointer'>✕</span></div>
  <a href='/' class='menu-item active'>🏠 หน้าหลัก</a>
  <a href='/' class='menu-item'>🗂️ ร้านค้า</a>
  <a href='/profile' class='menu-item'>💲 เติมเงิน</a>
  <a href='/history' class='menu-item'>🕐 ประวัติการสั่งซื้อ</a>
  <hr style='border-color:#222'><div style='font-size:14px;line-height:2'>{side_user}</div>
</div>
<div class='top'><div style='display:flex;align-items:center;gap:10px'><span onclick='toggleMenu()' style='font-size:22px;cursor:pointer'>☰</span>{logo_html}<b>{shop_name}</b></div><div style='display:flex;align-items:center;gap:10px'>{bell}{user_btn}</div></div>
<div style='max-width:900px;margin:auto;padding:0 12px 60px'>{body}</div>
<script>function toggleMenu(){{document.getElementById('sidebar').classList.toggle('open');document.getElementById('overlay').classList.toggle('show');}}</script>"""
    if u and u['role'] in ['owner','admin']:
        html += "<script>setInterval(async()=>{try{let r=await fetch('/api/unread');let d=await r.json();let b=document.getElementById('bell-badge');if(b){if(d.unread>0){b.style.display='inline';b.innerText=d.unread}else{b.style.display='none'}}}catch(e){}},8000);</script>"
    html += """<script>function createSnow(){document.querySelectorAll('.snowflake').forEach(e=>e.remove());for(let i=0;i<30;i++){let s=document.createElement('div');s.className='snowflake';s.innerHTML='❄';s.style.left=Math.random()*100+'vw';s.style.fontSize=(Math.random()*12+9)+'px';s.style.animationDuration=(Math.random()*5+5)+'s';s.style.animationDelay=(Math.random()*5)+'s';document.body.appendChild(s);}}createSnow();setInterval(createSnow,8000);</script>"""
    html += "</body></html>"
    return html

@app.route('/uploads/<path:fn>')
def uploads(fn): return send_from_directory(UPLOAD_FOLDER, fn)

@app.route('/')
def home():
    c = db()
    zones = c.execute("SELECT * FROM zones ORDER BY order_num ASC").fetchall()
    q = request.args.get('zone','')
    products = c.execute("SELECT * FROM products WHERE zone_id=? ORDER BY id DESC", (q,)).fetchall() if q else c.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_products = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    all_stock = 0
    for p in c.execute("SELECT stock FROM products").fetchall():
        all_stock += len([x for x in safe(p,'stock','').split('\\n') if x.strip()])
    for v in c.execute("SELECT stock FROM variants").fetchall():
        all_stock += len([x for x in safe(v,'stock','').split('\\n') if x.strip()])
    total_sold = c.execute("SELECT COALESCE(SUM(qty),0) FROM orders").fetchone()[0]
    latest = c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 8").fetchall()
    today = str(datetime.datetime.now().date())
    topup_rank = c.execute("SELECT username, SUM(amount) as total FROM topups WHERE status='approved' AND date LIKE ? GROUP BY username ORDER BY total DESC LIMIT 3", (f"%{today}%",)).fetchall()
    c.close(); st = get_setting()
    shop_name = safe(st,'shop_name','tim SHOP'); banner = safe(st,'banner','')
    body = f"<div class='marquee'><span>โปรแกรมมีปัญหาหรือรับมีปัญหาให้ติดต่อแอดมินได้ที่ Discord เท่านั้น !! &nbsp;&nbsp; โปรแกรมมีปัญหาหรือรับมีปัญหาให้ติดต่อแอดมินได้ที่ Discord เท่านั้น !!</span></div>"
    body += f"""<div style='margin:10px 0 14px'>
        <div style='display:inline-block;background:#111c2e;color:#2f7bff;padding:6px 14px;border-radius:20px;font-size:13px'>⚡ {shop_name}</div>
        <h1 style='font-size:26px;line-height:1.3;margin:12px 0 6px'>ยินดีต้อนรับเข้าสู่ร้าน {shop_name.upper()}</h1>
        <p style='color:#888;font-size:13px;margin:0 0 14px'>โปรแกรมมีปัญหาหรือรับมีปัญหาให้ติดต่อแอดมินได้ที่ Discord เท่านั้น !!</p>
        <div style='display:flex;gap:10px'>
            <a href='/profile' class='hero-btn' style='background:#2f6bff;color:#fff'>🚀 เริ่มต้นใช้งาน</a>
            <a href='#categories' class='hero-btn' style='background:#1a1f2a;color:#fff;border:1px solid #333'>📖 วิธีการสั่งซื้อ →</a>
        </div>
    </div>"""
    if banner:
        body += f"<div style='margin:12px 0;border-radius:16px;overflow:hidden;background:#000'><img src='/uploads/{banner}' style='width:100%;height:auto;object-fit:contain;display:block'></div>"
    else:
        body += f"""<div style='margin:12px 0;background:linear-gradient(180deg,#dfe8f5,#fff);border-radius:16px;padding:30px 16px;text-align:center;color:#000;position:relative;overflow:hidden'>
        <div style='font-size:12px;letter-spacing:6px;color:#666'>WELCOME TO</div>
        <div style='font-size:42px;font-weight:900;line-height:1'>{shop_name.upper()}</div>
        <div style='font-size:12px;color:#888;margin-top:8px'>Thank you for joining us.</div>
        <div style='position:absolute;left:12px;bottom:12px;background:#000;color:#fff;padding:6px 10px;border-radius:8px;font-size:12px'>{shop_name}</div></div>"""
    body += f"""<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px'>
        <div class='stat'>👥 <span style='color:#888;font-size:13px'>ผู้ใช้งาน</span><br><b>{total_users}</b> <span style='font-size:12px;color:#888'>คน</span><br><span style='color:#2f7bff'>━━</span></div>
        <div class='stat'>🗂️ <span style='color:#888;font-size:13px'>สินค้า</span><br><b>{total_products}</b> <span style='font-size:12px;color:#888'>รายการ</span><br><span style='color:#2f7bff'>━━</span></div>
        <div class='stat'>📦 <span style='color:#888;font-size:13px'>คลังสินค้า</span><br><b>{all_stock:,}</b> <span style='font-size:12px;color:#888'>ชิ้น</span><br><span style='color:#2f7bff'>━━</span></div>
        <div class='stat'>✅ <span style='color:#888;font-size:13px'>ขายแล้ว</span><br><b>{total_sold:,}</b> <span style='font-size:12px;color:#888'>ชิ้น</span><br><span style='color:#2f7bff'>━━</span></div>
    </div>"""
    body += "<div class='box'><h3 style='margin:0'>🕐 ซื้อล่าสุด</h3><div class='scroll-x'>"
    for o in latest:
        short = o['username'][:3] + "***"
        body += f"<div class='latest-item'><div style='width:36px;height:36px;background:#222;border-radius:8px;display:flex;align-items:center;justify-content:center'>🔥</div><div><div style='font-size:13px'><b>{short}</b> ซื้อ <b>{o['product_name'][:14]}</b></div><div style='font-size:12px;color:#888'>1 วัน</div></div></div>"
    if not latest: body += "<p style='color:#888'>ยังไม่มีออเดอร์</p>"
    body += "</div></div>"
    body += "<div class='box' id='categories'><h2 style='margin:0'>🗂️ หมวดหมู่แนะนำ</h2><p style='font-size:12px;color:#888;margin:0'>Recommended Categories</p><div class='zone-grid' style='margin-top:12px'>"
    for z in zones:
        zim = safe(z,'img','')
        if zim:
            body += f"<a href='/?zone={z['id']}' class='zone-card'><img src='/uploads/{zim}'><div class='zone-name'>{safe(z,'icon')} {z['name']}</div></a>"
        else:
            body += f"<a href='/?zone={z['id']}' class='zone-card'><div style='height:70px;background:#1a1f2a;display:flex;align-items:center;justify-content:center;font-size:28px'>{safe(z,'icon')}</div><div class='zone-name'>{z['name']}</div></a>"
    body += "</div></div><div class='grid'>"
    for p in products:
        img = safe(p,'img','')
        ih = f"<img src='/uploads/{img}'>" if img else "<div style='height:110px;background:#222;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:40px'>🔥</div>"
        body += f"<div class='card'>{ih}<h3>{p['name']}</h3><p style='color:#888;font-size:12px;min-height:18px;margin:0 0 6px'>{safe(p,'desc','')}</p><b style='color:#00ff88'>{fmt_price(p['price'])} บาท</b><a href='/product/{p['id']}' style='margin-top:auto'><button>ซื้อเลย</button></a></div>"
    body += "</div>"
    body += "<div class='box' style='text-align:center'><h2 style='margin:0'>🔥 Top Up ประจำวัน</h2><div style='display:flex;flex-direction:column;gap:10px;align-items:center;margin-top:12px'>"
    for i, r in enumerate(topup_rank):
        uname = r['username'][:2] + "****" + r['username'][-1:] if len(r['username'])>3 else r['username']
        body += f"<div style='display:flex;align-items:center;gap:12px;background:#1a1f2a;border:1px solid #333;border-radius:14px;padding:10px 14px;width:100%;max-width:320px'><div style='width:44px;height:44px;border-radius:50%;border:2px solid #a855f7;display:flex;align-items:center;justify-content:center;font-size:20px'>👤</div><div style='flex:1;text-align:left'><b>{uname}</b><br><span style='font-size:12px;color:#888'>เติม {int(r['total']):.2f} บาท</span></div><div style='background:#222;padding:6px 10px;border-radius:10px'>🏆 {i+1}</div></div>"
    if not topup_rank: body += "<p style='color:#888'>ยังไม่มีคนเติมวันนี้</p>"
    body += "</div></div>"
    body += f"<div style='display:flex;justify-content:space-between;padding:12px 4px;color:#888;font-size:12px'><span>© 2026 {shop_name} - ความเป็นส่วนตัว</span><span>● ONLINE</span></div>"
    return base(body)

@app.route('/product/<int:pid>', methods=['GET','POST'])
def product(pid):
    c = db(); p = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not p: c.close(); return "ไม่เจอสินค้า"
    if request.method=='POST':
        u = cur()
        if not u: c.close(); return redirect('/login')
        variant_id = request.form.get('variant_id')
        qty = int(float(request.form.get('qty',1) or 1))
        if variant_id:
            v = c.execute("SELECT * FROM variants WHERE id=?", (variant_id,)).fetchone()
            if not v: c.close(); return base("<div class='box'>❌ ไม่เจอช่องนี้</div>")
            use_price = v['price']; use_name = f"{p['name']} - {v['name']}"
            stock = [x for x in safe(v,'stock','').split('\\n') if x.strip()]
        else:
            use_price = p['price']; use_name = p['name']
            stock = [x for x in safe(p,'stock','').split('\\n') if x.strip()]
        ag = c.execute("SELECT * FROM agents WHERE username=?", (u['username'],)).fetchone()
        if ag: use_price = use_price * (100 - ag['discount']) / 100
        total = use_price * qty
        if u['coin'] < total: c.close(); return base("<div class='box'>❌ coin ไม่พอ <a href='/profile'>ไปเติมเงิน</a></div>")
        if len(stock) < qty: c.close(); return base("<div class='box'>❌ ของหมด</div>")
        codes = stock[:qty]; rest = "\\n".join(stock[qty:])
        c.execute("UPDATE users SET coin=coin-? WHERE id=?", (total, u['id']))
        if variant_id: c.execute("UPDATE variants SET stock=? WHERE id=?", (rest, variant_id))
        else: c.execute("UPDATE products SET stock=? WHERE id=?", (rest, pid))
        c.execute("INSERT INTO orders(username,product_name,qty,total,codes,date) VALUES(?,?,?,?,?,?)", (u['username'], use_name, qty, total, ", ".join(codes), str(datetime.datetime.now())))
        c.commit(); c.close()
        add_notify('order', u['username'], total, f"🛒 {u['username']} ซื้อ {use_name} x{qty}", f"ยอด {int(total)} บาท", "/admin")
        return base(f"<div class='box'><h2>✅ ซื้อสำเร็จ!</h2><p>{use_name}</p><div style='background:#000;padding:12px;border-radius:10px'>{'<br>'.join(codes)}</div><a href='/history'><button>ดูประวัติ</button></a></div>")
    variants = c.execute("SELECT * FROM variants WHERE product_id=? ORDER BY id ASC", (pid,)).fetchall()
    c.close()
    img = safe(p,'img',''); ih = f"<img src='/uploads/{img}' style='width:100%;border-radius:12px'>" if img else ""
    variant_html = ""
    if variants:
        variant_html = "<h3>⏰ เลือกช่อง / ตัวเลือกสินค้า</h3><p style='color:#888;font-size:12px'>กดเลือกช่องที่ต้องการ แล้วกดซื้อ</p>"
        for i,v in enumerate(variants):
            left = len([x for x in safe(v,'stock','').split('\\n') if x.strip()])
            checked = "checked" if i==0 else ""
            active = "active" if i==0 else ""
            variant_html += f"<label class='variant-label {active}' onclick=\"document.querySelectorAll('.variant-label').forEach(e=>e.classList.remove('active'));this.classList.add('active')\"><span><input type='radio' name='variant_id' value='{v['id']}' {checked} style='width:auto'> <b>{v['name']}</b> <span style='color:#888;font-size:12px'>เหลือ {left} ชิ้น</span></span><b style='color:#00ff88'>{fmt_price(v['price'])} บาท</b></label>"
    else:
        variant_html = f"<p>ราคา: <b style='color:#00ff88'>{fmt_price(p['price'])} บาท</b></p>"
    body = f"<div class='box'>{ih}<h2>{p['name']}</h2><p style='color:#888'>{safe(p,'desc','')}</p><form method='post'>{variant_html}จำนวน <input type='number' name='qty' value='1' min='1'><button>🛒 ซื้อเลย</button></form></div>"
    return base(body)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        un = request.form.get('username','').strip(); pw = request.form.get('password','').strip()
        if not un or not pw: return base("<div class='box'>❌ ใส่ให้ครบ</div>")
        c = db()
        try:
            c.execute("INSERT INTO users(username,password,coin,role,avatar,date) VALUES(?,?,0,'user','',?)", (un,pw,str(datetime.datetime.now()))); c.commit(); c.close()
            add_notify('register', un, 0, f"👤 สมัครใหม่! {un}", "สมัครสมาชิกใหม่", "/admin")
            return redirect('/login')
        except:
            c.close(); return base("<div class='box'>❌ ชื่อนี้มีแล้ว</div>")
    return base("<div class='box'><h2>📝 สมัครสมาชิก</h2><form method='post'><input name='username' placeholder='ชื่อผู้ใช้'><input name='password' type='password' placeholder='รหัสผ่าน'><button>สมัคร</button></form><p><a href='/login'>มีบัญชีแล้ว? เข้าสู่ระบบ</a></p></div>")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        c = db(); u = c.execute("SELECT * FROM users WHERE username=? AND password=?", (request.form.get('username'), request.form.get('password'))).fetchone(); c.close()
        if u: session.permanent=True; session['uid']=u['id']; return redirect('/')
        return base("<div class='box'>❌ ชื่อหรือรหัสผิด</div>")
    st = get_setting(); logo = safe(st,'logo',''); shop_name = safe(st,'shop_name','tim SHOP')
    lh = f"<img src='/uploads/{logo}' style='width:80px;height:80px;border-radius:50%;object-fit:cover;display:block;margin:0 auto 10px'>" if logo else f"<h1 style='text-align:center;color:#2f7bff'>{shop_name}</h1>"
    return base(f"<div class='box'>{lh}<h2 style='text-align:center'>🔑 เข้าสู่ระบบ {shop_name}</h2><form method='post'><input name='username' placeholder='ชื่อผู้ใช้'><input name='password' type='password' placeholder='รหัสผ่าน'><button>เข้าสู่ระบบ</button></form><p style='text-align:center'><a href='/register'>ยังไม่มีบัญชี? สมัคร</a></p></div>")

@app.route('/logout')
def logout(): session.pop('uid',None); return redirect('/')

def admin_panel_html(u):
    c = db()
    today = str(datetime.datetime.now().date())
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    today_users = c.execute("SELECT COUNT(*) FROM users WHERE date LIKE ?", (f"%{today}%",)).fetchone()[0]
    total_orders = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    today_orders = c.execute("SELECT COUNT(*) FROM orders WHERE date LIKE ?", (f"%{today}%",)).fetchone()[0]
    total_sales = c.execute("SELECT COALESCE(SUM(total),0) FROM orders").fetchone()[0]
    today_sales = c.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE date LIKE ?", (f"%{today}%",)).fetchone()[0]
    total_topup = c.execute("SELECT COALESCE(SUM(amount),0) FROM topups WHERE status='approved'").fetchone()[0]
    pending_topup = c.execute("SELECT COUNT(*) FROM topups WHERE status='pending'").fetchone()[0]
    total_products = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_agents = c.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    latest_orders = c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 5").fetchall()
    latest_users = c.execute("SELECT * FROM users ORDER BY id DESC LIMIT 5").fetchall()
    zones = c.execute("SELECT * FROM zones ORDER BY order_num ASC").fetchall()
    products = c.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    variants = c.execute("SELECT * FROM variants ORDER BY product_id ASC").fetchall()
    topups = c.execute("SELECT * FROM topups ORDER BY id DESC LIMIT 20").fetchall()
    credits = c.execute("SELECT * FROM credit_codes ORDER BY id DESC").fetchall()
    agent_keys = c.execute("SELECT * FROM agent_keys ORDER BY id DESC").fetchall()
    users = c.execute("SELECT * FROM users ORDER BY id DESC LIMIT 30").fetchall()
    c.close(); st = get_setting()
    checked = "checked" if safe(st,'auto_check',1)==1 else ""
    body = f"""
    <div class='box' style='border:2px solid #2f6bff'><h2 style='margin:0'>📊 แดชบอร์ดแอดมิน - {safe(st,'shop_name','tim SHOP')}</h2><p style='color:#888'>ดูได้แค่แอดมินเท่านั้น</p>
    <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px'>
      <div class='stat'>👥<br><b style='font-size:22px'>{total_users}</b><br><span style='color:#888;font-size:12px'>สมาชิกทั้งหมด</span><br><span style='color:#22c55e;font-size:12px'>+{today_users} วันนี้</span></div>
      <div class='stat'>🛒<br><b style='font-size:22px'>{total_orders}</b><br><span style='color:#888;font-size:12px'>ขายได้ทั้งหมด (ชิ้น)</span><br><span style='color:#22c55e;font-size:12px'>+{today_orders} วันนี้</span></div>
      <div class='stat'>💰<br><b style='font-size:22px'>{int(total_sales)}</b><br><span style='color:#888;font-size:12px'>ยอดขายทั้งหมด (บาท)</span><br><span style='color:#22c55e;font-size:12px'>+{int(today_sales)} วันนี้</span></div>
      <div class='stat'>💳<br><b style='font-size:22px'>{int(total_topup)}</b><br><span style='color:#888;font-size:12px'>ยอดเติมเงินทั้งหมด</span><br><span style='color:#f59e0b;font-size:12px'>รอเช็ค {pending_topup} รายการ</span></div>
      <div class='stat'>📦<br><b style='font-size:22px'>{total_products}</b><br><span style='color:#888;font-size:12px'>สินค้าทั้งหมด</span></div>
      <div class='stat'>👑<br><b style='font-size:22px'>{total_agents}</b><br><span style='color:#888;font-size:12px'>ตัวแทนทั้งหมด</span></div>
    </div></div>
    <div class='box'><h3>🕐 ซื้อล่าสุด 5 รายการ</h3>"""
    for o in latest_orders: body += f"<p style='font-size:13px;color:#aaa'>🛒 {o['username']} ซื้อ {o['product_name']} x{o['qty']} = {int(o['total'])} บาท<br><span style='color:#666'>{o['date']}</span></p>"
    if not latest_orders: body += "<p style='color:#888'>ยังไม่มีออเดอร์</p>"
    body += "</div><div class='box'><h3>👤 สมัครล่าสุด 5 คน</h3>"
    for us in latest_users: body += f"<p style='font-size:13px'>👤 {us['username']} - {us['role']} - {int(us['coin'])} coin<br><span style='color:#666'>{us['date']}</span></p>"
    body += "</div>"
    body += f"<div class='box'><h3>⚡ โลโก้ + แบนเนอร์ของกู + ตั้งค่า</h3><form method='post' action='/admin' enctype='multipart/form-data'><input type='hidden' name='act' value='settings'>ชื่อร้าน <input name='shop_name' value='{safe(st,'shop_name','tim SHOP')}'>พร้อมเพย์ <input name='promptpay' value='{safe(st,'promptpay','')}'>เบอร์ทรูมันนี่ <input name='truemoney_phone' value='{safe(st,'truemoney_phone','')}'><label><input type='checkbox' name='auto_check' {checked} style='width:auto'> เปิดตรวจเงินอัตโนมัติ</label><br>โลโก้ tim <input type='file' name='logo'>แบนเนอร์ใหญ่ของกู <input type='file' name='banner'><button>บันทึก</button></form></div>"
    body += "<div class='box'><h3>📦 โซน - เพิ่ม / แก้ / ลบ + ใส่รูปโซน</h3><p style='color:#888;font-size:12px'>โซนจะเรียงแบบ 3 ช่องต่อแถว</p><form method='post' action='/admin' enctype='multipart/form-data'><input type='hidden' name='act' value='add_zone'><input name='zone_name' placeholder='ชื่อโซน เช่น FREE FRIE AD'><input name='zone_icon' placeholder='ไอคอน 🔥'><input name='zone_order' type='number' placeholder='ลำดับ 1,2,3...'><label>รูปหน้าโซน (ป้าย)</label><input type='file' name='zone_img'><button>เพิ่มโซน</button></form>"
    for z in zones:
        zim = safe(z,'img',''); zim_html = f"<img src='/uploads/{zim}' style='width:100%;height:auto;object-fit:contain;border-radius:12px;margin:6px 0;display:block'>" if zim else ""
        body += f"<div style='background:#111;padding:10px;border-radius:10px;margin:6px 0'>{zim_html}<form method='post' action='/admin' enctype='multipart/form-data'><input type='hidden' name='act' value='edit_zone'><input type='hidden' name='zone_id' value='{z['id']}'><input name='zone_name' value='{z['name']}'><input name='zone_icon' value='{safe(z,'icon')}'><input name='zone_order' type='number' value='{safe(z,'order_num',0)}'><label>เปลี่ยนรูปโซน</label><input type='file' name='zone_img'><button>บันทึกแก้โซน</button></form><form method='post' action='/admin'><input type='hidden' name='act' value='del_zone'><input type='hidden' name='zone_id' value='{z['id']}'><button style='background:#ef4444'>ลบโซนนี้</button></form></div>"
    body += "</div>"
    body += "<div class='box'><h3>🛒 เพิ่มสินค้า</h3><form method='post' action='/admin' enctype='multipart/form-data'><input type='hidden' name='act' value='add_product'><label>เลือกโซน</label><select name='zone_id'>"
    for z in zones: body += f"<option value='{z['id']}'>{z['name']}</option>"
    body += "</select><input name='name' placeholder='ชื่อสินค้า'><input name='price' type='text' inputmode='decimal' placeholder='ราคา เช่น 10 หรือ 10.5 หรือ 10-450'><input name='desc' placeholder='รายละเอียด'><textarea name='stock' placeholder='สต็อก ทีละบรรทัด'></textarea><label>รูปสินค้า</label><input type='file' name='img'><button>เพิ่มสินค้า</button></form></div>"
    body += "<div class='box'><h3>🛒 สินค้าทั้งหมด - ปรับราคาได้ตรงนี้</h3>"
    for p in products:
        body += f"<form method='post' action='/admin' style='background:#111;padding:12px;border-radius:12px;margin:8px 0'><input type='hidden' name='act' value='edit_product'><input type='hidden' name='pid' value='{p['id']}'><input name='name' value='{p['name']}'><input name='price' type='text' inputmode='decimal' value='{fmt_price(p['price'])}' style='border:1px solid #00ff88;font-weight:bold'><input name='desc' value='{safe(p,'desc','')}'><button>💾 บันทึกการแก้ราคา</button></form><form method='post' action='/admin'><input type='hidden' name='act' value='del_product'><input type='hidden' name='pid' value='{p['id']}'><button style='background:#ef4444'>ลบสินค้านี้</button></form>"
    body += "</div>"
    body += "<div class='box' style='border:2px solid #00ff88'><h3>⏰ เพิ่มช่องตัวเลือกสินค้า</h3><p style='color:#888;font-size:12px'>เช่น สินค้าเดียว มีหลายช่อง: 1 ชั่วโมง / 1 วัน / 7 วัน / 30 วัน แต่ละช่องราคากับสต็อกแยกกัน</p><form method='post' action='/admin'><input type='hidden' name='act' value='add_variant'><label>1. เลือกสินค้าที่จะเพิ่มช่องให้</label><select name='product_id'>"
    for p in products: body += f"<option value='{p['id']}'>{p['name']} (โซน id {p['zone_id']})</option>"
    body += "</select><label>2. ชื่อช่อง เช่น 1 วัน / 7 วัน / 30 วัน</label><input name='variant_name' placeholder='ชื่อช่อง เช่น 1 วัน'><label>3. ราคาช่องนี้</label><input name='variant_price' type='text' inputmode='decimal' placeholder='ราคาช่องนี้ เช่น 59 หรือ 10-450'><label>4. สต็อกช่องนี้ (ใส่ทีละบรรทัด)</label><textarea name='variant_stock' placeholder='สต็อกช่องนี้ เช่น TIM-001\\nTIM-002'></textarea><button style='background:#00aa55'>+ เพิ่มช่องนี้</button></form>"
    body += "<h4 style='margin-top:16px'>ช่องที่มีอยู่ทั้งหมด - แก้ราคา / ลบได้</h4>"
    for v in variants:
        pname = ""
        for p in products:
            if p['id']==v['product_id']: pname = p['name']
        left = len([x for x in safe(v,'stock','').split('\\n') if x.strip()])
        body += f"<form method='post' action='/admin' style='background:#111;padding:10px;border-radius:10px;margin:6px 0'><input type='hidden' name='act' value='edit_variant_price'><input type='hidden' name='variant_id' value='{v['id']}'><b>📦 {pname}</b> <span style='color:#888;font-size:12px'>เหลือ {left} ชิ้น</span><br><input name='variant_name' value='{v['name']}'><input name='variant_price' type='text' inputmode='decimal' value='{fmt_price(v['price'])}' style='border:1px solid #00ff88'><button>💾 บันทึกราคาช่องนี้</button></form><form method='post' action='/admin'><input type='hidden' name='act' value='del_variant'><input type='hidden' name='variant_id' value='{v['id']}'><button style='background:#ef4444'>ลบช่องนี้</button></form>"
    body += "</div>"
    body += "<div class='box'><h3>💰 เติมเงินรออนุมัติ</h3>"
    for t in topups:
        btns = ""
        if t['status']=='pending':
            btns = f"<form method='post' action='/admin' style='display:inline'><input type='hidden' name='act' value='topup_action'><input type='hidden' name='tid' value='{t['id']}'><input type='hidden' name='action' value='approve'><button style='width:auto;background:#22c55e;padding:6px 10px'>อนุมัติ</button></form> <form method='post' action='/admin' style='display:inline'><input type='hidden' name='act' value='topup_action'><input type='hidden' name='tid' value='{t['id']}'><input type='hidden' name='action' value='reject'><button style='width:auto;background:#ef4444;padding:6px 10px'>ปฏิเสธ</button></form>"
        slip = f"<a href='/uploads/{t['slip']}' target='_blank'>ดูสลิป</a>" if t['slip'] else ""
        body += f"<p><b>{t['username']}</b> {int(t['amount'])} บาท - {t['method']} - {t['status']} - ซอง: {t['envelope_link']} {slip} {btns}</p>"
    body += "</div>"
    body += "<div class='box'><h3>🔑 สร้างคีย์ตัวแทน</h3><form method='post' action='/admin'><input type='hidden' name='act' value='add_agent_key'><input name='code' placeholder='คีย์ (ว่างไว้ = สุ่มให้)'><input name='discount' type='number' placeholder='ส่วนลด %'><input name='days' type='number' placeholder='กี่วัน'><input name='price' type='text' inputmode='decimal' placeholder='ราคาคีย์'><button>สร้างคีย์ตัวแทน</button></form>"
    for ak in agent_keys: body += f"<p>🔑 {ak['code']} - ลด {ak['discount']}% - {ak['days']} วัน - {'ใช้แล้ว' if ak['used'] else 'ยังไม่ใช้'}</p>"
    body += "</div>"
    body += "<div class='box'><h3>🎫 โค้ดรับเครดิต</h3><form method='post' action='/admin'><input type='hidden' name='act' value='add_credit'><input name='code' placeholder='โค้ด'><input name='amount' type='text' inputmode='decimal' placeholder='coin'><button>สร้างโค้ด</button></form>"
    for cc in credits: body += f"<p>{cc['code']} = {int(cc['amount'])} coin</p>"
    body += "</div><div class='box'><h3>👥 สมาชิก</h3>"
    for us in users: body += f"<p>{us['username']} - {int(us['coin'])} coin - {us['role']}</p>"
    body += "</div>"
    return body

@app.route('/profile', methods=['GET','POST'])
def profile():
    u = cur()
    if not u: return redirect('/login')
    c = db()
    if request.method=='POST':
        act = request.form.get('act')
        if act=='topup':
            amt = float(request.form.get('amount',0) or 0); method = request.form.get('method','พร้อมเพย์')
            slip = request.files.get('slip'); sname=""
            if slip and slip.filename:
                sname = secrets.token_hex(4)+"_"+slip.filename; slip.save(os.path.join(UPLOAD_FOLDER, sname))
            env = request.form.get('envelope_link',''); phone = request.form.get('phone','')
            c.execute("INSERT INTO topups(username,amount,method,slip,envelope_link,phone,status,date) VALUES(?,?,?,?,?,?, 'pending', ?)", (u['username'], amt, method, sname, env, phone, str(datetime.datetime.now()))); c.commit()
            st = get_setting()
            if safe(st,'auto_check',1)==1 and amt>0:
                c.execute("UPDATE users SET coin=coin+? WHERE id=?", (amt, u['id']))
                c.execute("UPDATE topups SET status='approved' WHERE username=? AND amount=? AND status='pending'", (u['username'], amt)); c.commit(); c.close()
                add_notify('topup', u['username'], amt, f"💰 เติมเงินอัตโนมัติ! {u['username']} เติม {int(amt)} บาท", f"วิธี: {method}", "/admin")
                return base(f"<div class='box'>✅ เติมเงินอัตโนมัติสำเร็จ! ได้รับ {int(amt)} coin แล้ว</div>")
            is_env = 'ซอง' in method or env.strip()!=""
            if is_env: add_notify('envelope', u['username'], amt, f"🎁 ใส่ซอง! {u['username']} ใส่ซอง {int(amt)} บาท", f"วิธี: {method} | ลิงก์: {env} | เบอร์: {phone}", "/admin")
            else: add_notify('topup', u['username'], amt, f"💰 เติมเงิน! {u['username']} เติม {int(amt)} บาท", f"วิธี: {method} | สลิป: {sname}", "/admin")
            c.close(); return base("<div class='box'>✅ ส่งยอดแล้ว รอเจ้าของอนุมัติ</div>")
        if act=='redeem_credit':
            code = request.form.get('code','').strip()
            cc = c.execute("SELECT * FROM credit_codes WHERE code=? AND used=0", (code,)).fetchone()
            if not cc: c.close(); return base("<div class='box'>❌ โค้ดผิด / ใช้แล้ว</div>")
            c.execute("UPDATE credit_codes SET used=1, used_by=? WHERE id=?", (u['username'], cc['id']))
            c.execute("UPDATE users SET coin=coin+? WHERE id=?", (cc['amount'], u['id'])); c.commit()
            add_notify('credit', u['username'], cc['amount'], f"🎫 {u['username']} ใส่โค้ด {code}", f"ได้ {int(cc['amount'])} coin", "/admin")
            c.close(); return base(f"<div class='box'>✅ ได้รับ {int(cc['amount'])} coin แล้ว!</div>")
        if act=='redeem_agent':
            code = request.form.get('agent_code','').strip()
            ak = c.execute("SELECT * FROM agent_keys WHERE code=? AND used=0", (code,)).fetchone()
            if not ak: c.close(); return base("<div class='box'>❌ คีย์ตัวแทนผิด / ใช้แล้ว</div>")
            expire = str(datetime.datetime.now() + timedelta(days=ak['days']))
            c.execute("UPDATE agent_keys SET used=1, used_by=? WHERE id=?", (u['username'], ak['id']))
            c.execute("INSERT OR REPLACE INTO agents(username,discount,expire,date) VALUES(?,?,?,?)", (u['username'], ak['discount'], expire, str(datetime.datetime.now())))
            c.execute("UPDATE users SET role='agent' WHERE id=?", (u['id'],)); c.commit()
            add_notify('agent', u['username'], 0, f"👑 {u['username']} สมัครตัวแทนแล้ว! คีย์ {code}", f"ส่วนลด {ak['discount']}% | หมดอายุ {expire}", "/admin")
            c.close(); return base(f"<div class='box'>✅ เป็นตัวแทนแล้ว! ได้ส่วนลด {ak['discount']}% ถึง {expire}</div>")
        if act=='avatar':
            f = request.files.get('avatar')
            if f and f.filename:
                fn = secrets.token_hex(4)+"_"+f.filename; f.save(os.path.join(UPLOAD_FOLDER, fn))
                c.execute("UPDATE users SET avatar=? WHERE id=?", (fn, u['id'])); c.commit()
            c.close(); return redirect('/profile')
    my = c.execute("SELECT * FROM topups WHERE username=? ORDER BY id DESC LIMIT 10", (u['username'],)).fetchall()
    is_agent = c.execute("SELECT * FROM agents WHERE username=?", (u['username'],)).fetchone()
    c.close(); st = get_setting(); av = safe(u,'avatar','')
    avh = f"<img src='/uploads/{av}' style='width:80px;height:80px;border-radius:50%;object-fit:cover'>" if av else "👤"
    body = f"<div class='box' style='text-align:center'>{avh}<h2>👤 {u['username']}</h2><p>💰 coin: <b style='color:#00ff88'>{int(u['coin'])}</b> | {u['role']}</p><form method='post' enctype='multipart/form-data'><input type='hidden' name='act' value='avatar'><input type='file' name='avatar'><button>เปลี่ยนรูปโปรไฟล์</button></form></div>"
    if is_agent:
        body += f"<div class='box' style='border:1px solid gold'><h3>👑 ตัวแทนของมึง</h3><p>ส่วนลด: {is_agent['discount']}% | หมดอายุ: {is_agent['expire']}</p></div>"
    else:
        body += "<div class='box'><h3>🔑 ใส่คีย์ตัวแทน</h3><form method='post'><input type='hidden' name='act' value='redeem_agent'><input name='agent_code' placeholder='ใส่คีย์ เช่น TIM-AGENT-100'><button>เปิดใช้งานตัวแทน</button></form></div>"
    body += f"<div class='box'><h3>💰 เติมเงิน / ใส่ซอง</h3><p style='color:#888'>พร้อมเพย์: {safe(st,'promptpay','-')} | ทรูมันนี่: {safe(st,'truemoney_phone','-')} | ตรวจอัตโนมัติ: {'เปิด ✅' if safe(st,'auto_check',1)==1 else 'ปิด ❌'}</p><form method='post' enctype='multipart/form-data'><input type='hidden' name='act' value='topup'><input name='amount' type='text' inputmode='decimal' placeholder='จำนวนเงิน'><select name='method'><option>พร้อมเพย์</option><option>ทรูมันนี่</option><option>ซองทรูมันนี่</option><option>โอนธนาคาร</option></select><input name='envelope_link' placeholder='ลิงก์ซองทรูมันนี่ (ถ้าใส่ซอง)'><input name='phone' placeholder='เบอร์ที่โอน'><input type='file' name='slip'><button>ส่งยอดเติมเงิน</button></form></div>"
    body += "<div class='box'><h3>🎫 ใส่โค้ดรับเครดิต</h3><form method='post'><input type='hidden' name='act' value='redeem_credit'><input name='code' placeholder='ใส่โค้ด'><button>แลกเครดิต</button></form></div>"
    if u['role'] in ['owner','admin']:
        body += admin_panel_html(u)
    else:
        body += "<div class='box'><h3>📜 ประวัติเติมเงิน</h3>"
        for t in my: body += f"<p>💰 {int(t['amount'])} บาท - {t['method']} - {t['status']}</p>"
        body += "<a href='/history'><button>ดูประวัติซื้อของ</button></a></div>"
    return base(body)

@app.route('/history')
def history():
    u = cur()
    if not u: return redirect('/login')
    c = db(); orders = c.execute("SELECT * FROM orders WHERE username=? ORDER BY id DESC", (u['username'],)).fetchall(); c.close()
    body = "<div class='box'><h2>📜 ประวัติซื้อของ</h2>"
    for o in orders: body += f"<p>🛒 {o['product_name']} x{o['qty']} = {int(o['total'])} บาท<br><span style='color:#00ff88'>โค้ด: {o['codes']}</span><br><span style='color:#888'>{o['date']}</span></p><hr>"
    if not orders: body += "<p>ยังไม่มีประวัติ</p>"
    body += "</div>"; return base(body)

@app.route('/notifications')
def notifications():
    u = cur()
    if not u or u['role'] not in ['owner','admin']: return redirect('/')
    c = db(); notis = c.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 50").fetchall(); c.close()
    body = "<div class='box'><h2>🔔 แจ้งเตือนเจ้าของเท่านั้น</h2><form method='post' action='/notifications/read_all'><button>✅ อ่านทั้งหมดแล้ว</button></form></div>"
    for n in notis:
        icon = "💰" if n['type']=='topup' else ("🎁" if n['type']=='envelope' else ("🎫" if n['type']=='credit' else ("🛒" if n['type']=='order' else "🔔")))
        bg = "#1a1a1a" if n['is_read']==1 else "#1e2a3a"
        body += f"<div class='box' style='background:{bg}'><b>{icon} {n['message']}</b><p style='color:#aaa;font-size:13px'>{n['detail']} | {n['date']}</p><a href='{n['link']}'><button>ไปจัดการ →</button></a><form method='post' action='/notifications/read/{n['id']}'><button style='background:#222'>อ่านแล้ว</button></form></div>"
    if not notis: body += "<div class='box'>ยังไม่มีแจ้งเตือน</div>"
    return base(body)

@app.route('/notifications/read/<int:nid>', methods=['POST'])
def read_one(nid):
    u = cur()
    if not u or u['role'] not in ['owner','admin']: return redirect('/')
    c = db(); c.execute("UPDATE notifications SET is_read=1 WHERE id=?", (nid,)); c.commit(); c.close(); return redirect('/notifications')
@app.route('/notifications/read_all', methods=['POST'])
def read_all():
    u = cur()
    if not u or u['role'] not in ['owner','admin']: return redirect('/')
    c = db(); c.execute("UPDATE notifications SET is_read=1"); c.commit(); c.close(); return redirect('/notifications')
@app.route('/api/unread')
def api_unread():
    u = cur()
    if not u or u['role'] not in ['owner','admin']: return {"unread":0}
    return {"unread": unread_count()}

@app.route('/admin', methods=['GET','POST'])
def admin():
    u = cur()
    if not u or u['role'] not in ['owner','admin']: return redirect('/login')
    c = db()
    if request.method=='POST':
        act = request.form.get('act')
        if act=='settings':
            c.execute("UPDATE settings SET shop_name=?, promptpay=?, truemoney_phone=?, auto_check=? WHERE id=1", (request.form.get('shop_name','tim SHOP'), request.form.get('promptpay',''), request.form.get('truemoney_phone',''), 1 if request.form.get('auto_check') else 0))
            for field in ['logo','banner']:
                f = request.files.get(field)
                if f and f.filename:
                    fn = secrets.token_hex(4)+"_"+f.filename; f.save(os.path.join(UPLOAD_FOLDER, fn))
                    c.execute(f"UPDATE settings SET {field}=? WHERE id=1", (fn,))
            c.commit()
        if act=='add_zone':
            zimg = request.files.get('zone_img'); zname=""
            if zimg and zimg.filename:
                zname = secrets.token_hex(4)+"_"+zimg.filename; zimg.save(os.path.join(UPLOAD_FOLDER, zname))
            c.execute("INSERT INTO zones(name,icon,order_num,img) VALUES(?,?,?,?)", (request.form.get('zone_name'), request.form.get('zone_icon','🔥'), request.form.get('zone_order',0), zname)); c.commit()
        if act=='edit_zone':
            zimg = request.files.get('zone_img')
            if zimg and zimg.filename:
                zname = secrets.token_hex(4)+"_"+zimg.filename; zimg.save(os.path.join(UPLOAD_FOLDER, zname))
                c.execute("UPDATE zones SET name=?, icon=?, order_num=?, img=? WHERE id=?", (request.form.get('zone_name'), request.form.get('zone_icon','🔥'), request.form.get('zone_order',0), zname, request.form.get('zone_id')))
            else:
                c.execute("UPDATE zones SET name=?, icon=?, order_num=? WHERE id=?", (request.form.get('zone_name'), request.form.get('zone_icon','🔥'), request.form.get('zone_order',0), request.form.get('zone_id')))
            c.commit()
        if act=='del_zone':
            c.execute("DELETE FROM zones WHERE id=?", (request.form.get('zone_id'),)); c.commit()
        if act=='add_product':
            stock = request.form.get('stock','').replace(',', '\\n')
            img_f = request.files.get('img'); img_name=""
            if img_f and img_f.filename:
                img_name = secrets.token_hex(4)+"_"+img_f.filename; img_f.save(os.path.join(UPLOAD_FOLDER, img_name))
            c.execute("INSERT INTO products(zone_id,name,price,desc,img,stock,date) VALUES(?,?,?,?,?,?,?)", (request.form.get('zone_id'), request.form.get('name'), parse_price(request.form.get('price')), request.form.get('desc'), img_name, stock, str(datetime.datetime.now()))); c.commit()
        if act=='edit_product':
            c.execute("UPDATE products SET name=?, price=?, desc=? WHERE id=?", (request.form.get('name'), parse_price(request.form.get('price')), request.form.get('desc'), request.form.get('pid'))); c.commit()
        if act=='del_product':
            c.execute("DELETE FROM products WHERE id=?", (request.form.get('pid'),)); c.commit()
        if act=='add_variant':
            stock = request.form.get('variant_stock','').replace(',', '\\n')
            c.execute("INSERT INTO variants(product_id,name,price,stock,date) VALUES(?,?,?,?,?)", (request.form.get('product_id'), request.form.get('variant_name'), parse_price(request.form.get('variant_price')), stock, str(datetime.datetime.now()))); c.commit()
        if act=='edit_variant_price':
            c.execute("UPDATE variants SET name=?, price=? WHERE id=?", (request.form.get('variant_name'), parse_price(request.form.get('variant_price')), request.form.get('variant_id'))); c.commit()
        if act=='del_variant':
            c.execute("DELETE FROM variants WHERE id=?", (request.form.get('variant_id'),)); c.commit()
        if act=='topup_action':
            t = c.execute("SELECT * FROM topups WHERE id=?", (request.form.get('tid'),)).fetchone()
            if t:
                if request.form.get('action')=='approve':
                    c.execute("UPDATE users SET coin=coin+? WHERE username=?", (t['amount'], t['username']))
                    c.execute("UPDATE topups SET status='approved' WHERE id=?", (t['id'],))
                else: c.execute("UPDATE topups SET status='rejected' WHERE id=?", (t['id'],))
                c.commit()
        if act=='add_credit':
            try: c.execute("INSERT INTO credit_codes(code,amount) VALUES(?,?)", (request.form.get('code'), parse_price(request.form.get('amount')))); c.commit()
            except: pass
        if act=='del_credit':
            c.execute("DELETE FROM credit_codes WHERE id=?", (request.form.get('cid'),)); c.commit()
        if act=='add_agent_key':
            code = request.form.get('code','').strip()
            if not code: code = "TIM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            try: c.execute("INSERT INTO agent_keys(code,discount,days,price,created_by,date) VALUES(?,?,?,?,?,?)", (code, request.form.get('discount',10), request.form.get('days',30), parse_price(request.form.get('price',0)), u['username'], str(datetime.datetime.now()))); c.commit()
            except: pass
        if act=='del_agent_key':
            c.execute("DELETE FROM agent_keys WHERE id=?", (request.form.get('kid'),)); c.commit()
    c.close()
    return redirect('/profile')

if __name__=='__main__':
    import os
    init()
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    
    