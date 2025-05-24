from flask import Flask, render_template
import pymysql

app = Flask(__name__)

def obtener_metadata():
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',  # Cambia esto si usas contraseña
        database='test_sgbd'
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'test_sgbd';
            """)
            return cursor.fetchall()
    finally:
        conn.close()

@app.route('/')
def index():
    metadata = obtener_metadata()
    return render_template('index.html', metadata=metadata)

if __name__ == '__main__':
    app.run(debug=True)
