#!/usr/bin/env python3
"""
API FastAPI pour le dashboard de détection de fraude
Permet de:
- Lister les alertes
- Approuver/Bloquer/Investiguer
- Statistiques fraud rate
- Historique décisions
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import importlib.util
import json
import psycopg2
import site
import sys
from pathlib import Path
from collections import defaultdict, Counter


def patch_kafka_vendor_six():
    """
    Compatibilité Python 3.13 pour kafka-python 2.0.2.
    """
    candidates = []
    try:
        candidates.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        candidates.append(site.getusersitepackages())
    except Exception:
        pass

    for base in candidates:
        six_path = Path(base) / "kafka" / "vendor" / "six.py"
        if not six_path.exists():
            continue
        spec = importlib.util.spec_from_file_location("kafka.vendor.six", six_path)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules.setdefault("kafka.vendor.six", module)
        sys.modules.setdefault("kafka.vendor.six.moves", module.moves)
        return


patch_kafka_vendor_six()
try:
    from kafka import KafkaConsumer
except Exception as e:
    KafkaConsumer = None
    KAFKA_IMPORT_ERROR = e
else:
    KAFKA_IMPORT_ERROR = None

app = FastAPI(
    title="KiVendTout Fraud Detection API",
    description="API pour la gestion des alertes de fraude",
    version="1.0.0"
)

# CORS pour permettre l'accès depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELS
# ============================================================================

class FraudAlert(BaseModel):
    alert_id: str
    alert_timestamp: str
    event_timestamp: Optional[str] = None
    customer_id: str
    session_id: str
    event_type: str
    device: str
    utm_source: str
    customer_country: str
    previous_payments: int
    is_new_customer: bool
    fraud_reasons: List[str]
    risk_score: int
    status: str
    severity: str
    decision: Optional[str] = None
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None

class AlertDecision(BaseModel):
    decision: str  # APPROVE, BLOCK, INVESTIGATE
    decided_by: str  # User ID/email
    notes: Optional[str] = None

class FraudStats(BaseModel):
    total_alerts: int
    alerts_by_severity: dict
    alerts_by_status: dict
    fraud_rate: float
    total_payments: int
    fraudulent_payments: int
    alerted_customers: int
    total_customers: int
    customer_alert_coverage: float
    top_fraud_reasons: List[dict]
    alerts_by_hour: List[dict]
    alerts_by_day: List[dict]

class IdentityVerificationRecord(BaseModel):
    verification_id: int
    customer_id: str
    verification_date: str
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    verification_status: Optional[str] = None
    verification_method: Optional[str] = None
    id_card_image_path: Optional[str] = None
    created_at: Optional[str] = None

class IdentityVerificationRequest(BaseModel):
    customer_id: str
    document_number: str
    document_type: str = "national_id"
    verification_method: str = "manual"
    is_adult: Optional[bool] = None
    id_card_image_path: Optional[str] = None

class IdentityStats(BaseModel):
    total_verifications: int
    by_status: dict
    by_method: dict

# ============================================================================
# DATABASE
# ============================================================================

def get_db_connection():
    """Connexion PostgreSQL"""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='kivendtout',
        user='postgres',
        password='postgres'
    )

def init_fraud_alerts_table():
    """
    Crée la table fraud_alerts si elle n'existe pas
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Migration défensive: si une ancienne table fraud_alerts existe avec
    # le schéma dataset (sans alert_timestamp), on la renomme.
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'fraud_alerts'
    """)
    existing_columns = {row[0] for row in cursor.fetchall()}
    if existing_columns and 'alert_timestamp' not in existing_columns:
        cursor.execute("SELECT to_regclass('public.fraud_alerts_legacy')")
        if cursor.fetchone()[0] is not None:
            cursor.execute("DROP TABLE fraud_alerts_legacy")
        cursor.execute("ALTER TABLE fraud_alerts RENAME TO fraud_alerts_legacy")
        print("⚠️ Ancienne table fraud_alerts renommée en fraud_alerts_legacy")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fraud_alerts (
            alert_id VARCHAR(100) PRIMARY KEY,
            alert_timestamp TIMESTAMP NOT NULL,
            event_timestamp TIMESTAMP,
            customer_id VARCHAR(20),
            session_id VARCHAR(50),
            event_type VARCHAR(50),
            device VARCHAR(50),
            utm_source VARCHAR(50),
            customer_country VARCHAR(10),
            previous_payments INT,
            is_new_customer BOOLEAN,
            fraud_reasons TEXT,
            risk_score INT,
            status VARCHAR(20) DEFAULT 'PENDING_REVIEW',
            severity VARCHAR(10),
            decision VARCHAR(20),
            decided_at TIMESTAMP,
            decided_by VARCHAR(100),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON fraud_alerts(status);
        CREATE INDEX IF NOT EXISTS idx_fraud_alerts_severity ON fraud_alerts(severity);
        CREATE INDEX IF NOT EXISTS idx_fraud_alerts_customer ON fraud_alerts(customer_id);
        CREATE INDEX IF NOT EXISTS idx_fraud_alerts_timestamp ON fraud_alerts(alert_timestamp);
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Table fraud_alerts initialisée")

def init_identity_verifications_table():
    """Crée la table identity_verifications si elle n'existe pas."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS identity_verifications (
            verification_id SERIAL PRIMARY KEY,
            customer_id VARCHAR(50) NOT NULL,
            verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            document_type VARCHAR(50),
            document_number VARCHAR(100),
            verification_status VARCHAR(50),
            verification_method VARCHAR(50),
            id_card_image_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_identity_verif_customer ON identity_verifications(customer_id);
        CREATE INDEX IF NOT EXISTS idx_identity_verif_status ON identity_verifications(verification_status);
        CREATE INDEX IF NOT EXISTS idx_identity_verif_created_at ON identity_verifications(created_at);
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Table identity_verifications initialisée")

