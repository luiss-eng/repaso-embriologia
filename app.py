import json
import random
import streamlit as st
from google import genai
from google.genai import types

# Configuración de página
st.set_page_config(
    page_title="Repasador Inteligente de Embriología",
    page_icon="🧬",
    layout="wide",
)

st.title("🧬 Repasador de Embriología con IA")
st.write(
    "Practica tus preguntas. La IA evaluará tus respuestas considerando"
    " sinónimos y conceptos."
)

# Sidebar - Configuración
st.sidebar.header("1. Clave de API")
api_key = st.sidebar.text_input(
    "Ingresa tu Gemini API Key:",
    type="password",
    help="Obtén una gratis en aistudio.google.com",
)

st.sidebar.header("2. Cargar Cuestionario")
uploaded_file = st.sidebar.file_uploader(
    "Sube tu cuestionario (.pdf)", type=["pdf"]
)


# Función segura que prueba con los modelos activos oficiales
def generar_con_fallback(client, contents):
    modelos_estables = ["gemini-2.0-flash", "gemini-1.5-flash"]
    ultimo_error = None

    for mod in modelos_estables:
        try:
            res = client.models.generate_content(model=mod, contents=contents)
            if res and res.text:
                return res.text
        except Exception as e:
            ultimo_error = e
            continue

    raise ultimo_error


if uploaded_file and api_key:
    client = genai.Client(api_key=api_key.strip())

    # Cargar y procesar el PDF directamente con Gemini si no se ha cargado antes
    if (
        "questions_data" not in st.session_state
        or st.session_state.get("last_file") != uploaded_file.name
    ):
        with st.spinner(
            "🧠 Analizando el documento PDF con IA... (Esto solo toma unos"
            " segundos)"
        ):
            try:
                pdf_bytes = uploaded_file.read()

                prompt_extractor = """
                Analiza el documento adjunto. Es un cuestionario de Embriología con preguntas numeradas y sus respuestas.
                Extrae TODAS las preguntas numeradas con su respectiva respuesta correcta.
                
                Devuelve ÚNICAMENTE un JSON válido con el siguiente formato exacto, sin bloques de código markdown extra:
                [
                  {
                    "num": "1",
                    "pregunta": "Texto exacto de la pregunta",
                    "respuesta_correcta": "Texto completo de la respuesta de referencia"
                  }
                ]
                """

                contents = [
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf",
                    ),
                    prompt_extractor,
                ]

                res_text = generar_con_fallback(client, contents)
                cleaned_text = (
                    res_text.strip()
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )
                questions_json = json.loads(cleaned_text)

                st.session_state["questions_data"] = questions_json
                st.session_state["last_file"] = uploaded_file.name
                st.rerun()

            except Exception as e:
                st.error(
                    f"🛑 Error procesando el PDF con IA: {str(e)}. Verifica que"
                    " tu API Key sea válida."
                )

    # Si ya tenemos las preguntas procesadas
    if "questions_data" in st.session_state:
        questions_data = st.session_state["questions_data"]

        st.sidebar.success(
            f"✅ Se procesaron {len(questions_data)} preguntas con éxito."
        )

        st.sidebar.header("3. Examen")
        num_q = st.sidebar.number_input(
            "¿Cuántas preguntas al azar?",
            min_value=1,
            max_value=len(questions_data),
            value=min(5, len(questions_data)),
        )

        if st.sidebar.button("🎲 Generar Preguntas"):
            st.session_state["quiz"] = random.sample(questions_data, num_q)

        # Mostrar Preguntas
        if "quiz" in st.session_state:
            st.subheader("📝 Cuestionario")

            for i, item in enumerate(st.session_state["quiz"], 1):
                st.markdown(
                    f"### Pregunta {i} *(Del documento: #{item['num']})*"
                )
                st.info(item["pregunta"])

                user_ans = st.text_area(
                    f"Tu respuesta:", key=f"ans_{i}", height=100
                )

                if st.button(f"🤖 Evaluar Respuesta {i}", key=f"btn_{i}"):
                    if not user_ans.strip():
                        st.warning("Escribe algo antes de evaluar.")
                    else:
                        with st.spinner("La IA está revisando tu respuesta..."):
                            prompt_eval = f"""
                            Eres un profesor experto en Embriología.
                            
                            PREGUNTA:
                            "{item['pregunta']}"
                            
                            RESPUESTA CORRECTA DE REFERENCIA:
                            "{item['respuesta_correcta']}"
                            
                            RESPUESTA DEL ESTUDIANTE:
                            "{user_ans}"
                            
                            EVALUACIÓN:
                            1. Determina si la respuesta del estudiante es conceptualmente correcta respecto a la respuesta de referencia.
                            2. Asigna una calificación de 0 a 100%.
                            3. Explica brevemente aciertos y correcciones necesarias.
                            """

                            try:
                                eval_text = generar_con_fallback(
                                    client, prompt_eval
                                )
                                st.markdown("### 📊 Resultado de la IA:")
                                st.write(eval_text)
                            except Exception as e:
                                st.error(
                                    f"🛑 Error evaluando con Gemini: {str(e)}"
                                )
                st.divider()

elif uploaded_file and not api_key:
    st.warning(
        "⚠️ Por favor ingresa tu API Key en la barra lateral para poder evaluar"
        " las respuestas."
    )
