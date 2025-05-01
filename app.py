from flask import Flask # Keep Flask
import sqlite3
import os # Import os module
# Removed imports: render_template, request, redirect, session, url_for, Response, io, csv, re, Markup
from routes import routes_bp # Import the Blueprint

app = Flask(__name__)
app.secret_key = os.urandom(24) # Add secret key for sessions
app.register_blueprint(routes_bp) # Register the Blueprint

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
    # More diverse data for search testing
    test_data = [
        # ID=1
        ('Laptop 1 (Work)', 'Hardware', 'Alice Smith', 'Active'),
        # ID=2
        ('Software License (Adobe)', 'Software', 'Bob Johnson', 'Active'),
        # ID=3
        ('Old Server (Dell)', 'Hardware', 'Charlie Brown', 'Retired'),
        # ID=4
        ('Missing Monitor', 'Hardware', 'Dana Scully', 'Missing'),
        # ID=5
        ('Keyboard (USB)', 'Hardware', 'Alice Smith', 'Active'),
        # ID=6
        ('Retired Laptop (Old)', 'Hardware', 'Eve Adams', 'Retired'),
        # ID=7
        ('Docking Station', 'Hardware', 'Bob Johnson', 'Active'),
        # ID=8
        ('Projector', 'Hardware', 'Charlie Brown', 'Missing') # Charlie has assets in multiple statuses
    ]
    c.executemany("INSERT INTO assets (asset_name, asset_type, assigned_to, status) VALUES (?, ?, ?, ?)", test_data)
    conn.commit()
    conn.close()
    print("Test data populated.")

# get_assets_by_status moved to routes.py

# Jinja Custom Filter and Routes moved to routes.py

