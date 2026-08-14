import random
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
st.write("Practica tus preguntas. La IA evaluará tus respuestas considerando sinónimos y conceptos.")

# Sidebar - Configuración
st.sidebar.header("1. Clave de API")
api_key = st.sidebar.text_input(
    "Ingresa tu Gemini API Key:",
    type="password",
    help="Obtén una gratis en aistudio.google.com",
)

st.sidebar.header("2. Cargar Documento")
uploaded_file = st.sidebar.file_uploader(
    "Sube tu cuestionario (.txt o .pdf)", type=["txt", "pdf"]
)

if uploaded_file and api_key:
    client = genai.Client(api_key=api_key)
    raw_text = ""

    # Extraer texto del archivo
    if uploaded_file.name.endswith(".txt"):
        raw_text = uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.endswith(".pdf"):
        pdf_reader = pypdf.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            raw_text += page.extract_text() + "\n"

    # Separar en bloques (asumiendo que las preguntas/respuestas están separadas por renglones)
    items = [line.strip() for line in raw_text.split("\n") if len(line.strip()) > 10]

    st.sidebar.success(f"✅ Se cargaron {len(items)} ítems.")

    st.sidebar.header("3. Examen")
    num_q = st.sidebar.number_input(
        "¿Cuántas preguntas al azar?",
        min_value=1,
        max_value=max(1, len(items)),
        value=min(5, len(items)),
    )

    if st.sidebar.button("🎲 Generar Preguntas"):
        st.session_state["quiz"] = random.sample(items, num_q)

    # Mostrar Preguntas
    if "quiz" in st.session_state:
        st.subheader("📝 Cuestionario")

        for i, item in enumerate(st.session_state["quiz"], 1):
            st.markdown(f"### Pregunta / Tema {i}")
            st.info(item)

            user_ans = st.text_area(
                f"Tu respuesta para la pregunta {i}:", key=f"ans_{i}", height=100
            )

            if st.button(f"🤖 Evaluar Respuesta {i}", key=f"btn_{i}"):
                if not user_ans.strip():
                    st.warning("Escribe algo antes de evaluar.")
                else:
                    with st.spinner("La IA está revisando tu respuesta..."):
                        # Prompt enviado a Gemini para comparar conceptos y sinónimos
                        prompt = f"""
                        Eres un profesor experto en Embriología.
                        
                        PREGUNTA/CONCEPTO BASE DEL DOCUMENTO:
                        "{item}"
                        
                        RESPUESTA DEL ESTUDIANTE:
                        "{user_ans}"
                        
                        EVALUACIÓN:
                        1. Determina si la respuesta del estudiante es idéntica en significado, tomando en cuenta sinónimos y variaciones de redacción médicas/biológicas.
                        2. Asigna una calificación de 0 a 100%.
                        3. Da una explicación breve (máximo 3 oraciones) de qué estuvo bien o qué le faltó.
                        """

                        response = client.models.generate_content(
                            model="gemini-2.5-flash", contents=prompt
                        )

                        st.markdown("### 📊 Resultado de la IA:")
                        st.write(response.text)
            st.divider()

elif uploaded_file and not api_key:
    st.warning("⚠️ Por favor ingresa tu API Key en la barra lateral para poder evaluar las respuestas.")
