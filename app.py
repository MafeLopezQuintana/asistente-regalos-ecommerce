import csv
from pathlib import Path

import pandas as pd
import streamlit as st
from src.models.asistente import (
    cargar_modelo_final,
    buscar_ideas_regalo,
    armar_combos,
)


# 1. Configuración de la página.
st.set_page_config(
    page_title="¿Qué le regalo?",
    page_icon="🎁",
    layout="centered",
)


# 2. Rutas y opciones.
CARPETA_PROYECTO = Path(__file__).resolve().parent

PORTADA = CARPETA_PROYECTO / "assets" / "portada.png"
RUTA_INTERESES = CARPETA_PROYECTO / "models" / "intereses.csv"
RUTA_CATALOGO = CARPETA_PROYECTO / "models" / "catalogo_app.parquet"

SORPRENDEME = "¡Sorprendeme!"
OPCION_CON_PRODUCTO = "Sí, quiero elegir un producto del catálogo"

INTERESES_RESPALDO = [
    "Decoración y hogar",
    "Cocina y repostería",
    "Accesorios",
    "Papelería y manualidades",
    "Fiestas y celebraciones",
    "Velas y aromas",
    "Niños y juegos",
    "Jardín y flores",
]


# 3. Lectura del catálogo y los intereses.
@st.cache_data
def cargar_catalogo():
    catalogo = pd.read_parquet(RUTA_CATALOGO)

    catalogo = catalogo.copy()
    catalogo["stock_code"] = catalogo["stock_code"].astype(str)

    return catalogo.sort_values("description").reset_index(drop=True)

@st.cache_resource
def cargar_modelo():
    return cargar_modelo_final()


def cargar_intereses():
    """Lee los intereses; si falla, utiliza la lista de respaldo."""
    try:
        with open(
            RUTA_INTERESES,
            encoding="utf-8",
            newline="",
        ) as archivo:
            nombres = [
                fila["interes"]
                for fila in csv.DictReader(archivo)
            ]

        nombres = [
            nombre
            for nombre in nombres
            if nombre and nombre != SORPRENDEME
        ]

    except (OSError, KeyError):
        nombres = []

    return (nombres or INTERESES_RESPALDO) + [SORPRENDEME]


