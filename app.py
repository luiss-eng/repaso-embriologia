import json
import random
import re
import pypdf
import streamlit as st
from google import genai

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
    "Sube tu cuestionario (.pdf o .txt)", type=["pdf", "txt"]
)


# --- FUNCIÓN INTELIGENTE DE CONEXIÓN CON GEMINI ---
def consultar_gemini_seguro(client, prompt):
    """Detecta dinámicamente qué modelos están habilitados para la API Key y los prueba en orden."""
    modelos_encontrados = []

    # 1. Intentar listar los modelos a los que tiene acceso tu API Key
    try:
        for m in client.models.list():
            if m.name and "gemini" in m.name.lower():
                nombre_limpio = m.name.replace("models/", "")
                modelos_encontrados.append(nombre_limpio)
    except Exception:
        pass

    # 2. Lista de nombres habituales ordenados por preferencia
    preferencias = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash-8b",
    ]

    # Priorizar los modelos detectados realmente en tu cuenta
    candidatos = [mod for mod in preferencias if mod in modelos_encontrados]

    # Agregar el resto por si el listado automático falló
    for mod in preferencias:
        if mod not in candidatos:
            candidatos.append(mod)

    for mod in modelos_encontrados:
        if mod not in candidatos:
            candidatos.append(mod)

    # 3. Probar modelo por modelo hasta encontrar uno funcional
    ultimo_error = None
    for mod in candidatos:
        try:
            res = client.models.generate_content(model=mod, contents=prompt)
            if res and res.text:
                return res.text
        except Exception as e:
            ultimo_error = e
            continue

    raise Exception(
        f"No se pudo conectar con los servidores de Google. Detalle del"
        f" error: {ultimo_error}"
    )


if uploaded_file and api_key:
    client = genai.Client(api_key=api_key.strip())

    # Procesar archivo si no se ha cargado previamente
    if (
        "questions_data" not in st.session_state
        or st.session_state.get("last_file") != uploaded_file.name
    ):
        with st.spinner(
            "🧠 Extrayendo texto y organizando el cuestionario con IA..."
        ):
            try:
                # Extraer texto básico
                raw_text = ""
                if uploaded_file.name.endswith(".pdf"):
                    pdf_reader = pypdf.PdfReader(uploaded_file)
                    for page in pdf_reader.pages:
                        t = page.extract_text()
                        if t:
                            raw_text += t + "\n"
                else:
                    raw_text = uploaded_file.read().decode("utf-8")

                if not raw_text.strip():
                    st.error(
                        "🛑 No se pudo extraer texto del archivo. Asegúrate de"
                        " que no sea un PDF escaneado como imagen."
                    )
                else:
                    prompt_extractor = f"""
                    Eres un profesor de Embriología estructurando un examen.
                    A continuación tienes el texto extraído de un cuestionario:

                    ---
                    {raw_text}
                    ---

                    Tu tarea es extraer TODAS las preguntas numeradas con su respectiva respuesta correcta.
                    
                    Devuelve ÚNICAMENTE un JSON válido con esta estructura (sin formato Markdown adicional):
                    [
                      {{
                        "num": "1",
                        "pregunta": "Enunciado exacto de la pregunta",
                        "respuesta_correcta": "Respuesta completa de referencia"
                      }}
                    ]
                    """

                    res_text = consultar_gemini_seguro(client, prompt_extractor)

                    # Limpieza de código JSON
                    cleaned_json_text = (
                        res_text.strip()
                        .replace("```json", "")
                        .replace("```", "")
                        .strip()
                    )
                    questions_json = json.loads(cleaned_json_text)

                    st.session_state["questions_data"] = questions_json
                    st.session_state["last_file"] = uploaded_file.name
                    st.rerun()

            except Exception as e:
                st.error(
                    f"🛑 Ocurrió un error al procesar el archivo: {str(e)}"
                )

    # Si las preguntas ya están cargadas en la sesión
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
                                eval_text = consultar_gemini_seguro(
                                    client, prompt_eval
                                )
                                st.markdown("### 📊 Resultado de la IA:")
                                st.write(eval_text)
                            except Exception as e:
                                st.error(
                                    f"🛑 Error evaluando la respuesta: {str(e)}"
                                )
                st.divider()

elif uploaded_file and not api_key:
    st.warning(
        "⚠️ Por favor ingresa tu API Key en la barra lateral para poder evaluar"
        " las respuestas."
    )
