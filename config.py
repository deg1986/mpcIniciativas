# 🔧 config.py - Configuración Central v2.6 - FIXED & SECURE
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== CONFIGURACIÓN NOCODB (Solo Variables de Entorno) =====
NOCODB_BASE_URL = os.environ.get('NOCODB_BASE_URL')
NOCODB_TABLE_ID = os.environ.get('NOCODB_TABLE_ID') 
NOCODB_TOKEN = os.environ.get('NOCODB_TOKEN')

# Validar configuración crítica
if not NOCODB_BASE_URL:
    logger.warning("⚠️ NOCODB_BASE_URL not configured")
if not NOCODB_TABLE_ID:
    logger.warning("⚠️ NOCODB_TABLE_ID not configured")
if not NOCODB_TOKEN:
    logger.warning("⚠️ NOCODB_TOKEN not configured")

# ===== CONFIGURACIÓN TELEGRAM (Solo Variables de Entorno) =====
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

# ===== CONFIGURACIÓN LLM =====
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = "llama-3.1-8b-instant"

# Log AI configuration status
if GROQ_API_KEY:
    logger.info("✅ Groq AI configured")
else:
    logger.warning("⚠️ Groq AI not configured - AI analysis will be disabled")

# ===== CONFIGURACIÓN CACHE - OPTIMIZED =====
initiatives_cache = {
    "data": None, 
    "timestamp": 0, 
    "ttl": 300  # 5 minutos - reducido para datos más frescos
}

# ===== CONFIGURACIÓN VALIDACIÓN =====
VALID_TEAMS = ['Product', 'Sales', 'Ops', 'CS', 'Controlling', 'Growth']
VALID_PORTALS = ['Seller', 'Droguista', 'Admin']

# ===== ESTADOS DE INICIATIVAS - REALES DE LA DB =====
VALID_STATUSES = ['Pending', 'Reviewed', 'Prioritized', 'Backlog', 'Sprint', 'Production', 'Monitoring', 'Discarded']
ACTIVE_STATUSES = ['Pending', 'Reviewed', 'Prioritized', 'Backlog', 'Sprint', 'Production', 'Monitoring']
SPRINT_STATUSES = ['Sprint']
PRODUCTION_STATUSES = ['Production', 'Monitoring']

# ===== CONFIGURACIÓN PAGINACIÓN =====
DEFAULT_LIMIT = 1000  # Límite por defecto
MAX_LIMIT = 1000      # Límite máximo permitido
DEFAULT_PAGE_SIZE = 50 # Tamaño de página para endpoints paginados

# ===== CONFIGURACIÓN TIMEOUTS - REDUCED FOR BETTER PERFORMANCE =====
NOCODB_TIMEOUT = 10   # Reducido de 15 a 10 segundos
TELEGRAM_TIMEOUT = 5  # Reducido de 8 a 5 segundos
LLM_TIMEOUT = 15      # Reducido de 20 a 15 segundos
WEBHOOK_TIMEOUT = 5   # Reducido de 8 a 5 segundos

# ===== CONFIGURACIÓN LLM - OPTIMIZED =====
LLM_MAX_TOKENS = 800  # Aumentado para análisis más completo
LLM_TEMPERATURE = 0.7 # Ligeramente más creativo para mejores insights
LLM_CONTEXT_LIMIT = 2000  # Aumentado para más contexto

# ===== CONFIGURACIÓN BOT - OPTIMIZED =====
MAX_RESULTS_SEARCH = 8   # Reducido de 10 a 8 para mejor performance
MAX_RESULTS_LIST = 10    # Mantenido en 10
MAX_MESSAGE_LENGTH = 4000 # Telegram limit

# ===== VALIDACIONES CAMPOS =====
MAX_INITIATIVE_NAME = 255
MAX_DESCRIPTION = 1000
MAX_OWNER_NAME = 100
MAX_KPI_LENGTH = 255

# ===== FILTROS PREDEFINIDOS - SEGÚN DB REAL =====
STATUS_FILTERS = {
    'active': ACTIVE_STATUSES,
    'pending': ['Pending'],
    'reviewed': ['Reviewed'],
    'prioritized': ['Prioritized'],
    'backlog': ['Backlog'],
    'sprint': ['Sprint'],
    'production': ['Production'],
    'monitoring': ['Monitoring'],
    'discarded': ['Discarded']
}

# ===== CONFIGURACIÓN GROWTH-SPECIFIC =====
GROWTH_FOCUS_TEAMS = ['Growth', 'Product', 'Sales']  # Teams más relevantes para growth
GROWTH_KPIS = ['GMV', 'Conversion Rate', 'Take Rate', 'User Retention', 'NPS', 'CAC', 'LTV']
MARKETPLACE_PORTALS = ['Seller', 'Droguista']  # Portales principales del marketplace

