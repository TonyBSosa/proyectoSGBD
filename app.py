from flask import Flask, render_template, request, redirect, url_for
import pyodbc
import pymysql

app = Flask(__name__, template_folder='webpage')

 # Funciones de conexión
 
def conectar_sqlserver():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=(localdb)\\VerbTables;'
        'DATABASE=Example DB;'
        'Trusted_Connection=yes;'
    )

def conectar_mysql():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='test_sgbd',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.Cursor
    )

 # Página principal
 
@app.route('/', methods=['GET', 'POST'])
def seleccionar_motor():
    if request.method == 'POST':
        motor = request.form['motor']
        return redirect(url_for('ver_metadata', motor=motor))
    return render_template('seleccionar_motor.html')

 # Mostrar metadata
 
@app.route('/metadata/<motor>')
def ver_metadata(motor):
    if motor == 'sqlserver':
        conn = conectar_sqlserver()
        query = """
        SELECT 
            t.name AS tabla,
            c.name AS columna,
            ty.name AS tipo
        FROM sys.tables t
        JOIN sys.columns c ON t.object_id = c.object_id
        JOIN sys.types ty ON c.user_type_id = ty.user_type_id
        ORDER BY t.name, c.column_id;
        """
    elif motor == 'mysql':
        conn = conectar_mysql()
        query = """
        SELECT 
            table_name AS tabla,
            column_name AS columna,
            data_type AS tipo
        FROM information_schema.columns
        WHERE table_schema = 'test_sgbd'
        ORDER BY table_name, ordinal_position;
        """
    else:
        return "Motor no válido"

    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            datos = cursor.fetchall()
    except Exception as e:
        return f"<h1>Error al obtener metadata</h1><p>{e}</p>"
    finally:
        conn.close()

    return render_template('metadata.html', datos=datos, motor=motor)

 # Crear tabla
 
TIPOS_VALIDOS = {'INT', 'VARCHAR', 'TEXT', 'DATE', 'BIT', 'FLOAT', 'DECIMAL'}

@app.route('/crear-tabla/<motor>', methods=['GET', 'POST'])
def crear_tabla(motor):
    mensaje = ''
    if request.method == 'POST':
        nombre_tabla = request.form['nombre_tabla']
        campos = request.form['campos']

        definiciones = campos.split(',')
        errores = []
        for campo in definiciones:
            partes = campo.strip().split()
            if len(partes) < 2:
                errores.append(f'❌ Definición incompleta: \"{campo.strip()}\"')
                continue
            tipo = partes[1].upper()
            if '(' in tipo:
                tipo = tipo.split('(')[0]
            if tipo not in TIPOS_VALIDOS:
                errores.append(f'❌ Tipo inválido: \"{tipo}\" en \"{campo.strip()}\"')

        if errores:
            mensaje = '<br>'.join(errores)
        else:
            query = f"CREATE TABLE {nombre_tabla} ({campos})"
            try:
                conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
                with conn.cursor() as cursor:
                    cursor.execute(query)
                conn.commit()
                mensaje = '✅ Tabla creada exitosamente'
            except Exception as e:
                mensaje = f'❌ Error SQL: {e}'
            finally:
                conn.close()

    return render_template('crear_tabla.html', mensaje=mensaje, motor=motor)

 # Crear relación
 
@app.route('/crear-relacion/<motor>', methods=['GET', 'POST'])
def crear_relacion(motor):
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
            conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
            with conn.cursor() as cursor:
                cursor.execute(alter_query)
            conn.commit()
            mensaje = '✅ Relación FOREIGN KEY creada exitosamente'
        except Exception as e:
            mensaje = f'❌ Error: {e}'
        finally:
            conn.close()

    return render_template('crear_relacion.html', mensaje=mensaje, motor=motor)

@app.route('/insertar/<motor>', methods=['GET', 'POST'])
def seleccionar_tabla_insertar(motor):
    tablas = []

    try:
        conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
        cursor = conn.cursor()
        if motor == 'mysql':
            cursor.execute("SHOW TABLES")
            tablas = [fila[0] for fila in cursor.fetchall()]
        else:
            cursor.execute("SELECT name FROM sys.tables")
            tablas = [fila[0] for fila in cursor.fetchall()]
    except Exception as e:
        return f"<h1>Error al obtener tablas</h1><p>{e}</p>"
    finally:
        conn.close()

    if request.method == 'POST':
        tabla_seleccionada = request.form['tabla']
        return redirect(url_for('insertar_datos', motor=motor, tabla=tabla_seleccionada))

    return render_template('seleccionar_tabla.html', tablas=tablas, motor=motor)



@app.route('/insertar/<motor>/<tabla>', methods=['GET', 'POST'])
def insertar_datos(motor, tabla):
    columnas = []

    try:
        conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
        cursor = conn.cursor()
        
        if motor == 'mysql':
            query = f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'test_sgbd' AND table_name = %s
            """
            cursor.execute(query, (tabla,))
        else:
            query = f"""
            SELECT c.name 
            FROM sys.columns c
            JOIN sys.tables t ON c.object_id = t.object_id
            WHERE t.name = ?
            """
            cursor.execute(query, (tabla,))
        
        columnas = [fila[0] for fila in cursor.fetchall()]

    except Exception as e:
        return f"<h1>Error obteniendo columnas</h1><p>{e}</p>"
    finally:
        conn.close()

    if request.method == 'POST':
        valores = [request.form[col] for col in columnas]
        campos_str = ', '.join(columnas)
        placeholders = ', '.join(['%s'] * len(valores)) if motor == 'mysql' else ', '.join(['?'] * len(valores))
        query_insert = f"INSERT INTO {tabla} ({campos_str}) VALUES ({placeholders})"

        try:
            conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
            cursor = conn.cursor()
            cursor.execute(query_insert, valores)
            conn.commit()
            mensaje = "✅ Registro insertado correctamente"
        except Exception as e:
            mensaje = f"❌ Error al insertar: {e}"
        finally:
            conn.close()
        
        return render_template('insertar_formulario.html', columnas=columnas, tabla=tabla, motor=motor, mensaje=mensaje)

    return render_template('insertar_formulario.html', columnas=columnas, tabla=tabla, motor=motor)



 # Iniciar servidor
 
 

if __name__ == '__main__':
    app.run(debug=True)