# ============================================================================
# KAFKA CONSUMER (Background sync)
# ============================================================================

def sync_alerts_from_kafka(max_messages=1000):
    """
    Synchronise les alertes depuis Kafka vers PostgreSQL
    """
    if KafkaConsumer is None:
        print(f"Kafka indisponible: {KAFKA_IMPORT_ERROR}")
        return 0

    try:
        consumer = KafkaConsumer(
            'fraud-alerts',
            bootstrap_servers=['localhost:9092', 'localhost:9093', 'localhost:9094'],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='fraud-dashboard-api',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=5000
        )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        count = 0
        for message in consumer:
            alert = message.value
            
            # Insérer dans PostgreSQL (ignore si existe déjà)
            try:
                cursor.execute("""
                    INSERT INTO fraud_alerts (
                        alert_id, alert_timestamp, event_timestamp, customer_id,
                        session_id, event_type, device, utm_source, customer_country,
                        previous_payments, is_new_customer, fraud_reasons,
                        risk_score, status, severity
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (alert_id) DO NOTHING
                """, (
                    alert['alert_id'],
                    alert['alert_timestamp'],
                    alert.get('event_timestamp'),
                    alert['customer_id'],
                    alert.get('session_id'),
                    alert.get('event_type'),
                    alert.get('device'),
                    alert.get('utm_source'),
                    alert.get('customer_country'),
                    alert.get('previous_payments', 0),
                    alert.get('is_new_customer', False),
                    ','.join(alert['fraud_reasons']),
                    alert['risk_score'],
                    alert['status'],
                    alert['severity']
                ))
                count += 1
            except Exception as e:
                print(f"Erreur insertion: {e}")
                conn.rollback()
            
            if count >= max_messages:
                break
        
        conn.commit()
        cursor.close()
        conn.close()
        consumer.close()
        
        return count
    
    except Exception as e:
        print(f"Erreur sync Kafka: {e}")
        return 0

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    print("🚀 Démarrage API Fraud Detection...")
    init_fraud_alerts_table()
    init_identity_verifications_table()
    print("✅ Initialisation API terminée")

@app.get("/")
async def root():
    """Page d'accueil API"""
    return {
        "message": "KiVendTout Fraud Detection API",
        "version": "1.0.0",
        "endpoints": {
            "alerts": "/api/alerts",
            "alert_detail": "/api/alerts/{alert_id}",
            "identity_verify": "/api/verify-id",
            "identity_stats": "/api/identity/stats",
            "stats": "/api/stats",
            "sync": "/api/sync"
        }
    }

