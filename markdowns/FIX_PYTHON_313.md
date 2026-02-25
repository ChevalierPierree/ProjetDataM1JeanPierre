# 🚨 FIX URGENT - Python 3.13 trop récent !

## Le problème
Jean utilise **Python 3.13** qui est trop récent.
`psycopg2-binary` n'a pas encore de version pré-compilée pour Python 3.13.

## ✅ Solution 1 - Installer Python 3.11 ou 3.12 (RECOMMANDÉ)

### Avec Homebrew (si installé)
```bash
# Installer Python 3.12
brew install python@3.12

# Vérifier l'installation
/opt/homebrew/bin/python3.12 --version

# Recréer le venv avec Python 3.12
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre
rm -rf .venv
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
./patator
```

### Sans Homebrew
1. Télécharger Python 3.12 : https://www.python.org/downloads/
2. Installer
3. Utiliser `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3` pour créer le venv

---

## ✅ Solution 2 - Forcer l'installation (peut échouer)

```bash
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre
source .venv/bin/activate

# Installer les dépendances système PostgreSQL (si pas déjà fait)
brew install postgresql@16

# Forcer l'installation
pip install psycopg2-binary --no-cache-dir --force-reinstall

# Si ça échoue, essayer psycopg (la nouvelle version)
pip uninstall psycopg2-binary
pip install psycopg[binary]

# Installer le reste
pip install pymongo kafka-python fastapi uvicorn pydantic pandas numpy python-dotenv requests
```

---

## ✅ Solution 3 - Utiliser psycopg3 au lieu de psycopg2

Modifier temporairement le `requirements.txt` :

```bash
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre
source .venv/bin/activate

# Installer psycopg3 au lieu de psycopg2
pip install "psycopg[binary]"
pip install pymongo kafka-python fastapi uvicorn pydantic pandas numpy python-dotenv requests

./patator
```

**Note** : Les scripts utilisent `psycopg2`, donc il faudra peut-être les adapter.

---

## 🎯 SOLUTION RECOMMANDÉE

**Installer Python 3.12 avec Homebrew** :

```bash
# 1. Installer Python 3.12
brew install python@3.12

# 2. Aller dans le projet
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre

# 3. Supprimer le venv Python 3.13
rm -rf .venv

# 4. Créer un nouveau venv avec Python 3.12
/opt/homebrew/bin/python3.12 -m venv .venv

# 5. Activer le venv
source .venv/bin/activate

# 6. Vérifier la version Python
python --version
# Doit afficher: Python 3.12.x

# 7. Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# 8. Tester
python test_dependencies.py

# 9. Lancer
./patator
```

---

## 🔍 Vérification version Python actuelle

```bash
python3 --version
# Si ça affiche 3.13.x, c'est le problème !
```

---

## 📊 Versions Python compatibles

- ✅ Python 3.11.x - Parfait
- ✅ Python 3.12.x - Parfait  
- ⚠️ Python 3.13.x - Trop récent, certains packages pas encore prêts

---

Tiens-moi au courant de la version Python qu'il a et quelle solution il veut essayer !

Pierre
