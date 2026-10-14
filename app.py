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

st.title("🛒 Control de Créditos - Tienda (Gestión e Inmuebles)")
st.markdown(
    "Control de fiados, trazabilidad de compradores y gestión de pagos/abonos por apartamento."
)

# Inicializar bases de datos en sesión
if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(
        columns=[
            "id_inmueble",
            "torre",
            "apartamento",
            "responsable",
            "telefono",
        ]
    )
    # Inmueble de prueba
    st.session_state.clientes.loc[0] = [
        "Torre 1 - Apto 302",
        "Torre 1",
        "Apto 302",
        "Juan Pérez",
        "573001234567",
    ]

if "transacciones" not in st.session_state:
    st.session_state.transacciones = pd.DataFrame(
        columns=[
            "id_transaccion",
            "id_inmueble",
            "fecha",
            "comprador",
            "descripcion",
            "monto",
            "estado",
        ]
    )
    # Transacción de prueba
    st.session_state.transacciones.loc[0] = [
        1,
        "Torre 1 - Apto 302",
        str(datetime.date.today()),
        "Juan Pérez",
        "Leche, Pan y Huevos",
        15000,
        "Pendiente",
    ]

# Menú lateral para navegar actualizado con la opción de Pagos/Abonos
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

    if len(st.session_state.clientes) == 0:
        st.warning(
            "Primero debes registrar al menos un inmueble en 'Registro y Edición de Inmuebles'."
        )
    else:
        with st.form("form_venta"):
            inmuebles_dict = {
                f"{row['torre']} - {row['apartamento']} (Contacto: {row['responsable']})": row[
                    "id_inmueble"
                ]
                for _, row in st.session_state.clientes.iterrows()
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
                nuevo_id = len(st.session_state.transacciones) + 1
                nueva_fila = {
                    "id_transaccion": nuevo_id,
                    "id_inmueble": id_inm,
                    "fecha": str(fecha),
                    "comprador": comprador,
                    "descripcion": descripcion,
                    "monto": monto,
                    "estado": "Pendiente",
                }
                st.session_state.transacciones.loc[
                    len(st.session_state.transacciones)
                ] = nueva_fila
                st.success(
                    f"¡Fío registrado a nombre de '{comprador}' para el inmueble {inmueble_seleccionado}!"
                )
            elif submitted:
                st.error("Por favor indica quién realizó la compra.")

# ---------------------------------------------------------
# 2. REGISTRAR ABONO O PAGO TOTAL
# ---------------------------------------------------------
elif menu == "Registrar Abono o Pago Total":
    st.header("💵 Registrar Abono o Pago de Deuda")
    st.markdown(
        "Aquí puedes reportar los pagos parciales (abonos) o la cancelación total de la cuenta de un apartamento."
    )

    if len(st.session_state.clientes) == 0:
        st.warning("No hay inmuebles registrados.")
    else:
        # Filtrar transacciones pendientes
        df_t_pend = st.session_state.transacciones[
            st.session_state.transacciones["estado"] == "Pendiente"
        ]

        if len(df_t_pend) == 0:
            st.success(
                "¡Excelente! No hay deudas pendientes en este momento para abonar."
            )
        else:
            inmuebles_dict = {
                f"{row['torre']} - {row['apartamento']} (Contacto: {row['responsable']})": row[
                    "id_inmueble"
                ]
                for _, row in st.session_state.clientes.iterrows()
            }
            inmueble_seleccionado = st.selectbox(
                "Seleccione el Apartamento que realiza el pago",
                options=list(inmuebles_dict.keys()),
            )
            id_inm_sel = inmuebles_dict[inmueble_seleccionado]

            # Calcular la deuda actual de este inmueble
            deudas_inmueble = df_t_pend[
                df_t_pend["id_inmueble"] == id_inm_sel
            ]
            total_deuda = deudas_inmueble["monto"].sum()

            if total_deuda > 0:
                st.info(
                    f"🏠 **{inmueble_seleccionado}** tiene una deuda pendiente total de: **${total_deuda:,.0f}**"
                )

                with st.expander("Ver detalle de las compras pendientes de este apartamento"):
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
                        "Valor del Abono ($) [Solo aplica si es Abono Parcial]",
                        min_value=0,
                        step=1000,
                        value=0,
                    )

                    ejecutar_pago = st.form_submit_button(
                        "Registrar Transacción de Pago"
                    )

                    if ejecutar_pago:
                        if tipo_pago == "Pago Total (Cancelar toda la deuda)":
                            # Marcar todas las transacciones pendientes de este inmueble como 'Pagado'
                            st.session_state.transacciones.loc[
                                (
                                    st.session_state.transacciones["id_inmueble"]
                                    == id_inm_sel
                                )
                                & (
                                    st.session_state.transacciones["estado"]
                                    == "Pendiente"
                                ),
                                "estado",
                            ] = "Pagado"
                            st.success(
                                f"¡Deuda cancelada en su totalidad! El apartamento {inmueble_seleccionado} ha quedado al día."
                            )
                            st.rerun()

                        else:  # Abono Parcial
                            if (
                                monto_abono <= 0
                            ):
                                st.error("Por favor ingresa un valor válido para el abono.")
                            elif monto_abono > total_deuda:
                                st.error(
                                    "El valor del abono no puede ser mayor a la deuda total actual."
                                )
                            else:
                                # Lógica para aplicar el abono: restamos de la deuda o registramos un ajuste
                                # Para simplificar y mantener limpio el historial, modificamos la primera transacción pendiente o creamos una nota de abono.
                                # Una forma muy limpia en contabilidad de tienda es descontar al registro más antiguo o insertar una transacción negativa de abono.
                                nuevo_id = len(st.session_state.transacciones) + 1
                                fila_abono = {
                                    "id_transaccion": nuevo_id,
                                    "id_inmueble": id_inm_sel,
                                    "fecha": str(datetime.date.today()),
                                    "comprador": "ABONO / PAGO",
                                    "descripcion": f"Abono parcial a la deuda",
                                    "monto": -monto_abono,  # Monto negativo para restar al saldo total
                                    "estado": "Pendiente",
                                }
                                st.session_state.transacciones.loc[
                                    len(st.session_state.transacciones)
                                ] = fila_abono
                                st.success(
                                    f"¡Abono de ${monto_abono:,.0f} registrado con éxito para {inmueble_seleccionado}! Nuevo saldo actualizado."
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
            responsable = st.text_input(
                "Nombre del residente principal / contacto fijo"
            )
            telefono = st.text_input(
                "Número de WhatsApp del contacto (Ej: 57300...)"
            )
            guardar_inm = st.form_submit_button("Registrar Inmueble")

            if guardar_inm and torre and apartamento and responsable and telefono:
                id_inm = f"{torre} - {apartamento}"
                if (
                    id_inm
                    in st.session_state.clientes["id_inmueble"].values
                ):
                    st.error(
                        f"¡El inmueble {id_inm} ya se encuentra registrado!"
                    )
                else:
                    nuevo_registro = [
                        id_inm,
                        torre,
                        apartamento,
                        responsable,
                        telefono,
                    ]
                    st.session_state.clientes.loc[
                        len(st.session_state.clientes)
                    ] = nuevo_registro
                    st.success(
                        f"Inmueble {id_inm} registrado correctamente."
                    )

    with tab2:
        if len(st.session_state.clientes) > 0:
            st.markdown(
                "Selecciona un inmueble para actualizar su responsable o número de WhatsApp sin perder su historial de saldos."
            )
            with st.form("form_editar_inmueble"):
                lista_inm = st.session_state.clientes["id_inmueble"].tolist()
                inmueble_a_editar = st.selectbox(
                    "Seleccione el Inmueble a Editar", options=lista_inm
                )

                datos_actuales = st.session_state.clientes[
                    st.session_state.clientes["id_inmueble"]
                    == inmueble_a_editar
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
                    st.session_state.clientes.loc[
                        st.session_state.clientes["id_inmueble"]
                        == inmueble_a_editar,
                        ["responsable", "telefono"],
                    ] = [nuevo_responsable, nuevo_telefono]
                    st.success(
                        f"¡Datos del inmueble {inmueble_a_editar} actualizados con éxito!"
                    )
        else:
            st.info("No hay inmuebles registrados para editar.")

    st.subheader("Base de Datos de Inmuebles Activos")
    st.dataframe(st.session_state.clientes, use_container_width=True)

# ---------------------------------------------------------
# 4. CORTE QUINCENAL Y COBRO POR WHATSAPP
# ---------------------------------------------------------
elif menu == "Corte Quincenal y Cobros WhatsApp":
    st.header(
        "💰 Liquidación Quincenal Consolidada por Torre y Apartamento"
    )
    st.markdown(
        "Aquí se consolida la deuda neta del hogar (incluyendo abonos y compras recientes)."
    )

    if len(st.session_state.transacciones) == 0:
        st.info("No hay transacciones pendientes.")
    else:
        # Solo tomamos las transacciones con estado 'Pendiente'
        df_t = st.session_state.transacciones[
            st.session_state.transacciones["estado"] == "Pendiente"
        ].copy()
        df_c = st.session_state.clientes

        if len(df_t) > 0:
            df_merged = df_t.merge(df_c, on="id_inmueble")

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

            # Filtramos por si acaso hay algún inmueble con deuda total en 0 o menor
            resumen_deudas = resumen_deudas[resumen_deudas["monto"] > 0]

            if len(resumen_deudas) > 0:
                st.subheader("Cuentas Pendientes por Apartamento")

                for _, row in resumen_deudas.iterrows():
                    with st.expander(
                        f"🏠 {row['id_inmueble']} | Contacto: {row['responsable']} — Deuda Total Neta: ${row['monto']:,.0f}"
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
                        whatsapp_link = (
                            f"https://wa.me/{row['telefono']}?text={mensaje_encoded}"
                        )

                        st.markdown(
                            f'<a href="{whatsapp_link}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">💬 Enviar Extracto de {row['id_inmueble']} por WhatsApp</button></a>',
                            unsafe_allow_html=True,
                        )
            else:
                st.success("¡Excelente! No hay saldos pendientes en este momento.")
        else:
            st.success("¡Excelente! No hay saldos pendientes en este momento.")
