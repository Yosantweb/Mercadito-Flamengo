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

st.title("🛒 Control de Créditos - Tienda (Gestión e Inmuebles)")
st.markdown(
    "Control de fiados, trazabilidad de compradores y gestión de pagos/abonos con Base de Datos Permanente."
)

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA BASE DE DATOS SQLITE (PERSISTENCIA)
# ---------------------------------------------------------
DB_NAME = "tienda.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabla de inmuebles / clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id_inmueble TEXT PRIMARY KEY,
            torre TEXT,
            apartamento TEXT,
            responsable TEXT,
            telefono TEXT
        )
    """)
    # Tabla de transacciones / fíos / abonos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacciones (
            id_transaccion INTEGER PRIMARY KEY AUTOINCREMENT,
            id_inmueble TEXT,
            fecha TEXT,
            comprador TEXT,
            descripcion TEXT,
            monto REAL,
            estado TEXT,
            FOREIGN KEY (id_inmueble) REFERENCES clientes (id_inmueble)
        )
    """)
    conn.commit()
    conn.close()


# Inicializar la base de datos al arrancar
init_db()

# Funciones de apoyo para interactuar con la Base de Datos
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


# Menú lateral para navegar
menu = st.sidebar.selectbox(
    "Menú de Navegación",
    [
        "Registrar Venta / Crédito (Fío)",
        "Registrar Abono o Pago Total",
        "Registro y Edición de Inmuebles",
        "Corte Quincenal y Cobros WhatsApp",
    ],
)

# ---------------------------------------------------------
# 1. REGISTRAR VENTA / CRÉDITO
# ---------------------------------------------------------
if menu == "Registrar Venta / Crédito (Fío)":
    st.header("📝 Registrar Nuevo Fío en la Tienda")

    df_clientes = cargar_clientes()

    if len(df_clientes) == 0:
        st.warning(
            "Primero debes registrar al menos un inmueble en 'Registro y Edición de Inmuebles'."
        )
    else:
        with st.form("form_venta"):
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
                "¿Quién hizo la compra hoy?",
                placeholder="Ej: El esposo, la esposa, el hijo, etc.",
            )
            descripcion = st.text_input(
                "Productos llevados",
                placeholder="Ej: 1 Arroz, 1 Aceite, Gaseosa",
            )
            monto = st.number_input(
                "Valor total del fío ($)",
                min_value=0,
                step=1000,
                value=12000,
            )
            fecha = st.date_input(
                "Fecha de la venta", value=datetime.date.today()
            )

            submitted = st.form_submit_button("Guardar Fío en la Cuenta")

            if submitted and comprador:
                id_inm = inmuebles_dict[inmueble_seleccionado]
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO transacciones (id_inmueble, fecha, comprador, descripcion, monto, estado)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        id_inm,
                        str(fecha),
                        comprador,
                        descripcion,
                        monto,
                        "Pendiente",
                    ),
                )
                conn.commit()
                conn.close()
                st.success(
                    f"¡Fío registrado permanentemente a nombre de '{comprador}' para el inmueble {inmueble_seleccionado}!"
                )
            elif submitted:
                st.error("Por favor indica quién realizó la compra.")

# ---------------------------------------------------------
# 2. REGISTRAR ABONO O PAGO TOTAL
# ---------------------------------------------------------
elif menu == "Registrar Abono o Pago Total":
    st.header("💵 Registrar Abono o Pago de Deuda")

    df_clientes = cargar_clientes()
    df_trans = cargar_transacciones()

    if len(df_clientes) == 0:
        st.warning("No hay inmuebles registrados.")
    else:
        df_t_pend = df_trans[df_trans["estado"] == "Pendiente"]

        if len(df_t_pend) == 0:
            st.success(
                "¡Excelente! No hay deudas pendientes registradas en la base de datos."
            )
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
            total_deuda = deudas_inmueble["monto"].sum()

            if total_deuda > 0:
                st.info(
                    f"🏠 **{inmueble_seleccionado}** tiene una deuda pendiente total de: **${total_deuda:,.0f}**"
                )

                with st.expander("Ver detalle de compras pendientes"):
                    st.table(
                        deudas_inmueble[
                            ["fecha", "comprador", "descripcion", "monto"]
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
                                UPDATE transacciones SET estado = 'Pagado'
                                WHERE id_inmueble = ? AND estado = 'Pendiente'
                            """,
                                (id_inm_sel,),
                            )
                            conn.commit()
                            conn.close()
                            st.success(
                                "¡Deuda cancelada en su totalidad y guardada en la base de datos!"
                            )
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
                                    INSERT INTO transacciones (id_inmueble, fecha, comprador, descripcion, monto, estado)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                    (
                                        id_inm_sel,
                                        str(datetime.date.today()),
                                        "ABONO / PAGO",
                                        "Abono parcial a la deuda",
                                        -monto_abono,
                                        "Pendiente",
                                    ),
                                )
                                conn.commit()
                                conn.close()
                                st.success(
                                    "¡Abono registrado y guardado con éxito!"
                                )
                                st.rerun()
            else:
                st.success("Este apartamento no tiene saldos pendientes.")

# ---------------------------------------------------------
# 3. REGISTRO Y EDICIÓN DE INMUEBLES
# ---------------------------------------------------------
elif menu == "Registro y Edición de Inmuebles":
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
                    st.success(
                        f"Inmueble {id_inm} guardado permanentemente en la base de datos."
                    )

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
# 4. CORTE QUINCENAL Y COBRO POR WHATSAPP
# ---------------------------------------------------------
elif menu == "Corte Quincenal y Cobros WhatsApp":
    st.header("💰 Liquidación Quincenal Consolidada")

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
                ])["monto"]
                .sum()
                .reset_index()
            )

            resumen_deudas = resumen_deudas[resumen_deudas["monto"] > 0]

            if len(resumen_deudas) > 0:
                st.subheader("Cuentas Pendientes por Apartamento")

                for _, row in resumen_deudas.iterrows():
                    with st.expander(
                        f"🏠 {row['id_inmueble']} | Contacto: {row['responsable']} — Deuda Total: ${row['monto']:,.0f}"
                    ):
                        compras_apartamento = df_merged[
                            df_merged["id_inmueble"] == row["id_inmueble"]
                        ]
                        st.table(
                            compras_apartamento[
                                ["fecha", "comprador", "descripcion", "monto"]
                            ]
                        )

                        mensaje = f"Hola {row['responsable']}, le escribimos de la tienda. Le compartimos el estado de cuenta quincenal con el saldo pendiente actual de su apartamento {row['id_inmueble']}, por un valor total de ${row['monto']:,.0f}. Puede realizar el pago por Nequi o Efectivo. ¡Muchas gracias!"
                        mensaje_encoded = urllib.parse.quote(mensaje)

                        tel_limpio = str(row["telefono"]).strip().replace(" ", "")
                        if not tel_limpio.startswith("57"):
                            tel_limpio = "57" + tel_limpio

                        whatsapp_link = (
                            f"https://wa.me/{tel_limpio}?text={mensaje_encoded}"
                        )

                        st.markdown(
                            f'<a href="{whatsapp_link}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">💬 Enviar Extracto de {row['id_inmueble']} por WhatsApp</button></a>',
                            unsafe_allow_html=True,
                        )
            else:
                st.success("¡Excelente! No hay saldos pendientes en este momento.")
        else:
            st.success("¡Excelente! No hay saldos pendientes en este momento.")
