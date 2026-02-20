import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "exhub_secure_key_99"
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, role TEXT, nid TEXT, status TEXT DEFAULT "Active")')
    cursor.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, desc TEXT, want TEXT, image TEXT, user_email TEXT, category TEXT, featured INTEGER DEFAULT 0, status TEXT DEFAULT "Pending")')
    cursor.execute('CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, product_id INTEGER, trxid TEXT, method TEXT, status TEXT DEFAULT "Pending")')
    cursor.execute('CREATE TABLE IF NOT EXISTS site_info (id INTEGER PRIMARY KEY, about TEXT, contact TEXT, refund TEXT, address TEXT)')
    if not cursor.execute("SELECT * FROM site_info").fetchone():
        cursor.execute("INSERT INTO site_info (id, about, contact, refund, address) VALUES (1, 'About us...', '০১৭১...', 'Refund Policy...', 'Gazipur')")
    conn.commit()
    conn.close()

init_db()

STYLE = """
<style>
    body { background-color: #0d1b2a; font-family: 'Segoe UI', sans-serif; color: white; margin: 0; }
    nav { background: #1b263b; padding: 10px 50px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f77f00; }
    nav a { color: #f77f00; text-decoration: none; font-weight: bold; margin: 0 10px; }
    .container { padding: 20px; text-align: center; }
    .card { background: white; color: #1b263b; padding: 25px; border-radius: 15px; width: 80%; max-width: 600px; margin: 20px auto; text-align: left; box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
    input, textarea, select { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
    .btn { width: 100%; background: #f77f00; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; text-decoration:none; display:block; text-align:center; }
    .footer { margin-top: 50px; padding: 20px; background: #1b263b; font-size: 13px; text-align: center; }
    .footer a { color: #f77f00; margin: 0 15px; text-decoration: none; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; color: black; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    .featured-tag { background: #ffd700; color: black; padding: 2px 8px; border-radius: 5px; font-size: 12px; font-weight: bold; }
</style>
"""

NAV = """
<nav>
    <div class="logo"><a href="/" style="font-size:24px; color:#f77f00;">ExHub</a></div>
    <div>
        <a href="/">Marketplace</a>
        {% if 'user' in session %}
            <a href="/upload">Upload</a>
            <a href="/profile">Profile</a>
            {% if session['role'] == 'admin' %} <a href="/admin" style="color:cyan;">অ্যাডমিন</a> {% endif %}
            <a href="/logout" style="color:red;">Logout</a>
        {% else %}
            <a href="/login">Login</a> | <a href="/register">Registration</a>
        {% endif %}
    </div>
</nav>
"""

FOOTER = """
<div class="footer">
    <a href="/about">About</a> | <a href="/contact">Contact</a> | <a href="/terms">Terms</a> | <a href="/refund">Refund</a>
    <p>© 2026 ExchangeHub | All Rights Reserved</p>
</div>
"""

