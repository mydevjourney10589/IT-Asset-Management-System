from flask import Flask, render_template, request, redirect, session, url_for, Response # Import Response
import sqlite3
import os # Import os module
import io # Import io for CSV
import csv # Import csv module

app = Flask(__name__)
app.secret_key = os.urandom(24) # Add secret key for sessions

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

        # Retrieve last status filter from session, default to 'Active'
        last_status = session.get('last_status_filter', 'Active')
        # Redirect back to the view page with the last used filter applied
        return redirect(url_for('view_assets', status=last_status))

    return render_template('add_asset.html')

@app.route('/view')
def view_assets():
    requested_status = request.args.get('status') # Get status from the actual request
    # Default to 'Active' if no status is provided in the URL
    status_filter = requested_status if requested_status is not None else 'Active'
    # Store the applied filter in the session
    session['last_status_filter'] = status_filter
    assets = get_assets_by_status(status_filter) # Use the helper function with the determined filter
    # Pass the filter actually used (default or requested) to the template
    return render_template('view_assets.html', assets=assets, current_status=status_filter)

@app.route('/export_csv')
def export_csv():
    """Exports the currently filtered assets to a CSV file."""
    requested_status = request.args.get('status')
    # Default to 'Active' if no status is provided in the URL query parameter
    status_filter = requested_status if requested_status is not None else 'Active'

    # Fetch the assets using the same logic as the view route
    assets = get_assets_by_status(status_filter)

    # Generate CSV data in memory
    si = io.StringIO()
    writer = csv.writer(si)

    # Write header row (matching the columns in view_assets.html)
    writer.writerow(['Asset Name', 'Type', 'Assigned To', 'Status'])

    # Write data rows from the fetched assets (indices 1, 2, 3, 4)
    for asset in assets:
        writer.writerow([asset[1], asset[2], asset[3], asset[4]])

    csv_data = si.getvalue()

    # Create the Flask Response object
    response = Response(csv_data, mimetype='text/csv')
    # Set headers for file download
    response.headers['Content-Disposition'] = 'attachment; filename=assets.csv'

    return response

