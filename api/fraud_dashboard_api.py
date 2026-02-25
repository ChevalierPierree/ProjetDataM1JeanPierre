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
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
from datetime import datetime, timedelta, date
import importlib.util
import json
import csv
import subprocess
import threading
import time
import os
import random
import psycopg2
import site
import sys
from pathlib import Path
from collections import defaultdict, Counter
from fastapi.responses import FileResponse
from uuid import uuid4


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

class ProductCatalogItem(BaseModel):
    product_id: int
    name: str
    category: Optional[str] = None
    price: float
    stock_quantity: int
    is_adult_restricted: bool

class IdCardPreview(BaseModel):
    file: str
    birthdate: str
    age: int
    is_adult: bool

class OrderItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)

class CheckoutRequest(BaseModel):
    customer_id: str
    id_card_file: str
    items: List[OrderItemRequest]
    payment_method: str = "card"

class CheckoutResponse(BaseModel):
    accepted: bool
    order_id: Optional[int] = None
    customer_id: str
    id_card_file: str
    customer_age: int
    total_amount: float
    blocked_reason: Optional[str] = None
    blocked_products: List[int] = []
    created_at: str

class CheckoutStats(BaseModel):
    window_hours: int
    total_attempts: int
    accepted_orders: int
    blocked_underage_orders: int
    rejection_rate: float
    adult_product_attempts: int
    adult_product_rejected: int
    adult_rejection_rate: float
    avg_customer_age: float
    last_attempt_at: Optional[str] = None

class CheckoutAttemptRecord(BaseModel):
    attempt_id: int
    attempted_at: str
    customer_id: Optional[str] = None
    id_card_file: Optional[str] = None
    customer_age: Optional[int] = None
    contains_adult_product: bool
    blocked_underage: bool
    accepted: bool
    blocked_products: Optional[str] = None
    total_amount: Optional[float] = None
    order_id: Optional[int] = None
    notes: Optional[str] = None

class FraudReasonStat(BaseModel):
    reason: str
    total: int
    high: int
    medium: int
    low: int

class AlertSimulationRequest(BaseModel):
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    event_type: Optional[str] = None
    device: Optional[str] = None
    utm_source: Optional[str] = None
    customer_country: Optional[str] = None
    previous_payments: Optional[int] = Field(default=None, ge=0, le=200)
    is_new_customer: Optional[bool] = None
    fraud_reasons: Optional[List[str]] = None
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    severity: Optional[str] = Field(default=None, pattern="^(LOW|MEDIUM|HIGH)$")
    status: str = Field(default="PENDING_REVIEW", pattern="^(PENDING_REVIEW|APPROVED|BLOCKED|INVESTIGATING)$")

class RuntimeRefreshRequest(BaseModel):
    sync_kafka: bool = True
    run_scaling: bool = True
    run_alert_scaling: bool = True
    restart_api: bool = True
    max_sync_messages: int = Field(default=2000, ge=0, le=50000)
    requests: int = Field(default=80, ge=1, le=5000)
    concurrency: int = Field(default=16, ge=1, le=200)
    adult_order_ratio: float = Field(default=0.6, ge=0.0, le=1.0)
    minor_ratio: float = Field(default=0.4, ge=0.0, le=1.0)
    scaling_mode: str = Field(default="realtime", pattern="^(burst|realtime)$")
    duration_seconds: int = Field(default=30, ge=1, le=3600)
    rps: int = Field(default=8, ge=1, le=200)
    alerts_mode: str = Field(default="realtime", pattern="^(burst|realtime)$")
    alerts_requests: int = Field(default=120, ge=1, le=20000)
    alerts_concurrency: int = Field(default=10, ge=1, le=200)
    alerts_duration_seconds: int = Field(default=30, ge=1, le=3600)
    alerts_rps: int = Field(default=6, ge=1, le=500)
    high_severity_ratio: float = Field(default=0.35, ge=0.0, le=1.0)

class RuntimeRefreshResponse(BaseModel):
    started_orders: bool
    orders_pid: Optional[int] = None
    started_alerts: bool
    alerts_pid: Optional[int] = None
    synced_alerts: int
    scaling_mode: str
    requests: int
    concurrency: int
    duration_seconds: int
    rps: int
    alerts_mode: str
    alerts_requests: int
    alerts_concurrency: int
    alerts_duration_seconds: int
    alerts_rps: int
    log_file: str
    message: str

# ============================================================================
# DATABASE
# ============================================================================

