# The Journey of Ava — stratégie de contenu

## 1. Le constat de départ

| Mesure | Avant |
|---|---|
| Publications par semaine | 15 (13 Reels citations + 2 chroniques) |
| Formats distincts | 2 |
| Engagement moyen par post | 1,83 (source : `db/mood_weights.json`, 151 posts) |
| Légende d'un Reel | la citation, seule |
| Hashtags d'un post livre | le même bloc de 15, à chaque fois |

Deux Reels par jour dans un format identique, ça ne double pas la portée : ça
divise l'attention. Et 13 citations par semaine épuisaient les 985 entrées de la
base en cinq mois.

## 2. Les quatre piliers

| Pilier | Rôle | Ce qu'il produit |
|---|---|---|
| **Reels citations** | portée | les Reels sont poussés aux non-abonnés — c'est le seul format qui recrute |
| **Chroniques livres** | identité + conversion | ce qui distingue le compte, et ce qui envoie vers le blog |
| **Ava lifestyle** (tenue, adresse) | attachement | on suit une personne, pas un flux de citations |
| **Voyage** | sauvegardes | les conseils concrets se sauvegardent et se partagent — le signal le plus fort pour l'algorithme |

## 3. Le calendrier

| Jour | Heure (Paris) | Format | Workflow |
|---|---|---|---|
| Lundi | 08h | Reel citation | `daily_post.yml` |
| Mardi | 19h | Reel citation | `daily_post.yml` |
| Mercredi | 19h | Chronique livre | `book_post.yml` |
| Jeudi | 15h | Voyage + conseils | `lifestyle_post.yml` |
| Vendredi | 19h | Tenue ou adresse | `lifestyle_post.yml` |
| Samedi | 16h | Reel citation | `daily_post.yml` |
| Samedi | 21h | Reel citation | `daily_post.yml` |
| Dimanche | 10h30 | Chronique livre | `book_post.yml` |
| Dimanche | 23h | Reel citation | `daily_post.yml` |

**9 publications par semaine** : 5 citations (56 %), 2 livres (22 %), 2 lifestyle
et voyage (22 %).

Pourquoi ces créneaux : ce sont ceux mesurés par `agent_analytics` une fois le
signal passé au taux rapporté à la portée (voir §4) —
`best_hours_utc = [6, 21, 14, 13, 19, 17]`, soit 8h, 23h, 16h, 15h, 21h et 19h
Paris. Le jeudi reste le jour le plus faible : il reçoit le format le moins
dépendant de la portée immédiate — le voyage, qui vit par les sauvegardes.

Ces mesures sont bruitées (26 abonnés, peu de posts par tranche horaire) et se
corrigent d'elles-mêmes : `agent_analytics` tourne avant chaque publication.
Relis `db/mood_weights.json` après un mois et réaligne les crons si l'ordre a
changé.

Pourquoi 9 et pas 15 : à ce volume, chaque publication reçoit une fenêtre de test
algorithmique complète, et la base de citations tient plus de trois ans.

> Les crons sont en UTC et calés sur l'heure d'été (Paris = UTC+2). En hiver
> tout se décale d'une heure — à corriger si les créneaux d'hiver comptent.

## 4. Le signal de mesure

Le token portait déjà `instagram_manage_insights` — c'est `agent_analytics` qui
ne demandait que `like_count` et `comments_count`. Corrigé.

On ne compte plus des likes bruts. La portée varie d'un facteur 40 d'une
publication à l'autre (mesuré sur trois posts consécutifs : 124, 4, 3 comptes
touchés) : comparer des totaux revenait à comparer des loteries.

```
interactions = likes + 2×commentaires + 3×enregistrements + 3×partages
taux         = interactions / portée
```

Enregistrements et partages pèsent le plus : ce sont les signaux que l'algorithme
valorise, et ceux que visent les formats voyage et lifestyle.

État au 4 août 2026, sur les 80 publications les plus récentes :

| | |
|---|---|
| Portée cumulée | 6 070 |
| Likes | 372 |
| Commentaires | 21 |
| **Enregistrements** | **11** |
| **Partages** | **15** |

11 enregistrements pour 6 070 comptes touchés, c'est le chiffre qui justifie tout
le reste : le contenu se consomme et s'oublie. Les formats voyage et lifestyle
existent pour déplacer cette ligne-là.

Classement des humeurs sur ce nouveau signal — cohérent avec l'ancien, mais
mieux fondé :

| mood | n | taux moyen | poids |
|---|---|---|---|
| melancholic | 13 | 1,635 | 1,656 |
| calm | 27 | 1,544 | 1,563 |
| energetic | 35 | 1,077 | 1,090 |
| warm | 48 | 0,781 | 0,791 |
| contemplative | 53 | 0,691 | 0,699 |

