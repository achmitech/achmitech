# Guide fonctionnel — Approbation des congés collaborateurs

**Module :** achmitech_portal_leaves
**Odoo :** 19.0

---

## Vue d'ensemble

Ce module permet de gérer les demandes de congés des collaborateurs en impliquant leur client (responsable de site) dans le processus d'approbation. Trois profils d'utilisateurs sont concernés :

| Profil | Rôle dans le module |
|---|---|
| **RH / Administrateur** | Configure les types de congés, affecte les collaborateurs à leurs missions, surveille les demandes en cours, peut forcer une décision si nécessaire |
| **Client** | Reçoit les notifications et approuve ou refuse les demandes de congés de ses collaborateurs via le portail |
| **Collaborateur** | Soumet ses demandes de congés via le portail et suit leur statut |

---

## 1. Configuration (RH / Administrateur)

### 1.1 Configurer les types de congés

Accès : **Configuration → Types de congés**

Pour chaque type de congé, un groupe de paramètres « Approbation client (Collaborateurs) » est disponible :

#### Option A — Approbation client requise
À utiliser pour les congés payés, non payés, compensation, etc.

- Cocher **« Approbation client requise »**
- La demande sera bloquée en attente de la décision du client avant toute validation RH
- Renseigner le **délai de réponse (jours)** : nombre de jours à partir de la soumission avant qu'un rappel automatique soit envoyé au client (défaut : 3 jours)

#### Option B — Notification client uniquement
À utiliser pour les congés maladie, maternité/paternité, etc.

- Cocher **« Notifier le client à la soumission »**
- Le client reçoit un email informatif, mais n'a aucune action à effectuer
- La demande suit le processus de validation RH habituel sans interruption

> **Important :** Un type de congé ne doit pas avoir les deux options activées simultanément.

---

### 1.2 Affecter les collaborateurs à leur mission

Accès : **Employés → [fiche du collaborateur] → Onglet Informations professionnelles**

- Renseigner le champ **« Projet client (mission actuelle) »**
- Sélectionner le projet correspondant à la mission en cours du collaborateur
- Le partenaire associé à ce projet sera automatiquement reconnu comme le client approbateur

> **Prérequis :** Le projet doit avoir un partenaire renseigné (champ « Client » sur la fiche projet). C'est ce partenaire qui recevra les emails et verra les demandes sur le portail.

---

### 1.3 Donner l'accès portail aux clients et aux collaborateurs

Accès : **Paramètres → Utilisateurs → Utilisateurs**

Pour chaque client et chaque collaborateur :

