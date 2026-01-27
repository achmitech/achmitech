# -*- coding: utf-8 -*-
"""
Migrations et upgrades pour le module de Tableau de Bord de Recrutement
"""

from odoo import api, SUPERUSER_ID


def migrate_0_1_to_0_2(cr, version):
    """
    Migration depuis version 0.1 vers 0.2
    Ajouter les permissions pour le nouveau modèle dashboard
    """
    if not version:
        return
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Créer les permissions pour les groupes de recrutement
    groups = [
        ('hr_recruitment.group_hr_recruitment_interviewer', 'Interviewer'),
        ('hr_recruitment.group_hr_recruitment_user', 'Officer'),
        ('hr_recruitment.group_hr_recruitment_manager', 'Manager'),
    ]
    
    for group_ref, label in groups:
        try:
            group = env.ref(group_ref)
            # Ajouter les permissions de lecture pour le dashboard
            model = env.ref('model_recruitment_dashboard')
            # Les permissions sont créées automatiquement dans ir.model.access.csv
        except Exception:
            pass  # Ignorer si le groupe n'existe pas


def post_init_hook(cr, registry):
    """
    Hook post-installation pour initialiser le dashboard
    """
    pass


def uninstall_hook(cr, registry):
    """
    Hook lors de la désinstallation
    """
    pass