`contemplative` est la plus produite (53 posts, 292 citations en base) et la
moins performante. La pondération corrige déjà le tir.

## 5. Le blog Hashnode ne fonctionne plus

**Aucune chronique n'a jamais été publiée sur le blog.** Hashnode a réservé son
API GraphQL aux publications Pro : `gql.hashnode.com` répond désormais par une
redirection 301 vers sa page d'annonce, `requests` la suit, et `resp.json()`
lève « Expecting value: line 1 column 1 ». C'est cette erreur qui remplit
`logs/pipeline_book.log` depuis le début, en masquant la vraie cause.

Deux conséquences corrigées :

- `agent_blog` détecte maintenant la redirection et lève un message explicite au
  lieu d'une erreur de parsing JSON ;
- le CTA ne contient plus de marqueur `[LIEN]`. Il porte l'URL réelle si la
  publication a réussi, et renvoie vers la bio sinon. Auparavant, le texte
  littéral « [LIEN] » partait sur la Page Facebook.

Pour réactiver le blog il faut un abonnement Hashnode Pro. Sinon, le CTA
« lien en bio » est le comportement correct, et il fonctionne déjà.

## 6. Anatomie d'une légende

Les 125 premiers caractères sont les seuls visibles avant « …plus ». Toutes les
légendes commencent donc par une accroche, jamais par la citation.

```
ACCROCHE          une phrase, 6–12 mots, qui n'annonce pas la suite
CITATION          « … » — Auteur
RÉFLEXION         1–2 phrases qui rendent la citation concrète
CTA LIVRE         pont explicite vers un titre de db/books.json
QUESTION          une vraie question ouverte, pas « et toi ? »
```

Accroche, réflexion et question sont rédigées par Gemini dans la voix d'Ava
(`AVA_VOICE`). Si l'API manque ou échoue, des réserves écrites à l'avance
prennent le relais : **une publication ne saute jamais à cause d'un quota**.

## 7. Hashtags

Mélange par paliers, recomposé à chaque publication :

```
1 très large   portée, forte concurrence
3–4 moyens     là où un petit compte peut ressortir
4–5 de niche   thème, humeur, ville, titre du livre
1 de marque    #thejourneyofava, toujours
```

Les hashtags des **2 dernières publications** sont écartés (sauf la marque). Deux
posts consécutifs ne présentent donc jamais le même bloc — c'est précisément le
motif qu'Instagram traite comme du spam, et c'est ce que faisait l'ancien bloc
fixe de 15 tags.

## 8. Vidéo

- Le texte se révèle **ligne par ligne** au lieu d'apparaître d'un bloc.
- Durée calculée sur le temps de lecture réel : **8 à 14 s** au lieu de 30 s
  fixes, dont les 20 dernières ne montraient plus rien de neuf.
- **3 gabarits** alternent (`center`, `lower`, `banner`), jamais deux fois de
  suite le même.
- **Travelling lent** simulé sur chaque plan — plus aucune image figée.
- **8 familles visuelles** au lieu de 5 listes de mots-clés, et une famille
  différente du post précédent.
- Un fond déjà utilisé n'est jamais repris tant qu'il reste des inédits.

Pour la génération de fonds par IA, voir `assets/backgrounds/README.md`.

## 9. Anti-doublon

`db/state.json` porte la mémoire du bot, et il est **commité par les workflows**.
Sans ce commit, tout repart de zéro à chaque exécution.

| Mémoire | Portée |
|---|---|
| `books_featured` | un livre chroniqué ne l'est jamais deux fois (comparaison sans accents ni casse) |
| `recent_cta_books` | rotation des livres cités en CTA sous les citations |
| `used_backgrounds` | 150 derniers clips |
| `recent_hashtags` | 10 derniers jeux |
| `picks` | rotation des marques, adresses, destinations |
| `last_family`, `last_template` | variété visuelle |

Le contrôle des livres agit à deux endroits : les titres déjà traités sont
**interdits dans le prompt** de génération, et le pipeline refuse de publier un
doublon (`--force` pour passer outre).

## 10. Ava, personnage de fiction — ce qu'il faut savoir

Les posts lifestyle et voyage montrent Ava, qui n'existe pas. Toute légende
issue de ces pipelines porte `config.AI_DISCLOSURE` et `#contenugenereparia`.

Ce n'est pas de la prudence de principe :

- **Meta** demande que les contenus photoréalistes générés par IA soient
  signalés, et applique ses propres étiquettes. Une mention explicite vaut mieux
  qu'une étiquette subie.
- Dès qu'une **marque est citée avec un lien d'affiliation**, la mention de
  partenariat est obligatoire en France, en Belgique, aux Pays-Bas et au
  Royaume-Uni. `db/brands.json` ajoute automatiquement la ligne dès qu'un `url`
  est renseigné.
