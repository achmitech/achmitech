# Configuration SSH Bitbucket - Guide Complet

## 🔑 Clé SSH Générée

Votre clé SSH a été trouvée et est chargée dans ssh-agent.

### Informations de votre clé

**Type** : ED25519  
**Fingerprint** : `SHA256:mjeiE5tmOawRW2W4pHPvx7gRAaQXXiBkjSVi+wjmtWk`  
**Utilisateur** : karim@sdql  

### Votre Clé Publique

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDQKbLSfovYNz4AcqXtzQfqC2gPIFkNL0i+jq8/4ZiCT karim@sdql
```

---

## ⚠️ Problème Actuel

```
git@bitbucket.org: Permission denied (publickey).
fatal: Could not read from remote repository.
```

**Cause** : Votre clé publique SSH n'est pas enregistrée sur Bitbucket.

---

## ✅ Solution : Ajouter la Clé à Bitbucket

### Étape 1 : Se Connecter à Bitbucket

1. Allez sur https://bitbucket.org
2. Connectez-vous avec vos identifiants
3. Cliquez sur votre avatar (en haut à droite)
4. Sélectionnez **Settings** ou **Paramètres**

### Étape 2 : Accéder aux Clés SSH

1. Dans le menu de gauche, cherchez **Security** ou **Sécurité**
2. Cliquez sur **SSH Keys** ou **Clés SSH**
3. Cliquez sur **Add key** ou **Ajouter une clé**

### Étape 3 : Copier Votre Clé Publique

Copiez cette clé publique exactement :

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDQKbLSfovYNz4AcqXtzQfqC2gPIFkNL0i+jq8/4ZiCT karim@sdql
```

Ou utilisez la commande :
```bash
cat ~/.ssh/id_ed25519.pub | xclip -selection clipboard
```

### Étape 4 : Coller la Clé

1. Collez votre clé publique dans le champ **Key**
2. Donnez-lui un label (ex: "Mon Ordinateur" ou "Dev Machine")
3. Cliquez sur **Add key** pour confirmer

### Étape 5 : Tester la Connexion

Après l'ajout, attendez quelques secondes, puis testez :

```bash
ssh -T git@bitbucket.org
```

**Résultat attendu** :
```
authenticated as karim.
You can use git to connect to Bitbucket. Use git @ git.bitbucket.org.
```

---

## 🔄 Après Configuration SSH

Une fois la clé ajoutée à Bitbucket, vous pourrez faire un git pull :

```bash
cd /home/karim/achmitech
git pull --tags origin main
```

---

## 🆘 Si Ça Ne Marche Toujours Pas

### Vérifier le dépôt Git

```bash
cd /home/karim/achmitech
git remote -v
```

Assurez-vous que l'URL commence par `git@bitbucket.org:` et non `https://`

### Changer l'URL SSH si nécessaire

```bash
git remote set-url origin git@bitbucket.org:votre-utilisateur/achmitech.git
```

### Déboguer SSH

```bash
ssh -vT git@bitbucket.org
```

Cela affichera les détails de la connexion pour trouver le problème exact.

---

## 📋 Checklist

- [ ] Clé SSH générée et présente dans `~/.ssh/`
- [ ] Clé SSH ajoutée à Bitbucket
- [ ] Connexion SSH testée avec succès
- [ ] URL du dépôt utilise SSH (`git@bitbucket.org:`)
- [ ] `git pull` fonctionne correctement

---

## 💡 Alternative : Utiliser HTTPS

Si vous préférez éviter SSH, vous pouvez utiliser HTTPS :

```bash
git remote set-url origin https://bitbucket.org/votre-utilisateur/achmitech.git
git pull --tags origin main
```

(Vous devrez entrer votre identifiant Bitbucket ou générer un mot de passe d'application)

---

**Besoin d'aide ?** Consultez la documentation Bitbucket :
https://support.atlassian.com/bitbucket-cloud/docs/set-up-an-ssh-key/
