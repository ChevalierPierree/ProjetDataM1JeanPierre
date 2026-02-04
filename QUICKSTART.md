# 🚀 PATATOR - Démarrage Ultra-Rapide

## Installation en 3 Commandes

```bash
# 1. Cloner
git clone https://github.com/ChevalierPierree/ProjetDataM1JeanPierre.git
cd ProjetDataM1JeanPierre && git checkout PierreDump

# 2. Installer dépendances (8 packages essentiels)
pip3 install -r requirements.txt

# 3. Lancer TOUT
chmod +x patator && ./patator
```

**C'est tout !** 🎉

Le script lance automatiquement :
- ✅ 13 services Docker
- ✅ Chargement des données (PostgreSQL + MongoDB)  
- ✅ Kafka streaming (71,694 événements)
- ✅ Détection de fraude (10,857 alertes)
- ✅ API Backend (port 8000)
- ✅ Dashboard Web (port 7600)

**Dashboard** : http://localhost:7600/fraud_dashboard.html

---

## Utilisation pour les Autres

Si quelqu'un récupère ton projet :

```bash
git clone <ton-repo>
cd <ton-projet>
chmod +x patator
./patator
```

**Durée totale** : 3-5 minutes ⏱️

---

## Alias Global (Optionnel)

Pour taper juste `patator` depuis n'importe où :

```bash
# macOS/Linux (zsh)
echo 'alias patator="$(pwd)/patator"' >> ~/.zshrc
source ~/.zshrc

# macOS/Linux (bash)
echo 'alias patator="$(pwd)/patator"' >> ~/.bash_profile
source ~/.bash_profile
```

Maintenant `patator` fonctionne partout ! 🚀

---

## Arrêter

```bash
docker compose down
```

---

## Documentation Complète

📖 Voir `INSTALLATION.md` pour le guide détaillé
