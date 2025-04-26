from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# Initialize DB
def init_db():
    conn = sqlite3.connect('assets.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY,
            asset_name TEXT,
            asset_type TEXT,
            assigned_to TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['GET', 'POST'])
def add_asset():
    if request.method == 'POST':
        asset_name = request.form['asset_name']
        asset_type = request.form['asset_type']
        assigned_to = request.form['assigned_to']
        status = request.form['status']

        conn = sqlite3.connect('assets.db')
        c = conn.cursor()
        c.execute("INSERT INTO assets (asset_name, asset_type, assigned_to, status) VALUES (?, ?, ?, ?)",
                  (asset_name, asset_type, assigned_to, status))
        conn.commit()
        conn.close()

        return redirect('/view')

    return render_template('add_asset.html')

@app.route('/view')
def view_assets():
    conn = sqlite3.connect('assets.db')
    c = conn.cursor()
    c.execute("SELECT * FROM assets")
    assets = c.fetchall()
    conn.close()
    return render_template('view_assets.html', assets=assets)

if __name__ == '__main__':
    app.run(debug=True)
