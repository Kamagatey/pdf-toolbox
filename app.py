import streamlit as st

from utils import (
    human_size,
    pdf_page_count,
    merge_pdfs,
    compress_pdf_preset,
    compress_pdf_to_target,
    images_to_pdf,
    split_pdf_to_zip,
    extract_pages,
    rotate_pdf,
    safe_filename,
)

st.set_page_config(page_title="PDF Toolbox", page_icon="📄", layout="wide")

# --------------------------------------------------------------------------- #
# Style
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    .stApp { background-color: #f5f7fb; }

    section[data-testid="stSidebar"] { background-color: #111827; }
    section[data-testid="stSidebar"] * { color: #e5e7eb !important; }
    section[data-testid="stSidebar"] .stRadio > div { gap: 0.25rem; }
    section[data-testid="stSidebar"] .stRadio label {
        padding: 0.35rem 0.5rem; border-radius: 8px;
    }

    .tool-header {
        padding: 1.2rem 1.5rem; border-radius: 16px; margin-bottom: 1.3rem;
        background: linear-gradient(135deg, #2E6BE6 0%, #6D8BF5 100%);
        color: white;
    }
    .tool-header h1 { margin: 0; font-size: 1.5rem; }
    .tool-header p { margin: 0.35rem 0 0 0; opacity: 0.92; font-size: 0.95rem; }

    div[data-testid="stMetric"] {
        background: white; border-radius: 12px; padding: 10px 16px;
        border: 1px solid #e5e7eb;
    }
    div[data-testid="stFileUploaderDropzone"] { border-radius: 12px; }

    .stButton > button, .stDownloadButton > button {
        border-radius: 10px; font-weight: 600; padding: 0.5rem 1.1rem;
    }
    .stDownloadButton > button { background-color: #16a34a; color: white; border: none; }
    .stDownloadButton > button:hover { background-color: #15803d; color: white; }

    [data-testid="stCameraInput"] { width: 100% !important; }
    [data-testid="stCameraInput"] video,
    [data-testid="stCameraInput"] img {
        width: 100% !important; max-width: 100% !important; height: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Outils + descriptions
# --------------------------------------------------------------------------- #
TOOLS = {
    "🔗 Fusionner des PDF": "Combine plusieurs PDF en un seul fichier, dans l'ordre de ton choix.",
    "📉 Réduire la taille d'un PDF": "Préréglage rapide ou taille cible en Ko/Mo.",
    "🖼️ Image(s) → PDF": "Transforme une ou plusieurs images en un PDF.",
    "✂️ Diviser un PDF": "Éclate un PDF en fichiers d'une page chacun.",
    "📑 Extraire / réorganiser des pages": "Garde et réordonne les pages de ton choix.",
    "🔄 Pivoter des pages": "Fait pivoter tout ou partie des pages d'un PDF.",
    "📷 Scanner (photos → PDF)": "Prends des photos à la suite, façon CamScanner, et assemble-les en PDF.",
}
TOOL_NAMES = list(TOOLS.keys())

with st.sidebar:
    st.markdown("## 📄 PDF Toolbox")
    st.caption(
        "Tes documents restent privés : tout se traite en mémoire, "
        "rien n'est envoyé à un service tiers."
    )
    st.markdown("---")
    tool = st.radio("Outil", TOOL_NAMES, label_visibility="collapsed")
    st.markdown("---")
    st.caption("Fait avec Streamlit 🐍")

st.markdown(
    f"""
    <div class="tool-header">
        <h1>{tool}</h1>
        <p>{TOOLS[tool]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# 1) Fusionner
# --------------------------------------------------------------------------- #
if tool == TOOL_NAMES[0]:
    with st.container(border=True):
        files = st.file_uploader(
            "Dépose tes PDF à fusionner", type="pdf", accept_multiple_files=True
        )

        if files:
            names = [f.name for f in files]
            st.write("Ordre de fusion (modifiable) :")
            for i, n in enumerate(names, start=1):
                st.text(f"{i}. {n}")

            default_order = ", ".join(str(i + 1) for i in range(len(names)))
            order_str = st.text_input(
                "Numéros dans l'ordre souhaité, séparés par des virgules",
                value=default_order,
            )
            out_name = st.text_input("Nom du fichier", value="fusion")

            if st.button("🔗 Fusionner", type="primary"):
                try:
                    order = [int(x.strip()) for x in order_str.split(",") if x.strip()]
                    assert sorted(order) == list(range(1, len(names) + 1))
                    ordered_bytes = [files[i - 1].getvalue() for i in order]
                    result = merge_pdfs(ordered_bytes)
                    st.success(f"PDF fusionné : {human_size(len(result))}")
                    st.download_button(
                        "⬇️ Télécharger le PDF fusionné",
                        data=result,
                        file_name=safe_filename(out_name, "fusion", ".pdf"),
                        mime="application/pdf",
                    )
                except (ValueError, AssertionError):
                    st.error(
                        "L'ordre indiqué doit contenir chaque numéro de fichier "
                        "une seule fois (ex : 2, 1, 3)."
                    )


# --------------------------------------------------------------------------- #
# 2) Réduire la taille
# --------------------------------------------------------------------------- #
elif tool == TOOL_NAMES[1]:
    with st.container(border=True):
        file = st.file_uploader("Dépose un PDF à compresser", type="pdf")

        if file:
            original = file.getvalue()
            st.metric("Taille actuelle", human_size(len(original)))

            mode = st.radio("Mode", ["Préréglage rapide", "Taille cible"], horizontal=True)

            if mode == "Préréglage rapide":
                preset = st.select_slider(
                    "Niveau de compression", options=["Légère", "Moyenne", "Forte"]
                )
                out_name = st.text_input("Nom du fichier", value="compresse", key="name_preset")

                if st.button("📉 Compresser", type="primary"):
                    with st.spinner("Compression en cours..."):
                        result = compress_pdf_preset(original, preset)
                    ratio = 100 * (1 - len(result) / len(original))
                    c1, c2 = st.columns(2)
                    c1.metric("Avant", human_size(len(original)))
                    c2.metric("Après", human_size(len(result)), delta=f"-{ratio:.0f}%")
                    st.download_button(
                        "⬇️ Télécharger le PDF compressé",
                        data=result,
                        file_name=safe_filename(out_name, "compresse", ".pdf"),
                        mime="application/pdf",
                    )

            else:
                col1, col2 = st.columns([2, 1])
                with col1:
                    target_value = st.number_input("Taille cible", min_value=1, value=500)
                with col2:
                    unit = st.selectbox("Unité", ["Ko", "Mo"])
                target_bytes = target_value * (1024 if unit == "Ko" else 1024 * 1024)
                out_name = st.text_input("Nom du fichier", value="compresse", key="name_target")

                if st.button("📉 Compresser vers la taille cible", type="primary"):
                    if target_bytes >= len(original):
                        st.info("Le fichier est déjà plus petit que la taille cible.")
                    else:
                        with st.spinner("Recherche du meilleur réglage..."):
                            result, achieved = compress_pdf_to_target(original, target_bytes)
                        ratio = 100 * (1 - len(result) / len(original))
                        c1, c2 = st.columns(2)
                        c1.metric("Avant", human_size(len(original)))
                        c2.metric("Après", human_size(len(result)), delta=f"-{ratio:.0f}%")
                        if achieved:
                            st.success("Objectif atteint 🎯")
                        else:
                            st.warning(
                                f"Impossible de descendre jusqu'à {human_size(target_bytes)} "
                                "sans trop dégrader le PDF — voici le meilleur résultat obtenu. "
                                "Un PDF surtout composé de texte compresse peu : "
                                "l'essentiel du gain vient des images qu'il contient."
                            )
                        st.download_button(
                            "⬇️ Télécharger le PDF compressé",
                            data=result,
                            file_name=safe_filename(out_name, "compresse", ".pdf"),
                            mime="application/pdf",
                        )


# --------------------------------------------------------------------------- #
# 3) Image(s) -> PDF
# --------------------------------------------------------------------------- #
elif tool == TOOL_NAMES[2]:
    with st.container(border=True):
        files = st.file_uploader(
            "Dépose une ou plusieurs images",
            type=["jpg", "jpeg", "png", "bmp", "webp", "tiff"],
            accept_multiple_files=True,
        )

        if files:
            names = [f.name for f in files]
            st.write("Ordre des pages (modifiable) :")
            for i, n in enumerate(names, start=1):
                st.text(f"{i}. {n}")

            default_order = ", ".join(str(i + 1) for i in range(len(names)))
            order_str = st.text_input(
                "Numéros dans l'ordre souhaité, séparés par des virgules",
                value=default_order,
            )
            page_size = st.selectbox("Format de page", ["A4", "Taille d'origine", "Letter"])
            out_name = st.text_input("Nom du fichier", value="images")

            if st.button("🖼️ Convertir en PDF", type="primary"):
                try:
                    order = [int(x.strip()) for x in order_str.split(",") if x.strip()]
                    assert sorted(order) == list(range(1, len(names) + 1))
                    ordered_bytes = [files[i - 1].getvalue() for i in order]
                    result = images_to_pdf(ordered_bytes, page_size=page_size)
                    st.success(f"PDF généré : {human_size(len(result))}")
                    st.download_button(
                        "⬇️ Télécharger le PDF",
                        data=result,
                        file_name=safe_filename(out_name, "images", ".pdf"),
                        mime="application/pdf",
                    )
                except (ValueError, AssertionError):
                    st.error("L'ordre indiqué doit contenir chaque numéro d'image une seule fois.")


# --------------------------------------------------------------------------- #
# 4) Diviser
# --------------------------------------------------------------------------- #
elif tool == TOOL_NAMES[3]:
    with st.container(border=True):
        file = st.file_uploader("Dépose un PDF à diviser", type="pdf")
        if file:
            original = file.getvalue()
            n_pages = pdf_page_count(original)
            st.metric("Pages", n_pages)
            out_name = st.text_input("Nom du fichier zip", value="pages")

            if st.button("✂️ Diviser en une page par fichier", type="primary"):
                result = split_pdf_to_zip(original)
                st.success("PDF divisé.")
                st.download_button(
                    "⬇️ Télécharger le zip",
                    data=result,
                    file_name=safe_filename(out_name, "pages", ".zip"),
                    mime="application/zip",
                )


# --------------------------------------------------------------------------- #
# 5) Extraire / réorganiser
# --------------------------------------------------------------------------- #
elif tool == TOOL_NAMES[4]:
    with st.container(border=True):
        file = st.file_uploader("Dépose un PDF", type="pdf")
        if file:
            original = file.getvalue()
            n_pages = pdf_page_count(original)
            st.metric("Pages", n_pages)

            pages_str = st.text_input(
                "Pages à garder, dans l'ordre voulu (ex : 1, 3, 2)",
                value=", ".join(str(i) for i in range(1, n_pages + 1)),
            )
            out_name = st.text_input("Nom du fichier", value="extrait")

            if st.button("📑 Générer le nouveau PDF", type="primary"):
                try:
                    pages = [int(x.strip()) for x in pages_str.split(",") if x.strip()]
                    assert all(1 <= p <= n_pages for p in pages) and pages
                    result = extract_pages(original, pages)
                    st.success(f"PDF généré : {human_size(len(result))}")
                    st.download_button(
                        "⬇️ Télécharger le PDF",
                        data=result,
                        file_name=safe_filename(out_name, "extrait", ".pdf"),
                        mime="application/pdf",
                    )
                except (ValueError, AssertionError):
                    st.error(f"Indique des numéros de page valides entre 1 et {n_pages}.")


# --------------------------------------------------------------------------- #
# 6) Pivoter
# --------------------------------------------------------------------------- #
elif tool == TOOL_NAMES[5]:
    with st.container(border=True):
        file = st.file_uploader("Dépose un PDF", type="pdf")
        if file:
            original = file.getvalue()
            n_pages = pdf_page_count(original)
            st.metric("Pages", n_pages)

            scope = st.radio(
                "Pages concernées", ["Toutes les pages", "Certaines pages"], horizontal=True
            )
            page_numbers = None
            if scope == "Certaines pages":
                pages_str = st.text_input("Numéros de page, séparés par des virgules", value="1")
            angle = st.select_slider("Angle de rotation (sens horaire)", options=[90, 180, 270])
            out_name = st.text_input("Nom du fichier", value="pivote")

            if st.button("🔄 Pivoter", type="primary"):
                try:
                    if scope == "Certaines pages":
                        page_numbers = [int(x.strip()) for x in pages_str.split(",") if x.strip()]
                        assert all(1 <= p <= n_pages for p in page_numbers)
                    result = rotate_pdf(original, angle, page_numbers)
                    st.success("PDF pivoté.")
                    st.download_button(
                        "⬇️ Télécharger le PDF",
                        data=result,
                        file_name=safe_filename(out_name, "pivote", ".pdf"),
                        mime="application/pdf",
                    )
                except (ValueError, AssertionError):
                    st.error(f"Indique des numéros de page valides entre 1 et {n_pages}.")


# --------------------------------------------------------------------------- #
# 7) Scanner : prendre des photos en direct -> PDF
# --------------------------------------------------------------------------- #
elif tool == TOOL_NAMES[6]:
    st.caption(
        "Prends tes photos une par une. Après chaque prise, l'appareil se réinitialise "
        "automatiquement pour la suivante."
    )

    capture_mode = st.radio(
        "Mode de capture",
        ["📷 Caméra intégrée (aperçu direct)", "📱 Appareil photo natif (meilleure qualité)"],
        horizontal=True,
    )

    if "scan_photos" not in st.session_state:
        st.session_state.scan_photos = []
    if "camera_key" not in st.session_state:
        st.session_state.camera_key = 0

    with st.container(border=True):
        if capture_mode.startswith("📷"):
            photo = st.camera_input(
                f"Photo n°{len(st.session_state.scan_photos) + 1}",
                key=f"camera_{st.session_state.camera_key}",
            )
        else:
            photo = st.file_uploader(
                f"Photo n°{len(st.session_state.scan_photos) + 1}",
                type=["jpg", "jpeg", "png"],
                key=f"camera_{st.session_state.camera_key}",
            )

    if photo is not None:
        st.session_state.scan_photos.append(photo.getvalue())
        st.session_state.camera_key += 1
        st.rerun()

    if st.session_state.scan_photos:
        with st.container(border=True):
            st.write(f"**{len(st.session_state.scan_photos)} photo(s) prise(s)**")
            cols = st.columns(4)
            for i, photo_bytes in enumerate(st.session_state.scan_photos):
                with cols[i % 4]:
                    st.image(photo_bytes, caption=f"Page {i + 1}", use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Supprimer la dernière photo"):
                    st.session_state.scan_photos.pop()
                    st.rerun()
            with col2:
                if st.button("🗑️ Tout effacer"):
                    st.session_state.scan_photos = []
                    st.rerun()

            scan_effect = st.checkbox("Effet scanner (noir & blanc + contraste)", value=False)
            page_size = st.selectbox(
                "Format de page", ["Taille d'origine", "A4", "Letter"], key="scan_page_size"
            )
            file_name = st.text_input("Nom du fichier", value="scan")

            if st.button("📄 Générer le PDF", type="primary"):
                result = images_to_pdf(
                    st.session_state.scan_photos, page_size=page_size, scan_effect=scan_effect
                )
                st.success(
                    f"PDF généré : {human_size(len(result))} "
                    f"({len(st.session_state.scan_photos)} page(s))"
                )
                st.download_button(
                    "⬇️ Télécharger le PDF",
                    data=result,
                    file_name=safe_filename(file_name, "scan", ".pdf"),
                    mime="application/pdf",
                )