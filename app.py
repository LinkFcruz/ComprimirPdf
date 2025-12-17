import io
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image

# ----------------------------
# Configuración de página
# ----------------------------
st.set_page_config(page_title="Compresor de PDF", layout="centered")

# ----------------------------
# Encabezado
# ----------------------------
st.title("Compresor de PDF")

st.markdown(
    """
👋 **¡Bienvenido!**

Esta aplicación web sirve para **comprimir archivos PDF** directamente desde tu navegador.

La verdad se hizo para mi amiga carolina jaja :)

### Opciones
- 📉 **Comprimir por %**: eliges el nivel de compresión.
- 📦 **Dejar menor a 50 MB** (o el límite que elijas): la app ajusta automáticamente hasta cumplir el tamaño.

👉 **Tus archivos no se guardan**: se procesan temporalmente y luego descargas el resultado.
"""
)

st.divider()

# ----------------------------
# Estado (para no recalcular y sí mostrar descarga)
# ----------------------------
if "out_bytes" not in st.session_state:
    st.session_state.out_bytes = None
if "out_name" not in st.session_state:
    st.session_state.out_name = None
if "out_info" not in st.session_state:
    st.session_state.out_info = None
if "out_key" not in st.session_state:
    st.session_state.out_key = None

if "uploaded_reset" not in st.session_state:
    st.session_state.uploaded_reset = 0  # fuerza reset del uploader

# ----------------------------
# Utilidades
# ----------------------------
def mb(nbytes: int) -> float:
    return nbytes / (1024 * 1024)

def reset_app():
    st.session_state.out_bytes = None
    st.session_state.out_name = None
    st.session_state.out_info = None
    st.session_state.out_key = None
    st.session_state.uploaded_reset += 1
    st.rerun()

