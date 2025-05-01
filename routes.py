# routes.py
from flask import Blueprint, render_template, request, redirect, session, url_for, Response # Added Blueprint
from markupsafe import Markup
import re
import io
import csv
import sqlite3

# Create Blueprint instance
routes_bp = Blueprint('routes', __name__, template_folder='templates')

# Database Helper Function (Moved from app.py)
def get_assets_by_status(status_filter=None, search_term=None):
    """Fetches assets from the database, optionally filtering by status and search term."""
    conn = sqlite3.connect('assets.db')
    c = conn.cursor()
    query = "SELECT * FROM assets"
    params = []
    conditions = []

    # Status condition
    if status_filter and status_filter.lower() != 'all':
        conditions.append("LOWER(status) = LOWER(?)")
        params.append(status_filter)

    # Search condition (case-insensitive search on asset_name or assigned_to)
    if search_term: # Check if search_term is not None and not an empty string
        conditions.append("(LOWER(asset_name) LIKE LOWER(?) OR LOWER(assigned_to) LIKE LOWER(?))")
        like_term = f'%{search_term}%'
        params.append(like_term)
        params.append(like_term)

    # Combine conditions
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Execute query
    c.execute(query, params)
    assets = c.fetchall()
    conn.close()
    return assets

# Jinja Custom Filter registered with the Blueprint
@routes_bp.app_template_filter('highlight')
def highlight(text, query):
    """Highlights occurrences of query in text using <mark> tags."""
    if not query or not text:
        return text
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    highlighted_text = pattern.sub(lambda m: f'<mark>{m.group(0)}</mark>', text)
    return Markup(highlighted_text)

# Route function definitions registered with the Blueprint
@routes_bp.route('/')
def index():
    return render_template('index.html')

@routes_bp.route('/add', methods=['GET', 'POST'])
def add_asset():
    if request.method == 'POST':
        asset_name = request.form.get('asset_name')
        asset_type = request.form.get('asset_type')
        assigned_to = request.form.get('assigned_to')
        status = request.form.get('status')
        errors = {}
        if not asset_name or not asset_name.strip():
            errors['asset_name'] = "Asset Name is required."
        if not asset_type or not asset_type.strip():
            errors['asset_type'] = "Asset Type is required."
        allowed_statuses = ['Active', 'Retired', 'Missing']
        if not status or status not in allowed_statuses:
            errors['status'] = "Invalid status selected. Must be Active, Retired, or Missing."

        if errors:
            return render_template('add_asset.html',
                                   errors=errors,
                                   asset_name=asset_name,
                                   asset_type=asset_type,
                                   assigned_to=assigned_to,
                                   status=status)
        else:
            # Database insertion
            conn = sqlite3.connect('assets.db')
            c = conn.cursor()
            c.execute("INSERT INTO assets (asset_name, asset_type, assigned_to, status) VALUES (?, ?, ?, ?)",
                      (asset_name, asset_type, assigned_to, status))
            conn.commit()
            conn.close()
            last_status = session.get('last_status_filter', 'Active')
            # Use '.view_assets' for endpoint within the same blueprint
            return redirect(url_for('.view_assets', status=last_status))

    # Handle GET request
    return render_template('add_asset.html', errors={})

@routes_bp.route('/view')
def view_assets():
    requested_status = request.args.get('status')
    search_term = request.args.get('search_term', '').strip()
    status_filter = requested_status if requested_status is not None else 'Active'
    session['last_status_filter'] = status_filter
    # Call the helper function (now defined in this file)
    assets = get_assets_by_status(status_filter, search_term) # Call is active
    return render_template('view_assets.html',
                           assets=assets,
                           current_status=status_filter,
                           search_term=search_term)

@routes_bp.route('/export_csv')
def export_csv():
    requested_status = request.args.get('status')
    status_filter = requested_status if requested_status is not None else 'Active'
    search_term = request.args.get('search_term', '').strip()
    # Call the helper function (now defined in this file)
    assets = get_assets_by_status(status_filter, search_term) # Call is active
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['Asset Name', 'Type', 'Assigned To', 'Status'])
    for asset in assets:
        writer.writerow([asset[1], asset[2], asset[3], asset[4]])
    csv_data = si.getvalue()
    response = Response(csv_data, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=assets.csv'
    return response
