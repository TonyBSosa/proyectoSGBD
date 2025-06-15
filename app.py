from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyodbc
import pymysql

 
app = Flask(__name__, template_folder='webpage')
app.secret_key = '123456' 


 # Funciones de conexión
 
def conectar_sqlserver():
    base = session.get('base_datos')  # default db
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=(localdb)\\VerbTables;'
        f'DATABASE={base};'
        'Trusted_Connection=yes;'
    )

def conectar_mysql():
    base = session.get('base_datos')
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database=base,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.Cursor
    )

#seleccion de motor 
@app.route('/', methods=['GET', 'POST'])
def seleccionar_motor():
    mensaje = ''
    if request.method == 'POST':
        motor = request.form['motor']
        accion = request.form['accion']

        if accion == 'predeterminada':
            base = 'Example DB' if motor == 'sqlserver' else 'test_sgbd' or 'base_datos'

        elif accion == 'existente':
            base = request.form.get('base_existente', '').strip()
            if not base:
                mensaje = "⚠️ Debes ingresar el nombre de una base existente."
                return render_template('seleccionar_motor.html', mensaje=mensaje)

        elif accion == 'crear':
            base = request.form.get('base_nueva', '').strip()
            if not base:
                mensaje = "⚠️ Debes ingresar un nombre para la nueva base."
                return render_template('seleccionar_motor.html', mensaje=mensaje)

            try:
                if motor == 'mysql':
                    conn = pymysql.connect(
                        host='localhost',
                        user='root',
                        password='',
                        charset='utf8mb4',
                        cursorclass=pymysql.cursors.Cursor
                    )
                    with conn.cursor() as cursor:
                        cursor.execute(f"CREATE DATABASE `{base}`")
                    conn.commit()
                else:
                    conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=(localdb)\\VerbTables;'
    'DATABASE=master;'
    'Trusted_Connection=yes;',
    autocommit=True  # Activa autocommit explícitamente
)

                    with conn.cursor() as cursor:
                        cursor.execute(f"CREATE DATABASE [{base}]")
                    conn.commit()
            except Exception as e:
                mensaje = f"❌ Error creando la base: {e}"
                return render_template('seleccionar_motor.html', mensaje=mensaje)
            finally:
                conn.close()
        else:
            mensaje = "⚠️ Opción inválida."
            return render_template('seleccionar_motor.html', mensaje=mensaje)

        # Guardar en la sesión y continuar
        session['motor'] = motor
        session['base_datos'] = base
        return redirect(url_for('ver_metadata', motor=motor))

    return render_template('seleccionar_motor.html', mensaje=mensaje)


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
        base_actual = session.get('base_datos', 'test_sgbd')
        conn = conectar_mysql()
        query = f"""
        SELECT 
            table_name AS tabla,
            column_name AS columna,
            data_type AS tipo
        FROM information_schema.columns
        WHERE table_schema = '{base_actual}'
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
        campos_sql = []
        i = 0
        while True:
            nombre_campo = request.form.get(f'nombre_campo_{i}')
            tipo_campo = request.form.get(f'tipo_campo_{i}')
            null_opcion = request.form.get(f'null_{i}')  # ← esta línea toma el valor de NULL o NOT NULL

            if not nombre_campo or not tipo_campo:
                break

            es_pk = f'pk_{i}' in request.form
            es_null = f'null_{i}' in request.form
            campo_def = f"{nombre_campo} {tipo_campo}"


            # Agregar NULL / NOT NULL
            if es_pk:
                campo_def += " PRIMARY KEY NOT NULL"

            # Agregar PRIMARY KEY si aplica
            elif not es_null:
                campo_def += " NOT NULL"

            campos_sql.append(campo_def)
            i += 1

        if not campos_sql:
            mensaje = "❌ Debes agregar al menos un campo."
        else:
            query = f"CREATE TABLE {nombre_tabla} ({', '.join(campos_sql)})"
            try:
                conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
                with conn.cursor() as cursor:
                    cursor.execute(query)
                conn.commit()
                return redirect(url_for('ver_metadata', motor=motor))
            except Exception as e:
                mensaje = f"❌ Error al crear tabla: {e}"
            finally:
                conn.close()

    return render_template('crear_tabla.html', mensaje=mensaje, motor=motor)


 # Crear relación
@app.route('/crear-relacion/<motor>', methods=['GET', 'POST'])
def crear_relacion(motor):
    conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
    cursor = conn.cursor()

    # Obtener todas las tablas para el formulario
    if motor == 'mysql':
        cursor.execute("SHOW TABLES")
        tablas = [fila[0] for fila in cursor.fetchall()]
    else:
        cursor.execute("SELECT name FROM sys.tables")
        tablas = [fila[0] for fila in cursor.fetchall()]

    mensaje = None

    if request.method == 'POST':
        tabla_pk = request.form.get('tabla_pk')
        campo_pk = request.form.get('campo_pk')
        tabla_fk = request.form.get('tabla_fk')
        campo_fk = request.form.get('campo_fk')
        on_update = 'CASCADE' if request.form.get('on_update') else 'NO ACTION'
        on_delete = 'CASCADE' if request.form.get('on_delete') else 'NO ACTION'



        if not all([tabla_pk, campo_pk, tabla_fk, campo_fk]):
            mensaje = "❌ Faltan datos necesarios para crear la relación"
        else:
            try:
                # Verificar tipos de datos
                if motor == 'mysql':
                    cursor.execute("""
                        SELECT data_type 
                        FROM information_schema.columns
                        WHERE table_schema = DATABASE()
                        AND table_name = %s AND column_name = %s
                    """, (tabla_pk, campo_pk))
                    tipo_pk = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT data_type 
                        FROM information_schema.columns
                        WHERE table_schema = DATABASE()
                        AND table_name = %s AND column_name = %s
                    """, (tabla_fk, campo_fk))
                    tipo_fk = cursor.fetchone()[0]
                else:  # SQL Server
                    cursor.execute("""
                        SELECT ty.name 
                        FROM sys.columns c
                        JOIN sys.tables t ON c.object_id = t.object_id
                        JOIN sys.types ty ON c.user_type_id = ty.user_type_id
                        WHERE t.name = ? AND c.name = ?
                    """, (tabla_pk, campo_pk))
                    tipo_pk = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT ty.name 
                        FROM sys.columns c
                        JOIN sys.tables t ON c.object_id = t.object_id
                        JOIN sys.types ty ON c.user_type_id = ty.user_type_id
                        WHERE t.name = ? AND c.name = ?
                    """, (tabla_fk, campo_fk))
                    tipo_fk = cursor.fetchone()[0]

                if tipo_pk != tipo_fk:
                    mensaje = f"❌ Tipos de datos no coinciden: {tipo_pk} ≠ {tipo_fk}"
                else:
                    # Crear relación
                    alter_sql = f"""
                        ALTER TABLE {tabla_fk}
                        ADD CONSTRAINT fk_{tabla_fk}_{campo_fk}
                        FOREIGN KEY ({campo_fk}) 
                        REFERENCES {tabla_pk}({campo_pk})
                        ON UPDATE {on_update}
                        ON DELETE {on_delete}
                    """
                    cursor.execute(alter_sql)
                    conn.commit()
                mensaje = f"✅ Relación entre {tabla_pk}({campo_pk}) → {tabla_fk}({campo_fk}) creada con éxito"
            except Exception as e:
                mensaje = f"❌ Error creando la relación: {e}"
            finally:
                conn.close()

    return render_template("crear_relacion.html", tablas=tablas, motor=motor, mensaje=mensaje)



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
    registros = []
    mensaje = ''
    base = session.get('base_datos', 'test_sgbd')  # Cambia si tu base predeterminada es otra

    try:
        conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
        cursor = conn.cursor()

        # Obtener nombres de columnas
        if motor == 'mysql':
            cursor.execute("""
                SELECT column_name, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = %s
            """, (base, tabla))
            columnas_info = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT c.name, c.is_nullable
                FROM sys.columns c
                JOIN sys.tables t ON c.object_id = t.object_id
                WHERE t.name = ?
            """, (tabla,))
            columnas_info = cursor.fetchall()

        columnas = [col[0] for col in columnas_info]
        campos_requeridos = [col[0] for col in columnas_info if (col[1] == 'NO' if motor == 'mysql' else col[1] == 0)]

        # Insertar datos si se envió el formulario
        if request.method == 'POST':
            valores = []
            for col in columnas:
                valor = request.form.get(col)
                valores.append(None if valor == '' else valor)

            campos_str = ', '.join(columnas)
            placeholders = ', '.join(['%s'] * len(valores)) if motor == 'mysql' else ', '.join(['?'] * len(valores))
            query_insert = f"INSERT INTO {tabla} ({campos_str}) VALUES ({placeholders})"

            cursor.execute(query_insert, valores)
            conn.commit()
            mensaje = "✅ Registro insertado correctamente"

        # Mostrar todos los registros actuales de la tabla
        cursor.execute(f"SELECT * FROM {tabla}")
        registros = cursor.fetchall()

    except Exception as e:
        if "FOREIGN KEY constraint" in str(e):
            mensaje = "❌ Error: Está intentando insertar un valor que no existe en una tabla relacionada."
        else:
            mensaje = f"❌ Error al insertar registro: {e}"
    finally:
        conn.close()

    return render_template(
        'insertar_formulario.html',
        columnas=columnas,
        tabla=tabla,
        motor=motor,
        mensaje=mensaje,
        registros=registros,
        campos_requeridos=campos_requeridos
    )

 