def compress_pdf_bytes(pdf_bytes: bytes, dpi: int, quality: int, progress_cb=None) -> bytes:
    """
    Rasteriza páginas a JPEG y reconstruye el PDF.
    progress_cb(current_page, total_pages) para actualizar barra.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out = fitz.open()
    total = len(doc)

    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)

        img_doc = fitz.open("jpeg", buf.getvalue())
        page_pdf = fitz.open("pdf", img_doc.convert_to_pdf())
        out.insert_pdf(page_pdf)

        if progress_cb:
            progress_cb(i, total)

    return out.tobytes()

# ----------------------------
# Controles globales
# ----------------------------
colA, colB = st.columns(2)
with colA:
    if st.button("🧹 Limpiar / Cerrar"):
        reset_app()
with colB:
    if st.button("📄 Comprimir otro PDF"):
        reset_app()

# ----------------------------
# UI principal
# ----------------------------
uploaded = st.file_uploader(
    "📤 Sube tu PDF",
    type=["pdf"],
    key=f"uploader_{st.session_state.uploaded_reset}"
)

mode = st.radio(
    "Selecciona el modo de compresión",
    ["Comprimir por %", "Dejar menor a 50 MB"],
    horizontal=True
)

# ----------------------------
# Si ya hay resultado guardado, mostrar descarga SIEMPRE
# ----------------------------
if st.session_state.out_bytes:
    st.success(st.session_state.out_info or "✅ Compresión finalizada")
    st.download_button(
        label="⬇️ Descargar PDF comprimido",
        data=st.session_state.out_bytes,
        file_name=st.session_state.out_name or "pdf_comprimido.pdf",
        mime="application/pdf"
    )
    st.info("Si deseas otro archivo, usa **📄 Comprimir otro PDF**.")
    st.divider()

# ----------------------------
# Procesamiento al subir PDF
# ----------------------------
if uploaded:
    original_bytes = uploaded.read()
    original_size = len(original_bytes)
    st.info(f"📄 **Tamaño original:** {mb(original_size):.2f} MB")

    # ==========================================
    # MODO 1: Comprimir por %
    # ==========================================
    if mode == "Comprimir por %":
        percentage = st.slider(
            "Nivel de compresión (%)",
            min_value=10,
            max_value=90,
            value=40,
            help="Más % = más compresión (menor tamaño, menor calidad)."
        )

        base_dpi = 120
        base_quality = 65
        factor = (100 - percentage) / 100.0

        dpi = max(60, int(base_dpi * factor))
        quality = max(20, int(base_quality * factor))

        st.caption(f"Parámetros → **DPI:** {dpi} | **Calidad JPEG:** {quality}")

        run_key = ("pct", original_size, percentage, dpi, quality)

        if st.button("📉 Comprimir PDF"):
            # Si cambió la configuración, limpiar resultado anterior
            if st.session_state.out_key != run_key:
                st.session_state.out_bytes = None
                st.session_state.out_name = None
                st.session_state.out_info = None

            with st.spinner("Comprimiendo... por favor espera"):
                bar = st.progress(0)
                status = st.empty()

                def progress_cb(i, total):
                    p = int((i / total) * 100)
                    bar.progress(p)
                    status.write(f"Procesando páginas: {i}/{total} ({p}%)")

                out_bytes = compress_pdf_bytes(
                    original_bytes, dpi=dpi, quality=quality, progress_cb=progress_cb
                )

                bar.progress(100)
                status.write("✅ Compresión finalizada")

            st.session_state.out_bytes = out_bytes
            st.session_state.out_name = "pdf_comprimido.pdf"
            st.session_state.out_info = f"✅ **Final:** {mb(len(out_bytes)):.2f} MB (DPI={dpi}, Calidad={quality})"
            st.session_state.out_key = run_key

            st.rerun()

    # ==========================================
    # MODO 2: Dejar menor a X MB (auto)
    # ==========================================
    else:
        target_mb = st.number_input("Límite de tamaño (MB)", min_value=1, max_value=200, value=50)
        target_bytes = int(target_mb * 1024 * 1024)

        start_dpi, start_q = 120, 65
        min_dpi, min_q = 60, 20

        run_key = ("limit", original_size, target_bytes)

        if st.button("📦 Comprimir a menor de límite"):
            if st.session_state.out_key != run_key:
                st.session_state.out_bytes = None
                st.session_state.out_name = None
                st.session_state.out_info = None

            combos = [(d, q) for d in range(start_dpi, min_dpi - 1, -10)
                             for q in range(start_q, min_q - 1, -5)]
            total = len(combos)

            with st.spinner("Buscando la mejor compresión que cumpla el límite..."):
                attempts_bar = st.progress(0)
                attempts_status = st.empty()

                best = None

                for idx, (dpi_try, q_try) in enumerate(combos, start=1):
                    attempts_status.write(f"Intento {idx}/{total} → DPI={dpi_try}, Calidad={q_try}")
                    attempts_bar.progress(int(idx / total * 100))

                    # Progreso por páginas para este intento
                    page_bar = st.progress(0)
                    page_status = st.empty()

                    def progress_cb(i, pages_total):
                        p = int((i / pages_total) * 100)
                        page_bar.progress(p)
                        page_status.write(f"Páginas: {i}/{pages_total} ({p}%)")

                    out_bytes = compress_pdf_bytes(
                        original_bytes, dpi=dpi_try, quality=q_try, progress_cb=progress_cb
                    )

                    # Limpiar barras de páginas del intento
                    page_bar.empty()
                    page_status.empty()

                    if len(out_bytes) <= target_bytes:
                        best = (out_bytes, dpi_try, q_try, idx)
                        break

            if not best:
                st.error("❌ No se pudo alcanzar el tamaño deseado con los parámetros actuales. Se necesitaría más compresión.")
            else:
                out_bytes, dpi_final, q_final, attempts_used = best
                st.session_state.out_bytes = out_bytes
                st.session_state.out_name = f"pdf_menor_{int(target_mb)}MB.pdf"
                st.session_state.out_info = (
                    f"✅ **Final:** {mb(len(out_bytes)):.2f} MB "
                    f"(DPI={dpi_final}, Calidad={q_final}, intentos={attempts_used})"
                )
                st.session_state.out_key = run_key
                st.rerun()

st.divider()
st.caption("ℹ️ Nota: este método convierte las páginas en imágenes. Si tu PDF tiene texto seleccionable, esa capa se perderá.")

