# Le Projet MatriskAI

## 1. Vue d'ensemble

Les chaînes d'approvisionnement (Supply Chains) modernes souffrent régulièrement de perturbations majeures, souvent causées par des défaillances de fournisseurs, des retards logistiques imprévus ou des problèmes de non-conformité qualité. 

Gérer ces risques complexes via des rapports Excel statiques (comme les *QML/ASL Reports*) est :
* **Extrêmement propice aux erreurs** (saisie manuelle, oublis).
* **Chronophage** (analyse ligne par ligne fastidieuse).
* **Fondamentalement réactif** (on constate le problème une fois qu'il est survenu).

**MatriskAI** résout ce problème en introduisant une plateforme d'intelligence artificielle proactive. C'est un pipeline ML complet en 4 étapes qui ingère les données brutes, évalue les risques de manière holistique, prévoit les dégradations futures et prescrit des actions concrètes.

## 2. Pourquoi MatriskAI ?

L'innovation principale de MatriskAI réside dans sa combinaison unique de technologies de pointe :
* **Analyse Prédictive (XGBoost)** : Pour classifier instantanément le niveau de risque global d'un matériau.
* **Explicabilité (SHAP)** : Pour comprendre *exactement* pourquoi l'IA a pris une décision (la "boîte noire" devient transparente).
* **Séries Temporelles Bayésiennes (Prophet)** : Pour anticiper les dégradations de fiabilité des fournisseurs à J+90.
* **Moteur Expert Prescriptif** : Pour traduire les prédictions en plans d'action compréhensibles par les équipes métier.

De plus, MatriskAI est conçu pour **tourner localement** (sans dépendance stricte à une infrastructure Cloud lourde), offrant un contrôle total sur les données industrielles sensibles, tout en assurant une transition de bout en bout : du simple fichier Excel vers des prescriptions actionnables.

## 3. L'Équipe

Ce projet a été conçu et développé par deux Ingénieures en Intelligence Artificielle & Data Science :

* **Intissar LAYAD** — AI Engineer & Data Scientist 
  * [Profil LinkedIn](https://www.linkedin.com/in/intissar-layad-07444b377/)
* **Aya IDHAMOUCH** — AI Engineer & Data Scientist 
  * [Profil LinkedIn](https://www.linkedin.com/in/aya-idhamouch-22a996319)

## 4. Contexte Industriel

Pour comprendre MatriskAI, il faut comprendre le langage de la Supply Chain :

* **QML (Qualified Manufacturer List)** : Liste des fabricants qualifiés pour produire un matériau spécifique. Leur statut (Certifié, Qualifié, Obsolète, etc.) dicte le risque intrinsèque du composant.
* **ASL (Approved Supplier List)** : Liste des fournisseurs approuvés. Un fournisseur peut être "Approved", "Waived", "Probation", etc.
* **SRI (Supply Risk Index)** : Un score synthétique, de 0 à 100, créé pour MatriskAI. Un SRI de 100 signifie un risque quasi-nul (sécurité maximale), tandis qu'un score bas (ex: < 40) indique un risque critique imminent de rupture ou de non-conformité.

Notre dataset fondateur repose sur un extrait représentatif : un rapport *QML report by Plant* contenant **1 978 matériaux** et **50 colonnes** brutes d'informations hétérogènes (textes, dates, statuts).

## 5. La Solution IA

### Ce que fait l'IA

1. **Ingestion et Nettoyage** : Le système nettoie automatiquement l'historique qualité des fournisseurs.
2. **Scoring** : Il génère le *Supply Risk Index (SRI)* en combinant de multiples facteurs (péremption, commentaires NLP, ancienneté de la mise à jour).
3. **Classification** : Il classe les anomalies et les matériaux en trois catégories : Faible, Moyen, Élevé.
4. **Prévision** : Il extrapole les tendances pour prévoir la dégradation des fournisseurs dans les 3 prochains mois (J+90).

### Pourquoi c'est innovant

L'approche ne se contente pas de prédire ; elle **explique** et **prescrit**. En intégrant l'explicabilité de SHAP, les décideurs logistiques peuvent faire confiance au modèle. L'utilisation de Prophet pour modéliser l'incertitude temporelle et le moteur de règles pour générer des actions concrètes font de MatriskAI un outil d'aide à la décision complet, dépassant de loin les simples tableaux de bord descriptifs.