# ===== CONFIGURACIÓN DE PERFORMANCE =====
PERFORMANCE_THRESHOLDS = {
    'db_query_warning': 5.0,      # Warn if DB query takes > 5s
    'ai_analysis_warning': 20.0,  # Warn if AI analysis takes > 20s
    'bot_response_warning': 10.0, # Warn if bot response takes > 10s
    'cache_hit_rate_min': 0.6     # Minimum cache hit rate
}

# ===== CONFIGURACIÓN DE RETRY =====
RETRY_CONFIG = {
    'max_attempts': 3,
    'base_delay': 1.0,    # Base delay between retries (seconds)
    'max_delay': 10.0,    # Maximum delay between retries
    'backoff_factor': 2.0 # Exponential backoff factor
}

# ===== HEALTH CHECK ENDPOINTS =====
HEALTH_CHECKS = {
    'nocodb': True,
    'groq_ai': bool(GROQ_API_KEY),
    'telegram': bool(TELEGRAM_TOKEN),
    'cache': True
}

# ===== LOG CONFIGURATION =====
LOG_CONFIG = {
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'level': logging.INFO,
    'performance_logging': True,  # Log performance metrics
    'error_tracking': True,       # Track errors with context
    'cache_logging': True         # Log cache hits/misses
}

# ===== FEATURE FLAGS =====
FEATURES = {
    'ai_analysis': bool(GROQ_API_KEY),
    'telegram_bot': bool(TELEGRAM_TOKEN),
    'growth_focus': True,         # Enable growth-specific features
    'performance_monitoring': True,
    'cache_optimization': True,
    'timeout_protection': True,
    'retry_mechanism': True
}

# ===== SALUDIA BUSINESS CONTEXT =====
SALUDIA_CONTEXT = {
    'business_model': 'B2B Marketplace',
    'industry': 'Pharmaceutical/Healthcare',
    'stakeholders': ['Droguerías', 'Sellers', 'Laboratorios'],
    'key_metrics': ['GMV', 'Take Rate', 'Active Users', 'Order Frequency', 'NPS'],
    'growth_priorities': [
        'User Acquisition (Droguerías)',
        'Seller Activation', 
        'Order Frequency',
        'Average Order Value',
        'Geographic Expansion'
    ],
    'market_focus': 'LatAm',
    'mission': 'Democratizar acceso a productos farmacéuticos'
}

# ===== RICE METHODOLOGY CONFIG =====
RICE_CONFIG = {
    'score_thresholds': {
        'high_priority': 2.0,    # 🔥 High priority
        'medium_priority': 1.0,  # ⭐ Medium priority
        'low_priority': 0.0      # 📋 Low priority
    },
    'default_values': {
        'reach': 0.0,
        'impact': 1,
        'confidence': 0.0,
        'effort': 1.0
    },
    'validation_ranges': {
        'reach': (0.0, 1.0),
        'impact': [1, 2, 3],
        'confidence': (0.0, 1.0),
        'effort': (0.1, 100.0)  # Minimum 0.1 to avoid division by zero
    }
}

# ===== ERROR MESSAGES =====
ERROR_MESSAGES = {
    'nocodb_connection': "❌ Error de conexión con base de datos",
    'timeout': "⏱️ Operación tardó demasiado tiempo",
    'validation': "⚠️ Datos inválidos",
    'ai_unavailable': "🤖 Análisis AI no disponible",
    'insufficient_data': "📊 Datos insuficientes para análisis",
    'cache_miss': "💾 Error accediendo cache",
    'unknown': "❓ Error desconocido"
}

# ===== SUCCESS MESSAGES =====
SUCCESS_MESSAGES = {
    'initiative_created': "✅ Iniciativa creada exitosamente",
    'analysis_complete': "📊 Análisis completado",
    'data_updated': "🔄 Datos actualizados",
    'cache_refreshed': "💾 Cache actualizado"
}

# ===== TELEGRAM COMMAND MAPPING =====
TELEGRAM_COMMANDS = {
    # Basic commands
    'start': ['start', 'inicio', 'hola'],
    'help': ['help', 'ayuda', 'comandos'],
    'initiatives': ['iniciativas', 'lista', 'proyectos'],
    'create': ['crear', 'nueva', 'nuevo'],
    'analyze': ['analizar', 'análisis'],
    'search': ['buscar', 'encontrar'],
    
    # Status filters
    'pending': ['pending', 'pendiente', 'pendientes'],
    'sprint': ['sprint', 'desarrollo', 'dev'],
    'production': ['production', 'produccion', 'prod'],
    'monitoring': ['monitoring', 'monitoreo'],
    
    # Growth-specific
    'growth': ['growth', 'crecimiento', 'crecer'],
    'stats': ['estadisticas', 'stats', 'métricas']
}

