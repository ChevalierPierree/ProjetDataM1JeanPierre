# 🎯 SOLUTION EXACTE POUR JEAN

## Ta situation actuelle
- Projet : `/Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre/`
- Venv : `.venv/bin/pip` existe
- Erreur : `ModuleNotFoundError: No module named 'psycopg2'`

## ✅ Solution en 3 commandes

```bash
# 1. Va dans le dossier du projet
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre

# 2. Active le venv (si pas déjà fait)
source .venv/bin/activate

# 3. Installe les dépendances DANS le venv avec pip (pas pip3!)
pip install -r requirements.txt
```

**C'EST TOUT !** Ensuite lance :
```bash
./patator
```

---

## 🔍 Pourquoi ça n'a pas marché avant ?

Tu as fait :
```bash
pip3 install -r requirements.txt  # ❌ Installe HORS du venv
```

Il fallait faire :
```bash
pip install -r requirements.txt   # ✅ Installe DANS le venv
```

**Dans un venv activé** :
- ✅ `pip` → installe dans le venv
- ❌ `pip3` → installe dans le système

---

## 🧪 Vérification

Après l'installation, vérifie que tout est bon :

```bash
# Tu dois être dans le venv (tu vois ".venv" au début de la ligne)
# Ex: (.venv) Mac-a-Rio:ProjetDataM1JeanPierre jeanmacario$

# Vérifie que pip pointe vers le venv
which pip
# Doit afficher: /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre/.venv/bin/pip

# Teste les imports
python test_dependencies.py
# Doit afficher 10/10 ✅
```

---

## 🚀 Lancement complet

```bash
# 1. Aller dans le projet
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre

# 2. Activer le venv
source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Vérifier
python test_dependencies.py

# 5. Lancer PATATOR
./patator
```

Le dashboard s'ouvrira automatiquement sur http://localhost:7600/fraud_dashboard.html

---

## 🆘 Si ça ne marche TOUJOURS pas

Recrée un venv propre :

```bash
# Désactiver le venv actuel
deactivate

# Aller dans le projet
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre

# Supprimer l'ancien venv
rm -rf .venv

# Créer un nouveau venv
python3 -m venv .venv

# Activer le nouveau venv
source .venv/bin/activate

# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances
pip install -r requirements.txt

# Vérifier
python test_dependencies.py

# Lancer
./patator
```

---

## 📊 Ce que PATATOR va faire

1. ✅ Vérifier Docker, Python, curl
2. ✅ Démarrer 13 services Docker (Kafka, PostgreSQL, MongoDB, etc.)
3. ✅ Charger 71,694 événements dans Kafka
4. ✅ Générer 10,857 alertes de fraude
5. ✅ Lancer l'API Backend (port 8000)
6. ✅ Lancer le Dashboard (port 7600)
7. ✅ Ouvrir le dashboard dans ton navigateur

**Durée** : 3-5 minutes

---

Tiens-moi au courant !

Pierre 🚀