- Faire porter une tenue à un personnage qui n'existe pas, sans le dire, tout en
  renvoyant vers un lien d'achat, c'est le scénario qui coûte un compte.

Vider `AI_DISCLOSURE` retire la mention. C'est ton appel.

## 11. Ce qui est fait, ce qui reste

### Fait

- **`db/brands.json`** — les 8 `@` relevés le 4 août 2026 dans le pied de page du
  site officiel de chaque marque : `@sezane`, `@saaj_paris`, `@despetitshauts`,
  `@sessun`, `@rouje`, `@balzacparis`, `@soeur_paris`,
  `@americanvintage_officiel`. Les `url` pointent vers les sites officiels, avec
  un champ `affiliate` à `false` : la mention de partenariat n'apparaîtra que le
  jour où tu mettras un vrai lien rémunéré.
- **`db/places.json`** — **15 adresses à clientèle 25-35 ans**, vérifiées une par
  une (existence, quartier, activité en 2026), toutes en `verified: true`.
  Les institutions ont été écartées — Café de Flore, Méert, La Chicorée,
  Le Cirio, Monmouth Coffee, Winkel 43, Café de Jaren, Dishoom : ce sont de
  vraies adresses, mais c'est le circuit des guides, file d'attente de touristes
  ou clientèle d'une autre génération.

  | Ville | Adresses |
  |---|---|
  | Paris | Holybelly 5, Ten Belles, Café Oberkampf, Combat, Folderol |
  | Lille | Coffee Makers, La Capsule |
  | Londres | Ozone Coffee Roasters, Satan's Whiskers |
  | Bruxelles | Bar du Matin, Café Belga |
  | Anvers | Normo Coffee, Caffènation |
  | Amsterdam | Scandinavian Embassy, Bar Botanique |

  Dix `@` relevés dans le pied de page du site officiel. Ten Belles, Café
  Oberkampf, Folderol et Satan's Whiskers n'ont pas de compte confirmable
  (Satan's Whiskers n'a même pas de site, c'est revendiqué) — ils sont publiés
  par leur nom, sans tag, plutôt que mal tagués.

  **Contrepartie assumée : une adresse branchée ferme bien plus vite qu'une
  institution.** Repasse `verified` à `false` dès qu'un lieu ferme — la légende
  parlera du quartier seul sans jamais citer le nom.

  Le hashtag de quartier est maintenant dérivé du champ `area` (`#belleville`,
  `#shoreditch`, `#depijp`…) : un `#jordaan` en dur sortait sous une photo prise
  à De Pijp.
- **Instagram Insights** — la permission était déjà sur le token, le défaut était
  dans le code. Corrigé (§4).
- **Créneaux** — réalignés sur les heures réellement mesurées.
- **Blog** — cause de la panne identifiée et effets corrigés (§5).
- **Voyage** — deux destinations ajoutées (Bali, New York) pour couvrir la
  photothèque existante.

### Reste — ce que je ne peux pas faire à ta place

1. **Secrets GitHub.** `gh` n'est pas installé sur cette machine et je n'ai pas
   de token GitHub : impossible d'écrire dans les secrets du dépôt. À ajouter
   sur `github.com/jeremielannoo-creator/QuotesAI` → Settings → Secrets :
   - `GEMINI_API_KEY` — sans elle, pas de photos d'Ava et les légendes tombent
     sur les réserves écrites d'avance (ça marche, c'est juste moins vivant).
   - `FACEBOOK_PAGE_ID` et `FACEBOOK_PAGE_TOKEN` — les valeurs sont déjà dans ton
     `.env` local et je les ai testées : la Page « The Journey of Ava » répond.
2. **`assets/backgrounds/`.** Générer des clips demande un compte Google Flow ou
   un budget d'API. Sans ça la banque reste vide — et ce n'est pas grave : la
   chaîne Pexels puis Pixabay tourne déjà avec l'anti-doublon et les 8 familles
   visuelles. La banque n'est qu'un supplément de qualité.
3. **Hashnode Pro**, si tu veux ressusciter le blog (§5).

## 12. Comment mesurer

Relance l'analyse quand tu veux :

```bash
python -m agents.agent_analytics --report
```

Ce qu'il faut regarder après un mois de nouveau rythme :

- engagement moyen par publication **en hausse** (le volume a baissé de 40 %) ;
- part des sauvegardes sur les posts voyage ;
- taux de commentaires : c'est ce que visent les questions en fin de légende ;
- humeur `contemplative`, surreprésentée (292 citations) et la moins performante
  (1,13 contre 3,4 pour `melancholic`) — la pondération la corrige déjà, il faut
  vérifier que l'écart se resserre.
