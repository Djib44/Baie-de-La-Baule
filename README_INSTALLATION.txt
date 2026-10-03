BAIE DE LA BAULE — V4

IMPORTANT : conservez exactement cette arborescence lors de l'envoi sur GitHub.

Racine :
  index.html
  peche.html
  wingfoil.html
  surf.html
  README_INSTALLATION.txt

Dossiers :
  api/
    tides.json
    clarity.json
  scripts/
    update_data.py
  .github/
    workflows/
      update-coastal-data.yml

NOUVEAU V4
- Phase de lune + éclairement approximatif ajoutés à la page principale.
- Arborescence GitHub corrigée : les fichiers ne doivent PAS être déplacés à la racine.
- Workflow placé directement dans .github/workflows/.
- Marées et clarté chargées depuis api/ sur les pages.
- Webcams intégrées sur l'accueil.

COPERNICUS
Créer les deux Repository secrets :
COPERNICUSMARINE_SERVICE_USERNAME
COPERNICUSMARINE_SERVICE_PASSWORD

Puis : Actions > Update coastal data > Run workflow.

CONSEIL POUR L'UPLOAD GITHUB
Décompressez le ZIP sur votre PC. Si l'interface GitHub aplati de nouveau les dossiers,
ne chargez pas les fichiers individuellement : utilisez l'arborescence telle quelle
ou créez les chemins indiqués ci-dessus.
