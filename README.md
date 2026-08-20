# 📄 PDF Toolbox

Petite app Streamlit tout-en-un pour manipuler des PDF sans les envoyer sur un
site tiers : tout le traitement se fait dans le processus Python de l'app
(en mémoire), que ce soit en local ou une fois déployée sur Streamlit
Community Cloud.

## Outils inclus

- 🔗 **Fusionner** plusieurs PDF (avec ordre personnalisable)
- 📉 **Réduire la taille** d'un PDF — préréglages rapides (légère / moyenne /
  forte) ou **taille cible** en Ko/Mo (recherche automatique du meilleur
  réglage)
- 🖼️ **Image(s) → PDF** (jpg, png, bmp, webp, tiff), avec choix du format de
  page (A4, Letter, taille d'origine)
- ✂️ **Diviser** un PDF (une page par fichier, dans un zip)
- 📑 **Extraire / réorganiser** des pages
- 🔄 **Pivoter** des pages (90° / 180° / 270°)

Aucune dépendance système externe (pas de Ghostscript) : uniquement
`pypdf` et `Pillow`, donc ça tourne partout sans configuration
supplémentaire.

## Installation locale

```bash
git clone https://github.com/Kamagatey/pdf-toolbox
cd pdf-toolbox
python -m venv .venv
source .venv/bin/activate  # sous Windows : .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

L'app s'ouvre sur http://localhost:8501

## Déploiement sur Streamlit Community Cloud (gratuit)

1. Crée un dépôt GitHub et pousse ce dossier dedans :

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/Kamagatey/pdf-toolbox/pdf-toolbox.git
   git push -u origin main
   ```

2. Va sur [share.streamlit.io](https://share.streamlit.io), connecte ton
   compte GitHub.
3. Clique sur **New app**, choisis ton dépôt, la branche `main`, et le
   fichier principal `app.py`.
4. Clique sur **Deploy**. L'app est en ligne en 1-2 minutes, avec une URL du
   type `https://<ton-app>.streamlit.app`.

À chaque `git push` sur `main`, l'app se redéploie automatiquement.

## Lien utilisable

https://pdf-toolbox-yk.streamlit.app/



## Structure du projet

```
pdf-toolbox/
├── app.py                   # Interface Streamlit (navigation + widgets)
├── utils.py                 # Logique métier (fusion, compression, etc.)
├── requirements.txt
├── .streamlit/config.toml   # Thème + taille max d'upload
└── .gitignore
```