# 4. Estilos de la pantalla.
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(
            135deg, #EDF2FF 0%, #FFFFFF 55%, #FFF9D6 100%
        );
    }

    h1, h2, h3 {
        color: #0739D9;
        font-family: "Trebuchet MS", Arial, sans-serif;
        font-weight: 800;
        letter-spacing: -0.5px;
    }

    [data-testid="stForm"] {
        background-color: #FFFFFF;
        border: 2px solid #CCD8FF;
        border-top: 7px solid #0047FF;
        border-radius: 24px;
        padding: 28px;
        box-shadow: 0 12px 32px rgba(0, 47, 160, 0.10);
    }

    [data-testid="stWidgetLabel"] p {
        color: #12205C;
        font-size: 17px;
        font-weight: 700;
    }

    [data-testid="stFormSubmitButton"] button {
        background-color: #FFE600;
        color: #12205C;
        border: 2px solid #FFE600;
        border-radius: 14px;
        min-height: 52px;
        font-weight: 800;
    }

    [data-testid="stFormSubmitButton"] button:hover {
        background-color: #FFD000;
        border-color: #FFD000;
        color: #12205C;
    }

    [data-testid="stFormSubmitButton"] button:focus-visible {
        outline: 3px solid #0047FF;
        outline-offset: 3px;
    }

    .st-key-presupuesto {
        background: linear-gradient(135deg, #0739D9, #082575);
        border: none !important;
        border-top: 6px solid #FFE600 !important;
        border-radius: 24px;
        padding: 28px;
        box-shadow: 0 14px 35px rgba(0, 47, 160, 0.18);
        margin-top: 24px;
        margin-bottom: 24px;
    }

    .st-key-presupuesto h3,
    .st-key-presupuesto [data-testid="stMarkdownContainer"] p,
    .st-key-presupuesto [data-testid="stWidgetLabel"] p {
        color: #FFFFFF;
    }

    .etiqueta-presupuesto {
        display: inline-block;
        background: #FFE600;
        color: #12205C;
        padding: 7px 12px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 1px;
    }

    .st-key-presupuesto [data-baseweb="select"] > div {
        background-color: #FFFFFF;
        color: #12205C;
        border-radius: 12px;
        min-height: 50px;
    }

    .importe-presupuesto {
        color: #FFE600;
        font-size: clamp(24px, 5vw, 36px);
        font-weight: 800;
        margin-top: 12px;
    }

    .importe-presupuesto span {
        color: #FFFFFF;
        font-size: 18px;
        font-weight: 400;
    }

    .gancho-regalos {
        text-align: center;
        padding: 38px 12px 32px;
    }

    .gancho-regalos .gancho-titulo {
        color: #12205C;
        font-family: "Trebuchet MS", Arial, sans-serif;
        font-size: clamp(34px, 6vw, 54px);
        font-weight: 800;
        line-height: 1.15;
        letter-spacing: -1.5px;
        margin: 0;
    }

    .gancho-regalos .gancho-destacado {
        display: inline-block;
        background: #FFE600;
        color: #0739D9;
        padding: 4px 14px 9px;
        border-radius: 14px;
        margin-top: 10px;
    }

    .gancho-regalos .gancho-descripcion {
        color: #12205C;
        font-size: 19px;
        line-height: 1.6;
        max-width: 570px;
        margin: 22px auto 0;
    }

    .pasos-regalos {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 16px;
        margin: 8px 0 32px;
    }

    .paso-regalo {
        background: #FFFFFF;
        border: 2px solid #DCE4FF;
        border-radius: 22px;
        padding: 24px 20px;
        box-shadow: 0 8px 22px rgba(0, 47, 160, 0.07);
        transition: transform 0.2s ease;
    }

    .paso-regalo:hover {
        transform: translateY(-5px);
    }

    .paso-regalo .paso-numero {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        background: #FFE600;
        color: #12205C;
        border-radius: 15px;
        font-size: 22px;
        font-weight: 800;
        margin-bottom: 18px;
    }

    .paso-regalo .paso-titulo {
        color: #0739D9;
        font-family: "Trebuchet MS", Arial, sans-serif;
        font-size: 25px;
        font-weight: 800;
        margin: 0 0 10px;
        letter-spacing: -0.5px;
    }

    .paso-regalo .paso-texto {
        color: #12205C;
        font-size: 16px;
        line-height: 1.6;
        margin: 0;
    }

    .paso-regalo.paso-final {
        background: #0739D9;
        border-color: #0739D9;
    }

    .paso-regalo.paso-final .paso-titulo,
    .paso-regalo.paso-final .paso-texto {
        color: #FFFFFF;
    }

    @media (max-width: 640px) {
        [data-testid="stForm"],
        .st-key-presupuesto {
            padding: 18px;
        }

        .pasos-regalos {
            grid-template-columns: 1fr;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .paso-regalo {
            transition: none;
        }

        .paso-regalo:hover {
            transform: none;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 5. Portada e introducción.
if PORTADA.exists():
    st.image(PORTADA, width="stretch")
else:
    st.title("🎁 ¿Qué le regalo?")

st.markdown(
    """
    <div class="gancho-regalos">
        <h1 class="gancho-titulo">
            Un regalo que diga:<br>
            <span class="gancho-destacado">pensé en vos</span> 💛
        </h1>
        <p class="gancho-descripcion">
            Vos conocés a esa persona.<br>
            Nosotros te ayudamos a encontrar el regalo.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="pasos-regalos">
    <div class="paso-regalo">
        <span class="paso-numero">01</span>
        <h3 class="paso-titulo">Contanos 💬</h3>
        <p class="paso-texto">
            Sus gustos, la ocasión y tu presupuesto.
            Con cinco respuestas, empezamos.
        </p>
    </div>
    <div class="paso-regalo">
        <span class="paso-numero">02</span>
        <h3 class="paso-titulo">Descubrí ✨</h3>
        <p class="paso-texto">
            Ideas de regalos y combos pensados
            para esa persona y tu bolsillo.
        </p>
    </div>
    <div class="paso-regalo paso-final">
        <span class="paso-numero">03</span>
        <h3 class="paso-titulo">Sorprendé 🎁</h3>
        <p class="paso-texto">
            Elegí ese detalle que diga:
            “Esto me hizo pensar en vos”.
        </p>
    </div>
</div>
    """,
    unsafe_allow_html=True,
)


# 6. Presupuesto.
with st.container(key="presupuesto", border=True):
    st.markdown(
        '<span class="etiqueta-presupuesto">'
        'PRIMERO, TU PRESUPUESTO</span>',
        unsafe_allow_html=True,
    )

    st.subheader("Un gran detalle, a tu medida")
    st.write("Elegí cuánto querés destinar al regalo o al combo completo.")

    rangos_presupuesto = {
        "De £0 a £2": (0, 2),
        "De £2 a £5": (2, 5),
        "De £5 a £15": (5, 15),
        "De £15 a £30": (15, 30),
        "Más de £30": (30, 1000),
    }

    presupuesto = st.selectbox(
        "Tu presupuesto total",
        options=list(rangos_presupuesto),
        key="rango_presupuesto",
    )

    precio_minimo, precio_maximo = rangos_presupuesto[presupuesto]

    if precio_maximo >= 1000:
        texto_importe = f"£{precio_minimo} <span>o más</span>"
    else:
        texto_importe = (
            f"£{precio_minimo} <span>a</span> £{precio_maximo}"
        )

    st.markdown(
        f'<div class="importe-presupuesto">{texto_importe}</div>',
        unsafe_allow_html=True,
    )

st.caption(
    "Precios en libras esterlinas (£), "
    "del catálogo de una tienda del Reino Unido."
)


# 7. Cargar el catálogo antes del formulario.
try:
    catalogo = cargar_catalogo()
except FileNotFoundError:
    st.error(
        "No se encontró el catálogo. Revisá que exista el archivo "
        "models/catalogo_app.parquet en tu proyecto."
    )
    st.stop()

if catalogo.empty:
    st.error("El catálogo está vacío. Revisá el archivo del catálogo.")
    st.stop()
try:
    modelo_final = cargar_modelo()
except FileNotFoundError:
    st.error(
        "No se encontró el modelo en models/modelo_final.pkl."
    )
    st.stop()

etiquetas_productos = {
    fila["stock_code"]: (
        f'{fila["description"]} — £{fila["price"]:.2f}'
        f' · Código: {fila["stock_code"]}'
    )
    for _, fila in catalogo.iterrows()
}

productos_por_codigo = catalogo.set_index("stock_code").to_dict(
    orient="index"
)


# 8. Formulario de preferencias.
st.divider()
st.subheader("Contanos un poquito de esa persona")
st.write(
    "¿Qué le gusta? ¿Qué celebran? ¿Un detalle o un combo? "
    "Vamos a encontrar una idea para sorprenderla."
)
st.caption(
    "Ya podés explorar el catálogo y elegir un producto de referencia. "
    "Las recomendaciones se incorporarán en la próxima etapa."
)

with st.form("cuestionario_regalos"):
    intereses = st.multiselect(
        "1. ¿Qué cosas le encantan?",
        cargar_intereses(),
        help="Podés elegir varias. Si no sabés, elegí solo ¡Sorprendeme!",
    )

    ocasion = st.selectbox(
        "2. ¿Qué ocasión queremos celebrar?",
        [
            "Cumpleaños",
            "Aniversario",
            "Agradecimiento",
            "Navidad / Fiestas",
            "Porque sí",
        ],
    )

    tipo_regalo = st.radio(
        "3. ¿Cómo te gustaría sorprender?",
        [
            "Un solo regalo",
            "Un combo de regalos",
            "Mostrame ambas opciones",
        ],
    )

    producto_previo = st.radio(
        "4. ¿Ya viste algo que podría gustarle?",
        [
            "No, necesito ideas",
            OPCION_CON_PRODUCTO,
        ],
    )

    producto_elegido = st.selectbox(
        "Elegí un producto de referencia (opcional)",
        options=catalogo["stock_code"].tolist(),
        index=None,
        placeholder="Escribí para buscar un producto",
        format_func=lambda codigo: etiquetas_productos[codigo],
        key="selector_producto",
    )

    st.caption(
        "Si marcaste que ya viste algo, elegilo acá. "
        "Si necesitás ideas, dejá este campo vacío. "
        "Los nombres se muestran como aparecen en el catálogo original."
    )

    enviado = st.form_submit_button(
        "Ver mis preferencias",
        type="primary",
        width="stretch",
    )


# 9. Personalización de la tarjeta.
st.divider()
st.subheader("🎁 Personalizá tu regalo")

personalizar = st.checkbox("Quiero agregar una tarjeta")

destinatario = ""
mensaje = ""
remitente = ""

if personalizar:
    destinatario = st.text_input(
        "¿Para quién es?",
        placeholder="Ejemplo: Sofi",
        key="tarjeta_destinatario",
    )

    mensaje = st.text_area(
        "¿Qué querés decirle?",
        placeholder="Escribí tu dedicatoria...",
        max_chars=300,
        key="tarjeta_mensaje",
    )

    remitente = st.text_input(
        "¿Quién lo envía?",
        placeholder="Tu nombre o firma",
        key="tarjeta_remitente",
    )

    st.markdown("### 💌 Vista previa")

    if destinatario.strip():
        st.write("Para:", destinatario)

    if mensaje.strip():
        st.text(mensaje)

    if remitente.strip():
        st.write("Con cariño,", remitente)


# 10. Validar y guardar las respuestas.
if enviado:
    quiere_producto = producto_previo == OPCION_CON_PRODUCTO
    errores = []

    if not intereses:
        errores.append(
            "Elegí algún interés o la opción ¡Sorprendeme!."
        )

    elif SORPRENDEME in intereses and len(intereses) > 1:
        errores.append(
            "Elegí intereses concretos o solo ¡Sorprendeme!, "
            "para que tu respuesta sea clara."
        )

    if quiere_producto and producto_elegido is None:
        errores.append(
            "Marcaste que querés elegir un producto del catálogo. "
            "Buscalo y seleccionalo antes de continuar."
        )

    if not quiere_producto and producto_elegido is not None:
        errores.append(
            "Seleccionaste un producto, pero marcaste "
            "«No, necesito ideas». Cambiá la respuesta a "
            "«Sí, quiero elegir un producto del catálogo» "
            "o quitá el producto con la X del selector."
        )

    if errores:
        st.session_state.pop("resumen_preferencias", None)

        for error in errores:
            st.warning(error)

    else:
        producto = (
            productos_por_codigo[producto_elegido]
            if quiere_producto
            else None
        )

        st.session_state["resumen_preferencias"] = {
            "presupuesto": presupuesto,
            "intereses": list(intereses),
            "ocasion": ocasion,
            "tipo_regalo": tipo_regalo,
            "producto_previo": producto_previo,
            "producto_codigo": (
                producto_elegido if quiere_producto else None
            ),
            "producto_nombre": (
                producto["description"] if producto else None
            ),
            "producto_precio": (
                float(producto["price"]) if producto else None
            ),
            "precio_minimo": precio_minimo,
            "precio_maximo": precio_maximo,
        }


# 11. Mostrar el resumen guardado.
if "resumen_preferencias" in st.session_state:
    resumen = st.session_state["resumen_preferencias"]

    st.divider()
    st.success("¡Listo! Este es el resumen de tus preferencias.")

    st.write("**Presupuesto:**", resumen["presupuesto"])
    st.write("**Intereses:**", ", ".join(resumen["intereses"]))
    st.write("**Ocasión:**", resumen["ocasion"])
    st.write("**Tipo de regalo:**", resumen["tipo_regalo"])

    if resumen.get("producto_nombre"):
        st.write(
            "**Producto de referencia:**",
            resumen["producto_nombre"],
        )

        if resumen.get("producto_precio") is not None:
            st.write(
                "**Precio del producto:**",
                f'£{resumen["producto_precio"]:.2f}',
            )

        st.write(
            "**Código del producto:**",
            resumen.get("producto_codigo"),
        )

    else:
        st.write(
            "**Producto de referencia:**",
            "Sin producto seleccionado. Necesito ideas.",
        )

    if personalizar and destinatario.strip():
        st.write("**Para quién:**", destinatario)

    st.caption(
        "Este resumen corresponde al último envío. "
        "Si cambiás tus preferencias, volvé a presionar "
        "Ver mis preferencias."
    )

    st.subheader("🎁 Ideas para sorprender")

    mostrar_regalos = resumen["tipo_regalo"] in [
        "Un solo regalo",
        "Mostrame ambas opciones",
    ]

    mostrar_combos = resumen["tipo_regalo"] in [
        "Un combo de regalos",
        "Mostrame ambas opciones",
    ]

    if mostrar_regalos:
        st.markdown("### Regalos individuales")

        ideas = buscar_ideas_regalo(
            resumen,
            catalogo,
            modelo_final,
            k=5,
        )

        if ideas.empty:
            st.info(
                "No encontramos regalos con estas preferencias. "
                "Probá con otro presupuesto o con ¡Sorprendeme!."
            )
        else:
            for _, idea in ideas.iterrows():
                with st.container(border=True):
                    st.write(idea["description"])
                    st.write(f'**Precio:** £{idea["price"]:.2f}')
                    st.write("**Interés:**", idea["interes"])
                    st.write("**Por qué aparece:**", idea["motivo"])

    if mostrar_combos:
        st.markdown("### Combos de regalos")

        combos = armar_combos(
            resumen,
            catalogo,
            modelo_final,
            n_combos=3,
        )

        if combos.empty:
            st.info(
                "No encontramos combos con estas preferencias. "
                "Probá ampliar el presupuesto o cambiar los intereses."
            )
        else:
            for numero, productos in combos.groupby("combo"):
                with st.container(border=True):
                    st.markdown(f"#### Combo {numero}")

                    for _, producto in productos.iterrows():
                        st.write(
                            f'{producto["description"]} '
                            f'— £{producto["price"]:.2f}'
                        )
                        st.caption(producto["motivo"])

                    total = float(productos["total_combo"].iloc[0])
                    st.write(f"**Total del combo: £{total:.2f}**")

                    if total < resumen["precio_minimo"]:
                        st.info(
                            "Esta alternativa cuesta menos que el "
                            "mínimo del rango elegido y no supera "
                            "tu presupuesto máximo."
                        )
                        
st.caption("Presente Analytics · Proyecto Final Henry")