@app.route('/actualizar-celda', methods=['POST'])
def actualizar_celda():
    motor = request.form['motor']
    tabla = request.form['tabla']
    columna = request.form['columna']
    id_columna = request.form['id_columna']
    id_valor = request.form['id_valor']
    valor = request.form['valor']

    try:
        conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
        cursor = conn.cursor()

        query = f"UPDATE {tabla} SET {columna} = %s WHERE {id_columna} = %s" if motor == 'mysql' \
                else f"UPDATE {tabla} SET {columna} = ? WHERE {id_columna} = ?"

        cursor.execute(query, (valor, id_valor))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        conn.close()


@app.route('/obtener-columnas')
def obtener_columnas():
    motor = request.args.get('motor')
    tabla = request.args.get('tabla')

    try:
        conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
        cursor = conn.cursor()

        if motor == 'mysql':
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = %s
            """, (tabla, session.get('base_datos')))
        else:
            cursor.execute("""
                SELECT c.name 
                FROM sys.columns c
                JOIN sys.tables t ON c.object_id = t.object_id
                WHERE t.name = ?
            """, (tabla,))
        
        columnas = [fila[0] for fila in cursor.fetchall()]
        return jsonify({'columnas': columnas})

    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()

# Funcion eliminar fila
@app.route('/eliminar-fila', methods=['POST'])
def eliminar_fila():
    motor = request.form['motor']
    tabla = request.form['tabla']
    id_columna = request.form['id_columna']
    id_valor = request.form['id_valor']

    try:
        conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
        cursor = conn.cursor()

        query = f"DELETE FROM {tabla} WHERE {id_columna} = %s" if motor == 'mysql' \
                else f"DELETE FROM {tabla} WHERE {id_columna} = ?"

        cursor.execute(query, (id_valor,))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        conn.close()


from flask import jsonify

#obtener campos

@app.route('/obtener-campos/<tabla>')

def obtener_campos(tabla):
    motor = request.args.get('motor', 'mysql')  # Por defecto mysql
    columnas = []

    try:
        conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
        cursor = conn.cursor()
        if motor == 'mysql':
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() AND table_name = %s
            """, (tabla,))
        else:
            cursor.execute("""
                SELECT c.name 
                FROM sys.columns c
                JOIN sys.tables t ON c.object_id = t.object_id
                WHERE t.name = ?
            """, (tabla,))
        columnas = [fila[0] for fila in cursor.fetchall()]
    except Exception as e:
        return jsonify([])  # Devuelve vacío si hay error
    finally:
        conn.close()

    return jsonify(columnas)

