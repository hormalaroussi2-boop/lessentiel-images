# L'Essentiel BeFr — instructions de publication

Ce dépôt sert à produire et publier les posts du compte Instagram **@lessentiel.befr**
(actualité Belgique 🇧🇪 + France 🇫🇷, en français). Les images sont hébergées ici
(dépôt public) pour qu'Instagram puisse les récupérer.

## Outils
- `node tools/render.js posts/<dossier>` : génère `slide-N.jpg` à partir de `post.json`
  (format décrit en tête du fichier). Il avertit si un texte déborde : raccourcis-le alors.
- `python3 tools/publish.py posts/<dossier>` : pousse les images, crée le carrousel et publie.
  Le token Meta est injecté par le proxy réseau pour graph.facebook.com (rien à configurer).
- Dossier d'un post : `posts/AAAA-MM-JJ-HHMM-<type>/` avec `post.json` et `caption.txt`.
- Avant de commencer : `git pull --rebase origin main`.

## Ligne éditoriale
Catégories (une story par catégorie, dans cet ordre) :
1. 💶 **ARGENT** : prix, salaires, impôts, aides, loyers, énergie.
2. 🗳️ **POLITIQUE** / **SOCIÉTÉ** : le grand débat du moment. **Toujours neutre** : les faits
   et les positions des deux camps, jamais d'opinion.
3. 🤖 **TECH & IA**
4. 🎮 **JEUX VIDÉO** : sorties, prix, mises à jour (Fortnite, EA FC, GTA…), e-sport, jeux gratuits.
5. ❤️ **HISTOIRE HUMAINE** : réussite, geste héroïque, insolite positif.

Week-end : moins de politique, plus de jeux vidéo, sport et histoires humaines.

Carrousel quotidien = 7 slides : cover (4 à 5 lignes) + 5 stories + end (question qui fait réagir).
Légende : 1 phrase d'accroche, le résumé des titres avec emojis, une question, la ligne
« Sources : … », puis 8 à 12 hashtags (#actualité #belgique #france #infos #news …).

## Règles de fiabilité (obligatoires)
- Chaque info doit être **datée du jour (ou de la veille au soir)** et confirmée par **au moins
  2 médias fiables** (RTBF, Le Soir, La Libre, L'Avenir, 7sur7, Sudinfo, franceinfo, Le Monde,
  AFP, Belga, BFM, Le Figaro, Libération, Les Échos, Jeuxvideo.com, Gamekult…).
- Rédiger avec ses propres mots. Ne jamais copier un texte d'article.
- Ne jamais utiliser de photo, vidéo, logo ou capture d'un média ou d'un éditeur de jeu.
- Éviter les faits divers violents impliquant des mineurs ou des victimes identifiables,
  les rumeurs non confirmées et les chiffres non recoupés. Dans le doute, ne pas publier l'info.
- Ne pas répéter une info déjà publiée le même jour (vérifier `posts/` du jour).

## Infos urgentes (veille horaire)
Ne publier un post « URGENT » que pour une info **majeure** pour la Belgique ou la France
(chute de gouvernement, catastrophe, attentat, décision qui touche tout le monde au porte-monnaie,
sortie ou annonce d'un jeu énorme type GTA 6, résultat sportif historique), confirmée par
au moins 2 médias fiables, et pas déjà publiée. Format : `edition: "URGENT"`, 1 ou 2 slides story.
Maximum 2 posts urgents par jour. S'il n'y a rien de majeur : ne rien publier.