@app.get("/api/alerts", response_model=List[FraudAlert])
async def get_alerts(
    status: Optional[str] = Query(None, description="Filter by status: PENDING_REVIEW, APPROVED, BLOCKED, INVESTIGATING"),
    severity: Optional[str] = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Liste les alertes de fraude avec filtres
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Construction de la requête
    query = "SELECT * FROM fraud_alerts WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = %s"
        params.append(status)
    
    if severity:
        query += " AND severity = %s"
        params.append(severity)
    
    query += " ORDER BY alert_timestamp DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    
    columns = [desc[0] for desc in cursor.description]
    results = []
    
    for row in cursor.fetchall():
        alert_dict = dict(zip(columns, row))
        alert_dict['fraud_reasons'] = alert_dict['fraud_reasons'].split(',') if alert_dict['fraud_reasons'] else []
        alert_dict['alert_timestamp'] = str(alert_dict['alert_timestamp'])
        alert_dict['event_timestamp'] = str(alert_dict['event_timestamp']) if alert_dict['event_timestamp'] else None
        alert_dict['decided_at'] = str(alert_dict['decided_at']) if alert_dict['decided_at'] else None
        results.append(alert_dict)
    
    cursor.close()
    conn.close()
    
    return results

@app.get("/api/alerts/{alert_id}", response_model=FraudAlert)
async def get_alert(alert_id: str):
    """
    Détails d'une alerte spécifique
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM fraud_alerts WHERE alert_id = %s", (alert_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Alert not found")
    
    columns = [desc[0] for desc in cursor.description]
    alert_dict = dict(zip(columns, row))
    alert_dict['fraud_reasons'] = alert_dict['fraud_reasons'].split(',') if alert_dict['fraud_reasons'] else []
    alert_dict['alert_timestamp'] = str(alert_dict['alert_timestamp'])
    alert_dict['event_timestamp'] = str(alert_dict['event_timestamp']) if alert_dict['event_timestamp'] else None
    alert_dict['decided_at'] = str(alert_dict['decided_at']) if alert_dict['decided_at'] else None
    
    cursor.close()
    conn.close()
    
    return alert_dict

@app.post("/api/alerts/{alert_id}/decide")
async def decide_alert(alert_id: str, decision: AlertDecision):
    """
    Prend une décision sur une alerte (APPROVE, BLOCK, INVESTIGATE)
    """
    if decision.decision not in ['APPROVE', 'BLOCK', 'INVESTIGATE']:
        raise HTTPException(status_code=400, detail="Invalid decision. Must be APPROVE, BLOCK, or INVESTIGATE")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Vérifier que l'alerte existe
    cursor.execute("SELECT status FROM fraud_alerts WHERE alert_id = %s", (alert_id,))
    result = cursor.fetchone()
    
    if not result:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Mettre à jour la décision
    new_status = 'INVESTIGATING' if decision.decision == 'INVESTIGATE' else decision.decision + 'D'
    
    cursor.execute("""
        UPDATE fraud_alerts
        SET decision = %s,
            status = %s,
            decided_at = %s,
            decided_by = %s,
            notes = %s
        WHERE alert_id = %s
    """, (
        decision.decision,
        new_status,
        datetime.now(),
        decision.decided_by,
        decision.notes,
        alert_id
    ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"message": "Decision recorded", "alert_id": alert_id, "decision": decision.decision}

@app.get("/api/stats", response_model=FraudStats)
async def get_stats():
    """
    Statistiques globales de fraude
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total alertes
    cursor.execute("SELECT COUNT(*) FROM fraud_alerts")
    total_alerts = cursor.fetchone()[0]
    
    # Par sévérité
    cursor.execute("SELECT severity, COUNT(*) FROM fraud_alerts GROUP BY severity")
    alerts_by_severity = dict(cursor.fetchall())
    
    # Par status
    cursor.execute("SELECT status, COUNT(*) FROM fraud_alerts GROUP BY status")
    alerts_by_status = dict(cursor.fetchall())
    
    # Volume de paiements
    cursor.execute("SELECT COUNT(*) FROM payments")
    total_payments = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM payments WHERE is_fraudulent = true")
    fraudulent_payments = cursor.fetchone()[0]

    # Taux de fraude cohérent métier: paiements frauduleux / paiements totaux
    fraud_rate = round((fraudulent_payments / total_payments) * 100, 2) if total_payments > 0 else 0.0

    # Couverture client des alertes (utile pour contextualiser le volume d'alertes)
    cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT customer_id) FROM fraud_alerts WHERE customer_id IS NOT NULL")
    alerted_customers = cursor.fetchone()[0]
    customer_alert_coverage = round((alerted_customers / total_customers) * 100, 2) if total_customers > 0 else 0.0
    
    # Top fraud reasons
    cursor.execute("SELECT fraud_reasons FROM fraud_alerts")
    all_reasons = []
    for row in cursor.fetchall():
        if row[0]:
            all_reasons.extend(row[0].split(','))
    
    reason_counts = Counter(all_reasons)
    top_fraud_reasons = [{"reason": r, "count": c} for r, c in reason_counts.most_common(10)]
    
    # Alertes par heure (dernières 24h)
    cursor.execute("""
        SELECT 
            EXTRACT(HOUR FROM alert_timestamp) as hour,
            COUNT(*)
        FROM fraud_alerts
        WHERE alert_timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY hour
        ORDER BY hour
    """)
    alerts_by_hour = [{"hour": int(h), "count": c} for h, c in cursor.fetchall()]
    
    # Alertes par jour (derniers 7 jours)
    cursor.execute("""
        SELECT 
            DATE(alert_timestamp) as day,
            COUNT(*)
        FROM fraud_alerts
        WHERE alert_timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY day
        ORDER BY day
    """)
    alerts_by_day = [{"day": str(d), "count": c} for d, c in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return FraudStats(
        total_alerts=total_alerts,
        alerts_by_severity=alerts_by_severity,
        alerts_by_status=alerts_by_status,
        fraud_rate=fraud_rate,
        total_payments=total_payments,
        fraudulent_payments=fraudulent_payments,
        alerted_customers=alerted_customers,
        total_customers=total_customers,
        customer_alert_coverage=customer_alert_coverage,
        top_fraud_reasons=top_fraud_reasons,
        alerts_by_hour=alerts_by_hour,
        alerts_by_day=alerts_by_day
    )

@app.get("/api/identity/verifications", response_model=List[IdentityVerificationRecord])
async def get_identity_verifications(
    status: Optional[str] = Query(None, description="Filter by status: pending, verified, rejected"),
    customer_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Liste les vérifications d'identité avec filtres."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM identity_verifications WHERE 1=1"
    params = []

    if status:
        query += " AND verification_status = %s"
        params.append(status)

    if customer_id:
        query += " AND customer_id = %s"
        params.append(customer_id)

    query += " ORDER BY verification_date DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    results = []
    for row in cursor.fetchall():
        item = dict(zip(columns, row))
        item['verification_date'] = str(item['verification_date']) if item['verification_date'] else None
        item['created_at'] = str(item['created_at']) if item['created_at'] else None
        results.append(item)

    cursor.close()
    conn.close()
    return results

@app.post("/api/verify-id")
async def verify_identity(payload: IdentityVerificationRequest):
    """Enregistre une vérification d'identité manuelle/API."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM customers WHERE customer_id = %s", (payload.customer_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Customer not found")

    if payload.is_adult is True:
        verification_status = "verified"
    elif payload.is_adult is False:
        verification_status = "rejected"
    else:
        verification_status = "pending"

    cursor.execute("""
        INSERT INTO identity_verifications (
            customer_id, verification_date, document_type, document_number,
            verification_status, verification_method, id_card_image_path, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING verification_id
    """, (
        payload.customer_id,
        datetime.now(),
        payload.document_type,
        payload.document_number,
        verification_status,
        payload.verification_method,
        payload.id_card_image_path,
        datetime.now()
    ))

    verification_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "message": "Identity verification saved",
        "verification_id": verification_id,
        "customer_id": payload.customer_id,
        "verification_status": verification_status
    }

@app.get("/api/identity/stats", response_model=IdentityStats)
async def get_identity_stats():
    """Statistiques des vérifications d'identité."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM identity_verifications")
    total_verifications = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(verification_status, 'unknown'), COUNT(*)
        FROM identity_verifications
        GROUP BY verification_status
    """)
    by_status = dict(cursor.fetchall())

    cursor.execute("""
        SELECT COALESCE(verification_method, 'unknown'), COUNT(*)
        FROM identity_verifications
        GROUP BY verification_method
    """)
    by_method = dict(cursor.fetchall())

    cursor.close()
    conn.close()

    return IdentityStats(
        total_verifications=total_verifications,
        by_status=by_status,
        by_method=by_method
    )

@app.post("/api/sync")
async def sync_from_kafka():
    """
    Force une synchronisation depuis Kafka
    """
    count = sync_alerts_from_kafka(max_messages=5000)
    return {"message": f"Synchronized {count} alerts from Kafka"}

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
