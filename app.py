import io
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image

# --------------------------------------------------
# Configuración de la página
# --------------------------------------------------
st.set_page_config(
    page_title="Compresor de PDF",
    layout="centered"
)

# --------------------------------------------------
# Saludo e introducción
# --------------------------------------------------
st.title("Compresor de PDF")

st.markdown(
    """
👋 **¡Bienvenido!**

Esta aplicación web sirve para **comprimir archivos PDF de forma gratuita**, directamente desde tu navegador.

Realmente se hizo para Carolina pero pueden usarla :)

 
### ¿Qué puedes hacer aquí?
- 📉 **Comprimir por porcentaje**: reduce el tamaño del PDF según el nivel de compresión que elijas.
- 📦 **Comprimir a un tamaño específico**: deja tu archivo **por debajo de 50 MB** (o el límite que necesites).

Es ideal para:
- PDFs escaneados  
- Archivos que necesitas subir a plataformas con límite de tamaño  

👉 **Tus archivos no se guardan**. Se procesan temporalmente y se descargan al instante.
"""
)

st.divider()

# --------------------------------------------------
# Funciones
# --------------------------------------------------
def compress_pdf_bytes(pdf_bytes: bytes, dpi: int, quality: int) -> bytes:
    """
    Convierte cada página del PDF en una imagen JPEG comprimida
    y reconstruye un nuevo PDF.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out = fitz.open()

    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)

        img_doc = fitz.open("jpeg", buffer.getvalue())
        page_pdf = fitz.open("pdf", img_doc.convert_to_pdf())
        out.insert_pdf(page_pdf)

    return out.tobytes()


def bytes_to_mb(nbytes: int) -> float:
    return nbytes / (1024 * 1024)

# --------------------------------------------------
# Subida de archivo
# --------------------------------------------------
uploaded_file = st.file_uploader(
    "📤 Sube tu archivo PDF",
    type=["pdf"]
)

if uploaded_file:
    original_bytes = uploaded_file.read()
    original_size_mb = bytes_to_mb(len(original_bytes))

    st.info(f"📄 **Tamaño original:** {original_size_mb:.2f} MB")

    # --------------------------------------------------
    # Selección de modo
    # --------------------------------------------------
    mode = st.radio(
        "Selecciona el modo de compresión",
        ["Comprimir por %", "Dejar menor a 50 MB"],
        horizontal=True
    )

    # --------------------------------------------------
    # MODO 1: Comprimir por porcentaje
    # --------------------------------------------------
    if mode == "Comprimir por %":
        percentage = st.slider(
            "Nivel de compresión (%)",
            min_value=10,
            max_value=90,
            value=40
        )

        # Valores base (buena calidad)
        base_dpi = 120
        base_quality = 65

        factor = (100 - percentage) / 100
        dpi = max(60, int(base_dpi * factor))
        quality = max(20, int(base_quality * factor))

        st.caption(f"Parámetros usados → DPI: {dpi}, Calidad JPEG: {quality}")

        if st.button("📉 Comprimir PDF"):
            compressed_bytes = compress_pdf_bytes(
                original_bytes,
                dpi=dpi,
                quality=quality
            )

            final_size_mb = bytes_to_mb(len(compressed_bytes))

            st.success(f"✅ **Tamaño final:** {final_size_mb:.2f} MB")

            st.download_button(
                label="⬇️ Descargar PDF comprimido",
                data=compressed_bytes,
                file_name="pdf_comprimido.pdf",
                mime="application/pdf"
            )

    # --------------------------------------------------
    # MODO 2: Comprimir a menor de 50 MB
    # --------------------------------------------------
    else:
        target_mb = st.number_input(
            "Límite de tamaño (MB)",
            min_value=1,
            max_value=200,
            value=50
        )

        target_bytes = int(target_mb * 1024 * 1024)

        start_dpi, start_quality = 120, 65
        min_dpi, min_quality = 60, 20

        if st.button("📦 Comprimir a menor de límite"):
            best_result = None

            for dpi in range(start_dpi, min_dpi - 1, -10):
                for quality in range(start_quality, min_quality - 1, -5):
                    compressed_bytes = compress_pdf_bytes(
                        original_bytes,
                        dpi=dpi,
                        quality=quality
                    )

                    if len(compressed_bytes) <= target_bytes:
                        best_result = (compressed_bytes, dpi, quality)