DATASET_DIR = Path(__file__).resolve().parent.parent / "kivendtout_dataset"
ID_CARDS_DIR = DATASET_DIR / "synthetic_id_cards"
ID_LABELS_FILE = DATASET_DIR / "synthetic_id_labels.csv"
ID_LABELS_CACHE = None
BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_LOG_FILE = BASE_DIR / "logs" / "runtime_refresh.log"
RUNTIME_REFRESH_LOCK = threading.Lock()
RUNTIME_SCALING_PROCESS = None
RUNTIME_ALERTS_PROCESS = None

FRAUD_REASON_POOL = [
    "FIRST_PAYMENT",
    "NEW_CUSTOMER",
    "UNUSUAL_HOUR",
    "MOBILE_DEVICE",
    "DIRECT_TRAFFIC",
    "PAYMENT_FAILED",
    "VELOCITY_HIGH",
    "NEW_DEVICE",
    "UNUSUAL_AMOUNT",
    "FAST_CHECKOUT",
    "GEO_MISMATCH"
]

def get_db_connection():
    """Connexion PostgreSQL"""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        database='kivendtout',
        user='postgres',
        password='postgres'
    )

def load_id_labels():
    """
    Charge le mapping fichier ID -> date de naissance.
    Source: synthetic_id_labels.csv associé aux synthetic_id_cards/*.png.
    """
    global ID_LABELS_CACHE
    if ID_LABELS_CACHE is not None:
        return ID_LABELS_CACHE

    if not ID_LABELS_FILE.exists():
        raise RuntimeError(f"Fichier labels introuvable: {ID_LABELS_FILE}")

    cache = {}
    with ID_LABELS_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            file_name = (row.get("file") or "").strip()
            birthdate = (row.get("birthdate") or "").strip()
            if not file_name or not birthdate:
                continue
            cache[file_name] = birthdate

    ID_LABELS_CACHE = cache
    return ID_LABELS_CACHE

def compute_age(birthdate_str: str) -> int:
    birth = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

def extract_age_from_id_card(id_card_file: str):
    """
    Retourne (file_name, birthdate_str, age) pour une carte d'identité synthétique.
    """
    safe_name = Path(id_card_file).name
    card_path = ID_CARDS_DIR / safe_name
    if not card_path.exists():
        raise HTTPException(status_code=404, detail=f"ID card not found: {safe_name}")

    labels = load_id_labels()
    if safe_name not in labels:
        raise HTTPException(status_code=400, detail=f"No birthdate label found for card: {safe_name}")

    birthdate_str = labels[safe_name]
    age = compute_age(birthdate_str)
    return safe_name, birthdate_str, age

def is_adult_restricted(category: Optional[str]) -> bool:
    return (category or "").strip().lower() == "adult"

def get_or_create_customer_address(cursor, customer_id: str) -> int:
    cursor.execute("""
        SELECT address_id
        FROM addresses
        WHERE customer_id = %s
        ORDER BY address_id
        LIMIT 1
    """, (customer_id,))
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute("SELECT country FROM customers WHERE customer_id = %s", (customer_id,))
    customer = cursor.fetchone()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer not found: {customer_id}")

    country = customer[0] or "FR"
    cursor.execute("""
        INSERT INTO addresses (customer_id, street, city, postal_code, country, address_type, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING address_id
    """, (
        customer_id,
        "1 Rue du Commerce",
        "Paris",
        "75001",
        country,
        "both",
        datetime.now()
    ))
    return cursor.fetchone()[0]

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