#consultas
@app.route('/consultas/<motor>', methods=['GET', 'POST'])
def consultas(motor):
    conn = conectar_mysql() if motor == 'mysql' else conectar_sqlserver()
    cursor = conn.cursor()

    tablas = []
    vistas = []
    funciones = []
    resultados = []
    columnas = []
    mensaje = ''
    consulta = ''

    try:
        # Obtener tablas
        if motor == 'mysql':
            cursor.execute("SHOW TABLES")
            tablas = [fila[0] for fila in cursor.fetchall()]
        else:
            cursor.execute("SELECT name FROM sys.tables")
            tablas = [fila[0] for fila in cursor.fetchall()]

        # Obtener vistas
        if motor == 'mysql':
            cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
            vistas = [fila[0] for fila in cursor.fetchall()]
        else:
            cursor.execute("SELECT name FROM sys.views")
            vistas = [fila[0] for fila in cursor.fetchall()]

        # Obtener funciones escalares (sin parámetros visibles)
        if motor == 'mysql':
            cursor.execute("SELECT routine_name FROM information_schema.routines WHERE routine_type='FUNCTION' AND routine_schema=DATABASE()")
            funciones = [f"{fila[0]}()" for fila in cursor.fetchall()]
        else:
            cursor.execute("SELECT name FROM sys.objects WHERE type = 'FN'")
            funciones = [f"{fila[0]}()" for fila in cursor.fetchall()]

        # Si viene una consulta por POST
        if request.method == 'POST':
            consulta = request.form.get('consulta', '').strip()

            if consulta:
                try:
                    cursor.execute(consulta)
                    if cursor.description:
                        columnas = [col[0] for col in cursor.description]
                        resultados = cursor.fetchall()
                    mensaje = "✅ Consulta ejecutada correctamente"
                except Exception as e:
                    mensaje = f"❌ Error: {e}"
    finally:
        conn.close()

    return render_template(
        'consultas.html',
        motor=motor,
        tablas=tablas,
        vistas=vistas,
        funciones=funciones,
        resultados=resultados,
        columnas=columnas,
        mensaje=mensaje,
        consulta=consulta
    )



 # Iniciar servidor
 
 

if __name__ == '__main__':
    app.run(debug=True)

