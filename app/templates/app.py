from flask import Flask, render_template, request, jsonify, redirect, Response, flash
import mysql.connector
import csv
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# הגדרות Flask
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# הגדרות חיבור לבסיס הנתונים
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Adar_112233',  # שנה כאן את הסיסמה של MariaDB
    'database': 'server_management'
}

# פונקציה לבדוק אם הקובץ הוא CSV
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # מחיקת רשומה
        if 'delete_id' in request.form:
            delete_id = request.form['delete_id']
            cursor.execute("DELETE FROM servers WHERE id = %s", (delete_id,))
            conn.commit()

        # הוספת רשומה
        elif 'server_name' in request.form:
            server_name = request.form['server_name']
            ip_address = request.form['ip_address']
            site_name = request.form['site_name']
            https_link = request.form['https_link']
            login_user = request.form['login_user']

            cursor.execute("""
                INSERT INTO servers (server_name, ip_address, site_name, https_link, login_user)
                VALUES (%s, %s, %s, %s, %s)
            """, (server_name, ip_address, site_name, https_link, login_user))
            conn.commit()

        return redirect('/')

    # שליפת הנתונים להצגה
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
    return render_template('index.html', servers=servers, search_query=search_query)

@app.route('/edit/<int:server_id>', methods=['POST'])
def edit_server(server_id):
    try:
        data = request.get_json()
        if not data or 'field' not in data or 'value' not in data:
            return jsonify({'error': 'Invalid data'}), 400

        field = data['field']
        value = data['value']

        valid_fields = {'server_name', 'ip_address', 'site_name', 'https_link', 'login_user'}
        if field not in valid_fields:
            return jsonify({'error': 'Invalid field'}), 400

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = f"UPDATE servers SET {field} = %s WHERE id = %s"
        cursor.execute(query, (value, server_id))
        conn.commit()
        conn.close()

        return jsonify({'success': True}), 200
    except mysql.connector.Error as err:
        return jsonify({'error': f"Database error: {err}"}), 500
    except Exception as e:
        return jsonify({'error': f"Server error: {e}"}), 500

@app.route('/rdp/<int:server_id>', methods=['GET'])
def generate_rdp(server_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT ip_address FROM servers WHERE id = %s", (server_id,))
    server = cursor.fetchone()
    conn.close()

    if not server:
        return "Server not found", 404

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

@app.route('/export', methods=['GET'])
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

@app.route('/import', methods=['GET', 'POST'])
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

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
