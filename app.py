from flask import Flask
import pyodbc

app = Flask(__name__)

def conectar_sqlserver():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=(localdb)\\VerbTables;'
        'DATABASE=Example DB;' 
        'Trusted_Connection=yes;'
    )

@app.route('/')
@app.route('/')
def metadata():
    conn = conectar_sqlserver()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    t.name AS tabla,
                    c.name AS columna,
                    ty.name AS tipo
                FROM sys.tables t
                JOIN sys.columns c ON t.object_id = c.object_id
                JOIN sys.types ty ON c.user_type_id = ty.user_type_id
                ORDER BY t.name, c.column_id;
            """)
            datos = cursor.fetchall()
        html = "<h1>Meta Data de la Base de Datos</h1>"
        html += "<table border='1'><tr><th>Tabla</th><th>Columna</th><th>Tipo</th></tr>"
        for fila in datos:
            html += f"<tr><td>{fila[0]}</td><td>{fila[1]}</td><td>{fila[2]}</td></tr>"
        html += "</table>"
        return html
    except Exception as e:
        return f"<h1>Error</h1><p>{e}</p>"
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
