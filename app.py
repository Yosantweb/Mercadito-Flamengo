import datetime
import sqlite3
import urllib.parse
import pandas as pd
import streamlit as st

# Configuración inicial de la página
st.set_page_config(
    page_title="Control de Créditos - Tienda Residencial",
    page_icon="🛒",
    layout="wide",
)

st.title("🛒 Control de Créditos y Cartera - Tienda Residencial")
st.markdown(
    "Panel de administración, ventas mixtas, control de cartera, cobros masivos y buzón de pedidos."
)

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA BASE DE DATOS SQLITE (CON AUTO-MIGRACIÓN)
# ---------------------------------------------------------
DB_NAME = "tienda.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabla de inmuebles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id_inmueble TEXT PRIMARY KEY,
            torre TEXT,
            apartamento TEXT,
            responsable TEXT,
            telefono TEXT
        )
    """)

    # Tabla de transacciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacciones (
            id_transaccion INTEGER PRIMARY KEY AUTOINCREMENT,
            id_inmueble TEXT,
            fecha TEXT,
            comprador TEXT,
            descripcion TEXT,
            monto_total REAL,
            monto_contado REAL,
            monto_credito REAL,
            estado TEXT,
            FOREIGN KEY (id_inmueble) REFERENCES clientes (id_inmueble)
        )
    """)

    # Tabla nueva para Buzón de Mensajes y Pedidos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id_mensaje INTEGER PRIMARY KEY AUTOINCREMENT,
            id_inmueble TEXT,
            fecha TEXT,
            tipo_mensaje TEXT,
            contenido TEXT,
            estado_mensaje TEXT,
            FOREIGN KEY (id_inmueble) REFERENCES clientes (id_inmueble)
        )
    """)

    # Autocorrección si la tabla transacciones ya existía sin las columnas nuevas
    cursor.execute("PRAGMA table_info(transacciones)")
    columnas_existentes = [col[1] for col in cursor.fetchall()]

    if "monto_total" not in columnas_existentes:
        cursor.execute(
            "ALTER TABLE transacciones ADD COLUMN monto_total REAL DEFAULT 0"
        )
    if "monto_contado" not in columnas_existentes:
        cursor.execute(
            "ALTER TABLE transacciones ADD COLUMN monto_contado REAL DEFAULT 0"
        )
    if "monto_credito" not in columnas_existentes:
        cursor.execute(
            "ALTER TABLE transacciones ADD COLUMN monto_credito REAL DEFAULT 0"
        )

    conn.commit()
    conn.close()


init_db()


def cargar_clientes():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM clientes", conn)
    conn.close()
    return df


def cargar_transacciones():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM transacciones", conn)
    conn.close()
    return df


def cargar_mensajes():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM mensajes", conn)
    conn.close()
    return df


# Menú lateral para navegar actualizado
menu = st.sidebar.selectbox(
    "Menú de Administración",
    [
        "📊 Dashboard y Cartera General",
        "📝 Registrar Venta (Contado / Crédito / Mixta)",
        "💵 Registrar Abono o Pago Total",
        "💬 Buzón de Pedidos y Requerimientos",
        "📈 Histórico Mensual y por Inmueble",
        "🏢 Registro y Edición de Inmuebles",
        "💰 Corte Quincenal y Cobros WhatsApp",
    ],
)

# ---------------------------------------------------------
# 0. DASHBOARD Y CARTERA GENERAL
# ---------------------------------------------------------
if menu == "📊 Dashboard y Cartera General":
    st.header("📊 Panel de Control General (Dashboard)")
    st.markdown("Resumen financiero en tiempo real del estado de tu negocio y cartera.")

    df_trans = cargar_transacciones()
    df_clientes = cargar_clientes()

    if len(df_trans) == 0 or len(df_clientes) == 0:
        st.info("Aún no hay suficientes datos registrados para mostrar el dashboard.")
    else:
        df_pendientes = df_trans[df_trans["estado"] == "Pendiente"]
        cartera_total = df_pendientes["monto_credito"].sum()
        ventas_totales = df_trans["monto_total"].sum()
        total_inmuebles = len(df_clientes)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="💰 Cartera Total en la Calle",
                value=f"${cartera_total:,.0f}",
                delta="Dinero pendiente por cobrar",
            )
        with col2:
            st.metric(
                label="🛒 Ventas Totales Históricas", value=f"${ventas_totales:,.0f}"
            )
        with col3:
            st.metric(
                label="🏠 Inmuebles Registrados", value=f"{total_inmuebles}"
            )

        st.divider()
        st.subheader("📋 Resumen de Cartera Actual por Apartamento")

        if len(df_pendientes) > 0:
            df_merged_p = df_pendientes.merge(df_clientes, on="id_inmueble")
            cartera_por_apto = (
                df_merged_p.groupby(
                    ["id_inmueble", "responsable", "telefono"]
                )["monto_credito"]
                .sum()
                .reset_index()
            )
            cartera_por_apto.columns = [
                "Inmueble",
                "Responsable",
                "Teléfono",
                "Deuda Pendiente ($)",
            ]
            st.dataframe(cartera_por_apto, use_container_width=True)
        else:
            st.success("¡Excelente! No hay cartera pendiente en este momento.")

# ---------------------------------------------------------
# 1. REGISTRAR VENTA (CONTADO / CRÉDITO / MIXTA)
# ---------------------------------------------------------
elif menu == "📝 Registrar Venta (Contado / Crédito / Mixta)":
    st.header("📝 Registro de Ventas")
    st.markdown(
        "Registra ventas de contado, fiadas por completo, o mixtas (parte pagada de contado y parte a crédito)."
    )

    df_clientes = cargar_clientes()

    if len(df_clientes) == 0:
        st.warning(
            "Primero debes registrar al menos un inmueble en 'Registro y Edición de Inmuebles'."
        )
    else:
        inmuebles_dict = {
            f"{row['torre']} - {row['apartamento']} (Contacto: {row['responsable']})": row[
                "id_inmueble"
            ]
            for _, row in df_clientes.iterrows()
        }
        inmueble_seleccionado = st.selectbox(
            "Seleccione el Apartamento / Casa",
            options=list(inmuebles_dict.keys()),
        )

        comprador = st.text_input(
            "¿Quién realizó la compra?",
            placeholder="Ej: El esposo, la esposa, el hijo, etc.",
        )
        descripcion = st.text_input(
            "Descripción de los productos",
            placeholder="Ej: 1 Arroz, 1 Aceite, Gaseosa",
        )
        monto_total = st.number_input(
            "Valor Total de la Venta ($)", min_value=0, step=1000, value=50000
        )

        tipo_venta = st.radio(
            "Forma de Pago de esta Venta",
            [
                "Crédito 100% (Todo al fío)",
                "Contado 100% (Pagado de inmediato)",
                "Venta Mixta (Parte contado y parte a crédito)",
            ],
        )

        monto_contado_ingresado = 0
        if tipo_venta == "Venta Mixta (Parte contado y parte a crédito)":
            monto_contado_ingresado = st.number_input(
                "¿Cuánto pagó de contado en efectivo/transferencia?",
                min_value=0,
                step=1000,
                value=20000,
            )

        fecha = st.date_input("Fecha de la venta", value=datetime.date.today())

        if st.button("Registrar Venta"):
            if not comprador:
                st.error("Por favor indica quién realizó la compra.")
            elif monto_total <= 0:
                st.error("El valor total de la venta debe ser mayor a cero.")
            else:
                id_inm = inmuebles_dict[inmueble_seleccionado]

                if tipo_venta == "Crédito 100% (Todo al fío)":
                    m_contado = 0.0
                    m_credito = float(monto_total)
                    estado = "Pendiente"
                elif tipo_venta == "Contado 100% (Pagado de inmediato)":
                    m_contado = float(monto_total)
                    m_credito = 0.0
                    estado = "Pagado"
                else:  # Venta Mixta
                    if monto_contado_ingresado >= monto_total:
                        st.error(
                            "El monto de contado no puede ser mayor o igual al valor total de la venta."
                        )
                        estado = None
                    elif monto_contado_ingresado < 0:
                        st.error("El abono de contado no puede ser negativo.")
                        estado = None
                    else:
                        m_contado = float(monto_contado_ingresado)
                        m_credito = float(monto_total - monto_contado_ingresado)
                        estado = "Pendiente"

                if "estado" in locals() and estado is not None:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO transacciones (id_inmueble, fecha, comprador, descripcion, monto_total, monto_contado, monto_credito, estado)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                id_inm,
                                str(fecha),
                                comprador,
                                descripcion,
                                float(monto_total),
                                m_contado,
                                m_credito,
                                estado,
                            ),
                        )
                        conn.commit()
                        conn.close()
                        st.success(
                            f"¡Venta registrada con éxito! Total: ${monto_total:,.0f} | Contado: ${m_contado:,.0f} | A crédito: ${m_credito:,.0f}"
                        )
                    except Exception as e:
                        st.error(f"Error al guardar en la base de datos: {e}")

# ---------------------------------------------------------
# 2. REGISTRAR ABONO O PAGO TOTAL
# ---------------------------------------------------------
elif menu == "💵 Registrar Abono o Pago Total":
    st.header("💵 Registrar Abono o Pago de Deuda")

    df_clientes = cargar_clientes()
    df_trans = cargar_transacciones()

    if len(df_clientes) == 0:
        st.warning("No hay inmuebles registrados.")
    else:
        df_t_pend = df_trans[df_trans["estado"] == "Pendiente"]

        if len(df_t_pend) == 0:
            st.success("¡Excelente! No hay deudas pendientes registradas.")
        else:
            inmuebles_dict = {
                f"{row['torre']} - {row['apartamento']} (Contacto: {row['responsable']})": row[
                    "id_inmueble"
                ]
                for _, row in df_clientes.iterrows()
            }
            inmueble_seleccionado = st.selectbox(
                "Seleccione el Apartamento que realiza el pago",
                options=list(inmuebles_dict.keys()),
            )
            id_inm_sel = inmuebles_dict[inmueble_seleccionado]

            deudas_inmueble = df_t_pend[
                df_t_pend["id_inmueble"] == id_inm_sel
            ]
            total_deuda = deudas_inmueble["monto_credito"].sum()

            if total_deuda > 0:
                st.info(
                    f"🏠 **{inmueble_seleccionado}** tiene una cartera pendiente total de: **${total_deuda:,.0f}**"
                )

                with st.expander("Ver detalle de compras pendientes a crédito"):
                    st.table(
                        deudas_inmueble[
                            [
                                "fecha",
                                "comprador",
                                "descripcion",
                                "monto_total",
                                "monto_credito",
                            ]
                        ]
                    )

                with st.form("form_pago"):
                    tipo_pago = st.radio(
                        "Tipo de Transacción",
                        ["Pago Total (Cancelar toda la deuda)", "Abono Parcial"],
                    )
                    monto_abono = st.number_input(
                        "Valor del Abono ($)", min_value=0, step=1000, value=0
                    )
                    ejecutar_pago = st.form_submit_button(
                        "Registrar Transacción de Pago"
                    )

                    if ejecutar_pago:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()

                        if tipo_pago == "Pago Total (Cancelar toda la deuda)":
                            cursor.execute(
                                """
                                UPDATE transacciones SET estado = 'Pagado', monto_credito = 0
                                WHERE id_inmueble = ? AND estado = 'Pendiente'
                            """,
                                (id_inm_sel,),
                            )
                            conn.commit()
                            conn.close()
                            st.success("¡Deuda cancelada en su totalidad!")
                            st.rerun()
                        else:
                            if monto_abono <= 0:
                                st.error("Ingresa un valor válido para el abono.")
                            elif monto_abono > total_deuda:
                                st.error(
                                    "El abono no puede ser mayor a la deuda total."
                                )
                            else:
                                cursor.execute(
                                    """
                                    INSERT INTO transacciones (id_inmueble, fecha, comprador, descripcion, monto_total, monto_contado, monto_credito, estado)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                    (
                                        id_inm_sel,
                                        str(datetime.date.today()),
                                        "ABONO / PAGO",
                                        "Abono parcial a la deuda",
                                        float(monto_abono),
                                        float(monto_abono),
                                        float(-monto_abono),
                                        "Pendiente",
                                    ),
                                )
                                conn.commit()
                                conn.close()
                                st.success("¡Abono registrado con éxito!")
                                st.rerun()
            else:
                st.success("Este apartamento no tiene saldos pendientes.")

