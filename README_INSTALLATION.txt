BAIE DE LA BAULE — VERSION CONSOLIDÉE 05/10/2026

Cette archive contient volontairement TOUS les fichiers nécessaires, y compris assets/ et les caches api/.
Ne chargez pas uniquement les fichiers HTML : conservez l'arborescence complète.

1. Décompresser le dossier Baie-de-La-Baule-main.
2. Envoyer son CONTENU à la racine du dépôt GitHub Pages en conservant :
   assets/  api/  scripts/  .github/workflows/
3. Dans GitHub > Settings > Secrets and variables > Actions, conserver/créer :
   COPERNICUSMARINE_SERVICE_USERNAME
   COPERNICUSMARINE_SERVICE_PASSWORD
4. Dans Actions, lancer "Update coastal data" une première fois.
5. Vérifier api/status.json : les flux opérationnels passent à true.

Sources principales :
- météo et température d'eau de la baie : Ville de La Baule-Escoublac
- météo marine complémentaire : Open-Meteo Marine
- qualité de l'air / pollen : Atmo France / Air Pays de la Loire (WFS open data)
- clarté : Copernicus Marine ZSD
- événements : agendas officiels des 4 communes
- marées courantes : maree.info avec repli Ville de Pornichet

IMPORTANT SHOM : l'API officielle de prédiction SHOM nécessite une clé d'abonnement pour l'accès programmatique complet. Les graphiques historiques SHOM ne sont donc pas fabriqués artificiellement.
