# Banque de fonds vidéo générés par IA

`agent_video` pioche **ici en priorité**, avant Pexels et Pixabay. Un clip déjà
utilisé n'est jamais repris tant qu'il reste des inédits (mémoire dans
`db/state.json`).

## Pourquoi une banque de clips plutôt qu'une génération à la volée

Le pipeline tourne sur GitHub Actions : 2 vCPU, 7 Go de RAM, **pas de GPU**. Les
modèles text-to-video de HuggingFace (Wan, LTX-Video, HunyuanVideo, CogVideoX…)
demandent 12 à 24 Go de VRAM. Les faire tourner sur le runner n'est pas une
question de configuration, c'est matériellement impossible. Restent deux voies :

| Voie | Coût | Mise en place |
|---|---|---|
| **Banque de clips** (celle-ci) | 0 € | Tu génères par lots quand tu veux, tu déposes les MP4 ici |
| API HuggingFace Inference Providers | ~0,10–0,50 $/clip | `VIDEO_AI_ENABLED=1` + `HF_TOKEN` |

## Remplir la banque

1. Générer des prompts variés :

```bash
python -m agents.agent_video_ai --prompts 16
```

2. Coller chaque prompt dans [Google Flow](https://labs.google/fx/fr/tools/flow)
   (ou n'importe quel modèle text-to-video), en **9:16**, 5 à 8 secondes.
   Les clips plus courts que la vidéo finale sont automatiquement bouclés au
   montage (`-stream_loop`), inutile de viser long.

3. Ranger le MP4 dans le sous-dossier de sa famille :

```
assets/backgrounds/
├── water/      océan, pluie sur vitre, lac, reflets
├── mountain/   crêtes, brume, dunes, falaises
├── forest/     rayons entre les arbres, feuilles, mousse
├── urban/      rue mouillée, néons, terrasse, métro
├── intimate/   tasse, livre ouvert, bougie, rideau
├── sky/        nuages, étoiles, aurore, horizon
├── texture/    encre dans l'eau, fumée, poussière, braises
└── human/      silhouette, dos, foule floue
```

Le rangement n'est pas décoratif : `agent_scenes` associe chaque humeur de
citation à des familles précises, et change de famille à chaque publication.
Un clip mal rangé sortira sur la mauvaise humeur.

Formats acceptés : `.mp4`, `.mov`, `.webm`.

## Combien de clips ?

À 5 Reels par semaine, 40 clips couvrent deux mois sans jamais répéter un fond.
Cinq par famille suffisent pour commencer.
