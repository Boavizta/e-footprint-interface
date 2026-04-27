**Objet :** Vision des prochains développements — onboarding, aide contextuelle et documentation de e-footprint

---

Hello à tous,

Je voulais vous partager en amont de notre prochaine réunion la vision fonctionnelle des développements qui arrivent sur e-footprint et son interface. L'idée n'est pas de rentrer dans la technique, mais de vous donner à voir ce que ces évolutions vont changer concrètement pour les utilisateurs, pour qu'on puisse ensuite en discuter ensemble.

Une première partie synthétique pour la vue d'ensemble, puis une seconde qui reprend les mêmes points en détail.

---

## 1. Vue d'ensemble

La cible, c'est de transformer e-footprint en un outil qu'une personne non-technique peut prendre en main seule, tout en gardant toute la profondeur dont les utilisateurs avancés ont besoin.

On vise trois évolutions majeures, qui forment un tout cohérent :

- **Un accompagnement intégré dès le premier clic.** Plutôt qu'un écran vide intimidant, le nouvel utilisateur arrivera sur un choix de modèles de démarrage (e-commerce, IA conversationnelle, IoT industriel, ou page blanche), avec une visite guidée courte qui lui explique où sont les choses et dans quel ordre modéliser.
- **De l'aide disponible partout, tout le temps.** Chaque champ, chaque type d'objet aura une icône d'info avec une explication claire, et un panneau d'aide détaillé accessible d'un clic. Plus besoin de savoir ce qu'est un « usage journey » avant de commencer : l'interface l'explique au moment où la question se pose.
- **Une documentation qui reste à jour par construction.** Tout le contenu descriptif (à quoi sert un objet, que signifie un paramètre) vivra à un seul endroit et sera consommé à la fois par l'interface et par la documentation publique. Impossible qu'un renommage de code laisse derrière lui une doc obsolète.

Deux briques secondaires viennent compléter le tableau : une meilleure lisibilité du modèle « edge » (IoT, équipements déployés) pour les utilisateurs industriels, et une refonte de la documentation publique pour qu'elle tienne enfin ses promesses (aujourd'hui plusieurs pages sont vides).

Point de départ concret : la première étape a déjà été livrée. Elle élimine une source majeure de frustration en désactivant préventivement les boutons dont les pré-requis ne sont pas encore remplis, avec une infobulle qui explique quoi faire pour les débloquer. Fini les erreurs qui tombent après coup — c'est la première pierre du principe directeur de toute la démarche : **jamais d'erreur punitive, toujours une indication claire de ce qui est possible et comment**.

---

## 2. Détail des évolutions

### Un premier contact guidé et rassurant

Aujourd'hui, un nouvel utilisateur arrive sur une interface vide sans savoir par où commencer. C'est le gros point noir.

La nouvelle expérience de premier contact combinera trois choses :

- **Un choix de modèles de démarrage** présenté dès l'arrivée. Chaque modèle est un système déjà fonctionnel, qu'on peut immédiatement modifier et faire tourner. On prévoit au minimum trois scénarios représentatifs — e-commerce classique, chatbot IA, installation industrielle avec IoT — et bien sûr l'option « partir de zéro ». Le choix du modèle oriente subtilement l'utilisateur : une personne d'une équipe produit SaaS prendra e-commerce, un industriel prendra IoT, et découvrira ainsi le mode « edge » sans avoir à savoir ce que c'est à l'avance.
- **Une visite guidée courte** qui se lance automatiquement la première fois. Elle montre où sont les différentes zones de l'interface (parcours d'usage, infrastructure, résultats), dans quel ordre construire un modèle, et où trouver de l'aide. La visite est rejouable à tout moment depuis un menu d'aide. Elle enseigne *la carte*, pas les concepts — ces derniers vivent dans l'aide contextuelle, pour ne pas noyer la personne.
- **Le principe « jamais d'erreur après-coup »** déjà en place (étape 1) reste la toile de fond. Si on ne peut pas encore ajouter un job parce qu'il n'y a pas de serveur, le bouton est grisé avec une infobulle qui le dit. L'utilisateur apprend l'ordre de construction par l'interface elle-même, sans se prendre de mur.

### Une aide contextuelle omniprésente

L'idée directrice : toute l'information dont on a besoin pour comprendre ce qu'on fait doit être à **un clic maximum** de l'endroit où on est en train de travailler.

Concrètement :

