# 🔧 config.py - Configuración Central v2.6 - SECURE
import os

# ===== CONFIGURACIÓN NOCODB (Solo Variables de Entorno) =====
NOCODB_BASE_URL = os.environ.get('NOCODB_BASE_URL')
NOCODB_TABLE_ID = os.environ.get('NOCODB_TABLE_ID') 
NOCODB_TOKEN = os.environ.get('NOCODB_TOKEN')

# ===== CONFIGURACIÓN TELEGRAM (Solo Variables de Entorno) =====
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

# ===== CONFIGURACIÓN LLM =====
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = "llama-3.1-8b-instant"

# ===== CONFIGURACIÓN CACHE =====
initiatives_cache = {
    "data": None, 
    "timestamp": 0, 
    "ttl": 300  # 5 minutos
}

# ===== CONFIGURACIÓN VALIDACIÓN =====
VALID_TEAMS = ['Product', 'Sales', 'Ops', 'CS', 'Controlling', 'Growth']
VALID_PORTALS = ['Seller', 'Droguista', 'Admin']

# ===== ESTADOS DE INICIATIVAS =====
VALID_STATUSES = ['Pending', 'In Sprint', 'Production', 'Monitoring', 'Cancelled', 'On Hold']
ACTIVE_STATUSES = ['Pending', 'In Sprint', 'Production', 'Monitoring']
SPRINT_STATUSES = ['In Sprint']
PRODUCTION_STATUSES = ['Production', 'Monitoring']

# ===== CONFIGURACIÓN PAGINACIÓN =====
DEFAULT_LIMIT = 1000  # Límite por defecto aumentado
MAX_LIMIT = 1000      # Límite máximo permitido
DEFAULT_PAGE_SIZE = 50 # Tamaño de página para endpoints paginados

# ===== CONFIGURACIÓN TIMEOUTS =====
NOCODB_TIMEOUT = 15  # segundos
TELEGRAM_TIMEOUT = 8  # segundos
LLM_TIMEOUT = 20     # segundos
WEBHOOK_TIMEOUT = 8  # segundos

# ===== CONFIGURACIÓN LLM =====
LLM_MAX_TOKENS = 600
LLM_TEMPERATURE = 0.6
LLM_CONTEXT_LIMIT = 1500

# ===== CONFIGURACIÓN BOT =====
MAX_RESULTS_SEARCH = 10   # Aumentado de 3 a 10 para mejor experiencia
MAX_RESULTS_LIST = 10
MAX_MESSAGE_LENGTH = 4000

# ===== VALIDACIONES CAMPOS =====
MAX_INITIATIVE_NAME = 255
MAX_DESCRIPTION = 1000
MAX_OWNER_NAME = 100
MAX_KPI_LENGTH = 255

# ===== FILTROS PREDEFINIDOS =====
STATUS_FILTERS = {
    'active': ACTIVE_STATUSES,
    'sprint': SPRINT_STATUSES,
    'production': PRODUCTION_STATUSES,
    'pending': ['Pending'],
    'cancelled': ['Cancelled'],
    'on_hold': ['On Hold']
}
