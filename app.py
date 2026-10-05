from pathlib import Path

import streamlit as st


# 1. Configuración de la página y ubicación de la imagen.
CARPETA_PROYECTO = Path(__file__).resolve().parent
PORTADA = CARPETA_PROYECTO / "assets" / "portada.png"

st.set_page_config(
    page_title="¿Qué le regalo?",
    page_icon="🎁",
    layout="centered",
)


# 2. Estilos de la pantalla.
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

    /* Caja de las cinco preguntas. */
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

    /* Botón amarillo. */
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

    /* Tarjeta azul del presupuesto. */
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

    @media (max-width: 640px) {
        [data-testid="stForm"],
        .st-key-presupuesto {
            padding: 18px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 3. Portada e introducción.
if PORTADA.exists():
    st.image(PORTADA, width="stretch")
else:
    st.title("🎁 ¿Qué le regalo?")
    st.warning("Falta guardar la imagen en assets/portada.png.")

st.markdown(
    """
    <style>
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
    </style>

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
<style>
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
<div class="pasos-regalos">
<div class="paso-regalo">
<span class="paso-numero">01</span>
<h3 class="paso-titulo">Contanos 💬</h3>
<p class="paso-texto">Sus gustos, la ocasión y tu presupuesto. Con cinco respuestas, empezamos.</p>
</div>
<div class="paso-regalo">
<span class="paso-numero">02</span>
<h3 class="paso-titulo">Descubrí ✨</h3>
<p class="paso-texto">Ideas de regalos y combos pensados para esa persona y tu bolsillo.</p>
</div>
<div class="paso-regalo paso-final">
<span class="paso-numero">03</span>
<h3 class="paso-titulo">Sorprendé 🎁</h3>
<p class="paso-texto">Elegí ese detalle que diga: “Esto me hizo pensar en vos”.</p>
</div>
</div>
""",
    unsafe_allow_html=True,
)


# 4. Presupuesto, fuera de las tres columnas.
with st.container(key="presupuesto", border=True):
    st.markdown(
        '<span class="etiqueta-presupuesto">'
        'PRIMERO, TU PRESUPUESTO</span>',
        unsafe_allow_html=True,
    )

    st.subheader("Un gran detalle, a tu medida")
    st.write("Elegí cuánto querés destinar al regalo o al combo completo.")

    rangos_presupuesto = {
        "De $50.000 a $100.000": (50000, 100000),
        "De $100.000 a $150.000": (100000, 150000),
        "De $150.000 a $200.000": (150000, 200000),
        "De $200.000 a $300.000": (200000, 300000),
    }

    presupuesto = st.selectbox(
        "Tu presupuesto total",
        options=list(rangos_presupuesto),
        key="rango_presupuesto",
    )

    precio_minimo, precio_maximo = rangos_presupuesto[presupuesto]

    minimo_texto = f"{precio_minimo:,.0f}".replace(",", ".")
    maximo_texto = f"{precio_maximo:,.0f}".replace(",", ".")

    st.markdown(
        f'<div class="importe-presupuesto">'
        f'${minimo_texto} <span>a</span> ${maximo_texto}'
        f'</div>',
        unsafe_allow_html=True,
    )


# 5. Un único formulario con cinco preguntas.
st.divider()
st.subheader("Contanos un poquito de esa persona")
st.write(
    "¿Qué le gusta? ¿Qué celebran? ¿Un detalle o un combo? "
    "Vamos a encontrar una idea para sorprenderla."
)
st.caption("Vista previa: los intereses se validarán con el catálogo.")

with st.form("cuestionario_regalos"):
    destinatario = st.radio(
        "1. ¿Para quién es ese regalo?",
        ["Mujer", "Hombre", "Prefiero no indicar"],
        index=2,
        horizontal=True,
    )

    intereses = st.multiselect(
        "2. ¿Qué cosas le encantan?",
        [
            "Cocina y repostería",
            "Decoración y hogar",
            "Jardín y flores",
            "Manualidades",
            "Accesorios",
            "Fiestas y celebraciones",
            "¡Sorprendeme!",
        ],
        help="Podés elegir varias. Si no sabés, elegí solo ¡Sorprendeme!",
    )

    ocasion = st.selectbox(
        "3. ¿Qué ocasión queremos celebrar?",
        [
            "Cumpleaños",
            "Aniversario",
            "Agradecimiento",
            "Navidad / Fiestas",
            "Porque sí",
        ],
    )

    tipo_regalo = st.radio(
        "4. ¿Cómo te gustaría sorprender?",
        [
            "Un solo regalo",
            "Un combo de regalos",
            "Mostrame ambas opciones",
        ],
    )

    producto_previo = st.radio(
        "5. ¿Ya viste algo que podría gustarle?",
        [
            "No, necesito ideas",
            "Sí, quiero elegir un producto del catálogo",
        ],
    )

    st.caption(
        "La selección de un producto se habilitará "
        "cuando conectemos el catálogo."
    )

    enviado = st.form_submit_button(
        "Ver mis preferencias",
        type="primary",
        width="stretch",
    )


# 6. Validación y resumen de las respuestas.
if enviado:
    if not intereses:
        st.warning("Elegí algún interés o la opción ¡Sorprendeme!.")

    elif "¡Sorprendeme!" in intereses and len(intereses) > 1:
        st.warning(
            "Elegí intereses concretos o solo ¡Sorprendeme!, "
            "para que tu respuesta sea clara."
        )

    else:
        st.success("¡Listo! Este es el resumen de tus preferencias.")
        st.write("**Presupuesto:**", presupuesto)
        st.write("**Para quién:**", destinatario)
        st.write("**Intereses:**", ", ".join(intereses))
        st.write("**Ocasión:**", ocasion)
        st.write("**Tipo de regalo:**", tipo_regalo)
        st.write("**Producto de referencia:**", producto_previo)

        st.info(
            "Todavía no se generan recomendaciones. "
            "El próximo paso es conectar el catálogo y el modelo."
        )

st.caption("Presente Analytics · Proyecto Final Henry")