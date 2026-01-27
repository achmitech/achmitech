# Démarrage Rapide - Tableau de Bord de Recrutement

## ⚡ Installation en 3 Étapes

### 1️⃣ Placer le Module
```bash
cp -r achmitech_hr_recruitment /path/to/odoo/addons/
```

### 2️⃣ Installer dans Odoo
```bash
odoo -d nom_base -u achmitech_hr_recruitment
```

### 3️⃣ Accéder au Dashboard
```
Menu → Recrutement → Tableau de Bord
```

---

## 📊 Tableau de Bord en 30 Secondes

Le tableau de bord affiche :

### Statistiques Principales (Cartes colorées)
- 📊 **Total Candidatures** : Nombre de dossiers reçus
- 🎯 **Postes Ouverts** : Nombre de postes en recrutement
- 👥 **Candidats** : Nombre de profils enregistrés
- 📈 **Taux de Conversion** : % candidatures finalisées

### Visualisations (Graphiques)
- 📊 Candidatures par étape (graphique barre)
- 🥧 Candidatures par poste (camembert)
- 📉 Évaluations par score (graphique barre)

### Actions Rapides (Boutons)
- Voir toutes les candidatures
- Voir les postes ouverts
- Voir candidatures non évaluées
- Voir entretiens cette semaine
- Analyse détaillée (Pivot)

---

## 🎯 Utilisation Quotidienne

### Matin
1. Ouvrir le tableau de bord
2. Vérifier les candidatures non évaluées
3. Vérifier les entretiens du jour

### Milieu de Semaine
1. Analyser les goulots d'étranglement
2. Mettre à jour les étapes des candidatures
3. Compléter les évaluations

### Fin de Semaine
1. Générer un rapport hebdomadaire
2. Analyser les top postes
3. Planifier la semaine suivante

---

## 🔍 Où Trouver Quoi ?

| Besoin | Où Chercher | Lien |
|--------|------------|------|
| Guide complet | README_DASHBOARD.md | [Lire](README_DASHBOARD.md) |
| Guide utilisateur | DASHBOARD_GUIDE.md | [Lire](DASHBOARD_GUIDE.md) |
| 8 cas d'usage | TABLEAU_DE_BORD_CAS_USAGE.md | [Lire](TABLEAU_DE_BORD_CAS_USAGE.md) |
| Résumé technique | DEVELOPMENT_SUMMARY.md | [Lire](DEVELOPMENT_SUMMARY.md) |
| Index complet | INDEX.md | [Lire](INDEX.md) |

---

## ✅ Vérifier l'Installation

Exécuter le script de vérification :

```bash
cd achmitech_hr_recruitment
bash check_dashboard.sh
```

✅ Résultat attendu :
```
✓ Toutes les vérifications sont passées !
Le tableau de bord est prêt à être utilisé.
```

---

## 🆘 Besoin d'Aide ?

### Installation
→ Voir [README_DASHBOARD.md#-installation](README_DASHBOARD.md#-installation)

### Utilisation
→ Voir [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)

### Cas d'Utilisation
→ Voir [TABLEAU_DE_BORD_CAS_USAGE.md](TABLEAU_DE_BORD_CAS_USAGE.md)

### Problèmes
→ Voir [README_DASHBOARD.md#-dépannage](README_DASHBOARD.md#-dépannage)

---

## 🚀 Vous Êtes Prêt !

Le tableau de bord de recrutement est maintenant installé et opérationnel. 

**Prochaines étapes :**
1. Créer des candidatures de test
2. Ajouter des évaluations
3. Explorer les différentes vues
4. Consulter les cas d'usage pour apprendre les bonnes pratiques

Bon recrutement ! 🎉
