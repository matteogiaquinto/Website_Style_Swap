# Website Style Swap

> **Prototype expérimental** : ce projet est une preuve de concept, pas un produit fini. Ses résultats peuvent être incomplets, inexacts ou inutilisables et doivent être vérifiés manuellement avant toute utilisation.

Website Style Swap explore le transfert du style visuel d’un site de référence vers le contenu d’un site source. Une application locale récupère la page source avec un crawler, observe la page de référence et demande à Claude de produire une spécification de design puis une nouvelle page HTML/CSS. L’interface permet de prévisualiser et télécharger le résultat et ses fichiers associés. Un crawler indépendant permet aussi d’explorer plusieurs pages et d’enregistrer leurs images.

## Prérequis et installation

- Python 3.10 ou plus récent et une connexion Internet.
- Un compte Anthropic, une **clé API Anthropic valide** et l’accès à un modèle compatible pour la génération. L’abonnement à Claude ne remplace pas nécessairement l’accès à l’API.
- Chromium, installé par Playwright comme indiqué ci-dessous.

Depuis la racine du dépôt :

```powershell
cd crawler-app/crawler-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

Sur macOS ou Linux, activez l’environnement avec `source .venv/bin/activate` au lieu de la commande PowerShell. Ouvrez ensuite <http://127.0.0.1:5050>. Saisissez l’URL du site source, celle du site de référence et votre clé API Anthropic, puis lancez la génération. La clé peut également être fournie via la variable d’environnement `ANTHROPIC_API_KEY` avant le lancement. Ne la publiez jamais dans le dépôt. Le modèle peut être configuré avec `ANTHROPIC_MODEL` ; le modèle par défaut indiqué dans le code doit être accessible à votre compte.

Le crawler seul est accessible à <http://127.0.0.1:5050/crawler> et ne nécessite pas de clé Claude. Arrêtez le serveur avec `Ctrl+C`.

## Fonctionnement et fichiers

1. Playwright visite la page source, enregistre son HTML et récupère les images disponibles.
2. L’application examine la référence et prend des captures à plusieurs tailles.
3. Claude analyse ces éléments selon `website_design_extraction_specification.md`, produit une spécification puis une page HTML/CSS, et tente une révision visuelle.
4. L’interface présente un aperçu et permet de télécharger les résultats. Les fichiers sont enregistrés localement dans `crawler-app/crawler-app/transfers/` ; les crawls sont dans `crawls/`.

Le serveur Flask se trouve dans `app.py`, le crawler dans `crawler.py`, la génération Claude dans `ai_transfer.py` et l’interface dans `static/`. Le dossier `classy-eth-preview/` et `interface_front_end.html` contiennent des aperçus ou essais d’interface. Pour plus de détails, voir les README dans `crawler-app/crawler-app/`.

## Coûts, données et limites

Les appels à l’API Anthropic peuvent être facturés sur votre compte et aucune limite de dépense n’est imposée par l’application. Le contenu source, des observations et des captures de la référence sont transmis à Anthropic : n’utilisez pas de données que vous ne souhaitez pas partager. Utilisez uniquement des sites et contenus pour lesquels vous disposez des autorisations nécessaires.

La page générée est un brouillon : textes, images, liens, mise en page et accessibilité peuvent comporter des erreurs ou omissions. Les interactions complexes, formulaires et services externes ne sont pas nécessairement reproduits ; l’aperçu bloque les scripts de la page générée. Certains éléments du site peuvent être inaccessibles. L’application est destinée à un usage local et ne doit pas être exposée sur Internet telle quelle.

## Responsabilité

Ce prototype est fourni **en l’état**, sans garantie de fonctionnement, de fiabilité, de sécurité ou d’adéquation à un usage particulier. Son utilisation, la vérification des résultats et le respect des droits et conditions applicables relèvent de l’utilisateur. Dans les limites permises par la loi applicable, les auteurs déclinent toute responsabilité pour les erreurs, pertes ou dommages directs ou indirects liés à son utilisation.

## Test local

Depuis `crawler-app/crawler-app`, `python test_transfer_smoke.py` exécute un test de la chaîne avec des réponses Claude simulées, sans appel API payant. Ce test ne garantit pas la qualité d’une génération réelle.
