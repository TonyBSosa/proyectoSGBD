from flask import Flask, render_template, request
import pyodbc

app = Flask(__name__, template_folder='webpage')

# Conexión a SQL Server
def conectar_sqlserver():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=(localdb)\\VerbTables;'
        'DATABASE=Example DB;'
        'Trusted_Connection=yes;'
    )

# Tipos válidos para validación básica
TIPOS_VALIDOS = {'INT', 'VARCHAR', 'TEXT', 'DATE', 'BIT', 'FLOAT', 'DECIMAL'}

# Mostrar estructura de la BD
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
        html += "<a href='/crear-tabla'>➕ Crear tabla</a> | <a href='/crear-relacion'>🔗 Crear relación</a><br><br>"
        html += "<table border='1'><tr><th>Tabla</th><th>Columna</th><th>Tipo</th></tr>"
        for fila in datos:
            html += f"<tr><td>{fila[0]}</td><td>{fila[1]}</td><td>{fila[2]}</td></tr>"
        html += "</table>"
        return html
    except Exception as e:
        return f"<h1>Error</h1><p>{e}</p>"
    finally:
        conn.close()

# Crear tabla con validación
@app.route('/crear-tabla', methods=['GET', 'POST'])
def crear_tabla():
    mensaje = ''
    if request.method == 'POST':
        nombre_tabla = request.form['nombre_tabla']
        campos = request.form['campos']

        # Validación básica de tipos
        definiciones = campos.split(',')
        errores = []
        for campo in definiciones:
            partes = campo.strip().split()
            if len(partes) < 2:
                errores.append(f'❌ Definición incompleta: "{campo.strip()}"')
                continue
            tipo = partes[1].upper()
            if '(' in tipo:
                tipo = tipo.split('(')[0]
            if tipo not in TIPOS_VALIDOS:
                errores.append(f'❌ Tipo inválido: "{tipo}" en "{campo.strip()}"')

        if errores:
            mensaje = '<br>'.join(errores)
        else:
            query = f"CREATE TABLE {nombre_tabla} ({campos})"
            try:
                conn = conectar_sqlserver()
                with conn.cursor() as cursor:
                    cursor.execute(query)
                conn.commit()
                mensaje = '✅ Tabla creada exitosamente'
            except Exception as e:
                mensaje = f'❌ Error SQL: {e}'
            finally:
                conn.close()

    return render_template('crear_tabla.html', mensaje=mensaje)

# Crear relación FOREIGN KEY
@app.route('/crear-relacion', methods=['GET', 'POST'])
def crear_relacion():
    mensaje = ''
    if request.method == 'POST':
        tabla_origen = request.form['tabla_origen']
        columna_origen = request.form['columna_origen']
        tabla_destino = request.form['tabla_destino']
        columna_destino = request.form['columna_destino']

        alter_query = f'''
        ALTER TABLE {tabla_origen}
        ADD CONSTRAINT fk_{tabla_origen}_{columna_origen}
        FOREIGN KEY ({columna_origen}) REFERENCES {tabla_destino}({columna_destino})
        '''

        try:
            conn = conectar_sqlserver()
            with conn.cursor() as cursor:
                cursor.execute(alter_query)
            conn.commit()
            mensaje = '✅ Relación (FOREIGN KEY) creada exitosamente'
        except Exception as e:
            mensaje = f'❌ Error: {e}'
        finally:
            conn.close()

    return render_template('crear_relacion.html', mensaje=mensaje)

if __name__ == '__main__':
    app.run(debug=True)