def init_checkout_attempts_table():
    """Crée la table d'audit des tentatives de checkout API."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkout_attempts (
            attempt_id BIGSERIAL PRIMARY KEY,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            customer_id VARCHAR(50),
            id_card_file VARCHAR(100),
            customer_age INT,
            contains_adult_product BOOLEAN DEFAULT FALSE,
            blocked_underage BOOLEAN DEFAULT FALSE,
            accepted BOOLEAN DEFAULT FALSE,
            blocked_products TEXT,
            total_amount NUMERIC(10, 2),
            order_id INTEGER,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_checkout_attempts_ts ON checkout_attempts(attempted_at);
        CREATE INDEX IF NOT EXISTS idx_checkout_attempts_blocked ON checkout_attempts(blocked_underage);
        CREATE INDEX IF NOT EXISTS idx_checkout_attempts_accepted ON checkout_attempts(accepted);
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Table checkout_attempts initialisée")

def log_checkout_attempt(
    customer_id: str,
    id_card_file: str,
    customer_age: int,
    contains_adult_product: bool,
    blocked_underage: bool,
    accepted: bool,
    blocked_products: List[int],
    total_amount: float,
    order_id: Optional[int] = None,
    notes: Optional[str] = None
):
    """
    Audit technique/métier des tentatives de commande API.
    Utilise une connexion dédiée pour conserver les logs même en cas de rollback checkout.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO checkout_attempts (
                attempted_at, customer_id, id_card_file, customer_age,
                contains_adult_product, blocked_underage, accepted,
                blocked_products, total_amount, order_id, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.now(),
            customer_id,
            id_card_file,
            customer_age,
            contains_adult_product,
            blocked_underage,
            accepted,
            ",".join(str(p) for p in sorted(blocked_products)) if blocked_products else None,
            round(total_amount, 2),
            order_id,
            notes
        ))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def infer_severity_from_score(risk_score: int) -> str:
    if risk_score >= 80:
        return "HIGH"
    if risk_score >= 60:
        return "MEDIUM"
    return "LOW"

def build_simulated_alert(payload: AlertSimulationRequest) -> dict:
    """
    Construit une alerte synthétique (fraude) pour alimenter le dashboard en temps réel.
    """
    now = datetime.now()
    customer_id = payload.customer_id or f"C{random.randint(1, 2500):05d}"
    session_id = payload.session_id or f"SIM_{uuid4().hex[:12]}"
    event_type = payload.event_type or random.choice(["payment_attempt", "checkout", "order_completed"])
    device = payload.device or random.choice(["ios", "android", "desktop"])
    utm_source = payload.utm_source or random.choice(["direct", "google", "instagram", "facebook", "email"])
    customer_country = payload.customer_country or random.choice(["FR", "ES", "PT", "DE", "IT", "GB"])
    previous_payments = payload.previous_payments if payload.previous_payments is not None else random.randint(0, 12)
    is_new_customer = payload.is_new_customer if payload.is_new_customer is not None else (previous_payments == 0)

    reasons = payload.fraud_reasons
    if not reasons:
        count = random.randint(1, 3)
        reasons = random.sample(FRAUD_REASON_POOL, k=count)

    risk_score = payload.risk_score
    if risk_score is None:
        risk_score = random.randint(60, 96) if random.random() < 0.35 else random.randint(45, 79)

    severity = payload.severity or infer_severity_from_score(risk_score)
    status = payload.status
    alert_id = f"FRD_SIM_{int(time.time() * 1000)}_{uuid4().hex[:6].upper()}"

    return {
        "alert_id": alert_id,
        "alert_timestamp": now,
        "event_timestamp": now - timedelta(seconds=random.randint(0, 8)),
        "customer_id": customer_id,
        "session_id": session_id,
        "event_type": event_type,
        "device": device,
        "utm_source": utm_source,
        "customer_country": customer_country,
        "previous_payments": previous_payments,
        "is_new_customer": bool(is_new_customer),
        "fraud_reasons": reasons,
        "risk_score": int(risk_score),
        "status": status,
        "severity": severity
    }

