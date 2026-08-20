import io

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
)

st.set_page_config(page_title="PDF Toolbox", page_icon="📄", layout="centered")

TOOLS = [
    "🔗 Fusionner des PDF",
    "📉 Réduire la taille d'un PDF",
    "🖼️ Image(s) → PDF",
    "✂️ Diviser un PDF",
    "📑 Extraire / réorganiser des pages",
    "🔄 Pivoter des pages",
]

st.sidebar.title("📄 PDF Toolbox")
tool = st.sidebar.radio("Outil", TOOLS, label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption(
    "Tout le traitement se fait localement dans l'app (en mémoire). "
    "Aucun fichier n'est envoyé à un service tiers."
)

st.title(tool)


# --------------------------------------------------------------------------- #
# 1) Fusionner
# --------------------------------------------------------------------------- #
if tool == TOOLS[0]:
    files = st.file_uploader(
        "Dépose tes PDF à fusionner", type="pdf", accept_multiple_files=True
    )

    if files:
        names = [f.name for f in files]
        st.write("Ordre de fusion (modifiable) :")
        default_order = ", ".join(str(i + 1) for i in range(len(names)))
        for i, n in enumerate(names, start=1):
            st.text(f"{i}. {n}")

        order_str = st.text_input(
            "Numéros dans l'ordre souhaité, séparés par des virgules",
            value=default_order,
        )

        if st.button("Fusionner", type="primary"):
            try:
                order = [int(x.strip()) for x in order_str.split(",") if x.strip()]
                assert sorted(order) == list(range(1, len(names) + 1))
                ordered_bytes = [files[i - 1].getvalue() for i in order]
                result = merge_pdfs(ordered_bytes)
                st.success(f"PDF fusionné : {human_size(len(result))}")
                st.download_button(
                    "⬇️ Télécharger le PDF fusionné",
                    data=result,
                    file_name="fusion.pdf",
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
elif tool == TOOLS[1]:
    file = st.file_uploader("Dépose un PDF à compresser", type="pdf")

    if file:
        original = file.getvalue()
        st.caption(f"Taille actuelle : {human_size(len(original))}")

        mode = st.radio("Mode", ["Préréglage rapide", "Taille cible"], horizontal=True)

        if mode == "Préréglage rapide":
            preset = st.select_slider("Niveau de compression", options=["Légère", "Moyenne", "Forte"])
            if st.button("Compresser", type="primary"):
                with st.spinner("Compression en cours..."):
                    result = compress_pdf_preset(original, preset)
                ratio = 100 * (1 - len(result) / len(original))
                st.success(
                    f"Nouvelle taille : {human_size(len(result))} "
                    f"({ratio:.0f}% de réduction)"
                )
                st.download_button(
                    "⬇️ Télécharger le PDF compressé",
                    data=result,
                    file_name="compresse.pdf",
                    mime="application/pdf",
                )

        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                target_value = st.number_input("Taille cible", min_value=1, value=500)
            with col2:
                unit = st.selectbox("Unité", ["Ko", "Mo"])
            target_bytes = target_value * (1024 if unit == "Ko" else 1024 * 1024)

            if st.button("Compresser vers la taille cible", type="primary"):
                if target_bytes >= len(original):
                    st.info("Le fichier est déjà plus petit que la taille cible.")
                else:
                    with st.spinner("Recherche du meilleur réglage..."):
                        result, achieved = compress_pdf_to_target(original, target_bytes)
                    ratio = 100 * (1 - len(result) / len(original))
                    if achieved:
                        st.success(
                            f"Objectif atteint : {human_size(len(result))} "
                            f"({ratio:.0f}% de réduction)"
                        )
                    else:
                        st.warning(
                            f"Impossible de descendre jusqu'à {human_size(target_bytes)} "
                            f"sans trop dégrader le PDF. Meilleur résultat obtenu : "
                            f"{human_size(len(result))} ({ratio:.0f}% de réduction). "
                            "Un PDF surtout composé de texte compresse peu : "
                            "l'essentiel du gain vient des images qu'il contient."
                        )
                    st.download_button(
                        "⬇️ Télécharger le PDF compressé",
                        data=result,
                        file_name="compresse.pdf",
                        mime="application/pdf",
                    )


# --------------------------------------------------------------------------- #
# 3) Image(s) -> PDF
# --------------------------------------------------------------------------- #
elif tool == TOOLS[2]:
    files = st.file_uploader(
        "Dépose une ou plusieurs images",
        type=["jpg", "jpeg", "png", "bmp", "webp", "tiff"],
        accept_multiple_files=True,
    )

    if files:
        names = [f.name for f in files]
        st.write("Ordre des pages (modifiable) :")
        default_order = ", ".join(str(i + 1) for i in range(len(names)))
        for i, n in enumerate(names, start=1):
            st.text(f"{i}. {n}")
        order_str = st.text_input(
            "Numéros dans l'ordre souhaité, séparés par des virgules",
            value=default_order,
        )

        page_size = st.selectbox("Format de page", ["Taille d'origine", "A4", "Letter"])

        if st.button("Convertir en PDF", type="primary"):
            try:
                order = [int(x.strip()) for x in order_str.split(",") if x.strip()]
                assert sorted(order) == list(range(1, len(names) + 1))
                ordered_bytes = [files[i - 1].getvalue() for i in order]
                result = images_to_pdf(ordered_bytes, page_size=page_size)
                st.success(f"PDF généré : {human_size(len(result))}")
                st.download_button(
                    "⬇️ Télécharger le PDF",
                    data=result,
                    file_name="images.pdf",
                    mime="application/pdf",
                )
            except (ValueError, AssertionError):
                st.error("L'ordre indiqué doit contenir chaque numéro d'image une seule fois.")


# --------------------------------------------------------------------------- #
# 4) Diviser
# --------------------------------------------------------------------------- #
elif tool == TOOLS[3]:
    file = st.file_uploader("Dépose un PDF à diviser", type="pdf")
    if file:
        original = file.getvalue()
        n_pages = pdf_page_count(original)
        st.caption(f"{n_pages} page(s)")
        if st.button("Diviser en une page par fichier", type="primary"):
            result = split_pdf_to_zip(original)
            st.success("PDF divisé.")
            st.download_button(
                "⬇️ Télécharger le zip",
                data=result,
                file_name="pages.zip",
                mime="application/zip",
            )


# --------------------------------------------------------------------------- #
# 5) Extraire / réorganiser
# --------------------------------------------------------------------------- #
elif tool == TOOLS[4]:
    file = st.file_uploader("Dépose un PDF", type="pdf")
    if file:
        original = file.getvalue()
        n_pages = pdf_page_count(original)
        st.caption(f"{n_pages} page(s)")
        pages_str = st.text_input(
            "Pages à garder, dans l'ordre voulu (ex : 1, 3, 2)",
            value=", ".join(str(i) for i in range(1, n_pages + 1)),
        )
        if st.button("Générer le nouveau PDF", type="primary"):
            try:
                pages = [int(x.strip()) for x in pages_str.split(",") if x.strip()]
                assert all(1 <= p <= n_pages for p in pages) and pages
                result = extract_pages(original, pages)
                st.success(f"PDF généré : {human_size(len(result))}")
                st.download_button(
                    "⬇️ Télécharger le PDF",
                    data=result,
                    file_name="extrait.pdf",
                    mime="application/pdf",
                )
            except (ValueError, AssertionError):
                st.error(f"Indique des numéros de page valides entre 1 et {n_pages}.")


# --------------------------------------------------------------------------- #
# 6) Pivoter
# --------------------------------------------------------------------------- #
elif tool == TOOLS[5]:
    file = st.file_uploader("Dépose un PDF", type="pdf")
    if file:
        original = file.getvalue()
        n_pages = pdf_page_count(original)
        st.caption(f"{n_pages} page(s)")
        scope = st.radio("Pages concernées", ["Toutes les pages", "Certaines pages"], horizontal=True)
        page_numbers = None
        if scope == "Certaines pages":
            pages_str = st.text_input("Numéros de page, séparés par des virgules", value="1")
        angle = st.select_slider("Angle de rotation (sens horaire)", options=[90, 180, 270])

        if st.button("Pivoter", type="primary"):
            try:
                if scope == "Certaines pages":
                    page_numbers = [int(x.strip()) for x in pages_str.split(",") if x.strip()]
                    assert all(1 <= p <= n_pages for p in page_numbers)
                result = rotate_pdf(original, angle, page_numbers)
                st.success("PDF pivoté.")
                st.download_button(
                    "⬇️ Télécharger le PDF",
                    data=result,
                    file_name="pivote.pdf",
                    mime="application/pdf",
                )
            except (ValueError, AssertionError):
                st.error(f"Indique des numéros de page valides entre 1 et {n_pages}.")
