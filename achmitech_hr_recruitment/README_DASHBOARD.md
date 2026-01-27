# Tableau de Bord de Recrutement - Documentation Complète

## 🎯 Vue d'ensemble

Le **Tableau de Bord de Recrutement** est une extension puissante du module de recrutement d'Odoo qui fournit des insights en temps réel sur vos processus de recrutement.

### Fonctionnalités Principales

- **Statistiques Temps Réel** : Total candidatures, postes ouverts, candidats, taux de conversion
- **Visualisations Graphiques** : Candidatures par étape, par poste, distribution des évaluations
- **Analyse Avancée** : Vue Pivot pour analyses croisées
- **Gestion des Entretiens** : Suivi des entretiens programmés
- **Actions Rapides** : Accès direct aux candidatures non évaluées et entretiens de la semaine
- **Permissions Granulaires** : Accès basé sur les rôles

## 📦 Installation

### Prérequis
- Odoo 14+ (compatible avec versions ultérieures)
- Module `hr_recruitment` d'Odoo installé
- Python 3.6+

### Étapes d'installation

1. **Placer le module** dans le dossier addons d'Odoo :
   ```
   /path/to/odoo/addons/achmitech_hr_recruitment/
   ```

2. **Mettre à jour la liste des modules** :
   - Allez à **Applications** → **Mise à jour des Applications**
   - Activez le filtre **Applications Non Installées**
   - Recherchez `achmitech_hr_recruitment`

3. **Installer le module** :
   - Cliquez sur le module
   - Cliquez sur **Installer**

4. **Accéder au tableau de bord** :
   - Allez à **Recrutement** → **Tableau de Bord**

## 🚀 Utilisation

### Accès au Tableau de Bord

```
Recrutement (Menu) → Tableau de Bord
```

### Vues Disponibles

#### 1. Vue Formulaire (Par Défaut)
- Statistiques principales en cartes colorées
- Actions rapides vers les différentes analyses
- Liens directs vers les listes de candidatures

#### 2. Vue Kanban
- Visualisation des candidatures par étape
- Glisser-déposer pour déplacer les candidatures
- Accès rapide aux fiches candidature

#### 3. Vues Graphiques

**Graphique par Étape** (Barre)
- Montre la distribution des candidatures par étape
- Identifie les goulots d'étranglement

**Graphique par Poste** (Camembert)
- Affiche les postes les plus demandés
- Aide à l'allocation des ressources

**Graphique des Évaluations** (Barre)
- Distribution des scores d'évaluation
- Qualité globale des candidatures

#### 4. Vue Pivot
- Analyse croisée par étape et par poste
- Permet des investigations détaillées

### Actions Disponibles

| Action | Description | Accès |
|--------|-------------|-------|
| Voir Toutes les Candidatures | Liste complète des candidatures | Dashboard |
| Voir Tous les Candidats | Liste des candidats enregistrés | Dashboard |
| Voir Postes Ouverts | Postes en recrutement actif | Dashboard |
| Voir Non Évaluées | Candidatures sans évaluation | Bouton action |
| Entretiens Cette Semaine | Entretiens programmés | Bouton action |
| Analyse Détaillée | Vue Pivot | Bouton action |

## 🔧 Configuration

### Paramètres Système

Accédez à **Paramètres** → **Recrutement** pour configurer :

- **Intervalle de Rafraîchissement** : Fréquence de mise à jour du dashboard (défaut: 60s)
- **Nombre de Postes Affichés** : Combien de postes dans "Top Postes" (défaut: 5)
- **Activer les Notifications** : Notifications d'événements importants (défaut: Activé)

### Permissions d'Accès

Les permissions sont définies par groupe d'utilisateurs :

```
Recruteurs         → Lecture seule
Responsables RH    → Lecture / Édition
Managers Généraux  → Lecture seule
Direction          → Lecture seule
```

Modifiez les permissions dans **Paramètres** → **Utilisateurs et Société** → **Groupes**.

## 📊 Données du Dashboard

### Structure des Données

