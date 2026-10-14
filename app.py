import datetime
import pandas as pd
import streamlit as st

# Configuración inicial de la página
st.set_page_config(
    page_title="Control de Créditos - Negocio", page_icon="📊", layout="wide"
)

st.title("🥤 Control de Créditos y Cobros por WhatsApp")
st.markdown(
    "Gestiona los fiados diarios de tus clientes y genera reportes de cobro quincenales."
)

# Simulamos una base de datos en memoria (en un proyecto real se conecta a SQLite o PostgreSQL)
if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(
        columns=["id_cliente", "nombre", "telefono", "direccion"]
    )
    # Cliente de prueba
    st.session_state.clientes.loc[0] = [
        1,
        "Juan Pérez",
        "573001234567",
        "Torre 1 - Apto 302",
    ]

if "transacciones" not in st.session_state:
    st.session_state.transacciones = pd.DataFrame(
        columns=[
            "id_transaccion",
            "id_cliente",
            "fecha",
            "descripcion",
            "monto",
            "estado",
        ]
    )
    # Transacción de prueba
    st.session_state.transacciones.loc[0] = [
        1,
        1,
        str(datetime.date.today()),
        "Smoothie Red Energy 500ml",
        12000,
        "Pendiente",
    ]

# Menú lateral para navegar
menu = st.sidebar.selectbox(
    "Menú de Navegación",
    [
        "Registrar Venta / Crédito",
        "Clientes",
        "Corte Quincenal y Cobros WhatsApp",
    ],
)

# ---------------------------------------------------------
# 1. REGISTRAR VENTA / CRÉDITO
# ---------------------------------------------------------
if menu == "Registrar Venta / Crédito":
    st.header("📝 Registrar Nuevo Consumo (Fío)")

    if len(st.session_state.clientes) == 0:
        st.warning(
            "Primero debes registrar al menos un cliente en la sección 'Clientes'."
        )
    else:
        with st.form("form_venta"):
            # Seleccionar cliente
            clientes_dict = {
                row["nombre"]: row["id_cliente"]
                for _, row in st.session_state.clientes.iterrows()
            }
            cliente_seleccionado = st.selectbox(
                "Seleccione el Cliente", options=list(clientes_dict.keys())
            )

            descripcion = st.text_input(
                "Descripción del producto",
                placeholder="Ej: Smoothie Tropical Green + Chía",
            )
            monto = st.number_input(
                "Monto ($)", min_value=0, step=1000, value=10000
            )
            fecha = st.date_input(
                "Fecha de la venta", value=datetime.date.today()
            )

            submitted = st.form_submit_button("Guardar Crédito")

            if submitted:
                id_cli = clientes_dict[cliente_seleccionado]
                nuevo_id = len(st.session_state.transacciones) + 1
                nueva_fila = {
                    "id_transaccion": nuevo_id,
                    "id_cliente": id_cli,
                    "fecha": str(fecha),
                    "descripcion": descripcion,
                    "monto": monto,
                    "estado": "Pendiente",
                }
                st.session_state.transacciones.loc[len(st.session_state.transacciones)] = (
                    nueva_fila
                )
                st.success(
                    f"¡Crédito registrado con éxito para {cliente_seleccionado}!"
                )

# ---------------------------------------------------------
# 2. GESTIÓN DE CLIENTES
# ---------------------------------------------------------
elif menu == "Clientes":
    st.header("👥 Gestión de Clientes")

    with st.form("form_cliente"):
        nombre = st.text_input("Nombre completo del cliente")
        telefono = st.text_input(
            "Número de WhatsApp (con código de país, ej: 57300...)"
        )
        direccion = st.text_input("Conjunto / Torre / Apartamento")
        guardar_cli = st.form_submit_button("Agregar Cliente")

        if guardar_cli and nombre and telefono:
            nuevo_id = len(st.session_state.clientes) + 1
            st.session_state.clientes.loc[len(st.session_state.clientes)] = [
                nuevo_id,
                nombre,
                telefono,
                direccion,
            ]
            st.success(f"Cliente {nombre} agregado correctamente.")

    st.subheader("Lista de Clientes Registrados")
    st.dataframe(st.session_state.clientes, use_container_width=True)

# ---------------------------------------------------------
# 3. CORTE QUINCENAL Y COBRO POR WHATSAPP
# ---------------------------------------------------------
elif menu == "Corte Quincenal y Cobros WhatsApp":
    st.header("💰 Resumen de Saldos y Cobros (Corte cada 15 días)")

    if len(st.session_state.transacciones) == 0:
        st.info("No hay transacciones registradas.")
    else:
        # Unir transacciones con clientes para sumar deudas por persona
        df_t = st.session_state.transacciones[
            st.session_state.transacciones["estado"] == "Pendiente"
        ].copy()
        df_c = st.session_state.clientes

        if len(df_t) > 0:
            df_merged = df_t.merge(df_c, on="id_cliente")
            resumen_deudas = (
                df_merged.groupby(
                    ["id_cliente", "nombre", "telefono", "direccion"]
                )["monto"]
                .sum()
                .reset_index()
            )

            st.subheader("Saldos Pendientes por Cliente")

            for _, row in resumen_deudas.iterrows():
                with st.expander(
                    f"👤 {row['nombre']} - Total a Pagar: ${row['monto']:,.0f} ({row['direccion']})"
                ):
                    # Mostrar detalle de lo que debe
                    compras_cliente = df_merged[
                        df_merged["id_cliente"] == row["id_cliente"]
                    ]
                    st.table(
                        compras_cliente[["fecha", "descripcion", "monto"]]
                    )

                    # Botón para generar el mensaje directo de WhatsApp
                    mensaje = f"Hola {row['nombre']}, te escribo de Healthy Express para recordarte tu saldo pendiente acumulado de los últimos 15 días por valor de ${row['monto']:,.0f}. Puedes realizar el pago por Nequi o Efectivo. ¡Muchas gracias!"
                    # Codificar mensaje para URL de WhatsApp
                    import urllib.parse

                    mensaje_encoded = urllib.parse.quote(mensaje)
                    whatsapp_link = (
                        f"https://wa.me/{row['telefono']}?text={mensaje_encoded}"
                    )

                    st.markdown(
                        f'<a href="{whatsapp_link}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">💬 Enviar Cobro por WhatsApp</button></a>',
                        unsafe_allow_html=True,
                    )
        else:
            st.success(
                "¡Excelente! No hay saldos pendientes en este momento. Todos los créditos están al día."
            )