from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from collections import defaultdict
from datetime import datetime
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount REAL,
        category TEXT,
        date TEXT
    )''')

    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "admin123"))
    except:
        pass

    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/')
        else:
            error = "❌ Invalid username or password"

    return render_template("login.html", error=error)

# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None

    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=?", (u,))
        if c.fetchone():
            error = "⚠️ Username already exists"
            return render_template("register.html", error=error)

        c.execute("INSERT INTO users VALUES (NULL, ?, ?)", (u, p))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template("register.html", error=error)

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------- DASHBOARD ----------
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # 🔍 Filters
    search = request.args.get("search")
    month = request.args.get("month")

    query = "SELECT * FROM transactions WHERE user_id=?"
    params = [session['user_id']]

    if search:
        query += " AND category LIKE ?"
        params.append(f"%{search}%")

    if month:
        query += " AND date LIKE ?"
        params.append(f"{month}%")

    c.execute(query, params)
    data = c.fetchall()

    # 💰 Calculations
    income = sum(i[3] for i in data if i[2] == "income")
    expense = sum(i[3] for i in data if i[2] == "expense")
    balance = income - expense

    from collections import defaultdict
    category_data = defaultdict(float)

    for row in data:
        if row[2] == "expense":
            category_data[row[4]] += row[3]

    # 🧠 Suggestions
    suggestions = []
    if expense > income:
        suggestions.append("⚠️ Expenses exceed income")
    if expense > 0.8 * income:
        suggestions.append("⚠️ Spending too high (>80%)")
    if category_data:
        max_cat = max(category_data, key=category_data.get)
        suggestions.append(f"💡 Highest spending: {max_cat}")
    if balance > 0:
        suggestions.append("✅ Good savings!")

    conn.close()

    return render_template("index.html",
                           data=data,
                           income=income,
                           expense=expense,
                           balance=balance,
                           categories=list(category_data.keys()),
                           amounts=list(category_data.values()),
                           suggestions=suggestions)




# ---------- ADD ----------
@app.route('/add', methods=['GET','POST'])
def add():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        t = request.form['type']
        amt = float(request.form['amount'])
        cat = request.form['category']
        date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("INSERT INTO transactions VALUES (NULL, ?, ?, ?, ?, ?)",
                  (session['user_id'], t, amt, cat, date))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("add.html")


@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("DELETE FROM transactions WHERE id=? AND user_id=?",
              (id, session['user_id']))

    conn.commit()
    conn.close()

    return redirect('/')

# ---------- EXPORT ----------
@app.route('/export/excel')
def export_excel():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")

    df = pd.read_sql_query(
        "SELECT type, amount, category, date FROM transactions WHERE user_id=?",
        conn,
        params=(session['user_id'],)
    )

    conn.close()

    path = "expenses.xlsx"
    df.to_excel(path, index=False)

    return send_file(path, as_attachment=True)
@app.route('/export/pdf')
def export_pdf():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""SELECT type, amount, category, date 
                 FROM transactions WHERE user_id=?""",
              (session['user_id'],))

    data = c.fetchall()
    conn.close()

    path = "expenses.pdf"
    doc = SimpleDocTemplate(path)

    table = Table([["Type","Amount","Category","Date"]] + data)
    doc.build([table])

    return send_f
    ile(path, as_attachment=True)

@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == 'POST':
        t = request.form['type']
        amt = request.form['amount']
        cat = request.form['category']

        c.execute("""UPDATE transactions 
                     SET type=?, amount=?, category=? 
                     WHERE id=? AND user_id=?""",
                  (t, amt, cat, id, session['user_id']))

        conn.commit()
        conn.close()

        return redirect('/')

    c.execute("SELECT * FROM transactions WHERE id=? AND user_id=?",
              (id, session['user_id']))

    data = c.fetchone()
    conn.close()

    return render_template("edit.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)