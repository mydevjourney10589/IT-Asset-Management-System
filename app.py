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

# Database Helper Functions
def populate_test_data():
    """Clears the assets table and populates it with test data."""
    conn = sqlite3.connect('assets.db')
    c = conn.cursor()
    c.execute("DELETE FROM assets") # Clear existing data
    test_data = [
        ('Laptop 1', 'Hardware', 'Alice', 'Active'),
        ('Software License', 'Software', 'Bob', 'Active'),
        ('Old Server', 'Hardware', 'Charlie', 'Retired'),
        ('Missing Monitor', 'Hardware', 'Dana', 'Missing'),
        ('Keyboard', 'Hardware', 'Alice', 'Active'),
        ('Retired Laptop', 'Hardware', 'Eve', 'Retired')
    ]
    c.executemany("INSERT INTO assets (asset_name, asset_type, assigned_to, status) VALUES (?, ?, ?, ?)", test_data)
    conn.commit()
    conn.close()
    print("Test data populated.")

def get_assets_by_status(status_filter=None):
    """Fetches assets from the database, optionally filtering by status."""
    conn = sqlite3.connect('assets.db')
    c = conn.cursor()
    query = "SELECT * FROM assets"
    params = []
    if status_filter and status_filter.lower() != 'all':
        query += " WHERE status = ?"
        params.append(status_filter)

    c.execute(query, params)
    assets = c.fetchall()
    conn.close()
    return assets

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
    status_filter = request.args.get('status') # Get status from the actual request
    assets = get_assets_by_status(status_filter) # Use the helper function
    return render_template('view_assets.html', assets=assets, current_status=status_filter)

# Test Runner Function
def run_tests():
    print("Running tests...")
    populate_test_data() # Ensure clean test data

    # Test cases: (status_filter, expected_count, expected_statuses)
    test_cases = [
        ('Active', 3, {'Active'}),
        ('Retired', 2, {'Retired'}),
        ('Missing', 1, {'Missing'}),
        ('all', 6, {'Active', 'Retired', 'Missing'}), # Case-insensitivity check for 'all'
        ('All', 6, {'Active', 'Retired', 'Missing'}),
        (None, 6, {'Active', 'Retired', 'Missing'}), # Default (no filter)
        ('NonExistentStatus', 0, set()) # Test status with no assets
    ]

    all_tests_passed = True
    for status_filter, expected_count, expected_statuses in test_cases:
        print(f"\nTesting filter: {status_filter}")
        assets = get_assets_by_status(status_filter)
        actual_count = len(assets)
        actual_statuses = {asset[4] for asset in assets} # Extract status from tuple (index 4)

        # Check count
        if actual_count == expected_count:
            print(f"  [PASS] Count check: Expected {expected_count}, Got {actual_count}")
        else:
            print(f"  [FAIL] Count check: Expected {expected_count}, Got {actual_count}")
            all_tests_passed = False

        # Check statuses (only if expected count > 0)
        if expected_count > 0:
            if actual_statuses == expected_statuses:
                print(f"  [PASS] Status check: Expected {expected_statuses}, Got {actual_statuses}")
            else:
                print(f"  [FAIL] Status check: Expected {expected_statuses}, Got {actual_statuses}")
                all_tests_passed = False
        elif actual_count == 0: # If expected count is 0, ensure no assets were returned
             print(f"  [PASS] Status check: Correctly returned no assets.")
        else: # Should not happen if count check passed, but included for robustness
             print(f"  [FAIL] Status check: Expected 0 assets but got some.")
             all_tests_passed = False


    print("\n--------------------")
    if all_tests_passed:
        print("All tests passed!")
    else:
        print("Some tests FAILED!")
    print("--------------------")
    return all_tests_passed


if __name__ == '__main__':
    # Run tests before starting the server
    run_tests()
    # Start the Flask app (optional, comment out if only running tests)
    # app.run(debug=True)
