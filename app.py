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

st.sidebar.header("2. Cargar Documento")
uploaded_file = st.sidebar.file_uploader(
    "Sube tu cuestionario (.txt o .pdf)", type=["txt", "pdf"]
)

if uploaded_file and api_key:
    llave_limpia = api_key.strip()
    client = genai.Client(api_key=llave_limpia)
    raw_text = ""

    # Extraer texto del archivo
    if uploaded_file.name.endswith(".txt"):
        raw_text = uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.endswith(".pdf"):
        pdf_reader = pypdf.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            text_page = page.extract_text()
            if text_page:
                raw_text += text_page + "\n"

    # --- LECTURA INTELIGENTE DE PREGUNTAS Y RESPUESTAS ---
    questions_data = []
    pattern = r"\n(?=\d+\.)"
    blocks = re.split(pattern, "\n" + raw_text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        m = re.match(r"^(\d+)\.\s*(.*)", block, re.DOTALL)
        if m:
            num = m.group(1)
            content = m.group(2).strip()

            if not content:
                continue

            lines = [l.strip() for l in content.split("\n") if l.strip()]
            if not lines:
                continue

            q_lines = []
            for line in lines:
                # 1. Detección exacta de viñetas (•, -, *, etc.)
                if re.match(
                    r"^\s*[•\-\*\u2022\u25cf\u25cb\uf0b7\uf0a7\u2013\u2014\u25ba\u25b6]",
                    line,
                ):
                    break

                # 2. Palabras clave de inicio de respuesta en exámenes
                if q_lines and re.match(
                    r"^(Origen|Papel|Fallo|Partes|Mitosis|Meiosis|Capa|Tejido|Ocurre|Originan|Aberturas|Neuroporo|Carnívoros|Rumiantes|Equinos|Respuesta|Resp|Solución):",
                    line,
                    re.IGNORECASE,
                ):
                    break

                # 3. Etiquetas de respuesta genéricas ("Texto:")
                if q_lines:
                    prev = q_lines[-1]
                    if (prev.endswith(":") or prev.endswith("?")) and re.match(
                        r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ0-9\s\(\/\-]{1,35}:",
                        line,
                    ):
                        break

                q_lines.append(line)

            q_text = " ".join(q_lines) if q_lines else lines[0]

            if len(q_text) > 5:
                questions_data.append(
                    {"num": num, "question": q_text, "full_context": block}
                )

    if questions_data:
        st.sidebar.success(
            f"✅ Se detectaron {len(questions_data)} preguntas numeradas."
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
                st.info(item["question"])

                user_ans = st.text_area(
                    f"Tu respuesta:", key=f"ans_{i}", height=100
                )

                if st.button(f"🤖 Evaluar Respuesta {i}", key=f"btn_{i}"):
                    if not user_ans.strip():
                        st.warning("Escribe algo antes de evaluar.")
                    else:
                        with st.spinner("La IA está revisando tu respuesta..."):
                            prompt = f"""
                            Eres un profesor experto en Embriología.
                            
                            TEXTO ORIGINAL DEL DOCUMENTO (Esta es la respuesta correcta de referencia):
                            "{item['full_context']}"
                            
                            RESPUESTA DEL ESTUDIANTE:
                            "{user_ans}"
                            
                            EVALUACIÓN:
                            1. Determina si la respuesta del estudiante captura los conceptos correctos del TEXTO ORIGINAL.
                            2. Asigna una calificación de 0 a 100%.
                            3. Da una explicación breve de la evaluación.
                            """

                            # MODELOS ESTABLES EN ORDEN DE PREFERENCIA
                            modelos_a_probar = [
                                "gemini-2.0-flash",
                                "gemini-2.5-flash",
                                "gemini-1.5-flash",
                            ]
                            response = None
                            ultimo_error = ""

                            for mod in modelos_a_probar:
                                try:
                                    response = client.models.generate_content(
                                        model=mod, contents=prompt
                                    )
                                    if response and response.text:
                                        break
                                except Exception as e:
                                    ultimo_error = str(e)
                                    continue

                            if response and response.text:
                                st.markdown("### 📊 Resultado de la IA:")
                                st.write(response.text)
                            else:
                                st.error(
                                    f"🛑 Error al conectar con Gemini:"
                                    f" {ultimo_error}"
                                )
                st.divider()
    else:
        st.error(
            "⚠️ No pude encontrar preguntas numeradas (formato '1. ', '2. ',"
            " etc.). Revisa tu archivo."
        )

elif uploaded_file and not api_key:
    st.warning(
        "⚠️ Por favor ingresa tu API Key en la barra lateral para poder evaluar"
        " las respuestas."
    )
