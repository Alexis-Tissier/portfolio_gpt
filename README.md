# Portfolio Photo Local

Application locale en Python permettant d’afficher automatiquement un portfolio photo à partir d’un dossier principal.

L’application recherche tous les dossiers nommés `Retouché`, récupère les photos qu’ils contiennent, puis les affiche dans une galerie web locale, triée par date.

## Fonctionnalités

- Scan automatique d’une arborescence de dossiers
- Détection des dossiers `Retouché`
- Récupération des photos dans les sous-dossiers
- Tri chronologique à partir du nom du fichier
- Affichage par mois
- Galerie web locale
- Lecture seule des fichiers

## Format des fichiers

L’application utilise la date présente au début du nom du fichier.

Exemple :

```text
20260616-200152-0001-Alexis Tissier.jpg
```

La date détectée est :

```text
20260616 = 16 juin 2026
```

## Installation

Cloner le projet :

```bash
git clone https://github.com/Alexis-Tissier/portfolio_gpt.git
cd portfolio_gpt
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

## Lancement

Sous Windows :

```text
lancer_windows.bat
```

Ou manuellement :

```bash
python server.py
```

L’application s’ouvre ensuite dans le navigateur à l’adresse :

```text
http://127.0.0.1:8000
```

## Configuration

Le fichier `config.json` n’est pas envoyé sur GitHub, car il dépend du chemin local de chaque utilisateur.

Exemple :

```json
{
  "photos_root": "C:/Users/Alexis/Documents/Photos",
  "target_folder_name": "Retouché"
}
```

## Structure du projet

```text
portfolio_gpt/
├── static/
├── .gitignore
├── README.md
├── lancer_windows.bat
├── lancer_mac_linux.sh
├── requirements.txt
└── server.py
```

## Important

Les photos ne sont pas stockées dans GitHub.  
L’application lit simplement les fichiers présents sur l’ordinateur.