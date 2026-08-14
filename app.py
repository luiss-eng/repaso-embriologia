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
            raw_text += page.extract_text() + "\n"

    # --- LECTURA INTELIGENTE MULTILÍNEA ---
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
            content = m.group(2)

            # Analizamos línea por línea para capturar la pregunta completa antes de la respuesta
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            q_lines = []

            for idx, line in enumerate(lines):
                # Si encontramos un símbolo de viñeta (•, -, *, etc.), aquí empieza la respuesta
                if re.match(r"^[\u2022\u25cf\u25cb\uf0b7\-\*•]", line):
                    break

                # Si ya tenemos texto de pregunta y la nueva línea parece un encabezado de respuesta
                if q_lines:
                    prev_line = q_lines[-1]
                    if (
                        prev_line.endswith(":") or prev_line.endswith("?")
                    ) and re.match(
                        r"^(Etapas|Capas|Proteínas|Acondroplasia|En |Vías|Respuesta|Resp|Solución|[A-Z][a-z]+:)",
                        line,
                    ):
                        break

                q_lines.append(line)

            q_text = " ".join(q_lines) if q_lines else lines[0]

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

                            # SISTEMA MULTI-MODELO DE RESPALDO AUTOMÁTICO
                            modelos = [
                                "gemini-2.5-flash",
                                "gemini-1.5-flash",
                                "gemini-2.0-flash-exp",
                            ]
                            response = None
                            error_msg = ""

                            for mod in modelos:
                                try:
                                    response = client.models.generate_content(
                                        model=mod, contents=prompt
                                    )
                                    if response:
                                        break
                                except Exception as e:
                                    error_msg = str(e)
                                    continue

                            if response:
                                st.markdown("### 📊 Resultado de la IA:")
                                st.write(response.text)
                            else:
                                st.error(
                                    f"🛑 No se pudo conectar con los modelos de"
                                    f" Google: {error_msg}"
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
