from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'

@app.route('/')
def home():
    conn = sqlite3.connect('businesses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM businesses")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return render_template("index.html", categories=categories)

@app.route('/businesses')
def businesses():
    search = request.args.get('search', '')
    category = request.args.get('category', '')

    conn = sqlite3.connect('businesses.db')
    cursor = conn.cursor()

    if category:
        cursor.execute("SELECT * FROM businesses WHERE category LIKE ?", ('%' + category + '%',))
    elif search:
        cursor.execute("""
            SELECT * FROM businesses 
            WHERE name LIKE ? OR category LIKE ? OR area LIKE ?
        """, ('%' + search + '%', '%' + search + '%', '%' + search + '%'))
    else:
        cursor.execute("SELECT * FROM businesses")

    businesses = cursor.fetchall()
    conn.close()
    return render_template("listings.html", businesses=businesses)

@app.route('/business/<int:id>')
def business_detail(id):
    conn = sqlite3.connect('businesses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM businesses WHERE id = ?", (id,))
    business = cursor.fetchone()
    conn.close()

    if business:
        hours = business[7]
        if "to" in hours:
            try:
                start_time, end_time = [t.strip() for t in hours.split("to")]
                start_12 = datetime.strptime(start_time, "%H:%M").strftime("%I:%M %p")
                end_12 = datetime.strptime(end_time, "%H:%M").strftime("%I:%M %p")
                business = list(business)
                business[7] = f"{start_12} to {end_12}"
            except:
                pass

    return render_template("detail.html", business=business)

@app.route('/add', methods=['GET', 'POST'])
def add_business():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        other_category = request.form.get('other-category', '').strip()
        area = request.form['area']
        address = request.form['address']
        contact = request.form['contact']
        email = request.form['email']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        description = request.form['description']
        raw_map_input = request.form['map_link'].strip()

        map_link = ''
        match = re.search(r'src=["\'](https://www\.google\.com/maps/embed[^"\']+)["\']', raw_map_input)
        if match:
            map_link = match.group(1)
        else:
            map_link = raw_map_input

        if category == "-- Others --" and other_category:
            category = other_category

        hours = f"{start_time} to {end_time}"
        owner_id = session.get('owner_id')

        conn = sqlite3.connect('businesses.db')
        cursor = conn.cursor()

        if owner_id:
            cursor.execute("""
                INSERT INTO businesses 
                (name, category, area, address, contact, email, hours, description, map_link, owner_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, category, area, address, contact, email, hours, description, map_link, owner_id))
        else:
            cursor.execute("""
                INSERT INTO businesses 
                (name, category, area, address, contact, email, hours, description, map_link) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, category, area, address, contact, email, hours, description, map_link))

        conn.commit()
        conn.close()

        return redirect(url_for('add_business', success=1))

    success = request.args.get('success')
    return render_template("add.html", success=success)

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/login-dashboard')
def login_dashboard():
    return render_template('login_dashboard.html')

@app.route('/owner_login', methods=['GET', 'POST'])
def owner_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('businesses.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM owners WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['owner_id'] = user[0]
            return redirect(url_for('shop_dashboard', login_success=True))
        else:
            return render_template('owner_login.html', login_failed=True)

    return render_template('owner_login.html')

@app.route('/shop_dashboard')
def shop_dashboard():
    if 'owner_id' not in session:
        return redirect('/owner_login')
    login_success = request.args.get('login_success')
    return render_template('shop_dashboard.html', login_success=login_success)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/owner/register', methods=['POST'])
def register_owner():
    name = request.form['name']
    contact = request.form['contact']
    email = request.form['email']
    address = request.form['address']
    password = request.form['password']

    hashed_password = generate_password_hash(password)

    conn = sqlite3.connect('businesses.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO owners (name, contact, email, address, password)
            VALUES (?, ?, ?, ?, ?)
        """, (name, contact, email, address, hashed_password))
        conn.commit()
        return redirect(url_for('owner_login', success='register'))
    except sqlite3.IntegrityError:
        return redirect(url_for('owner_login', error='exists'))
    finally:
        conn.close()

@app.route('/modify_business')
def modify_business():
    if 'owner_id' not in session:
        return redirect('/owner_login')
    
    owner_id = session['owner_id']
    conn = sqlite3.connect('businesses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM businesses WHERE owner_id = ?", (owner_id,))
    businesses = cursor.fetchall()
    conn.close()
    return render_template("modify_business.html", businesses=businesses)

@app.route('/delete_business/<int:id>')
def delete_business(id):
    if 'owner_id' not in session:
        return redirect('/owner_login')
    
    conn = sqlite3.connect('businesses.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM businesses WHERE id = ? AND owner_id = ?", (id, session['owner_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('modify_business'))


@app.route('/edit_business/<int:id>', methods=['GET', 'POST'])
def edit_business(id):
    if 'owner_id' not in session and not session.get('support_logged_in'):
        return redirect('/owner_login')

    conn = sqlite3.connect('businesses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        area = request.form['area']
        address = request.form['address']
        contact = request.form['contact']
        email = request.form['email']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        description = request.form['description']
        raw_map_input = request.form['map_link'].strip()

        map_link = ''
        match = re.search(r'src=["\'](https://www\.google\.com/maps/embed[^"\']+)["\']', raw_map_input)
        if match:
            map_link = match.group(1)
        else:
            map_link = raw_map_input

        hours = f"{start_time} to {end_time}"

        if 'owner_id' in session:
            # Restrict edit to only owner’s businesses
            cursor.execute("""
                UPDATE businesses 
                SET name=?, category=?, area=?, address=?, contact=?, email=?, hours=?, description=?, map_link=? 
                WHERE id=? AND owner_id=?
            """, (name, category, area, address, contact, email, hours, description, map_link, id, session['owner_id']))
        else:
            # Support team can edit any business
            cursor.execute("""
                UPDATE businesses 
                SET name=?, category=?, area=?, address=?, contact=?, email=?, hours=?, description=?, map_link=? 
                WHERE id=?
            """, (name, category, area, address, contact, email, hours, description, map_link, id))

        conn.commit()
        conn.close()

        # ✅ Support team redirection to handle_query with query_id
        if session.get('support_logged_in'):
            query_id = request.form.get('query_id') or request.args.get('query_id')
            return redirect(url_for('handle_query', query_id=query_id, updated=1))

        # ✅ Shop owner redirection (existing behavior)
        return redirect(url_for('modify_business', updated=1))

    # GET request logic
    if 'owner_id' in session:
        cursor.execute("SELECT * FROM businesses WHERE id = ? AND owner_id = ?", (id, session['owner_id']))
    else:
        cursor.execute("SELECT * FROM businesses WHERE id = ?", (id,))
    
    business = cursor.fetchone()
    conn.close()

    if business:
        return render_template("edit_business.html", business=business)
    else:
        return "Not authorized or business not found", 403




@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == 'admin@nearnest.com' and password == 'admin@123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error=True)

    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('businesses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM businesses")
    total_businesses = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM owners")
    total_owners = cursor.fetchone()[0]

    search = request.args.get('search', '').strip()

    if search:
        cursor.execute("""
            SELECT b.id, b.name, b.category, o.name AS owner_name
            FROM businesses b
            LEFT JOIN owners o ON b.owner_id = o.id
            WHERE b.name LIKE ? OR b.category LIKE ? OR o.name LIKE ?
        """, (f'%{search}%', f'%{search}%', f'%{search}%'))
    else:
        cursor.execute("""
            SELECT b.id, b.name, b.category, o.name AS owner_name
            FROM businesses b
            LEFT JOIN owners o ON b.owner_id = o.id
        """)
    businesses = cursor.fetchall()

    cursor.execute("SELECT name, email, address FROM owners")
    owners = cursor.fetchall()

    cursor.execute("""
        SELECT b.name, o.name AS owner_name 
        FROM businesses b
        LEFT JOIN owners o ON b.owner_id = o.id
        ORDER BY b.id DESC LIMIT 5
    """)
    recent = cursor.fetchall()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_businesses=total_businesses,
        total_owners=total_owners,
        businesses=businesses,
        owners=owners,
        recent=recent
    )

@app.route('/admin/delete_business/<int:id>', methods=['POST'])
def admin_delete_business(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('businesses.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM businesses WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/support_login', methods=['GET', 'POST'])
def support_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Hardcoded support credentials
        support_email = 'support@nearnest.com'
        support_password = 'support@123'

        if email == support_email and password == support_password:
            session['support_logged_in'] = True
            return redirect(url_for('support_dashboard'))
        else:
            return render_template('support_login.html', error="Invalid email or password.")

    return render_template('support_login.html')

@app.route('/support_dashboard', methods=['GET', 'POST'])
def support_dashboard():
    if not session.get('support_logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('support_login'))

    conn = sqlite3.connect('businesses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        business_name = request.form['business_name']
        owner_name = request.form['owner_name']
        owner_email = request.form['owner_email']
        owner_contact = request.form['owner_contact']
        problem = request.form['problem']
        status = request.form['status']

        cursor.execute("""
            INSERT INTO support_queries 
            (business_name, owner_name, owner_email, owner_contact, problem, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (business_name, owner_name, owner_email, owner_contact, problem, status))
        conn.commit()
        return redirect(url_for('support_dashboard', success='1'))

    # Fetch counts
    cursor.execute("SELECT COUNT(*) FROM support_queries WHERE status='Open'")
    open_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM support_queries WHERE status='In Progress'")
    in_progress_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM support_queries WHERE status='Resolved'")
    resolved_count = cursor.fetchone()[0]

    conn.close()
    return render_template(
        "support_dashboard.html",
        open_count=open_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        success=request.args.get('success')
    )


@app.route('/queries')
def view_queries():
    if not session.get('support_logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('support_login'))

    conn = sqlite3.connect('businesses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM support_queries")
    queries = cursor.fetchall()
    conn.close()

    return render_template('queries.html', queries=queries)


@app.route('/handle_query/<int:query_id>', methods=['GET'])
def handle_query(query_id):
    if not session.get('support_logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('support_login'))

    conn = sqlite3.connect('businesses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get the query details
    cursor.execute("SELECT * FROM support_queries WHERE id = ?", (query_id,))
    query = cursor.fetchone()

    if not query:
        conn.close()
        return "Query not found", 404

    # Handle business search (if performed)
    search = request.args.get('search', '').strip()
    search_results = []

    if search:
        cursor.execute("""
            SELECT * FROM businesses 
            WHERE name LIKE ? OR category LIKE ? OR area LIKE ?
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))
        search_results = cursor.fetchall()

    conn.close()

    return render_template("handle.html", query=query, search_results=search_results)


@app.route('/update_status/<int:query_id>', methods=['GET', 'POST'])
def update_status(query_id):
    if not session.get('support_logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('support_login'))

    if request.method == 'POST':
        new_status = request.form['status']
        conn = sqlite3.connect('businesses.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE support_queries SET status = ? WHERE id = ?", (new_status, query_id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_queries', updated='1'))

    return render_template("status.html", query_id=query_id)


@app.route('/close_query/<int:query_id>', methods=['POST'])
def close_query(query_id):
    # Optional: You can delete or mark it differently
    conn = sqlite3.connect('businesses.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM support_queries WHERE id=?", (query_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_queries'))


@app.route('/support/delete_business/<int:business_id>/<int:query_id>', methods=['POST'])
def support_delete_business(business_id, query_id):
    if not session.get('support_logged_in'):
        flash('Please login first', 'warning')
        return redirect(url_for('support_login'))

    conn = sqlite3.connect('businesses.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM businesses WHERE id = ?", (business_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('handle_query', query_id=query_id, deleted='1'))





@app.route('/test-db')
def test_db():
    try:
        conn = sqlite3.connect('businesses.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return f"✅ Database connected! Tables: {tables}"
    except Exception as e:
        return f"❌ Database connection failed: {e}"

@app.route('/test-owners')
def test_owners():
    conn = sqlite3.connect('businesses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM owners")
    rows = cursor.fetchall()
    conn.close()

    result = "<h2>Owners Table</h2><ul>"
    for row in rows:
        result += f"<li>{row['id']}: {row['name']} | {row['email']} | {row['contact']} | {row['address']} | {row['password']}</li>"
    result += "</ul>"
    return result

@app.route('/test-businesses')
def test_businesses():
    conn = sqlite3.connect('businesses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM businesses")
    rows = cursor.fetchall()
    conn.close()

    result = "<h2>Businesses Table</h2><ul>"
    for row in rows:
        result += f"<li>ID: {row['id']}<br>" \
                  f"Name: {row['name']}<br>" \
                  f"Category: {row['category']}<br>" \
                  f"Area: {row['area']}<br>" \
                  f"Address: {row['address']}<br>" \
                  f"Contact: {row['contact']}<br>" \
                  f"Email: {row['email']}<br>" \
                  f"Hours: {row['hours']}<br>" \
                  f"Description: {row['description']}<br>" \
                  f"Map Link: {row['map_link']}<br>" \
                  f"Owner ID: {row['owner_id'] if 'owner_id' in row.keys() else 'N/A'}" \
                  f"</li><br><br>"
    result += "</ul>"
    return result

@app.template_filter('datetime')
def datetime_filter(value, format="%H:%M"):
    try:
        return datetime.strptime(value, format)
    except:
        return value

if __name__ == '__main__':
    app.run(debug=True)
