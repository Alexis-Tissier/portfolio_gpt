# Portfolio Photo Local

Application web locale en français pour afficher automatiquement les photos présentes dans tous les dossiers nommés **Retouché**.

## Ce que fait l'application

- Elle lit ton dossier principal de photos, sans déplacer ni supprimer de fichiers.
- Elle cherche automatiquement tous les dossiers nommés `Retouché` dans toute l'arborescence.
- Elle récupère les photos contenues dans ces dossiers, même si elles sont dans plusieurs sous-dossiers.
- Elle trie les photos par date à partir du nom du fichier, par exemple :

```text
20260616-200152-0001-Alexis Tissier.jpg
```

Ici, la date détectée est : `16/06/2026`.

- Elle regroupe l'affichage par mois : `Juin 2026`, `Mai 2026`, etc.
- Elle affiche une galerie propre avec recherche, filtre par année, mode sombre/clair et affichage plein écran.

## Installation rapide

### 1. Dézipper le dossier

Dézippe le fichier puis ouvre le dossier `photo_portfolio_app`.

### 2. Lancer l'application

Sur Windows, double-clique sur :

```text
lancer_windows.bat
```

Sinon, dans un terminal :

```bash
python server.py
```

L'application s'ouvre ensuite dans le navigateur :

```text
http://127.0.0.1:8000
```

### 3. Configurer le dossier photo

Dans l'interface, indique le dossier racine, par exemple :

```text
C:\Users\Alexis\Documents\Photos
```

Puis clique sur **Enregistrer et scanner**.

## Lancement avec le dossier directement

Tu peux aussi lancer comme ça :

```bash
python server.py --root "C:\Users\Alexis\Documents\Photos"
```

## Miniatures plus rapides

L'application fonctionne sans installation supplémentaire.

Pour que les miniatures chargent plus vite, installe Pillow :

```bash
pip install -r requirements.txt
```

Si Pillow n'est pas installé, l'application affichera quand même les photos, mais elle utilisera les fichiers originaux comme miniatures.

## Formats reconnus

```text
.jpg, .jpeg, .png, .webp, .bmp, .gif, .tif, .tiff
```

Les fichiers RAW Canon comme `.CR2` ne s'affichent pas directement dans un navigateur. Il faut plutôt exporter les photos retouchées en JPEG, PNG ou WebP.

## Notes importantes

- L'application lit seulement tes photos.
- Elle ne copie pas tes images.
- Elle ne modifie pas les fichiers originaux.
- Elle fonctionne en local sur ton ordinateur.
- Le site n'est pas publié sur Internet.

## Structure du projet

```text
photo_portfolio_app/
├── server.py
├── config.json
├── requirements.txt
├── lancer_windows.bat
├── lancer_mac_linux.sh
├── static/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── cache/
    └── thumbnails/
```
