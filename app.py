import datetime
import urllib.parse
import pandas as pd
import streamlit as st

# Configuración inicial de la página
st.set_page_config(
    page_title="Control de Créditos - Tienda Residencial",
    page_icon="🛒",
    layout="wide",
)

st.title("🛒 Control de Créditos y Tienda - Gestión por Inmueble")
st.markdown(
    "Lleva el registro de fiados por cliente y liquida cuentas por Torre y Apartamento."
)

# Inicializar bases de datos en sesión
if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(
        columns=[
            "id_cliente",
            "nombre_cliente",
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
        "Leche, Pan y Huevos",
        15000,
        "Pendiente",
    ]

# Menú lateral para navegar
menu = st.sidebar.selectbox(
    "Menú de Navegación",
    [
        "Registrar Venta / Crédito (Fío)",
        "Registro de Clientes",
        "Corte Quincenal y Cobros WhatsApp",
    ],
)

# ---------------------------------------------------------
# 1. REGISTRAR VENTA / CRÉDITO
# ---------------------------------------------------------
if menu == "Registrar Venta / Crédito (Fío)":
    st.header("📝 Registrar Nuevo Fío en la Tienda")

    if len(st.session_state.clientes) == 0:
        st.warning(
            "Primero debes registrar al menos un cliente en la sección 'Registro de Clientes'."
        )
    else:
        with st.form("form_venta"):
            # Mostrar claramente la Torre, el Apartamento y el nombre de quien compra
            clientes_dict = {
                f"{row['torre']} - {row['apartamento']} | Cliente: {row['nombre_cliente']}": row[
                    "id_cliente"
                ]
                for _, row in st.session_state.clientes.iterrows()
            }
            cliente_seleccionado = st.selectbox(
                "Seleccione el Inmueble y Cliente que fía",
                options=list(clientes_dict.keys()),
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

            submitted = st.form_submit_button("Guardar Fío")

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
                    f"¡Fío registrado correctamente para {cliente_seleccionado}!"
                )

# ---------------------------------------------------------
# 2. REGISTRO DE CLIENTES
# ---------------------------------------------------------
elif menu == "Registro de Clientes":
    st.header("👥 Gestión de Clientes y Residentes")
    st.markdown(
        "Aquí puedes registrar los datos de cada persona, indicando su torre y apartamento correspondiente."
    )

    with st.form("form_cliente"):
        nombre_cliente = st.text_input("Nombre completo de la persona")
        torre = st.text_input("Torre / Bloque (Ej: Torre 1, Manzana A)")
        apartamento = st.text_input(
            "Apartamento / Casa (Ej: Apto 201, Casa 15)"
        )
        telefono = st.text_input(
            "Número de WhatsApp (con código de país, ej: 57300...)"
        )
        guardar_cli = st.form_submit_button("Guardar Cliente")

        if guardar_cli and nombre_cliente and torre and apartamento and telefono:
            nuevo_id = len(st.session_state.clientes) + 1
            st.session_state.clientes.loc[len(st.session_state.clientes)] = [
                nuevo_id,
                nombre_cliente,
                torre,
                apartamento,
                telefono,
            ]
            st.success(
                f"Cliente {nombre_cliente} ({torre} - {apartamento}) registrado con éxito."
            )

    st.subheader("Base de Datos de Clientes Registrados")
    st.dataframe(st.session_state.clientes, use_container_width=True)

# ---------------------------------------------------------
# 3. CORTE QUINCENAL Y COBRO POR WHATSAPP
# ---------------------------------------------------------
elif menu == "Corte Quincenal y Cobros WhatsApp":
    st.header("💰 Liquidación y Corte por Inmueble (Torre y Apartamento)")
    st.markdown(
        "El sistema agrupa automáticamente todas las compras de un mismo apartamento, sin importar quién haya ido a la tienda."
    )

    if len(st.session_state.transacciones) == 0:
        st.info("No hay transacciones registradas.")
    else:
        df_t = st.session_state.transacciones[
            st.session_state.transacciones["estado"] == "Pendiente"
        ].copy()
        df_c = st.session_state.clientes

        if len(df_t) > 0:
            df_merged = df_t.merge(df_c, on="id_cliente")

            # Agrupamos estrictamente por Torre y Apartamento para sumar la deuda total del hogar
            resumen_inmueble = (
                df_merged.groupby(["torre", "apartamento", "telefono"])[
                    "monto"
                ]
                .sum()
                .reset_index()
            )

            st.subheader("Cuentas Pendientes por Apartamento")

            for _, row in resumen_inmueble.iterrows():
                # Buscamos los nombres de los clientes asociados a este apartamento para tener referencia
                clientes_apto = df_merged[
                    (df_merged["torre"] == row["torre"])
                    & (df_merged["apartamento"] == row["apartamento"])
                ]["nombre_cliente"].unique()
                nombres_str = ", ".join(clientes_apto)

                with st.expander(
                    f"🏠 {row['torre']} - {row['apartamento']} | Residentes: {nombres_str} — Total Deuda: ${row['monto']:,.0f}"
                ):
                    # Mostrar detalle de todas las compras hechas por cualquier integrante del apartamento
                    compras_inmueble = df_merged[
                        (df_merged["torre"] == row["torre"])
                        & (df_merged["apartamento"] == row["apartamento"])
                    ]
                    st.table(
                        compras_inmueble[
                            ["fecha", "nombre_cliente", "descripcion", "monto"]
                        ]
                    )

                    # Botón para generar mensaje de WhatsApp dirigido al contacto del apartamento
                    mensaje = f"Hola, le escribimos de la tienda. Le compartimos el resumen de cobro quincenal de los consumos realizados por los residentes del {row['torre']} - {row['apartamento']}, con un saldo pendiente total de ${row['monto']:,.0f}. Puede realizar el pago por Nequi o Efectivo. ¡Muchas gracias!"
                    mensaje_encoded = urllib.parse.quote(mensaje)
                    whatsapp_link = (
                        f"https://wa.me/{row['telefono']}?text={mensaje_encoded}"
                    )

                    st.markdown(
                        f'<a href="{whatsapp_link}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">💬 Enviar Liquidación por WhatsApp ({row['torre']} {row['apartamento']})</button></a>',
                        unsafe_allow_html=True,
                    )
        else:
            st.success(
                "¡Excelente! No hay saldos pendientes en este momento. Todas las cuentas están al día."
            )
