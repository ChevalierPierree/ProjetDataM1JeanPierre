# Streaming MVP - KiVendTout

**Objectif** : valider un flux bout-en-bout simple et mesurable.

## Flux cible

`events.jsonl` -> Kafka `user-events` -> MongoDB `events`

## Configuration (.env)

- MongoDB
  - `MONGO_URI`, `MONGO_DB`, `MONGO_COLLECTION`
  - ou fallback : `MONGODB_HOST`, `MONGODB_PORT`, `MONGODB_USER`, `MONGODB_PASSWORD`, `MONGODB_DB`
- Kafka
  - `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC_USER_EVENTS`

## Prerequis

- Docker Compose demarre
- Kafka + MongoDB accessibles
- Dependencies Python (streaming uniquement)

```bash
python3 -m pip install -r requirements-streaming.txt
```

## Etapes

1. Creer les topics Kafka

```bash
./scripts/streaming/create_topics.sh
```

2. Produire les evenements

```bash
python3 scripts/streaming/producer_events.py \
  --file kivendtout_dataset/events.jsonl \
  --max-per-second 500
```

3. Consommer vers MongoDB

```bash
python3 scripts/streaming/consumer_events_to_mongo.py \
  --from-beginning \
  --batch-size 1000
```

## Validation

- Le count MongoDB doit correspondre au JSONL
- Kafka UI montre des offsets consommes
- Latence moyenne < 2s sur relecture

## Depannage

Si tu vois `Authentication failed` :

1. Verifie que le conteneur MongoDB est bien demarre.
2. Verifie que les identifiants dans `.env` correspondent a ceux du conteneur.
3. Si tu avais deja un volume Mongo avec d'anciens identifiants, il faut soit:
   - remettre les anciens identifiants dans `.env`, ou
   - recreer les volumes (attention: perte de donnees).

Test rapide:

```bash
mongosh \"mongodb://admin:admin@localhost:27017/?authSource=admin\" --eval \"db.runCommand({ ping: 1 })\"\n```

## Commandes utiles

Compter les evenements JSONL

```bash
wc -l kivendtout_dataset/events.jsonl
```

Compter les documents MongoDB

```bash
mongosh "mongodb://admin:admin@localhost:27017" --eval "db.getSiblingDB('kivendtout').events.countDocuments()"
```

## Notes techniques

- Le consumer convertit `ts` en datetime (champ `ts`) et conserve le brut dans `ts_raw`.
- `event_id` est utilise comme `_id` pour eviter les doublons.
- Un TTL de 2 ans est applique sur le champ `ts`.