# Test Runner Function
def run_tests():
    print("Running tests...")
    populate_test_data() # Ensure clean test data
    client = app.test_client() # Create a test client
    all_tests_passed = True # Initialize overall test status

    # --- Test Section: get_assets_by_status ---
    print("\n--- Testing get_assets_by_status Helper ---")
    get_assets_tests_passed = True
    # Import the function from routes for direct testing
    from routes import get_assets_by_status
    # Test cases: (status_filter, search_term, expected_ids) - Using IDs for precise checks
    get_assets_test_cases = [
        # Status only
        ('Active', None, {1, 2, 5, 7}),
        ('Retired', None, {3, 6}),
        ('Missing', None, {4, 8}),
        ('All', None, {1, 2, 3, 4, 5, 6, 7, 8}),
        (None, None, {1, 2, 5, 7}), # Default status is Active
        ('NonExistentStatus', None, set()),
        # Search only (across all statuses)
        ('All', 'laptop', {1, 6}), # Case insensitive name
        ('All', 'alice', {1, 5}),   # Case insensitive assignee
        ('All', 'bob', {2, 7}),     # Assignee
        ('All', 'key', {5}),       # Partial name
        ('All', 'smi', {1, 5}),     # Partial assignee
        ('All', 'Dell', {3}),      # Case sensitive name part
        ('All', 'XYZ', set()),      # No match search
        ('All', '', {1, 2, 3, 4, 5, 6, 7, 8}), # Empty search = no search filter
        # Combined Status and Search
        ('Active', 'laptop', {1}),
        ('Active', 'alice', {1, 5}),
        ('Retired', 'laptop', {6}),
        ('Missing', 'monitor', {4}),
        ('Active', 'bob', {2, 7}),
        ('Active', 'xyz', set()), # No match within status
        (None, 'alice', {1, 5}), # Default status (Active) + search
        ('All', 'Brown', {3, 8}), # Assignee across statuses
        ('Retired', 'Brown', {3}), # Assignee within status
        ('Missing', 'Brown', {8}), # Assignee within status
    ]

    for status_filter, search_term, expected_ids in get_assets_test_cases:
        print(f"\nTesting helper: status='{status_filter}', search='{search_term}'")
        assets = get_assets_by_status(status_filter, search_term)
        actual_ids = {asset[0] for asset in assets} # Get asset IDs (index 0)

        if actual_ids == expected_ids:
            print(f"  [PASS] Helper results: Expected IDs {expected_ids}, Got {actual_ids}")
        else:
            print(f"  [FAIL] Helper results: Expected IDs {expected_ids}, Got {actual_ids}")
            get_assets_tests_passed = False
            all_tests_passed = False # Update overall status

    if not get_assets_tests_passed: print(" - get_assets_by_status tests failed")


    # --- Test Section: /view rendering (Simulated) ---
    # Note: Fully testing rendering requires HTML parsing or more advanced techniques.
    # We will focus on verifying the data passed to render_template using mocking.
    print("\n--- Testing /view route (Data Passed to Template) ---")
    view_render_tests_passed = True
    # We need unittest.mock for this
    try:
        from unittest.mock import patch
    except ImportError:
        print(" [SKIP] unittest.mock not available. Cannot test data passed to render_template.")
        view_render_tests_passed = False # Mark as skipped/failed
        all_tests_passed = False
    else:
        # Test cases: (status_param, search_param, expected_status_context, expected_search_context, expected_asset_ids)
        view_test_cases = [
            (None, None, 'Active', '', {1, 2, 5, 7}), # Default view
            ('Retired', None, 'Retired', '', {3, 6}), # Status only
            (None, 'laptop', 'Active', 'laptop', {1}), # Default status + Search
            ('All', 'alice', 'All', 'alice', {1, 5}),  # All status + Search
            ('Active', 'bob', 'Active', 'bob', {2, 7}), # Specific status + Search
            ('Missing', 'xyz', 'Missing', 'xyz', set()), # No results search
            ('All', '', 'All', '', {1, 2, 3, 4, 5, 6, 7, 8}), # Empty search
        ]

        for status_param, search_param, expected_status, expected_search, expected_ids in view_test_cases:
             print(f"\nTesting /view render: status='{status_param}', search='{search_param}'")
             # Build URL using url_for, handling None params
             query_params = {}
             if status_param is not None: query_params['status'] = status_param
             if search_param is not None: query_params['search_term'] = search_param
             url = url_for('view_assets', **query_params)

             # Patch render_template within this test's scope
             with patch('app.render_template') as mock_render:
                 client.get(url) # Make the request

                 # Check if render_template was called
                 if not mock_render.called:
                     print("  [FAIL] render_template was not called.")
                     view_render_tests_passed = False
                     all_tests_passed = False
                     continue

                 # Get the arguments passed to render_template
                 call_args, call_kwargs = mock_render.call_args
                 template_name = call_args[0]
                 context_assets = call_kwargs.get('assets', [])
                 context_status = call_kwargs.get('current_status', None)
                 context_search = call_kwargs.get('search_term', None)

                 # Verify template name
                 if template_name == 'view_assets.html':
                     print(f"  [PASS] Template name: Correct ('{template_name}')")
                 else:
                     print(f"  [FAIL] Template name: Expected 'view_assets.html', Got '{template_name}'")
                     view_render_tests_passed = False
                     all_tests_passed = False

                 # Verify context variables
                 actual_asset_ids = {asset[0] for asset in context_assets}
                 if actual_asset_ids == expected_ids:
                     print(f"  [PASS] Context assets: Expected IDs {expected_ids}, Got {actual_asset_ids}")
                 else:
                     print(f"  [FAIL] Context assets: Expected IDs {expected_ids}, Got {actual_asset_ids}")
                     view_render_tests_passed = False
                     all_tests_passed = False

                 if context_status == expected_status:
                     print(f"  [PASS] Context status: Expected '{expected_status}', Got '{context_status}'")
                 else:
                     print(f"  [FAIL] Context status: Expected '{expected_status}', Got '{context_status}'")
                     view_render_tests_passed = False
                     all_tests_passed = False

                 if context_search == expected_search:
                      print(f"  [PASS] Context search term: Expected '{expected_search}', Got '{context_search}'")
                 else:
                      print(f"  [FAIL] Context search term: Expected '{expected_search}', Got '{context_search}'")
                      view_render_tests_passed = False
                      all_tests_passed = False

        if not view_render_tests_passed: print(" - /view render tests failed")


    # --- Test Section: /view session setting ---
    # (Keep existing session tests, they remain relevant)
    print("\n--- Testing /view session setting ---")

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

    print("\n--- Testing /export_csv with Search ---")
    csv_tests_passed = True
    csv_header = "Asset Name,Type,Assigned To,Status\r\n"
    # Define expected CSV outputs for combined filter/search scenarios
    # Based on the *enhanced* test data
    expected_csv_search = {
        # Default status (Active), search 'alice' -> Laptop 1, Keyboard
        ('None', 'alice'): csv_header + \
                           "Laptop 1 (Work),Hardware,Alice Smith,Active\r\n" + \
                           "Keyboard (USB),Hardware,Alice Smith,Active\r\n",
        # All statuses, search 'bob' -> Software License, Docking Station
        ('All', 'bob'): csv_header + \
                        "Software License (Adobe),Software,Bob Johnson,Active\r\n" + \
                        "Docking Station,Hardware,Bob Johnson,Active\r\n",
        # Retired status, search 'laptop' -> Retired Laptop
        ('Retired', 'laptop'): csv_header + \
                               "Retired Laptop (Old),Hardware,Eve Adams,Retired\r\n",
        # Missing status, search 'Brown' -> Projector
        ('Missing', 'Brown'): csv_header + \
                              "Projector,Hardware,Charlie Brown,Missing\r\n",
        # Active status, search 'xyz' -> Header only
        ('Active', 'xyz'): csv_header,
        # All statuses, empty search -> All assets
        ('All', ''): csv_header + \
                     "Laptop 1 (Work),Hardware,Alice Smith,Active\r\n" + \
                     "Software License (Adobe),Software,Bob Johnson,Active\r\n" + \
                     "Old Server (Dell),Hardware,Charlie Brown,Retired\r\n" + \
                     "Missing Monitor,Hardware,Dana Scully,Missing\r\n" + \
                     "Keyboard (USB),Hardware,Alice Smith,Active\r\n" + \
                     "Retired Laptop (Old),Hardware,Eve Adams,Retired\r\n" + \
                     "Docking Station,Hardware,Bob Johnson,Active\r\n" + \
                     "Projector,Hardware,Charlie Brown,Missing\r\n",
         # Default status (Active), no search -> Active assets
        ('None', None): csv_header + \
                        "Laptop 1 (Work),Hardware,Alice Smith,Active\r\n" + \
                        "Software License (Adobe),Software,Bob Johnson,Active\r\n" + \
                        "Keyboard (USB),Hardware,Alice Smith,Active\r\n" + \
                        "Docking Station,Hardware,Bob Johnson,Active\r\n",
    }

    # Test cases: (status_param, search_param)
    test_export_cases = [
        (None, 'alice'),
        ('All', 'bob'),
        ('Retired', 'laptop'),
        ('Missing', 'Brown'),
        ('Active', 'xyz'),
        ('All', ''),
        (None, None), # Test default status, no search
        ('Active', None) # Explicit Active, no search (should be same as default)
    ]

    for status_param, search_param in test_export_cases:
        filter_key = (status_param if status_param is not None else 'None', search_param)
        print(f"\nTesting /export_csv: status='{status_param}', search='{search_param}'")

        # Build URL
        query_params = {}
        if status_param is not None: query_params['status'] = status_param
        if search_param is not None: query_params['search_term'] = search_param
        url = url_for('export_csv', **query_params)
        response = client.get(url)

        # --- Assertions ---
        # Status code
        if response.status_code == 200:
            print(f"  [PASS] Status code: Expected 200, Got {response.status_code}")
        else:
            print(f"  [FAIL] Status code: Expected 200, Got {response.status_code}")
            csv_tests_passed = False
            all_tests_passed = False

        # Mimetype
        if response.mimetype == 'text/csv':
            print(f"  [PASS] Mimetype: Expected 'text/csv', Got '{response.mimetype}'")
        else:
            print(f"  [FAIL] Mimetype: Expected 'text/csv', Got '{response.mimetype}'")
            csv_tests_passed = False
            all_tests_passed = False

        # Content-Disposition header
        content_disposition = response.headers.get('Content-Disposition', '')
        expected_disposition = 'attachment; filename=assets.csv'
        if expected_disposition in content_disposition:
            print(f"  [PASS] Content-Disposition: Expected contains '{expected_disposition}', Got '{content_disposition}'")
        else:
            print(f"  [FAIL] Content-Disposition: Expected contains '{expected_disposition}', Got '{content_disposition}'")
            csv_tests_passed = False
            all_tests_passed = False

        # CSV content
        actual_csv_content = response.data.decode('utf-8')
        # Use filter_key which is a tuple (status, search)
        expected_csv_content = expected_csv_search.get(filter_key, "ERROR: Expected CSV not defined for this case")
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

    if not csv_tests_passed: print(" - /export_csv search tests failed")


    # --- Test Section: highlight Filter ---
    # --- Test Section: highlight Filter ---
    print("\n--- Testing highlight Filter ---")
    highlight_tests_passed = True
    # Import the function from routes for direct testing
    from routes import highlight
    # Test cases: (input_text, query, expected_output)
    highlight_test_cases = [
        # Basic cases
        ('Some Text', '', 'Some Text'),
        ('', 'query', ''),
        ('Some Text', None, 'Some Text'), # None query
        (None, 'query', None), # None text
        ('Some Text', 'query', 'Some Text'), # No match
        # Simple match
        ('Hello World', 'World', 'Hello <mark>World</mark>'),
        # Case-insensitive match
        ('Hello World', 'hello', '<mark>Hello</mark> World'),
        ('Hello World', 'world', 'Hello <mark>World</mark>'),
        ('HELLO WORLD', 'world', 'HELLO <mark>WORLD</mark>'),
        # Multiple matches
        ('hello world hello', 'hello', '<mark>hello</mark> world <mark>hello</mark>'),
        ('The quick brown fox jumps over the lazy fox', 'fox', 'The quick brown <mark>fox</mark> jumps over the lazy <mark>fox</mark>'),
        # Query with special regex chars (should be escaped correctly)
        ('Text with (parentheses)', '(parentheses)', 'Text with <mark>(parentheses)</mark>'),
        ('File.txt', '.', 'File<mark>.</mark>txt'), # Match literal dot
        ('Amount $5.00', '$5.00', 'Amount <mark>$5.00</mark>'), # Match currency
        # Test preservation of original case in replacement
        ('Hello World', 'world', 'Hello <mark>World</mark>'),
        ('Hello World', 'Hello', '<mark>Hello</mark> World'),
    ]

    for input_text, query, expected_output in highlight_test_cases:
        print(f"\nTesting highlight: text='{input_text}', query='{query}'")
        # Directly call the filter function
        result = highlight(input_text, query)
        # Compare string representation as filter returns Markup
        actual_output = str(result) if result is not None else None

        if actual_output == expected_output:
            print(f"  [PASS] Highlight: Expected '{expected_output}', Got '{actual_output}'")
        else:
            print(f"  [FAIL] Highlight: Expected '{expected_output}', Got '{actual_output}'")
            highlight_tests_passed = False
            all_tests_passed = False # Update overall status

    if not highlight_tests_passed: print(" - highlight filter tests failed")


    # --- Test Section: /add Validation ---
    print("\n--- Testing /add Validation ---")
    add_validation_tests_passed = True

    def get_db_count():
        """Helper to get current asset count."""
        conn = sqlite3.connect('assets.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM assets")
        count = c.fetchone()[0]
        conn.close()
        return count

    # --- Invalid Submission Tests ---
    invalid_add_cases = [
        (
            "Missing Asset Name",
            {'asset_name': '', 'asset_type': 'TestType', 'status': 'Active'},
            ["Asset Name is required."],
            {'asset_type': 'TestType', 'status': 'Active'}
        ),
        (
            "Missing Asset Type",
            {'asset_name': 'TestName', 'asset_type': ' ', 'status': 'Active'},
            ["Asset Type is required."],
            {'asset_name': 'TestName', 'status': 'Active'}
        ),
        (
            "Invalid Status",
            {'asset_name': 'TestName', 'asset_type': 'TestType', 'status': 'Broken'},
            ["Invalid status selected"],
            {'asset_name': 'TestName', 'asset_type': 'TestType'}
        ),
        (
            "Multiple Errors",
            {'asset_name': '', 'asset_type': '', 'status': 'Invalid'},
            ["Asset Name is required.", "Asset Type is required.", "Invalid status selected"],
            {} # No fields expected to be repopulated correctly with empty/invalid initial data
        ),
    ]

    for name, post_data, expected_errors, expected_values in invalid_add_cases:
        print(f"\nTesting Invalid Add: {name}")
        populate_test_data() # Reset DB for each case
        initial_count = get_db_count()
        response = client.post(url_for('add_asset'), data=post_data, follow_redirects=False)
        html = response.data.decode()

        test_passed = True
        # Check status code 200 (re-render)
        if response.status_code == 200:
            print(f"  [PASS] Status code: Expected 200, Got {response.status_code}")
        else:
            print(f"  [FAIL] Status code: Expected 200, Got {response.status_code}")
            test_passed = False

        # Check error messages
        for error_msg in expected_errors:
            if error_msg in html:
                print(f"  [PASS] Error message found: '{error_msg}'")
            else:
                print(f"  [FAIL] Error message NOT found: '{error_msg}'")
                test_passed = False

        # Check retained values
        for field, value in expected_values.items():
             # Check input fields
             if field in ['asset_name', 'asset_type', 'assigned_to']:
                 expected_input_html = f'name="{field}" value="{value}"'
                 if expected_input_html in html:
                      print(f"  [PASS] Retained value: Field '{field}' has value '{value}'")
                 else:
                      print(f"  [FAIL] Retained value: Field '{field}' did not have value '{value}'. Check HTML: {expected_input_html}")
                      test_passed = False
             # Check select field
             elif field == 'status':
                  expected_select_html = f'<option value="{value}" selected'
                  if expected_select_html in html:
                       print(f"  [PASS] Retained value: Status '{value}' is selected")
                  else:
                       print(f"  [FAIL] Retained value: Status '{value}' was not selected. Check HTML: {expected_select_html}")
                       test_passed = False


        # Check DB count (should not change)
        final_count = get_db_count()
        if final_count == initial_count:
            print(f"  [PASS] DB Count: Unchanged ({initial_count})")
        else:
            print(f"  [FAIL] DB Count: Changed from {initial_count} to {final_count}")
            test_passed = False

        if not test_passed:
            add_validation_tests_passed = False
            all_tests_passed = False # Update overall status

    # --- Valid Submission Test ---
    print("\nTesting Valid Add Submission")
    populate_test_data() # Reset DB
    initial_count = get_db_count()
    valid_data = {
        'asset_name': 'ValidAsset-XYZ',
        'asset_type': 'ValidType',
        'assigned_to': 'Test User',
        'status': 'Retired'
    }
    # Set session before POST to check redirect correctly
    with client.session_transaction() as sess:
        sess['last_status_filter'] = 'All' # Set a known previous filter

    response = client.post(url_for('add_asset'), data=valid_data, follow_redirects=False)
    valid_test_passed = True

    # Check status code 302 (redirect)
    if response.status_code == 302:
        print(f"  [PASS] Status code: Expected 302, Got {response.status_code}")
    else:
        print(f"  [FAIL] Status code: Expected 302, Got {response.status_code}")
        valid_test_passed = False

    # Check redirect location (should redirect back to view with last status filter)
    expected_redirect_location = url_for('view_assets', status='All')
    actual_location = response.location
    if actual_location and actual_location.endswith(expected_redirect_location):
         print(f"  [PASS] Redirect location: Expected ends with '{expected_redirect_location}', Got '{actual_location}'")
    else:
         print(f"  [FAIL] Redirect location: Expected ends with '{expected_redirect_location}', Got '{actual_location}'")
         valid_test_passed = False


    # Check DB count (should increase by 1)
    final_count = get_db_count()
    if final_count == initial_count + 1:
        print(f"  [PASS] DB Count: Increased from {initial_count} to {final_count}")
    else:
        print(f"  [FAIL] DB Count: Expected {initial_count + 1}, Got {final_count}")
        valid_test_passed = False

    # Check if the specific asset was added correctly
    conn = sqlite3.connect('assets.db')
    c = conn.cursor()
    c.execute("SELECT * FROM assets WHERE asset_name = ?", (valid_data['asset_name'],))
    new_asset = c.fetchone()
    conn.close()
    if new_asset and new_asset[1] == valid_data['asset_name'] and new_asset[2] == valid_data['asset_type'] and new_asset[3] == valid_data['assigned_to'] and new_asset[4] == valid_data['status']:
        print(f"  [PASS] DB Verification: Found new asset '{valid_data['asset_name']}' with correct details.")
    else:
        print(f"  [FAIL] DB Verification: Could not find new asset '{valid_data['asset_name']}' with correct details.")
        valid_test_passed = False

    if not valid_test_passed:
        add_validation_tests_passed = False
        all_tests_passed = False # Update overall status

    if not add_validation_tests_passed: print(" - /add validation tests failed")


    # --- Final Reporting ---
    print("\n--------------------")
    if all_tests_passed:
        print("All tests passed!")
    else:
        print("Some tests FAILED!")
        # Detailed reporting already happened in each section
        # List specific sections that failed at the end for summary
        if not get_assets_tests_passed: print("   - get_assets_by_status tests failed")
        if not view_render_tests_passed: print("   - /view render tests failed")
        if not view_session_tests_passed: print("   - /view session setting tests failed")
        if not add_redirect_tests_passed: print("   - /add redirect tests failed") # Note: This section might be partially redundant now
        if not add_validation_tests_passed: print("   - /add validation tests failed")
        if not csv_tests_passed: print("   - /export_csv search tests failed")
        if not highlight_tests_passed: print("   - highlight filter tests failed")
    print("--------------------")
    return all_tests_passed


# Add import for patch and url_for (needed for tests)
from unittest.mock import patch
from flask import url_for

if __name__ == '__main__':
    # Run tests before starting the server
    test_result = run_tests()
    # Start the Flask app (optional, comment out if only running tests and tests passed)
    # if test_result:
    #    app.run(debug=True)