# ===== API ENDPOINT MAPPING =====
API_ENDPOINTS = {
    'initiatives': '/api/initiatives',
    'statistics': '/api/initiatives/statistics', 
    'search': '/api/initiatives/search',
    'create': '/api/create',
    'analyze': '/ai/analyze-initiatives',
    'health': '/health',
    'webhook_setup': '/setup-webhook'
}

# ===== GROWTH ANALYSIS PROMPTS =====
GROWTH_PROMPTS = {
    'general_analysis': """
    Analiza el portfolio de iniciativas de Saludia con enfoque en GROWTH y crecimiento del marketplace farmacéutico.
    
    Prioriza:
    1. Iniciativas que maximicen GMV y retención
    2. Balance entre adquisición (droguerías) y activación (sellers)
    3. Optimización del embudo de conversión
    4. Experiencia del usuario en ambos portales
    
    Proporciona insights accionables para el equipo de Growth.
    """,
    
    'growth_specific': """
    Enfócate específicamente en las iniciativas del equipo Growth de Saludia.
    
    Evalúa:
    - Potencial de impacto en GMV
    - Estrategias de adquisición vs retención
    - Gaps en la estrategia de crecimiento
    - ROI esperado de cada iniciativa
    
    Recomienda acciones concretas para maximizar el crecimiento del marketplace.
    """,
    
    'portfolio_balance': """
    Analiza el balance del portfolio de iniciativas considerando el objetivo de growth de Saludia.
    
    Considera:
    - Distribución entre equipos y su impacto en crecimiento
    - Iniciativas complementarias entre Product, Sales y Growth
    - Gaps en la estrategia general de marketplace
    - Oportunidades de sinergia entre iniciativas
    """
}

# ===== MONITORING METRICS =====
MONITORING_METRICS = {
    'performance': {
        'response_time_p95': 5.0,      # 95th percentile response time
        'error_rate_max': 0.05,        # Maximum 5% error rate
        'cache_hit_rate_min': 0.7,     # Minimum 70% cache hit rate
        'timeout_rate_max': 0.02       # Maximum 2% timeout rate
    },
    'business': {
        'initiatives_created_daily': 5,
        'analysis_requests_daily': 20,
        'search_queries_daily': 50,
        'active_users_weekly': 10
    }
}

# ===== RATE LIMITING =====
RATE_LIMITS = {
    'api_requests_per_minute': 60,
    'ai_analysis_per_hour': 10,
    'search_queries_per_minute': 30,
    'initiative_creation_per_hour': 5
}

# Log successful configuration
def log_configuration_status():
    """Log configuration status on startup"""
    config_status = []
    
    # Database
    if NOCODB_BASE_URL and NOCODB_TABLE_ID and NOCODB_TOKEN:
        config_status.append("✅ NocoDB configured")
    else:
        config_status.append("❌ NocoDB incomplete")
    
    # AI
    if GROQ_API_KEY:
        config_status.append("✅ AI analysis enabled")
    else:
        config_status.append("⚠️ AI analysis disabled")
    
    # Telegram
    if TELEGRAM_TOKEN:
        config_status.append("✅ Telegram bot enabled")
    else:
        config_status.append("⚠️ Telegram bot disabled")
    
    # Features
    enabled_features = [k for k, v in FEATURES.items() if v]
    config_status.append(f"✅ Features: {', '.join(enabled_features)}")
    
    logger.info("🔧 Configuration Status:")
    for status in config_status:
        logger.info(f"   {status}")
    
    return config_status

# Export configuration summary
def get_config_summary():
    """Get configuration summary for API endpoints"""
    return {
        "version": "2.6-fixed",
        "focus": "Growth-oriented initiatives for Saludia marketplace",
        "features": FEATURES,
        "performance": {
            "timeouts": {
                "nocodb": NOCODB_TIMEOUT,
                "llm": LLM_TIMEOUT,
                "telegram": TELEGRAM_TIMEOUT
            },
            "cache_ttl": initiatives_cache["ttl"],
            "retry_config": RETRY_CONFIG
        },
        "business_context": SALUDIA_CONTEXT,
        "rice_config": RICE_CONFIG,
        "valid_teams": VALID_TEAMS,
        "valid_portals": VALID_PORTALS,
        "valid_statuses": VALID_STATUSES
    }

# Validate critical configuration on import
if __name__ == "__main__":
    log_configuration_status()
