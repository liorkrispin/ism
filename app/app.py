from flask import Flask, render_template, request, redirect, session, flash, jsonify, Response
import mysql.connector
import os
import csv
from werkzeug.utils import secure_filename
from datetime import datetime
from azure.identity import InteractiveBrowserCredential
from azure.mgmt.compute import ComputeManagementClient
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
from flask import jsonify, request

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# הגדרות חיבור למסד הנתונים
db_config = {
    'host': 'mariadb-container',  # שם הקונטיינר במקום localhost
    'user': 'root',
    'password': 'Adar_112233',
    'database': 'server_management'
}

# פונקציה לבדוק אם קובץ הוא מסוג CSV
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# פונקציה לבדוק אם משתמש מחובר
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# פונקציית לוגין
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # שליפת הנתונים שהמשתמש הזין
        username = request.form['username']
        password = request.form['password']  # סיסמה רגילה שהמשתמש מכניס
        print(f"Username entered: {username}, Password entered: {password}")  # DEBUG

        try:
            # חיבור למסד הנתונים
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            
            # שליפת משתמש לפי שם משתמש
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            conn.close()

            if user:
                print(f"User found: {user}")  # DEBUG
                print(f"Stored hash: {user['password']}")  # DEBUG
            else:
                print("User not found.")  # DEBUG

            # בדיקת סיסמה
            if user and check_password_hash(user['password'], password):
                print("Password is correct!")  # DEBUG
                # שמירת נתונים ב-session
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']  # שמירת תפקיד המשתמש

                flash('Login successful!', 'success')
                return redirect('/')
            else:
                print("Invalid username or password.")  # DEBUG
                flash('Invalid username or password.', 'danger')
        except Exception as e:
            print(f"Error during login: {e}")  # DEBUG
            flash(f"Error during login: {e}", 'danger')

    return render_template('login.html')
@app.route('/logout')
def user_logout():
    """
    מסיים את הסשן של המשתמש ומעביר אותו לדף הלוגין.
    """
    session.pop('user_id', None)  # מוחק את ה-ID של המשתמש מהסשן
    session.pop('username', None)  # מוחק את שם המשתמש מהסשן
    flash('Logged out successfully.', 'success')  # הודעת פידבק
    return redirect('/login')  # מעביר לדף הלוגין
# דף דשבורד ראשי
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        server_name = request.form['server_name']
        ip_address = request.form['ip_address']
        site_name = request.form['site_name']
        https_link = request.form['https_link']
        login_user = request.form['login_user']
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("""
            INSERT INTO servers (server_name, ip_address, site_name, https_link, login_user, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (server_name, ip_address, site_name, https_link, login_user, created_at))
        conn.commit()

        flash('Server added successfully!', 'success')
        return redirect('/')

    search_query = request.args.get('search', '').strip()
    if search_query:
        cursor.execute("""
            SELECT * FROM servers
            WHERE server_name LIKE %s OR ip_address LIKE %s OR site_name LIKE %s
        """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM servers")
    servers = cursor.fetchall()
    conn.close()
    return render_template('index.html', servers=servers, search_query=search_query, username=session.get('username'))

# פונקציה למחיקת שרת
@app.route('/delete/<int:server_id>', methods=['POST'])
@login_required
def delete_server(server_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM servers WHERE id = %s", (server_id,))
        conn.commit()
        conn.close()
        flash(f"Server with ID {server_id} deleted successfully.", 'success')
        return redirect('/')
    except Exception as e:
        flash(f"Error deleting server: {e}", 'danger')
        return redirect('/')

# פונקציה לייצוא CSV
@app.route('/export', methods=['GET'])
@login_required
def export_csv():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM servers")
    servers = cursor.fetchall()
    conn.close()

    def generate_csv():
        if servers:
            header = servers[0].keys()
            yield ','.join(header) + '\n'
            for server in servers:
                yield ','.join(str(server[field]) for field in header) + '\n'
        else:
            yield "No data available\n"

    response = Response(generate_csv(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment; filename=servers.csv")
    return response

# פונקציה לייבוא CSV
@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_csv():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect('/import')

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect('/import')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with open(filepath, 'r') as csv_file:
                reader = csv.DictReader(csv_file)
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()

                for row in reader:
                    cursor.execute("""
                        INSERT INTO servers (server_name, ip_address, site_name, https_link, login_user)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (row['server_name'], row['ip_address'], row['site_name'], row['https_link'], row['login_user']))

                conn.commit()
                conn.close()

            flash('File imported successfully!', 'success')
            return redirect('/')

        else:
            flash('Invalid file type. Only CSV files are allowed.', 'danger')
            return redirect('/import')

    return render_template('import.html')