def insert_fraud_alert(alert: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO fraud_alerts (
                alert_id, alert_timestamp, event_timestamp, customer_id,
                session_id, event_type, device, utm_source, customer_country,
                previous_payments, is_new_customer, fraud_reasons,
                risk_score, status, severity
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alert_id) DO NOTHING
        """, (
            alert["alert_id"],
            alert["alert_timestamp"],
            alert["event_timestamp"],
            alert["customer_id"],
            alert["session_id"],
            alert["event_type"],
            alert["device"],
            alert["utm_source"],
            alert["customer_country"],
            alert["previous_payments"],
            alert["is_new_customer"],
            ",".join(alert["fraud_reasons"]),
            alert["risk_score"],
            alert["status"],
            alert["severity"]
        ))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def append_runtime_log(message: str):
    """Écrit une ligne horodatée dans le log runtime refresh."""
    try:
        RUNTIME_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with RUNTIME_LOG_FILE.open("a", encoding="utf-8") as log_file:
            timestamp = datetime.now().isoformat(timespec="seconds")
            log_file.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Erreur écriture runtime log: {e}")

def start_scaling_process(
    scaling_mode: str,
    requests: int,
    concurrency: int,
    adult_order_ratio: float,
    minor_ratio: float,
    duration_seconds: int,
    rps: int
) -> Tuple[bool, Optional[int], str]:
    """Lance scripts/scale_order_api.py en arrière-plan si aucun run n'est actif."""
    global RUNTIME_SCALING_PROCESS

    script_path = BASE_DIR / "scripts" / "scale_order_api.py"
    if not script_path.exists():
        message = f"Script scaling introuvable: {script_path}"
        append_runtime_log(message)
        return False, None, message

    with RUNTIME_REFRESH_LOCK:
        if RUNTIME_SCALING_PROCESS is not None and RUNTIME_SCALING_PROCESS.poll() is None:
            pid = RUNTIME_SCALING_PROCESS.pid
            message = f"Scaling déjà en cours (pid={pid})"
            append_runtime_log(message)
            return False, pid, message

        cmd = [
            sys.executable,
            str(script_path),
            "--api-url", "http://localhost:8000",
            "--mode", str(scaling_mode),
            "--requests", str(requests),
            "--concurrency", str(concurrency),
            "--adult-order-ratio", str(adult_order_ratio),
            "--minor-ratio", str(minor_ratio),
            "--duration-seconds", str(duration_seconds),
            "--rps", str(rps),
        ]

        # Le log runtime consolide les déclenchements et sorties du scaling.
        log_handle = RUNTIME_LOG_FILE.open("a", encoding="utf-8")
        append_runtime_log(f"Lancement scaling: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        log_handle.close()

        RUNTIME_SCALING_PROCESS = process
        message = f"Scaling lancé (pid={process.pid})"
        append_runtime_log(message)
        return True, process.pid, message

def start_alert_scaling_process(
    alerts_mode: str,
    alerts_requests: int,
    alerts_concurrency: int,
    alerts_duration_seconds: int,
    alerts_rps: int,
    high_severity_ratio: float
) -> Tuple[bool, Optional[int], str]:
    """Lance scripts/scale_alerts_api.py en arrière-plan si aucun run n'est actif."""
    global RUNTIME_ALERTS_PROCESS

    script_path = BASE_DIR / "scripts" / "scale_alerts_api.py"
    if not script_path.exists():
        message = f"Script alert scaling introuvable: {script_path}"
        append_runtime_log(message)
        return False, None, message

    with RUNTIME_REFRESH_LOCK:
        if RUNTIME_ALERTS_PROCESS is not None and RUNTIME_ALERTS_PROCESS.poll() is None:
            pid = RUNTIME_ALERTS_PROCESS.pid
            message = f"Alert scaling déjà en cours (pid={pid})"
            append_runtime_log(message)
            return False, pid, message

        cmd = [
            sys.executable,
            str(script_path),
            "--api-url", "http://localhost:8000",
            "--mode", str(alerts_mode),
            "--requests", str(alerts_requests),
            "--concurrency", str(alerts_concurrency),
            "--duration-seconds", str(alerts_duration_seconds),
            "--rps", str(alerts_rps),
            "--high-severity-ratio", str(high_severity_ratio),
        ]

        log_handle = RUNTIME_LOG_FILE.open("a", encoding="utf-8")
        append_runtime_log(f"Lancement alert scaling: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        log_handle.close()

        RUNTIME_ALERTS_PROCESS = process
        message = f"Alert scaling lancé (pid={process.pid})"
        append_runtime_log(message)
        return True, process.pid, message

def schedule_api_restart(delay_seconds: float = 1.2):
    """
    Planifie un redémarrage du process API après la réponse HTTP.
    Utilise execv pour relancer le script courant sur le même port.
    """
    def _restart():
        time.sleep(delay_seconds)
        append_runtime_log("Redémarrage API demandé via runtime refresh")
        script_path = Path(__file__).resolve()
        try:
            os.execv(sys.executable, [sys.executable, str(script_path)])
        except Exception as e:
            append_runtime_log(f"Erreur redémarrage API: {e}")

    threading.Thread(target=_restart, daemon=True).start()

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
    # Garantit la présence du fichier pour `tail -f logs/runtime_refresh.log`
    append_runtime_log("API startup")
    init_fraud_alerts_table()
    init_identity_verifications_table()
    init_checkout_attempts_table()
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
            "simulate_alert": "/api/alerts/simulate",
            "identity_verify": "/api/verify-id",
            "identity_stats": "/api/identity/stats",
            "products": "/api/products",
            "id_cards": "/api/id-cards",
            "id_card_image": "/api/id-cards/image/{file_name}",
            "checkout": "/api/orders/checkout",
            "checkout_stats": "/api/checkout/stats",
            "checkout_attempts": "/api/checkout/attempts",
            "fraud_reason_stats": "/api/fraud/reasons/stats",
            "fraud_reason_alerts": "/api/fraud/reasons/{reason}/alerts",
            "runtime_refresh": "/api/runtime/refresh",
            "runtime_logs": "/api/runtime/logs",
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

@app.post("/api/alerts/simulate", response_model=FraudAlert)
async def simulate_alert(payload: AlertSimulationRequest):
    """
    Génère une alerte synthétique et l'insère dans fraud_alerts.
    Utilisé par le simulateur temps réel pour rendre le dashboard dynamique.
    """
    alert = build_simulated_alert(payload)
    insert_fraud_alert(alert)

    return FraudAlert(
        alert_id=alert["alert_id"],
        alert_timestamp=str(alert["alert_timestamp"]),
        event_timestamp=str(alert["event_timestamp"]) if alert["event_timestamp"] else None,
        customer_id=alert["customer_id"],
        session_id=alert["session_id"],
        event_type=alert["event_type"],
        device=alert["device"],
        utm_source=alert["utm_source"],
        customer_country=alert["customer_country"],
        previous_payments=int(alert["previous_payments"]),
        is_new_customer=bool(alert["is_new_customer"]),
        fraud_reasons=list(alert["fraud_reasons"]),
        risk_score=int(alert["risk_score"]),
        status=alert["status"],
        severity=alert["severity"],
        decision=None,
        decided_at=None,
        decided_by=None
    )

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

@app.get("/api/products", response_model=List[ProductCatalogItem])
async def get_products(
    adult_only: bool = Query(False, description="Retourne uniquement les produits catégorie Adult"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Catalogue produits pour pilotage des commandes API."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT product_id, name, category, price, stock_quantity
        FROM products
        WHERE 1=1
    """
    params = []

    if adult_only:
        query += " AND LOWER(category) = 'adult'"

    query += " ORDER BY product_id LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    cursor.execute(query, params)

    items = []
    for row in cursor.fetchall():
        category = row[2]
        items.append(ProductCatalogItem(
            product_id=row[0],
            name=row[1],
            category=category,
            price=float(row[3]),
            stock_quantity=int(row[4]),
            is_adult_restricted=is_adult_restricted(category)
        ))

    cursor.close()
    conn.close()
    return items

@app.get("/api/id-cards", response_model=List[IdCardPreview])
async def get_id_cards(
    adult: Optional[bool] = Query(None, description="true=18+, false=<18"),
    limit: int = Query(60, ge=1, le=500)
):
    """
    Retourne un aperçu des cartes d'identité synthétiques.
    La date de naissance est extraite du dataset des cartes (labels associés aux PNG).
    """
    labels = load_id_labels()
    rows = []
    for file_name, birthdate in sorted(labels.items()):
        age = compute_age(birthdate)
        is_adult = age >= 18
        if adult is not None and is_adult != adult:
            continue
        rows.append(IdCardPreview(
            file=file_name,
            birthdate=birthdate,
            age=age,
            is_adult=is_adult
        ))
        if len(rows) >= limit:
            break
    return rows

@app.get("/api/id-cards/image/{file_name}")
async def get_id_card_image(file_name: str):
    """Expose une image synthetic_id_card pour affichage dashboard."""
    safe_name = Path(file_name).name
    card_path = ID_CARDS_DIR / safe_name
    if not card_path.exists():
        raise HTTPException(status_code=404, detail=f"ID card image not found: {safe_name}")
    return FileResponse(card_path)

@app.get("/api/fraud/reasons/stats", response_model=List[FraudReasonStat])
async def get_fraud_reason_stats(
    window_hours: int = Query(24, ge=1, le=720, description="Fenêtre d'observation en heures")
):
    """
    Distribution des types de fraude (raisons) pour dashboard typologies.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        WITH reason_rows AS (
            SELECT
                TRIM(UNNEST(string_to_array(fraud_reasons, ','))) AS reason,
                severity
            FROM fraud_alerts
            WHERE fraud_reasons IS NOT NULL
              AND fraud_reasons <> ''
              AND alert_timestamp >= NOW() - (%s || ' hours')::INTERVAL
        )
        SELECT
            reason,
            COUNT(*)::INT AS total,
            COALESCE(SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END), 0)::INT AS high,
            COALESCE(SUM(CASE WHEN severity = 'MEDIUM' THEN 1 ELSE 0 END), 0)::INT AS medium,
            COALESCE(SUM(CASE WHEN severity = 'LOW' THEN 1 ELSE 0 END), 0)::INT AS low
        FROM reason_rows
        GROUP BY reason
        ORDER BY total DESC, reason ASC
    """, (window_hours,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        FraudReasonStat(
            reason=row[0],
            total=row[1],
            high=row[2],
            medium=row[3],
            low=row[4]
        )
        for row in rows
    ]

@app.get("/api/fraud/reasons/{reason}/alerts", response_model=List[FraudAlert])
async def get_alerts_by_reason(
    reason: str,
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Alertes associées à une raison précise (ex: FIRST_PAYMENT, VELOCITY_HIGH).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM fraud_alerts
        WHERE %s = ANY(string_to_array(fraud_reasons, ','))
        ORDER BY alert_timestamp DESC
        LIMIT %s
    """, (reason, limit))

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

@app.post("/api/orders/checkout", response_model=CheckoutResponse)
async def create_checkout_order(payload: CheckoutRequest):
    """
    Création d'une commande client via API avec garde-fou majorité:
    - Lit la date de naissance via la carte d'identité synthétique (id.png + labels)
    - Refuse les produits catégorie Adult si âge < 18 ans
    """
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required")

    safe_card_name, birthdate_str, age = extract_age_from_id_card(payload.id_card_file)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT 1 FROM customers WHERE customer_id = %s", (payload.customer_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Customer not found: {payload.customer_id}")

        quantities_by_product = defaultdict(int)
        for item in payload.items:
            quantities_by_product[item.product_id] += item.quantity

        product_ids = list(quantities_by_product.keys())
        placeholders = ",".join(["%s"] * len(product_ids))
        cursor.execute(f"""
            SELECT product_id, name, category, price, stock_quantity
            FROM products
            WHERE product_id IN ({placeholders})
            FOR UPDATE
        """, product_ids)
        products = {row[0]: row for row in cursor.fetchall()}

        missing = [pid for pid in product_ids if pid not in products]
        if missing:
            raise HTTPException(status_code=400, detail=f"Unknown product_id(s): {missing}")

        blocked_adult_products = []
        contains_adult_product = False
        total_amount = 0.0
        for product_id, qty in quantities_by_product.items():
            _, _, category, unit_price, stock_qty = products[product_id]
            product_is_adult = is_adult_restricted(category)
            if product_is_adult:
                contains_adult_product = True
            if age < 18 and product_is_adult:
                blocked_adult_products.append(product_id)
            if qty > int(stock_qty):
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for product {product_id}: requested={qty}, stock={stock_qty}"
                )
            total_amount += float(unit_price) * qty

        if blocked_adult_products:
            # Matérialise le contrôle 18+ sur le dashboard via table d'audit dédiée.
            try:
                log_checkout_attempt(
                    customer_id=payload.customer_id,
                    id_card_file=safe_card_name,
                    customer_age=age,
                    contains_adult_product=contains_adult_product,
                    blocked_underage=True,
                    accepted=False,
                    blocked_products=blocked_adult_products,
                    total_amount=total_amount,
                    notes="Blocked underage for adult products"
                )
            except Exception as log_error:
                print(f"Erreur log checkout (blocked): {log_error}")

            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Adult products are restricted to 18+ customers",
                    "customer_age": age,
                    "id_card_file": safe_card_name,
                    "birthdate": birthdate_str,
                    "blocked_products": sorted(blocked_adult_products)
                }
            )

        address_id = get_or_create_customer_address(cursor, payload.customer_id)

        # Génération robuste d'identifiant de commande sous concurrence
        cursor.execute("LOCK TABLE orders IN EXCLUSIVE MODE")
        cursor.execute("SELECT COALESCE(MAX(order_id), 0) + 1 FROM orders")
        next_order_id = cursor.fetchone()[0]

        now = datetime.now()
        cursor.execute("""
            INSERT INTO orders (
                order_id, customer_id, order_date, total_amount, status,
                shipping_address_id, billing_address_id, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            next_order_id,
            payload.customer_id,
            now,
            round(total_amount, 2),
            "pending",
            address_id,
            address_id,
            now
        ))

        for product_id, qty in quantities_by_product.items():
            unit_price = float(products[product_id][3])
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (next_order_id, product_id, qty, unit_price, now))

            cursor.execute("""
                UPDATE products
                SET stock_quantity = stock_quantity - %s
                WHERE product_id = %s
            """, (qty, product_id))

        conn.commit()

        try:
            log_checkout_attempt(
                customer_id=payload.customer_id,
                id_card_file=safe_card_name,
                customer_age=age,
                contains_adult_product=contains_adult_product,
                blocked_underage=False,
                accepted=True,
                blocked_products=[],
                total_amount=total_amount,
                order_id=next_order_id,
                notes="Checkout accepted"
            )
        except Exception as log_error:
            print(f"Erreur log checkout (accepted): {log_error}")

        return CheckoutResponse(
            accepted=True,
            order_id=next_order_id,
            customer_id=payload.customer_id,
            id_card_file=safe_card_name,
            customer_age=age,
            total_amount=round(total_amount, 2),
            created_at=now.isoformat()
        )

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Checkout failed: {e}")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/checkout/stats", response_model=CheckoutStats)
async def get_checkout_stats(
    window_hours: int = Query(24, ge=1, le=720, description="Fenêtre d'observation en heures")
):
    """
    KPIs checkout API pour matérialiser le contrôle de majorité sur dashboard.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*)::INT AS total_attempts,
            COALESCE(SUM(CASE WHEN accepted THEN 1 ELSE 0 END), 0)::INT AS accepted_orders,
            COALESCE(SUM(CASE WHEN blocked_underage THEN 1 ELSE 0 END), 0)::INT AS blocked_underage_orders,
            COALESCE(SUM(CASE WHEN contains_adult_product THEN 1 ELSE 0 END), 0)::INT AS adult_product_attempts,
            COALESCE(SUM(CASE WHEN contains_adult_product AND blocked_underage THEN 1 ELSE 0 END), 0)::INT AS adult_product_rejected,
            COALESCE(AVG(customer_age), 0)::FLOAT AS avg_customer_age,
            MAX(attempted_at) AS last_attempt_at
        FROM checkout_attempts
        WHERE attempted_at >= NOW() - (%s || ' hours')::INTERVAL
    """, (window_hours,))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    total_attempts = int(row[0] or 0)
    accepted_orders = int(row[1] or 0)
    blocked_underage_orders = int(row[2] or 0)
    adult_product_attempts = int(row[3] or 0)
    adult_product_rejected = int(row[4] or 0)
    avg_customer_age = float(row[5] or 0.0)
    last_attempt_at = row[6]

    rejection_rate = round((blocked_underage_orders / total_attempts) * 100, 2) if total_attempts > 0 else 0.0
    adult_rejection_rate = round((adult_product_rejected / adult_product_attempts) * 100, 2) if adult_product_attempts > 0 else 0.0

    return CheckoutStats(
        window_hours=window_hours,
        total_attempts=total_attempts,
        accepted_orders=accepted_orders,
        blocked_underage_orders=blocked_underage_orders,
        rejection_rate=rejection_rate,
        adult_product_attempts=adult_product_attempts,
        adult_product_rejected=adult_product_rejected,
        adult_rejection_rate=adult_rejection_rate,
        avg_customer_age=round(avg_customer_age, 2),
        last_attempt_at=last_attempt_at.isoformat() if last_attempt_at else None
    )

@app.get("/api/checkout/attempts", response_model=List[CheckoutAttemptRecord])
async def get_checkout_attempts(
    blocked_underage: Optional[bool] = Query(None),
    accepted: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Historique des tentatives checkout API (support dashboard mineurs/ID cards).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            attempt_id, attempted_at, customer_id, id_card_file, customer_age,
            contains_adult_product, blocked_underage, accepted, blocked_products,
            total_amount, order_id, notes
        FROM checkout_attempts
        WHERE 1=1
    """
    params = []

    if blocked_underage is not None:
        query += " AND blocked_underage = %s"
        params.append(blocked_underage)

    if accepted is not None:
        query += " AND accepted = %s"
        params.append(accepted)

    query += " ORDER BY attempted_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    cursor.execute(query, params)

    records = []
    for row in cursor.fetchall():
        records.append(CheckoutAttemptRecord(
            attempt_id=row[0],
            attempted_at=str(row[1]) if row[1] else "",
            customer_id=row[2],
            id_card_file=row[3],
            customer_age=row[4],
            contains_adult_product=bool(row[5]),
            blocked_underage=bool(row[6]),
            accepted=bool(row[7]),
            blocked_products=row[8],
            total_amount=float(row[9]) if row[9] is not None else None,
            order_id=row[10],
            notes=row[11]
        ))

    cursor.close()
    conn.close()
    return records

