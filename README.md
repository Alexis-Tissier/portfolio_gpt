# Portfolio Photo Public

Version publique et statique de mon portfolio photo.

Ce site affiche uniquement une sélection de photos destinées à être publiées en ligne.
Les photos privées, les dossiers locaux, les fichiers de configuration et les caches ne sont pas envoyés sur GitHub.

## Fonctionnement

Les photos publiques sont générées à partir du dossier local :

```text
A_publier/
```

Ce dossier est ignoré par Git et reste uniquement sur l’ordinateur.

Le script d’export :

```text
export_public.py
```

permet de :

* convertir les images en `.webp` ;
* supprimer les métadonnées EXIF ;
* renommer les fichiers proprement ;
* générer le fichier `docs/data/photos.json` ;
* placer les images publiques dans `docs/photos/`.

## Structure

```text
docs/
├── index.html
├── static/
│   ├── script.js
│   └── style.css
├── data/
│   └── photos.json
└── photos/
    └── photo-0001.webp
```

Le dossier `docs/` est utilisé pour GitHub Pages.

## Mettre à jour les photos publiques

1. Ajouter les photos publiables dans :

```text
A_publier/
```

2. Lancer l’export :

```bash
python export_public.py
```

3. Tester en local :

```bash
cd docs
python -m http.server 8080
```

Puis ouvrir :

```text
http://127.0.0.1:8080
```

4. Envoyer la mise à jour sur GitHub :

```bash
cd ..
git add docs/ export_public.py
git commit -m "Mise à jour du portfolio public"
git push
```

## Confidentialité

Ce site est public.

Ne doivent être placées dans `A_publier/` que des photos pouvant être publiées en ligne.
Les photos privées, les dossiers sources, les fichiers de configuration et les caches doivent rester hors GitHub.

Fichiers ignorés volontairement :

```text
A_publier/
config.json
config.local.json
cache/
Retouché/
photos sources
```

## Déploiement

Le site est prévu pour être publié avec GitHub Pages depuis :

```text
branche : online
dossier : /docs
```