# פונקציה ליצירת קובץ RDP
@app.route('/rdp/<int:server_id>', methods=['GET'])
@login_required
def generate_rdp(server_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ip_address FROM servers WHERE id = %s", (server_id,))
        server = cursor.fetchone()
        conn.close()

        if not server:
            flash("Server not found.", 'danger')
            return redirect('/')

        ip_address = server['ip_address']
        rdp_content = f"""
screen mode id:i:2
desktopwidth:i:1920
desktopheight:i:1080
session bpp:i:32
full address:s:{ip_address}
prompt for credentials:i:1
administrative session:i:1
        """

        response = Response(rdp_content, mimetype='application/x-rdp')
        response.headers.set("Content-Disposition", f"attachment; filename=server-{server_id}.rdp")
        return response
    except Exception as e:
        flash(f"Error generating RDP: {e}", 'danger')
        return redirect('/')

# פונקציה לריסטרט של שרת
@app.route('/reboot', methods=['POST'])
@login_required
def reboot_server():
    server_name = request.form.get('server_name')

    if not server_name:
        flash('Server name not provided.', 'danger')
        return redirect('/')

    try:
        credential = InteractiveBrowserCredential()
        subscription_id = "YOUR_AZURE_SUBSCRIPTION_ID"
        compute_client = ComputeManagementClient(credential, subscription_id)
        resource_group_name = "YOUR_RESOURCE_GROUP_NAME"
        vm_name = server_name

        async_vm_restart = compute_client.virtual_machines.begin_restart(resource_group_name, vm_name)
        async_vm_restart.wait()

        flash(f'Server "{server_name}" rebooted successfully!', 'success')
    except Exception as e:
        flash(f'Error rebooting server: {e}', 'danger')

    return redirect('/')

@app.route('/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        # DEBUG: Print to check the values received from the form
        print(f"Username: {username}, Password: {password}, Role: {role}")

        if not username or not password or not role:
            flash('All fields are required!', 'danger')
            return redirect('/create-user')

        hashed_password = generate_password_hash(password)

        try:
         
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password, role)
                VALUES (%s, %s, %s)
            """, (username, hashed_password, role))
            conn.commit()
            conn.close()

            # הודעה על הצלחה
            flash(f'User "{username}" created successfully!', 'success')
            return redirect('/')
        except mysql.connector.Error as err:
            flash(f"Error: {err.msg}", 'danger')
            return redirect('/create-user')

    return render_template('create_user.html')

@app.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    # בדיקה אם המשתמש המחובר הוא admin
    user_role = session.get('role')  # לוודא שפרמטר role נשמר בסשן
    if user_role != 'admin':
        flash('You do not have permission to delete users.', 'danger')
        return redirect('/')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # בדיקה כדי למנוע מחיקת המשתמש admin
        cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user and user[0] == 'admin':
            flash('Cannot delete the admin user.', 'danger')
            return redirect('/')

        # מחיקת המשתמש מהדאטהבייס
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()

        flash(f"User with ID {user_id} deleted successfully.", 'success')
        return redirect('/manage-users')
    except Exception as e:
        flash(f"Error deleting user: {e}", 'danger')
        return redirect('/manage-users')

@app.route('/manage-users', methods=['GET'])
@login_required
def manage_users():
    # בדיקה אם המשתמש המחובר הוא admin
    if session.get('role') != 'admin':
        flash('You do not have permission to view this page.', 'danger')
        return redirect('/')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, role FROM users")
        users = cursor.fetchall()
        conn.close()
        return render_template('manage_users.html', users=users)
    except Exception as e:
        flash(f"Error fetching users: {e}", 'danger')
        return redirect('/')

@app.route('/ping', methods=['GET'])
def ping():
    ip = request.args.get('ip')
    if not ip:
        return jsonify({"success": False, "error": "No IP address provided."})

    try:
        # Run the ping command
        result = subprocess.run(
            ["ping", "-c", "4", ip],  # "-c 4" for Linux/macOS, replace with "-n 4" for Windows
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            return jsonify({"success": True, "output": result.stdout})
        else:
            return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
