# Correctifs du 5 octobre 2026

- Photos de bandeau intégrées directement dans les pages HTML : elles ne dépendent plus du dossier `assets` pour s’afficher.
- Température de l’eau de la baie : source officielle Ville de La Baule, parser renforcé et valeur du jour initiale vérifiée.
- Température Plateau du Four : affichée uniquement si une valeur instrumentale Cerema en °C est effectivement récupérée.
- Pêche : correction du JavaScript qui bloquait « Meilleurs créneaux » et utilisation de la table de marées sur 7 jours.
- Windfinder : widget de prévision rétabli avec l’URL widget qui avait été utilisée dans une version antérieure.
- Surf et Wingfoil : sections « Heure par heure » retirées de l’affichage.
- Événements : jeu initial multi-communes vérifié depuis les agendas officiels ; le script continue de tenter la mise à jour automatique.
- Climat : comparaison corrigée pour comparer la période écoulée du mois 2026 aux mêmes jours de 2015–2024, plutôt qu’une température instantanée à une moyenne mensuelle complète.
