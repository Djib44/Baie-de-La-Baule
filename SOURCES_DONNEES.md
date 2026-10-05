# Sources des données

- **Conditions locales du jour (air, eau de la baie, vent, rafales, houle)** : Ville de La Baule-Escoublac, page météo officielle. Les champs absents restent indisponibles ; ils ne sont pas inventés.
- **Température d’eau au large** : Cerema, bouée Plateau du Four 04403, valeur diffusée par Infoclimat.
- **Qualité de l’air** : Air Pays de la Loire, indice ATMO communal La Baule-Escoublac via le flux WFS officiel.
- **Pollens** : Atmo France / AASQA, indice communal. Le pin ne fait pas partie des six taxons suivis. La version actuelle du site renvoie vers l’indice officiel ; une récupération automatisée complète nécessite un accès à l’API Atmo Data.
- **Clarté de l’eau** : Copernicus Marine, profondeur de Secchi ZSD.
- **Historique climat** : ERA5 via Open-Meteo Historical Weather API, série homogène pour les comparaisons.
- **Prévisions horaires Surf/Wingfoil** : Open-Meteo Weather/Marine, utilisées lorsque la granularité horaire n’est pas disponible dans la source locale.
- **Marées** : la version actuelle conserve la source déjà opérationnelle (maree.info, avec repli Ville de Pornichet). Le passage au SHOM n’est pas présenté comme réalisé tant qu’un accès API SHOM n’est pas configuré.

Aucune valeur historique de marée n’est fabriquée : les graphiques restent vides tant qu’une série officielle n’est pas connectée.
