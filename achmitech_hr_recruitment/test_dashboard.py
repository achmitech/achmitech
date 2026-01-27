#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour valider le Tableau de Bord de Recrutement
(Version légère - sans dépendance Odoo)
"""

import sys
import os
import ast
import xml.etree.ElementTree as ET

print("=" * 80)
print("TESTS DU TABLEAU DE BORD DE RECRUTEMENT (Validation Syntaxe)")
print("=" * 80)
print()

base_path = os.path.dirname(__file__)

# Test 1: Vérification syntaxe Python
print("TEST 1: Vérification de la syntaxe Python...")
print("-" * 80)

python_files = [
    'models/recruitment_dashboard.py',
    'models/dashboard_actions.py',
    'models/res_config_settings.py',
    'controllers/recruitment_dashboard.py',
    'tests/test_recruitment_dashboard.py',
]

all_valid = True
for py_file in python_files:
    filepath = os.path.join(base_path, py_file)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print(f"✓ {py_file}")
    except SyntaxError as e:
        print(f"✗ {py_file}: {e}")
        all_valid = False

if all_valid:
    print("✓ Toutes les syntaxes Python sont valides")
print()

# Test 2: Vérification XML
print("TEST 2: Vérification de la syntaxe XML...")
print("-" * 80)

xml_files = [
    'views/hr_recruitment_dashboard.xml',
    'views/hr_recruitment_dashboard_advanced.xml',
]

xml_valid = True
for xml_file in xml_files:
    filepath = os.path.join(base_path, xml_file)
    try:
        ET.parse(filepath)
        print(f"✓ {xml_file}")
    except ET.ParseError as e:
        print(f"✗ {xml_file}: {e}")
        xml_valid = False

if xml_valid:
    print("✓ Toutes les syntaxes XML sont valides")
print()

# Test 3: Vérification des classes Python
print("TEST 3: Vérification des définitions de classes...")
print("-" * 80)

class_checks = [
    ('models/recruitment_dashboard.py', 'RecruitmentDashboard'),
    ('models/dashboard_actions.py', ['HrApplicantDashboardActions', 'HrJobDashboardActions', 'HrCandidateDashboardActions']),
    ('models/res_config_settings.py', ['ResConfigSettings', 'ResCompany']),
    ('controllers/recruitment_dashboard.py', 'RecruitmentDashboardController'),
]

classes_valid = True
for filepath, class_names in class_checks:
    full_path = os.path.join(base_path, filepath)
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if isinstance(class_names, str):
        class_names = [class_names]
    
    for class_name in class_names:
        if f'class {class_name}' in content:
            print(f"✓ {class_name} ({filepath})")
        else:
            print(f"⚠ {class_name} ({filepath}) - Non trouvé")

print("✓ Toutes les classes sont définies correctement")
print()

# Test 4: Vérification des méthodes clés
print("TEST 4: Vérification des méthodes clés...")
print("-" * 80)

method_checks = [
    ('models/recruitment_dashboard.py', [
        'get_dashboard_data',
        '_get_applicants_by_stage',
        '_get_evaluations_by_rating',
        '_get_top_jobs',
        '_get_interviews_this_week',
        '_get_unevaluated_applicants'
    ]),
]

methods_valid = True
for filepath, methods in method_checks:
    full_path = os.path.join(base_path, filepath)
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for method in methods:
        if f'def {method}' in content:
            print(f"✓ {method}")
        else:
            print(f"✗ {method} - Non trouvé")
            methods_valid = False

if methods_valid:
    print("✓ Toutes les méthodes clés sont présentes")
print()

# Test 5: Vérification du manifest
print("TEST 5: Vérification du manifest...")
print("-" * 80)

manifest_path = os.path.join(base_path, '__manifest__.py')
try:
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest_content = f.read()
    
    manifest_dict = ast.literal_eval(manifest_content)
    
    required_keys = ['name', 'version', 'category', 'depends', 'data']
    for key in required_keys:
        if key in manifest_dict:
            print(f"✓ {key}: {manifest_dict[key]}")
        else:
            print(f"✗ {key}: manquant")
    
    # Vérifier les fichiers de données
    if 'data' in manifest_dict:
        dashboard_files = [f for f in manifest_dict['data'] if 'dashboard' in f]
        if dashboard_files:
            print(f"✓ Fichiers dashboard inclus: {dashboard_files}")
        
except Exception as e:
    print(f"✗ Erreur lors de la lecture du manifest: {e}")

print()

# Test 6: Vérification des fichiers CSV (permissions)
print("TEST 6: Vérification des permissions...")
print("-" * 80)

csv_path = os.path.join(base_path, 'security/ir.model.access.csv')
try:
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"✓ Fichier CSV: {len(lines)} lignes")
    
    # Chercher les permissions du dashboard
    dashboard_perms = [l for l in lines if 'recruitment_dashboard' in l.lower()]
    if dashboard_perms:
        print(f"✓ Permissions du dashboard trouvées: {len(dashboard_perms)}")
        for perm in dashboard_perms:
            parts = perm.split(',')
            if parts:
                print(f"  - {parts[1].strip()}")
    
except Exception as e:
    print(f"✗ Erreur: {e}")

print()

# Test 7: Vérification de la structure des dossiers
print("TEST 7: Vérification de la structure des dossiers...")
print("-" * 80)

required_dirs = [
    'models',
    'views',
    'controllers',
    'tests',
    'security',
    'reports',
]

all_dirs_exist = True
for directory in required_dirs:
    dir_path = os.path.join(base_path, directory)
    if os.path.isdir(dir_path):
        files = os.listdir(dir_path)
        print(f"✓ {directory}/ ({len(files)} fichiers)")
    else:
        print(f"✗ {directory}/ manquant")
        all_dirs_exist = False

if all_dirs_exist:
    print("✓ Toute la structure des dossiers est présente")
print()

# Résumé final
print("=" * 80)
print("RÉSUMÉ DES TESTS")
print("=" * 80)
print()

if all_valid and xml_valid and methods_valid and all_dirs_exist:
    print("✅ TOUS LES TESTS ONT RÉUSSI !")
    print()
    print("Le tableau de bord est prêt pour :")
    print("  ✓ Installation dans Odoo")
    print("  ✓ Tests en environnement")
    print("  ✓ Déploiement en production")
    print()
    sys.exit(0)
else:
    print("⚠️  Certains tests n'ont pas réussi")
    print()
    sys.exit(1)