1. Ouvrir la fiche du partenaire (ou de l'utilisateur)
2. Cliquer sur **« Accorder l'accès portail »**
3. L'utilisateur reçoit un email d'invitation avec ses identifiants de connexion

> **Pour le client :** le partenaire portail doit être le même que celui renseigné sur le projet de mission.
> **Pour le collaborateur :** l'utilisateur portail doit être lié à la fiche employé via le champ « Utilisateur associé » (Paramètres → Utilisateurs, ou directement sur la fiche employé).

---

### 1.4 Vérifier le cron de rappel

Accès : **Paramètres → Technique → Automatisation → Actions planifiées**

- Rechercher **« Absences collaborateurs: rappel client en attente »**
- Vérifier qu'il est actif et configuré sur **1 jour**
- Ce cron envoie automatiquement un email de rappel aux clients dont le délai de réponse est dépassé (un seul rappel par demande)

---

### 1.5 Types de congés exceptionnels (Article 274)

Les types de congés suivants sont créés automatiquement à l'installation du module :

- Mariage de l'employé
- Mariage d'un enfant
- Naissance d'un enfant
- Décès du conjoint / d'un enfant / du père ou de la mère / d'un frère ou d'une sœur
- Circoncision d'un enfant
- Opération chirurgicale (conjoint ou enfant)

Tous sont configurés sans allocation (droits légaux accordés sur événement), avec notification client, validation par le responsable congés, et justificatif obligatoire. Les durées légales ne sont pas bloquées par le système — le responsable valide en connaissance de cause.

---

## 2. Utilisation — Client

### 2.1 Accéder au portail

Le client se connecte sur `[URL du site]/web/login` avec ses identifiants portail.

Sur la page d'accueil du portail, une carte **« Demandes de congés »** est visible :
- Si le compteur affiché est supérieur à 0, des demandes sont en attente de réponse
- Cliquer sur la carte pour accéder à la liste

---

### 2.2 Consulter les demandes

La page liste comporte deux onglets :

- **En attente** : demandes nécessitant une action du client (badge avec le nombre)
- **Historique** : demandes déjà traitées (approuvées ou refusées)

Des outils de recherche et de tri sont disponibles :
- Trier par date, par collaborateur, par type de congé ou par délai de réponse
- Regrouper par collaborateur ou par type de congé
- Rechercher par nom de collaborateur ou par type de congé

---

### 2.3 Approuver une demande

1. Cliquer sur **« Voir »** sur la ligne de la demande (ou directement sur le lien dans l'email reçu)
2. Vérifier les informations : collaborateur, type de congé, dates, durée, motif éventuel
3. Cliquer sur **« Approuver »**
4. Confirmer dans la boîte de dialogue
5. Le collaborateur reçoit automatiquement un email de confirmation

---

### 2.4 Refuser une demande

1. Ouvrir le détail de la demande
2. Cliquer sur **« Refuser »**
3. Saisir un motif de refus (facultatif mais recommandé)
4. Confirmer
5. Le collaborateur reçoit automatiquement un email de refus avec le motif renseigné

---

### 2.5 Email de rappel

Si le client n'a pas répondu dans le délai configuré sur le type de congé, il reçoit automatiquement un email de rappel contenant un lien direct vers la demande en attente. Ce rappel n'est envoyé qu'une seule fois.

---

## 3. Utilisation — Collaborateur

### 3.1 Accéder au portail

Le collaborateur se connecte sur `[URL du site]/web/login` avec ses identifiants portail.

Sur la page d'accueil, une carte **« Mes demandes de congé »** est visible. Cliquer dessus pour accéder à la liste de ses demandes.

---

### 3.2 Soumettre une demande de congé

1. Cliquer sur **« Nouvelle demande »**
2. Remplir le formulaire :
   - **Type de congé** : seuls les types compatibles avec le workflow client sont proposés (ceux configurés avec approbation ou notification client). Si un type n'apparaît pas dans la liste, c'est qu'il ne nécessite pas d'implication du client.
   - **Date de début** et **Date de fin** (la date de fin doit être égale ou postérieure à la date de début)
   - **Motif** (facultatif)
3. Cliquer sur **« Soumettre »**

Selon le type de congé choisi :
- **Approbation requise** : la demande passe en statut *« En attente du client »* et un email est envoyé au client pour décision
- **Notification uniquement** : la demande est transmise directement au service RH ; le client est informé par email

---

### 3.3 Suivre le statut d'une demande

Le tableau de bord affiche toutes les demandes avec leur statut :

| Statut | Signification |
|---|---|
| **À confirmer** | Demande en cours de traitement initial |
| **En attente de validation** | Demande transmise, en cours de traitement |
| **Approuvé** | Congé validé |
| **Refusé** | Congé refusé (le motif du refus est indiqué dans l'email reçu) |

Le collaborateur reçoit un email automatique dès que le client prend une décision (approbation ou refus).

---

## 4. Interventions RH sur les demandes en attente

Si un client est injoignable ou tarde à répondre, le service RH peut intervenir directement depuis le backend Odoo.

Accès : **Congés → Demandes de congés → [ouvrir la demande concernée]**

Deux boutons sont disponibles lorsqu'une demande est au statut *« En attente du client »* :

- **Forcer la validation** (bouton orange) : valide la demande sans attendre le client ; une confirmation est demandée avant l'action
- **Forcer le refus** (bouton rouge) : refuse la demande sans attendre le client ; une confirmation est demandée avant l'action

> Ces boutons ne sont visibles que pour les utilisateurs ayant le rôle **Gestionnaire des congés** (`hr_holidays.group_hr_holidays_manager`).

---

## 5. Cas particuliers et points d'attention

### Le collaborateur change de mission en cours de contrat
Mettre à jour le champ **« Projet client »** sur la fiche employé. Les nouvelles demandes iront au nouveau client. Les demandes déjà en cours restent rattachées à l'ancien client (le champ `client_partner_id` est calculé à la création et stocké).

### Un type de congé nécessite une allocation préalable
Si le collaborateur n'a pas d'allocation approuvée pour un type de congé donné (ex. congés payés), ce type n'apparaîtra pas dans le formulaire de soumission. Il faut d'abord qu'un gestionnaire RH crée une allocation approuvée pour cet employé.

### Le client n'a pas de compte portail
Sans accès portail, le client ne peut pas approuver les demandes en ligne. Il faut lui créer un accès (voir section 1.3) ou utiliser les boutons de forçage RH pour traiter les demandes manuellement.

### Le collaborateur n'a pas de projet client renseigné
Si aucun projet client n'est associé au collaborateur, aucune notification ne sera envoyée au client et la demande ne passera pas par le workflow d'approbation, même si le type de congé est configuré avec approbation requise. Vérifier que le champ « Projet client » est bien renseigné sur la fiche employé.

### Solde affiché sur le portail
Le solde affiché correspond aux jours alloués moins les congés **validés** (approuvés définitivement), y compris les congés futurs déjà approuvés. Les demandes en attente (client ou RH) n'impactent pas l'affichage — elles sont néanmoins prises en compte dans le contrôle de la limite de jours négatifs au moment de la soumission.

### Limite de jours négatifs
Si le type de congé autorise un solde négatif, le système bloque toute soumission qui ferait dépasser cette limite, en tenant compte de toutes les demandes en cours (y compris celles en attente d'approbation client). De même, si le client tente d'approuver une demande qui dépasserait la limite (suite à d'autres validations entre-temps), l'approbation est annulée et un message d'erreur est affiché.

### Soumission sur jours fériés ou week-ends
Le portail rejette automatiquement toute demande dont la période ne contient aucun jour ouvrable (week-end ou jour férié). La vérification utilise le calendrier de travail de l'employé.

### Soumission pour une date passée
Le portail rejette les demandes dont la date de début est antérieure à la date du jour.