# Test Runner Function
def run_tests():
    print("Running tests...")
    populate_test_data() # Ensure clean test data
    client = app.test_client() # Create a test client

    print("\n--- Testing get_assets_by_status ---")
    # Test cases for get_assets_by_status: (status_filter, expected_count, expected_statuses)
    test_cases = [
        ('Active', 3, {'Active'}),
        ('Retired', 2, {'Retired'}),
        ('Missing', 1, {'Missing'}),
        ('all', 6, {'Active', 'Retired', 'Missing'}), # Case-insensitivity check for 'all'
        ('All', 6, {'Active', 'Retired', 'Missing'}),
        # (None, 6, {'Active', 'Retired', 'Missing'}), # Old Default (no filter shows all) - No longer applies
        (None, 3, {'Active'}), # New Default (no filter shows 'Active')
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

    print("\n--- Testing /view session setting ---")
    view_session_tests_passed = True
    test_view_statuses = ['Retired', 'All', 'Active', None] # Include None for default check
    for status in test_view_statuses:
        print(f"\nTesting /view with status: {status}")
        expected_session_status = status if status is not None else 'Active' # Determine expected status in session
        url = url_for('view_assets', status=status) if status is not None else url_for('view_assets')
        client.get(url) # Access the view page to set the session
        with client.session_transaction() as sess:
            actual_session_status = sess.get('last_status_filter')
            if actual_session_status == expected_session_status:
                 print(f"  [PASS] Session check: Expected '{expected_session_status}', Got '{actual_session_status}'")
            else:
                 print(f"  [FAIL] Session check: Expected '{expected_session_status}', Got '{actual_session_status}'")
                 view_session_tests_passed = False
                 all_tests_passed = False


    print("\n--- Testing /add redirect based on session ---")
    add_redirect_tests_passed = True
    test_redirect_statuses = ['Missing', 'Active', 'All']
    for test_status in test_redirect_statuses:
        print(f"\nTesting /add redirect with session status: {test_status}")
        # Manually set session variable for the test client
        with client.session_transaction() as sess:
            sess['last_status_filter'] = test_status

        # Simulate POST request to /add
        response = client.post(url_for('add_asset'), data={
            'asset_name': 'Test Asset',
            'asset_type': 'Test Type',
            'assigned_to': 'Tester',
            'status': 'Active' # Asset's own status doesn't affect redirect
        }, follow_redirects=False) # Don't follow the redirect automatically

        # Check redirect status code
        if response.status_code == 302:
            print(f"  [PASS] Redirect status code: Got {response.status_code}")
        else:
            print(f"  [FAIL] Redirect status code: Expected 302, Got {response.status_code}")
            add_redirect_tests_passed = False
            all_tests_passed = False

        # Check redirect location header
        expected_location = url_for('view_assets', status=test_status)
        actual_location = response.location
        # Normalize URLs for comparison (e.g., handle potential leading slashes or full URLs)
        if actual_location and actual_location.endswith(expected_location):
             print(f"  [PASS] Redirect location: Expected ends with '{expected_location}', Got '{actual_location}'")
        else:
             print(f"  [FAIL] Redirect location: Expected ends with '{expected_location}', Got '{actual_location}'")
             add_redirect_tests_passed = False
             all_tests_passed = False

    print("\n--- Testing /export_csv ---")
    csv_tests_passed = True
    # Define expected CSV outputs based on populate_test_data()
    # Note: csv.writer uses \r\n by default
    csv_header = "Asset Name,Type,Assigned To,Status\r\n"
    expected_csv = {
        'Active': csv_header + \
                  "Laptop 1,Hardware,Alice,Active\r\n" + \
                  "Software License,Software,Bob,Active\r\n" + \
                  "Keyboard,Hardware,Alice,Active\r\n",
        'Retired': csv_header + \
                   "Old Server,Hardware,Charlie,Retired\r\n" + \
                   "Retired Laptop,Hardware,Eve,Retired\r\n",
        'Missing': csv_header + \
                   "Missing Monitor,Hardware,Dana,Missing\r\n",
        'All': csv_header + \
               "Laptop 1,Hardware,Alice,Active\r\n" + \
               "Software License,Software,Bob,Active\r\n" + \
               "Old Server,Hardware,Charlie,Retired\r\n" + \
               "Missing Monitor,Hardware,Dana,Missing\r\n" + \
               "Keyboard,Hardware,Alice,Active\r\n" + \
               "Retired Laptop,Hardware,Eve,Retired\r\n",
        'None': csv_header + \
                "Laptop 1,Hardware,Alice,Active\r\n" + \
                "Software License,Software,Bob,Active\r\n" + \
                "Keyboard,Hardware,Alice,Active\r\n" # Default is Active
    }

    test_export_statuses = ['Active', 'Retired', 'Missing', 'All', None]
    for status in test_export_statuses:
        filter_key = status if status is not None else 'None' # Key for expected_csv dictionary
        print(f"\nTesting /export_csv with status: {status}")
        url = url_for('export_csv', status=status) if status is not None else url_for('export_csv')
        response = client.get(url)

        # Check status code
        if response.status_code == 200:
            print(f"  [PASS] Status code: Expected 200, Got {response.status_code}")
        else:
            print(f"  [FAIL] Status code: Expected 200, Got {response.status_code}")
            csv_tests_passed = False
            all_tests_passed = False

        # Check mimetype
        if response.mimetype == 'text/csv':
            print(f"  [PASS] Mimetype: Expected 'text/csv', Got '{response.mimetype}'")
        else:
            print(f"  [FAIL] Mimetype: Expected 'text/csv', Got '{response.mimetype}'")
            csv_tests_passed = False
            all_tests_passed = False

        # Check Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition', '')
        expected_disposition = 'attachment; filename=assets.csv'
        if expected_disposition in content_disposition:
            print(f"  [PASS] Content-Disposition: Expected contains '{expected_disposition}', Got '{content_disposition}'")
        else:
            print(f"  [FAIL] Content-Disposition: Expected contains '{expected_disposition}', Got '{content_disposition}'")
            csv_tests_passed = False
            all_tests_passed = False

        # Check CSV content
        actual_csv_content = response.data.decode('utf-8')
        expected_csv_content = expected_csv[filter_key]
        if actual_csv_content == expected_csv_content:
            print(f"  [PASS] CSV Content: Matches expected output.")
            # print(f"      Expected:\n{expected_csv_content}") # Optional: Print for verification
            # print(f"      Actual:\n{actual_csv_content}")   # Optional: Print for verification
        else:
            print(f"  [FAIL] CSV Content: Does not match expected output.")
            print(f"      Expected:\n{expected_csv_content}") # Print diffs on failure
            print(f"      Actual:\n{actual_csv_content}")   # Print diffs on failure
            csv_tests_passed = False
            all_tests_passed = False


    print("\n--------------------")
    if all_tests_passed:
        print("All tests passed!")
    else:
        print("Some tests FAILED!")
        if not view_session_tests_passed: print(" - /view session setting tests failed")
        if not add_redirect_tests_passed: print(" - /add redirect tests failed")
        if not csv_tests_passed: print(" - /export_csv tests failed") # Add CSV test result
    print("--------------------")
    return all_tests_passed


if __name__ == '__main__':
    # Run tests before starting the server
    test_result = run_tests()
    # Start the Flask app (optional, comment out if only running tests and tests passed)
    # if test_result:
    #    app.run(debug=True)