- **Une icône d'info sur chaque champ de formulaire.** Au survol, une description claire de ce que le paramètre représente. Pas de jargon, pas de renvois vers de la doc externe pour les choses élémentaires.
- **Une icône d'info sur chaque type d'objet.** Qu'est-ce qu'un serveur ? Qu'est-ce qu'un edge device ? La réponse est là, sans devoir quitter l'écran.
- **Un panneau d'aide détaillé** pour aller plus loin : distinctions entre objets similaires (ex. quand choisir tel type de serveur plutôt qu'un autre), pièges courants, conseils d'usage. Accessible depuis les cartes d'objets.
- **Des liens profonds vers la documentation publique** quand l'utilisateur veut vraiment creuser. L'interface ne dupliquera pas les longs contenus pédagogiques ; elle pointe au bon endroit.

Cette aide est particulièrement critique pour l'audience visée : une personne non-technique doit pouvoir utiliser e-footprint sans avoir lu préalablement quoi que ce soit.

### Une documentation maintenable par construction

Le risque classique avec ce genre d'effort, c'est que les descriptions se dédoublent (une dans le code, une dans la doc, une dans l'interface) et divergent au premier refactoring. On s'attaque à ça directement :

- **Un seul endroit où écrire chaque description.** Les explications de classes, de paramètres et d'attributs calculés vivent dans le code e-footprint, au plus près de ce qu'elles décrivent. L'interface et le site de documentation publique les consomment tous les deux automatiquement.
- **Des tests qui bloquent la sortie d'une nouvelle version** si une description manque, si elle contient un mot interdit (jargon technique qu'un non-technicien ne comprendrait pas), ou si elle fait référence à quelque chose qui n'existe plus. La doc ne peut plus silencieusement pourrir.
- **La documentation publique** (actuellement plusieurs pages vides) est complétée : explications, guides pratiques, FAQ, une page dédiée à la distinction web / edge. Les pages de référence auto-générées passent d'un état « squelette » à du vrai contenu, alimenté par la même source de vérité.

### Clarifier le modèle edge pour les utilisateurs industriels

e-footprint sait modéliser deux paradigmes — les services web classiques (pilotés par la demande) et les déploiements d'équipements (pilotés par le nombre d'unités déployées, typiquement IoT). Aujourd'hui, cette distinction est invisible dans l'interface, ce qui désoriente tout le monde.

Côté évolutions visibles :

- **Un interrupteur « modélisation edge : on/off »** dans la barre du haut. Éteint par défaut pour les nouveaux utilisateurs web, les objets edge ne polluent pas l'interface. Allumé automatiquement pour les modèles qui en contiennent déjà.
- **Des badges discrets** sur les cartes d'objets edge pour que, sur un modèle mixte, on voit d'un coup d'œil à quel monde appartient chaque brique.
- **Une page dédiée** dans la documentation publique qui explique la distinction, quand utiliser l'un ou l'autre, et comment les deux mondes se connectent.

### Récap du parcours utilisateur cible

Pour résumer, voilà ce que vivra un nouvel utilisateur non-technique après tous ces développements :

1. Il arrive → on lui propose un modèle de démarrage qui ressemble à son cas d'usage.
2. Une visite guidée courte l'oriente dans l'interface.
3. Il modifie, ajoute des objets. Les boutons non pertinents sont grisés avec l'explication de ce qui manque.
4. Quand il a une question, l'icône d'info à côté lui répond. Pour aller plus loin, un panneau d'aide, et si besoin un lien vers la doc publique.
5. Son modèle se construit dans le bon ordre, sans erreur punitive, sans blocage inexpliqué.

---

## Pour la réunion

Ce mail pose la vision ; la réunion sera le bon moment pour en discuter ensemble, remonter les éventuels points de désaccord ou les angles manquants, et prioriser si besoin. Quelques questions que j'ai déjà en tête pour lancer la discussion :

- Est-ce que les trois modèles de démarrage retenus (e-commerce, chatbot IA, IoT industriel) vous semblent couvrir les cas d'usage qu'on rencontre le plus ? D'autres à ajouter ?
- Sur le ton et le vocabulaire de l'aide contextuelle : qui serait le mieux placé pour relire les descriptions au fil de l'eau ?
- Y a-t-il des retours utilisateurs récents dont on devrait tenir compte et que je n'ai pas intégrés ici ?

N'hésitez pas à me faire remonter vos premières réactions par retour de mail si vous préférez, ou à les garder pour qu'on en parle de vive voix.

À très vite,
Vincent
