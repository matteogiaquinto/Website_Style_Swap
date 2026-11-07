# Restyle — MVP avec Claude

Restyle utilise le crawler existant pour récupérer une page source, puis Claude pour étudier une page de référence, remplir un rapport de design Markdown suivant `website_design_extraction_specification.md` et créer une nouvelle page HTML/CSS.

## Démarrer sur Windows

Dans PowerShell, depuis ce dossier, installer les dépendances si nécessaire :

```powershell
py -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-win\Scripts\python.exe -m playwright install chromium
```

Lancer ensuite le serveur :

```powershell
.\.venv-win\Scripts\python.exe app.py
```

Ouvrir http://127.0.0.1:5050 et saisir les deux URL et la clé API Anthropic dans le champ prévu, puis cliquer sur **Generate**. La clé est transmise au serveur local pour ce travail, conservée en mémoire pendant son exécution puis supprimée de ce contexte ; elle n’est pas enregistrée dans les fichiers de résultat ni affichée dans l’état du travail. Le champ est vidé après le démarrage. Il est également possible de définir `ANTHROPIC_API_KEY` dans l’environnement avant de lancer le serveur et de laisser le champ vide.

Le modèle par défaut est `claude-sonnet-5-5`, avec un niveau de raisonnement `medium` pour chaque requête ; pour en choisir un autre disponible sur votre compte, définir `$env:ANTHROPIC_MODEL` avant de lancer le serveur. Garder le serveur et l’onglet ouverts jusqu’à la fin. Pour arrêter le serveur : Ctrl+C. Le crawler initial reste sur http://127.0.0.1:5050/crawler.

## Étapes

1. Le crawler visite une seule page du site source, enregistre le HTML rendu, les liens et les images disponibles.
2. Le navigateur ouvre la référence, examine le DOM et les feuilles accessibles et enregistre des captures. Claude reçoit la spécification Markdown fournie dans le dossier, les données du crawler, un résumé de la référence et des captures ordinateur/mobile. Il peut demander des inspections supplémentaires des éléments et de leurs styles calculés à différentes tailles d’écran ; ces inspections sont en lecture seule et portent uniquement sur la page ouverte.
3. Claude produit `design-specification.md`, avec les rubriques numérotées de la spécification. Les propriétés inaccessibles doivent être indiquées comme inconnues. Si les rubriques obligatoires manquent, la génération est interrompue.
4. Claude reçoit ce rapport, les captures de référence et le résultat du crawler et produit `index.html`. Le navigateur prend ensuite des captures de ce premier résultat sur ordinateur et mobile : Claude les compare à la référence et propose une version révisée. Si cette étape échoue, la première version reste disponible et le rapport le signale. Une vérification textuelle approximative signale les fragments potentiellement manquants dans `design-report.json`. L’aperçu est isolé : les scripts de la page générée sont bloqués, tandis que les boutons de navigation de l’aperçu sont autorisés.
5. L’archive téléchargeable contient la page, la spécification, le rapport, les observations, les captures et le dossier source du crawler, y compris les images téléchargées.

## Coût et données envoyées

Chaque génération utilise plusieurs requêtes API Anthropic, facturées sur votre compte. Le coût dépend du modèle, du nombre d’inspections, de la longueur des pages et des images ; aucune limite de dépense n’est appliquée par cette application. Si le HTML source dépasse 500 000 caractères, la génération attend votre confirmation avant tout envoi à Claude. Vous pouvez continuer avec l’intégralité du contenu ou annuler ; la taille ne permet pas de prévoir exactement le coût, et les limites propres à Claude restent applicables. La confirmation expire après 30 minutes. Les données de la page source, les observations et les captures de la page de référence sont envoyées à Anthropic : ne pas utiliser de contenu que vous ne souhaitez pas transmettre.

## Limites

Le résultat est un brouillon généré, pas une reproduction garantie : les structures et les contenus peuvent différer et la sortie doit être vérifiée. Le rapport peut contenir des omissions ou erreurs malgré la vérification des titres. Le contrôle des textes est indicatif et ne garantit pas les liens, les images, la mise en page ni l’absence d’ajouts. Les CSS et scripts inaccessibles, états interactifs et certains assets ne peuvent pas être entièrement analysés. La page produite ne contient pas de JavaScript ; les interactions complexes, formulaires et services externes ne sont pas recréés. Certaines images peuvent rester distantes ou échouer au téléchargement. À la demande de l’utilisateur, les couleurs et la typographie visuelle de la référence sont privilégiées tout en conservant le logo et les contenus source : cette instruction prévaut sur les règles contraires de la guideline. Les fichiers de polices ne sont pas automatiquement intégrés.

Les travaux sont enregistrés localement dans `transfers/`. Les résultats terminés restent accessibles après un redémarrage ; les travaux en cours ne reprennent pas automatiquement. La barre indique le nombre d’étapes terminées, sans estimer le temps restant. À la fin, la page générée s’ouvre dans le navigateur ; le bouton de retour permet de retrouver les téléchargements et le rapport. L’application est limitée à un usage local sur 127.0.0.1 et ne doit pas être exposée telle quelle sur Internet. Respecter les autorisations d’accès aux sites.

## Test sans coût API

`python test_transfer_smoke.py` utilise des pages locales, le vrai crawler et des réponses Claude simulées. Il vérifie la boucle d’inspection, le rapport, la génération, la comparaison visuelle simulée, l’aperçu et l’archive. Ce test ne démontre pas la qualité d’une génération réelle ni l’accès à un compte Claude.