@app.post("/api/runtime/refresh", response_model=RuntimeRefreshResponse)
async def runtime_refresh(payload: RuntimeRefreshRequest):
    """
    Refresh runtime unifié:
    - sync Kafka -> PostgreSQL
    - lancement scaling commandes API
    - redémarrage API (optionnel)
    """
    synced_alerts = 0
    started_orders = False
    orders_pid = None
    started_alerts = False
    alerts_pid = None
    messages = []

    append_runtime_log(
        "Runtime refresh demandé "
        f"(sync={payload.sync_kafka}, scaling_orders={payload.run_scaling}, scaling_alerts={payload.run_alert_scaling}, "
        f"restart_api={payload.restart_api}, order_mode={payload.scaling_mode}, order_requests={payload.requests}, "
        f"order_concurrency={payload.concurrency}, order_duration={payload.duration_seconds}, order_rps={payload.rps}, "
        f"alerts_mode={payload.alerts_mode}, alerts_requests={payload.alerts_requests}, "
        f"alerts_concurrency={payload.alerts_concurrency}, alerts_duration={payload.alerts_duration_seconds}, "
        f"alerts_rps={payload.alerts_rps})"
    )

    if payload.sync_kafka:
        synced_alerts = sync_alerts_from_kafka(max_messages=payload.max_sync_messages)
        messages.append(f"sync={synced_alerts}")
    else:
        messages.append("sync=skipped")

    if payload.run_scaling:
        started_orders, orders_pid, scaling_message = start_scaling_process(
            scaling_mode=payload.scaling_mode,
            requests=payload.requests,
            concurrency=payload.concurrency,
            adult_order_ratio=payload.adult_order_ratio,
            minor_ratio=payload.minor_ratio,
            duration_seconds=payload.duration_seconds,
            rps=payload.rps
        )
        messages.append(scaling_message)
    else:
        messages.append("order scaling skipped")

    if payload.run_alert_scaling:
        started_alerts, alerts_pid, alert_scaling_message = start_alert_scaling_process(
            alerts_mode=payload.alerts_mode,
            alerts_requests=payload.alerts_requests,
            alerts_concurrency=payload.alerts_concurrency,
            alerts_duration_seconds=payload.alerts_duration_seconds,
            alerts_rps=payload.alerts_rps,
            high_severity_ratio=payload.high_severity_ratio
        )
        messages.append(alert_scaling_message)
    else:
        messages.append("alert scaling skipped")

    if payload.restart_api:
        restart_delay = 1.2
        if payload.run_scaling and payload.scaling_mode == "realtime":
            restart_delay = max(restart_delay, min(float(payload.duration_seconds) + 2.0, 120.0))
        elif payload.run_scaling:
            restart_delay = max(restart_delay, 3.0)

        if payload.run_alert_scaling and payload.alerts_mode == "realtime":
            restart_delay = max(restart_delay, min(float(payload.alerts_duration_seconds) + 2.0, 120.0))
        elif payload.run_alert_scaling:
            restart_delay = max(restart_delay, 3.0)

        schedule_api_restart(delay_seconds=restart_delay)
        messages.append(f"API restart planifié (+{restart_delay:.1f}s)")
    else:
        messages.append("API restart désactivé")

    return RuntimeRefreshResponse(
        started_orders=started_orders,
        orders_pid=orders_pid,
        started_alerts=started_alerts,
        alerts_pid=alerts_pid,
        synced_alerts=synced_alerts,
        scaling_mode=payload.scaling_mode,
        requests=payload.requests,
        concurrency=payload.concurrency,
        duration_seconds=payload.duration_seconds,
        rps=payload.rps,
        alerts_mode=payload.alerts_mode,
        alerts_requests=payload.alerts_requests,
        alerts_concurrency=payload.alerts_concurrency,
        alerts_duration_seconds=payload.alerts_duration_seconds,
        alerts_rps=payload.alerts_rps,
        log_file=str(RUNTIME_LOG_FILE),
        message=" | ".join(messages)
    )

@app.get("/api/runtime/logs")
async def runtime_logs(
    lines: int = Query(80, ge=1, le=500)
):
    """Retourne les dernières lignes du log runtime refresh."""
    if not RUNTIME_LOG_FILE.exists():
        return {"log_file": str(RUNTIME_LOG_FILE), "lines": []}

    with RUNTIME_LOG_FILE.open("r", encoding="utf-8") as f:
        rows = f.read().splitlines()
    return {"log_file": str(RUNTIME_LOG_FILE), "lines": rows[-lines:]}

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
