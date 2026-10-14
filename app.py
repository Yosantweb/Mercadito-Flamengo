import datetime
import urllib.parse
import pandas as pd
import streamlit as st

# Configuración inicial de la página
st.set_page_config(
    page_title="Control de Créditos - Unidad Residencial",
    page_icon="🏢",
    layout="wide",
)

st.title("🥤 Control de Créditos - Healthy Express")
st.markdown("Gestión de fiados por Torre, Apartamento y Cobros por WhatsApp.")

# Inicializar bases de datos en sesión
if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(
        columns=[
            "id_cliente",
            "nombre",
            "torre",
            "apartamento",
            "telefono",
        ]
    )
    # Cliente de prueba
    st.session_state.clientes.loc[0] = [
        1,
        "Juan Pérez",
        "Torre 1",
        "Apto 302",
        "573001234567",
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
        "Clientes (Torre / Apto)",
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
            # Mostrar cliente con su torre y apartamento para identificarlo fácil
            clientes_dict = {
                f"{row['torre']} - {row['apartamento']} ({row['nombre']})": row[
                    "id_cliente"
                ]
                for _, row in st.session_state.clientes.iterrows()
            }
            cliente_seleccionado = st.selectbox(
                "Seleccione la Torre y Apartamento (Cliente)",
                options=list(clientes_dict.keys()),
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
                st.session_state.transacciones.loc[
                    len(st.session_state.transacciones)
                ] = nueva_fila
                st.success(
                    f"¡Crédito registrado con éxito para {cliente_seleccionado}!"
                )

# ---------------------------------------------------------
# 2. GESTIÓN DE CLIENTES
# ---------------------------------------------------------
elif menu == "Clientes (Torre / Apto)":
    st.header("🏢 Gestión de Residentes por Torre y Apartamento")

    with st.form("form_cliente"):
        nombre = st.text_input(
            "Nombre del residente principal o responsable"
        )
        torre = st.text_input("Torre o Bloque (Ej: Torre 1, Manzana B)")
        apartamento = st.text_input("Apartamento o Casa (Ej: Apto 302, Casa 12)")
        telefono = st.text_input(
            "Número de WhatsApp (con código de país, ej: 57300...)"
        )
        guardar_cli = st.form_submit_button("Agregar Residente")

        if guardar_cli and nombre and torre and apartamento and telefono:
            nuevo_id = len(st.session_state.clientes) + 1
            st.session_state.clientes.loc[len(st.session_state.clientes)] = [
                nuevo_id,
                nombre,
                torre,
                apartamento,
                telefono,
            ]
            st.success(
                f"Residente de {torre} - {apartamento} agregado correctamente."
            )

    st.subheader("Lista de Residentes Registrados")
    st.dataframe(st.session_state.clientes, use_container_width=True)

# ---------------------------------------------------------
# 3. CORTE QUINCENAL Y COBRO POR WHATSAPP
# ---------------------------------------------------------
elif menu == "Corte Quincenal y Cobros WhatsApp":
    st.header("💰 Resumen de Saldos por Apartamento (Corte Quincenal)")

    if len(st.session_state.transacciones) == 0:
        st.info("No hay transacciones registradas.")
    else:
        df_t = st.session_state.transacciones[
            st.session_state.transacciones["estado"] == "Pendiente"
        ].copy()
        df_c = st.session_state.clientes

        if len(df_t) > 0:
            df_merged = df_t.merge(df_c, on="id_cliente")
            # Agrupar por Torre y Apartamento
            resumen_deudas = (
                df_merged.groupby(
                    ["id_cliente", "torre", "apartamento", "nombre", "telefono"]
                )["monto"]
                .sum()
                .reset_index()
            )

            st.subheader(
                "Saldos Pendientes Organizados por Inmueble (Torre / Apto)"
            )

            for _, row in resumen_deudas.iterrows():
                with st.expander(
                    f"🏠 {row['torre']} - {row['apartamento']} | Responsable: {row['nombre']} — Total a Pagar: ${row['monto']:,.0f}"
                ):
                    # Mostrar detalle de lo que debe ese apartamento
                    compras_cliente = df_merged[
                        df_merged["id_cliente"] == row["id_cliente"]
                    ]
                    st.table(
                        compras_cliente[["fecha", "descripcion", "monto"]]
                    )

                    # Botón para generar mensaje directo de WhatsApp enfocado en el inmueble
                    mensaje = f"Hola {row['nombre']}, te escribo de Healthy Express. Te compartimos el resumen de cobro quincenal de su consumo en el {row['torre']} - {row['apartamento']}, con un saldo pendiente total de ${row['monto']:,.0f}. Puedes realizar el pago por Nequi o Efectivo. ¡Muchas gracias!"
                    mensaje_encoded = urllib.parse.quote(mensaje)
                    whatsapp_link = (
                        f"https://wa.me/{row['telefono']}?text={mensaje_encoded}"
                    )

                    st.markdown(
                        f'<a href="{whatsapp_link}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">💬 Enviar Cobro por WhatsApp ({row['torre']} {row['apartamento']})</button></a>',
                        unsafe_allow_html=True,
                    )
        else:
            st.success(
                "¡Excelente! No hay saldos pendientes en este momento. Todos los créditos están al día."
            )
