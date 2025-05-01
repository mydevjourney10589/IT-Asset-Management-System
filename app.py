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
    c.execute('''
        CREATE TABLE IF NOT EXISTS assignment_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER,
            employee_name TEXT,
            assignment_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_id) REFERENCES assets (id)
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
        # Get the id of the newly inserted asset
        new_asset_id = c.lastrowid
        # Log the initial assignment in assignment_history
        if assigned_to: # Only log if assigned_to is not empty
            c.execute("INSERT INTO assignment_history (asset_id, employee_name) VALUES (?, ?)",
                      (new_asset_id, assigned_to))
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

@app.route('/asset-history/<int:asset_id>')
def view_asset_history(asset_id):
    conn = sqlite3.connect('assets.db')
    conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    c = conn.cursor()

    # Get asset name
    c.execute("SELECT asset_name FROM assets WHERE id = ?", (asset_id,))
    asset = c.fetchone()
    asset_name = asset['asset_name'] if asset else "Unknown Asset"

    # Get assignment history
    c.execute("""
        SELECT employee_name, assignment_timestamp
        FROM assignment_history
        WHERE asset_id = ?
        ORDER BY assignment_timestamp DESC
    """, (asset_id,))
    history_records = c.fetchall()

    conn.close()

    return render_template('asset_history.html',
                           history=history_records,
                           asset_name=asset_name,
                           asset_id=asset_id)

if __name__ == '__main__':
    app.run(debug=True)