```python
{
    'total_applicants': int,           # Nombre total de candidatures
    'total_candidates': int,           # Nombre total de candidats
    'open_jobs': int,                  # Postes ouverts
    'new_applicants_week': int,        # Candidatures cette semaine
    'conversion_rate': float,          # % candidatures finalisées
    'applicants_by_stage': [           # Candidatures par étape
        {
            'stage_name': str,
            'count': int,
            'stage_id': int
        }
    ],
    'evaluations_by_rating': [         # Évaluations par score
        {
            'rating': str,
            'count': int,
            'rating_value': str
        }
    ],
    'top_jobs': [                      # Top postes
        {
            'job_name': str,
            'count': int,
            'job_id': int
        }
    ],
    'interviews_this_week': [          # Entretiens semaine
        {
            'candidate_name': str,
            'job_name': str,
            'stage_name': str,
            'date': datetime,
            'interviewer': str
        }
    ],
    'unevaluated_count': int           # Candidatures sans évaluation
}
```

## 🔌 API REST

### Endpoint: Get Dashboard Data

```
GET /recruitment/dashboard/data
```

**Authentification** : Requise (utilisateur Odoo)

**Réponse** :
```json
{
    "total_applicants": 45,
    "total_candidates": 32,
    "open_jobs": 3,
    "conversion_rate": 8.5,
    ...
}
```

## 📈 Métriques Clés

| Métrique | Formule | Interprétation |
|----------|---------|-----------------|
| **Taux de Conversion** | Embauches / Candidatures × 100 | % candidatures finalisées |
| **Durée du Processus** | Date embauche - Date candidature | Rapidité du recrutement |
| **Taux d'Abandon** | Éliminés / Reçus × 100 | % candidatures éliminées |
| **Coût par Embauche** | Budget / Embauches | ROI du recrutement |
| **Temps Moyen par Étape** | Σ(Date fin - Date début) / n | Efficacité de chaque étape |

## 🐛 Dépannage

### Problème : Dashboard vide ou n'affiche pas de données

**Causes possibles** :
- Pas de candidatures enregistrées
- Permissions insuffisantes
- Filtre appliqué masquant les données

**Solution** :
```python
# Dans la console Python d'Odoo:
dashboard = env['recruitment.dashboard']
data = dashboard.get_dashboard_data()
print(data)  # Affiche les données brutes
```

### Problème : Les graphiques ne se chargent pas

**Cause** : Module graphique non installé

**Solution** :
```bash
# Réinstaller le module
odoo -d nom_base -u achmitech_hr_recruitment
```

### Problème : Lenteur du dashboard

**Cause** : Trop de données ou requêtes SQL inefficaces

**Solution** :
1. Vérifier la base de données
2. Augmenter `recruitment_dashboard_refresh_interval`
3. Optimiser les index SQL

## 🔐 Sécurité

### Permissions Minimales Requises

- Accès au module `hr_recruitment`
- Lecture des modèles : `hr.applicant`, `hr.candidate`, `hr.applicant.evaluation`
- Accès à l'utilisateur connecté

### Données Sensibles

- Les données affichées respectent les filtres de sécurité d'Odoo
- Les candidatures d'autres sociétés ne sont pas visibles
- Les données sont filtrées par les règles de domaine

## 🧪 Tests

Exécuter les tests du tableau de bord :

```bash
python manage.py test achmitech_hr_recruitment.tests.test_recruitment_dashboard
```

Ou dans l'interface Odoo :
1. **Paramètres** → **Développeur** → **Tests**
2. Rechercher `test_recruitment_dashboard`
3. Cliquer sur **Lancer les Tests**

## 📝 Changelog

### v0.1 (Janvier 2026)
- ✅ Tableau de bord initial
- ✅ Statistiques en temps réel
- ✅ Graphiques interactifs
- ✅ Vue Kanban
- ✅ Actions rapides
- ✅ Permissions granulaires
- ✅ API REST

## 📞 Support et Contribution

**Auteur** : Ayoub Jbili - ACHMITECH

**Documentation** :
- [Guide Utilisateur](./DASHBOARD_GUIDE.md)
- [Cas d'Usage](./TABLEAU_DE_BORD_CAS_USAGE.md)

**Rapporter un Bug** :
- Créer une issue sur le système de tickets
- Fournir : version Odoo, version module, étapes de reproduction

## 📄 Licence

Ce module est sous licence **LGPL-3**

---

**Dernière mise à jour** : 27 janvier 2026