@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    items = conn.execute("SELECT * FROM products WHERE status='Approved' ORDER BY featured DESC, id DESC").fetchall()
    conn.close()
    return render_template_string(STYLE + NAV + """<div class="container"><h2>Marketplace</h2><div style="display:flex; flex-wrap:wrap; gap:20px; justify-content:center;">{% for i in items %}<div class="card" style="width:220px; background:#1b263b; color:white;">{% if i[7]==1 %}<span class="featured-tag">FEATURED ⭐</span>{% endif %}<img src="/static/uploads/{{i[4]}}" style="width:100%; border-radius:8px; margin-top:5px;"><h3 style="margin:10px 0;">{{i[1]}}</h3><p style="font-size:14px; color:#ddd;">In exchange: {{i[3]}}</p></div>{% endfor %}</div></div>""" + FOOTER, items=items)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin': return "Access Denied!"
    conn = sqlite3.connect('database.db')
    if request.method == 'POST' and 'site_up' in request.form:
        conn.execute("UPDATE site_info SET about=?, contact=?, refund=?, address=? WHERE id=1", (request.form.get('a'), request.form.get('c'), request.form.get('r'), request.form.get('ad')))
        conn.commit()
    pending_p = conn.execute("SELECT * FROM products WHERE status='Pending'").fetchall()
    pending_pay = conn.execute("SELECT payments.*, products.name FROM payments JOIN products ON payments.product_id = products.id WHERE payments.status='Pending'").fetchall()
    site = conn.execute("SELECT * FROM site_info WHERE id=1").fetchone()
    conn.close()
    return render_template_string(STYLE + NAV + """<div class="container"><h2>অ্যাডমিন প্যানেল</h2>
    <div class="card"><h3>পেন্ডিং পেমেন্ট</h3><table><tr><th>পণ্য</th><th>TrxID</th><th>অ্যাকশন</th></tr>{% for py in pending_pay %}<tr><td>{{py[4]}}</td><td>{{py[3]}}</td><td><a href="/approve_pay/{{py[2]}}/{{py[0]}}">অ্যাপ্রুভ</a></td></tr>{% endfor %}</table></div>
    <div class="card"><h3>পেন্ডিং পণ্য</h3>{% for p in pending_p %}<p>{{p[1]}} - <a href="/approve_prod/{{p[0]}}">অ্যাপ্রুভ করুন</a></p>{% endfor %}</div>
    <div class="card"><h3>সাইট সেটিংস</h3><form method="POST"><input type="hidden" name="site_up" value="1"><input name="ad" value="{{s[4]}}"><input name="c" value="{{s[2]}}"><textarea name="a">{{s[1]}}</textarea><textarea name="r">{{s[3]}}</textarea><button class="btn">আপডেট</button></form></div></div>""" + FOOTER, pending_p=pending_p, pending_pay=pending_pay, s=site)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = sqlite3.connect('database.db')
        user = conn.execute("SELECT * FROM users WHERE email=?", (request.form.get('e'),)).fetchone()
        conn.close()
        if user and check_password_hash(user[3], request.form.get('p')):
            session['user'], session['role'] = user[2], user[4]
            return redirect(url_for('home'))
    return render_template_string(STYLE + NAV + """<div class="card"><h2>Login</h2><form method="POST"><input name="e" placeholder="Email"><input name="p" type="password" placeholder="Password"><button class="btn">Enter</button></form></div>""" + FOOTER)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        pwd = generate_password_hash(request.form.get('p'))
        email = request.form.get('e')
        role = 'admin' if email == 'admin@exchange.com' else 'user'
        conn = sqlite3.connect('database.db')
        try:
            conn.execute("INSERT INTO users (name, email, nid, password, role) VALUES (?,?,?,?,?)", (request.form.get('u'), email, request.form.get('n'), pwd, role))
            conn.commit(); return redirect(url_for('login'))
        except: return "This Email is used!"
        finally: conn.close()
    return render_template_string(STYLE + NAV + """<div class="card"><h2>Registration</h2><form method="POST"><input name="u" placeholder="Name"><input name="e" placeholder="Email"><input name="n" placeholder="NID"><input name="p" type="password" placeholder="Password"><button class="btn">Sign up</button></form></div>""" + FOOTER)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['img']; fname = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO products (name, desc, want, image, user_email) VALUES (?,?,?,?,?)", (request.form.get('n'), request.form.get('d'), request.form.get('w'), fname, session['user']))
        conn.commit(); conn.close(); return "Successfull! Please wait for approval।"
    return render_template_string(STYLE + NAV + """<div class="card"><h2>Upload product</h2><form method="POST" enctype="multipart/form-data"><input name="n" placeholder="Proudct Name" required><textarea name="d" placeholder="About product"></textarea><input name="w" placeholder="What would you want?" required><input type="file" name="img" required><button class="btn">Upload</button></form></div>""" + FOOTER)

@app.route('/approve_prod/<int:id>')
def approve_prod(id):
    if session.get('role') == 'admin':
        conn = sqlite3.connect('database.db'); conn.execute("UPDATE products SET status='Approved' WHERE id=?", (id,)); conn.commit(); conn.close()
    return redirect(url_for('admin'))

@app.route('/profile')
def profile():
    if 'user' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    my_items = conn.execute("SELECT * FROM products WHERE user_email=?", (session['user'],)).fetchall()
    conn.close()
    return render_template_string(STYLE + NAV + """<div class="container"><h2>My products</h2><div style="display:flex; flex-wrap:wrap; gap:20px; justify-content:center;">{% for i in my_items %}<div class="card" style="width:250px;"><h3>{{i[1]}}</h3><p>Sta: <b>{{i[8]}}</b></p></div>{% endfor %}</div></div>""" + FOOTER, my_items=my_items)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/static/uploads/<f>')
def uploaded_file(f): return send_from_directory(app.config['UPLOAD_FOLDER'], f)

if __name__ == '__main__':
    app.run(debug=True)