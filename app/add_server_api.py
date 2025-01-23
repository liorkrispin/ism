from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# הגדרות חיבור למסד הנתונים
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Adar_112233',  # שנה כאן לסיסמת מסד הנתונים שלך
    'database': 'server_management'
}

@app.route('/api/add_server', methods=['POST'])
def add_server():
    try:
        # קבלת הנתונים מבקשת POST
        data = request.get_json()

        # בדיקת תקינות הנתונים
        required_fields = ['server_name', 'ip_address', 'site_name', 'https_link', 'login_user']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f"Missing field: {field}"}), 400

        # חיבור למסד הנתונים
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # הוספת הרשומה לטבלה
        query = """
        INSERT INTO servers (server_name, ip_address, site_name, https_link, login_user)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data['server_name'],
            data['ip_address'],
            data['site_name'],
            data['https_link'],
            data['login_user']
        ))
        conn.commit()
        conn.close()

        # החזרת תגובה והדפסתה
        response = jsonify({'success': True, 'message': 'Server added successfully'})
        print("Response:", response.get_data(as_text=True))  # הוספת הדפסה
        return response, 201

    except mysql.connector.Error as err:
        return jsonify({'error': f"Database error: {err}"}), 500
    except Exception as e:
        return jsonify({'error': f"Server error: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)