#!/bin/bash
# Script de vérification du Tableau de Bord de Recrutement

echo "════════════════════════════════════════════════════════════"
echo "Vérification du Tableau de Bord de Recrutement"
echo "════════════════════════════════════════════════════════════"
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Compteurs
total_checks=0
passed_checks=0
failed_checks=0

# Fonction de test
check_file() {
    local file=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description"
        passed_checks=$((passed_checks + 1))
    else
        echo -e "${RED}✗${NC} $description"
        failed_checks=$((failed_checks + 1))
    fi
}

check_dir() {
    local dir=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $description"
        passed_checks=$((passed_checks + 1))
    else
        echo -e "${RED}✗${NC} $description"
        failed_checks=$((failed_checks + 1))
    fi
}

check_content() {
    local file=$1
    local pattern=$2
    local description=$3
    total_checks=$((total_checks + 1))
    
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $description"
        passed_checks=$((passed_checks + 1))
    else
        echo -e "${RED}✗${NC} $description"
        failed_checks=$((failed_checks + 1))
    fi
}

echo "📁 Vérification des fichiers du module..."
echo ""

# Vérifier les fichiers principaux
check_file "__manifest__.py" "Manifest du module"
check_file "README_DASHBOARD.md" "Documentation du dashboard"
check_file "DASHBOARD_GUIDE.md" "Guide utilisateur"
check_file "TABLEAU_DE_BORD_CAS_USAGE.md" "Cas d'usage"
check_file "migrations.py" "Migrations"

echo ""
echo "📊 Vérification des modèles..."
echo ""

check_file "models/recruitment_dashboard.py" "Modèle principal du dashboard"
check_file "models/dashboard_actions.py" "Actions du dashboard"
check_file "models/res_config_settings.py" "Paramètres de configuration"
check_file "models/__init__.py" "Init des models"

# Vérifier que les imports sont corrects
check_content "models/__init__.py" "recruitment_dashboard" "Import du modèle dashboard"
check_content "models/__init__.py" "dashboard_actions" "Import des actions"
check_content "models/__init__.py" "res_config_settings" "Import des paramètres"

echo ""
echo "👁️  Vérification des vues..."
echo ""

check_file "views/hr_recruitment_dashboard.xml" "Vues du dashboard"
check_file "views/hr_recruitment_dashboard_advanced.xml" "Vues avancées du dashboard"

# Vérifier que les vues sont référencées
check_content "__manifest__.py" "hr_recruitment_dashboard" "Vue dashboard en manifest"
check_content "__manifest__.py" "hr_recruitment_dashboard_advanced" "Vue avancée en manifest"

echo ""
echo "🔧 Vérification des contrôleurs..."
echo ""

check_file "controllers/recruitment_dashboard.py" "Contrôleur du dashboard"
check_content "controllers/__init__.py" "recruitment_dashboard" "Import du contrôleur"

echo ""
echo "🧪 Vérification des tests..."
echo ""

check_file "tests/test_recruitment_dashboard.py" "Tests du dashboard"

echo ""
echo "🔐 Vérification des permissions..."
echo ""

check_file "security/ir.model.access.csv" "Fichier de permissions"
check_content "security/ir.model.access.csv" "recruitment_dashboard" "Permissions pour recruitment_dashboard"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "Résumé"
echo "════════════════════════════════════════════════════════════"
echo ""
echo -e "Total des vérifications: ${total_checks}"
echo -e "${GREEN}Réussi: ${passed_checks}${NC}"
if [ $failed_checks -gt 0 ]; then
    echo -e "${RED}Échoué: ${failed_checks}${NC}"
else
    echo -e "${GREEN}Échoué: ${failed_checks}${NC}"
fi
echo ""

if [ $failed_checks -eq 0 ]; then
    echo -e "${GREEN}✓ Toutes les vérifications sont passées !${NC}"
    echo ""
    echo "Le tableau de bord est prêt à être utilisé."
    echo ""
    echo "Prochaines étapes :"
    echo "1. Installer le module dans Odoo"
    echo "2. Accéder à Recrutement → Tableau de Bord"
    echo "3. Consulter la documentation pour les détails d'utilisation"
    exit 0
else
    echo -e "${YELLOW}⚠️  Certaines vérifications ont échoué.${NC}"
    echo ""
    echo "Veuillez vérifier les fichiers manquants."
    exit 1
fi