# ---------------------------------------------------------
# 3. BUZÓN DE PEDIDOS Y REQUERIMIENTOS
# ---------------------------------------------------------
elif menu == "💬 Buzón de Pedidos y Requerimientos":
    st.header("💬 Buzón de Pedidos y Requerimientos de Vecinos")
    st.markdown(
        "Canal de comunicación donde los residentes pueden enviar pedidos de tienda, consultas de productos o encargos."
    )

    df_clientes = cargar_clientes()

    if len(df_clientes) == 0:
        st.warning("No hay inmuebles registrados para usar el buzón.")
    else:
        tab_envio, tab_bandeja = st.tabs(
            ["Enviar Pedido / Mensaje", "Bandeja de Entrada (Tendero)"]
        )

        with tab_envio:
            with st.form("form_enviar_mensaje"):
                inmuebles_dict = {
                    f"{row['torre']} - {row['apartamento']} (Contacto: {row['responsable']})": row[
                        "id_inmueble"
                    ]
                    for _, row in df_clientes.iterrows()
                }
                inmueble_remitente = st.selectbox(
                    "Seleccione su Apartamento / Casa",
                    options=list(inmuebles_dict.keys()),
                )

                tipo_solicitud = st.selectbox(
                    "Tipo de Requerimiento",
                    [
                        "Pedido de Tienda / Domicilio",
                        "Consulta de Disponibilidad",
                        "Otro Mensaje al Tendero",
                    ],
                )
                contenido_mensaje = st.text_area(
                    "Escriba su mensaje o listado de productos",
                    placeholder="Ej: Don Julio, por favor envíeme 1 pan, 6 huevos y una leche deslactosada para recoger a las 5pm.",
                )

                enviar_btn = st.form_submit_button("Enviar Mensaje al Tendero")

                if enviar_btn and contenido_mensaje:
                    id_inm = inmuebles_dict[inmueble_remitente]
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO mensajes (id_inmueble, fecha, tipo_mensaje, contenido, estado_mensaje)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            id_inm,
                            str(datetime.date.today()),
                            tipo_solicitud,
                            contenido_mensaje,
                            "Pendiente",
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success(
                        "¡Mensaje enviado con éxito al tendero! Pronto le responderá o preparará su pedido."
                    )

        with tab_bandeja:
            st.subheader("📬 Mensajes y Pedidos Recibidos")
            df_mensajes = cargar_mensajes()

            if len(df_mensajes) > 0:
                df_merged_m = df_mensajes.merge(df_clientes, on="id_inmueble")
                df_merged_m = df_merged_m.sort_values(
                    by="id_mensaje", ascending=False
                )

                for _, row in df_merged_m.iterrows():
                    with st.expander(
                        f"🏠 [{row['fecha']}] {row['id_inmueble']} — {row['tipo_mensaje']} (Estado: {row['estado_mensaje']})"
                    ):
                        st.markdown(f"**Residente:** {row['responsable']}")
                        st.markdown(f"**Teléfono:** {row['telefono']}")
                        st.markdown(f"**Contenido del pedido:**")
                        st.info(row["contenido"])

                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            if st.button(
                                f"Marcar Atendido #{row['id_mensaje']}",
                                key=f"atendido_{row['id_mensaje']}",
                            ):
                                conn = sqlite3.connect(DB_NAME)
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    UPDATE mensajes SET estado_mensaje = 'Atendido'
                                    WHERE id_mensaje = ?
                                """,
                                    (row["id_mensaje"],),
                                )
                                conn.commit()
                                conn.close()
                                st.success("¡Marcado como atendido!")
                                st.rerun()
                        with col_m2:
                            # Botón para responderle directamente por WhatsApp al vecino desde el pedido
                            tel_limpio = (
                                str(row["telefono"]).strip().replace(" ", "")
                            )
                            if not tel_limpio.startswith("57"):
                                tel_limpio = "57" + tel_limpio
                            resp_w, _ = st.columns([3, 1])
                            msg_w = urllib.parse.quote(
                                f"Hola {row['responsable']}, le escribimos de la tienda sobre su mensaje: '{row['contenido']}'."
                            )
                            st.markdown(
                                f'<a href="https://wa.me/{tel_limpio}?text={msg_w}" target="_blank"><button style="background-color:#25D366; color:white; padding:8px 16px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">💬 Responder por WhatsApp</button></a>',
                                unsafe_allow_html=True,
                            )
            else:
                st.info("No hay mensajes ni pedidos en el buzón por ahora.")

# ---------------------------------------------------------
# 4. HISTÓRICO MENSUAL Y POR INMUEBLE
# ---------------------------------------------------------
elif menu == "📈 Histórico Mensual y por Inmueble":
    st.header("📈 Histórico General y por Inmueble")
    st.markdown(
        "Consulta el comportamiento de las ventas y los créditos filtrando por mes y por apartamento."
    )

    df_trans = cargar_transacciones()
    df_clientes = cargar_clientes()

    if len(df_trans) == 0:
        st.info("No hay transacciones registradas para mostrar histórico.")
    else:
        df_trans["mes"] = df_trans["fecha"].astype(str).str.slice(0, 7)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            meses_disponibles = sorted(df_trans["mes"].unique(), reverse=True)
            mes_seleccionado = st.selectbox(
                "Filtrar por Mes (AÑO-MES)", options=meses_disponibles
            )
        with col_f2:
            opciones_inm = ["Todos los Inmuebles"] + df_clientes[
                "id_inmueble"
            ].tolist()
            inm_seleccionado = st.selectbox(
                "Filtrar por Inmueble", options=opciones_inm
            )

        df_filtrado = df_trans[df_trans["mes"] == mes_seleccionado]
        if inm_seleccionado != "Todos los Inmuebles":
            df_filtrado = df_filtrado[
                df_filtrado["id_inmueble"] == inm_seleccionado
            ]

        st.subheader(f"Resultados para el período: {mes_seleccionado}")

        if len(df_filtrado) > 0:
            t_ventas = df_filtrado["monto_total"].sum()
            t_contado = df_filtrado["monto_contado"].sum()
            t_credito = df_filtrado["monto_credito"].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("Ventas Totales del Mes", f"${t_ventas:,.0f}")
            c2.metric("Ingresos de Contado", f"${t_contado:,.0f}")
            c3.metric("Créditos Otorgados", f"${t_credito:,.0f}")

            st.divider()
            st.subheader("Detalle de Transacciones del Período")
            st.dataframe(
                df_filtrado[
                    [
                        "fecha",
                        "id_inmueble",
                        "comprador",
                        "descripcion",
                        "monto_total",
                        "monto_contado",
                        "monto_credito",
                        "estado",
                    ]
                ],
                use_container_width=True,
            )
        else:
            st.info("No se encontraron registros para los filtros seleccionados.")

# ---------------------------------------------------------
# 5. REGISTRO Y EDICIÓN DE INMUEBLES
# ---------------------------------------------------------
elif menu == "🏢 Registro y Edición de Inmuebles":
    st.header("🏢 Gestión y Actualización de Inmuebles")

    tab1, tab2 = st.tabs(["Registrar Nuevo Inmueble", "Editar Inmueble Existente"])

    with tab1:
        with st.form("form_inmueble"):
            torre = st.text_input("Torre / Bloque (Ej: Torre 1, Manzana A)")
            apartamento = st.text_input(
                "Apartamento / Casa (Ej: Apto 201, Casa 15)"
            )
            responsable = st.text_input("Nombre del residente principal")
            telefono = st.text_input("Número de WhatsApp (Ej: 3226834617)")
            guardar_inm = st.form_submit_button("Registrar Inmueble")

            if guardar_inm and torre and apartamento and responsable and telefono:
                id_inm = f"{torre} - {apartamento}"
                df_clientes = cargar_clientes()

                if (
                    len(df_clientes) > 0
                    and id_inm in df_clientes["id_inmueble"].values
                ):
                    st.error(
                        f"¡El inmueble {id_inm} ya se encuentra registrado!"
                    )
                else:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO clientes (id_inmueble, torre, apartamento, responsable, telefono)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (id_inm, torre, apartamento, responsable, telefono),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Inmueble {id_inm} guardado correctamente.")

    with tab2:
        df_clientes = cargar_clientes()
        if len(df_clientes) > 0:
            with st.form("form_editar_inmueble"):
                lista_inm = df_clientes["id_inmueble"].tolist()
                inmueble_a_editar = st.selectbox(
                    "Seleccione el Inmueble a Editar", options=lista_inm
                )

                datos_actuales = df_clientes[
                    df_clientes["id_inmueble"] == inmueble_a_editar
                ].iloc[0]

                nuevo_responsable = st.text_input(
                    "Nuevo nombre del responsable",
                    value=datos_actuales["responsable"],
                )
                nuevo_telefono = st.text_input(
                    "Nuevo número de WhatsApp",
                    value=datos_actuales["telefono"],
                )

                actualizar_btn = st.form_submit_button("Actualizar Datos")

                if actualizar_btn:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE clientes SET responsable = ?, telefono = ?
                        WHERE id_inmueble = ?
                    """,
                        (
                            nuevo_responsable,
                            nuevo_telefono,
                            inmueble_a_editar,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success(
                        f"¡Datos del inmueble {inmueble_a_editar} actualizados con éxito!"
                    )
        else:
            st.info("No hay inmuebles registrados.")

    st.subheader("Base de Datos de Inmuebles Activos")
    st.dataframe(cargar_clientes(), use_container_width=True)

# ---------------------------------------------------------
# 6. CORTE QUINCENAL Y COBROS WHATSAPP (CON ENVÍO MASIVO)
# ---------------------------------------------------------
elif menu == "💰 Corte Quincenal y Cobros WhatsApp":
    st.header("💰 Liquidación Quincenal y Panel de Cobros por WhatsApp")
    st.markdown(
        "Envía los extractos individuales o utiliza el **Panel de Envío Masivo** para notificar a todos los deudores en la víspera de la quincena."
    )

    df_trans = cargar_transacciones()
    df_clientes = cargar_clientes()

    if len(df_trans) == 0:
        st.info("No hay transacciones registradas.")
    else:
        df_t = df_trans[df_trans["estado"] == "Pendiente"].copy()

        if len(df_t) > 0 and len(df_clientes) > 0:
            df_merged = df_t.merge(df_clientes, on="id_inmueble")

            resumen_deudas = (
                df_merged.groupby([
                    "id_inmueble",
                    "torre",
                    "apartamento",
                    "responsable",
                    "telefono",
                ])["monto_credito"]
                .sum()
                .reset_index()
            )

            resumen_deudas = resumen_deudas[resumen_deudas["monto_credito"] > 0]

            if len(resumen_deudas) > 0:
                st.info(
                    "🚀 **Panel de Envío Masivo Quincenal:** Haz clic en los botones verdes de abajo de manera consecutiva para abrir rápidamente los chats de WhatsApp de cada apartamento con su saldo listo."
                )

                st.subheader(
                    f"📋 Listado de Cobros Pendientes ({len(resumen_deudas)} Inmuebles en total)"
                )

                for _, row in resumen_deudas.iterrows():
                    with st.expander(
                        f"🏠 {row['id_inmueble']} | Contacto: {row['responsable']} — Deuda Total: ${row['monto_credito']:,.0f}"
                    ):
                        compras_apartamento = df_merged[
                            df_merged["id_inmueble"] == row["id_inmueble"]
                        ]
                        st.table(
                            compras_apartamento[
                                [
                                    "fecha",
                                    "comprador",
                                    "descripcion",
                                    "monto_total",
                                    "monto_credito",
                                ]
                            ]
                        )

                        numero_nequi = "3226834617"
                        numero_daviplata = "3226834617"

                        mensaje = (
                            f"Hola {row['responsable']}, le escribimos de la tienda. "
                            f"Le compartimos el estado de cuenta con el saldo pendiente actual de su apartamento {row['id_inmueble']}, "
                            f"por un valor total de ${row['monto_credito']:,.0f}.\n\n"
                            f"💳 *Medios de pago disponibles:*\n"
                            f"• Nequi: {numero_nequi}\n"
                            f"• Daviplata: {numero_daviplata}\n"
                            f"• Efectivo directamente en la tienda.\n\n"
                            f"¡Muchas gracias!"
                        )

                        mensaje_encoded = urllib.parse.quote(mensaje)

                        tel_limpio = (
                            str(row["telefono"]).strip().replace(" ", "")
                        )
                        if not tel_limpio.startswith("57"):
                            tel_limpio = "57" + tel_limpio

                        whatsapp_link = (
                            f"https://wa.me/{tel_limpio}?text={mensaje_encoded}"
                        )

                        st.markdown(
                            f'<a href="{whatsapp_link}" target="_blank"><button style="background-color:#25D366; color:white; padding:12px 24px; border:none; border-radius:6px; cursor:pointer; font-weight:bold; font-size:15px;">💬 Enviar Liquidación de {row['id_inmueble']} por WhatsApp</button></a>',
                            unsafe_allow_html=True,
                        )
            else:
                st.success("¡Excelente! No hay saldos pendientes en este momento.")
        else:
            st.success("¡Excelente! No hay saldos pendientes en este momento.")
