# 🔧 utils.py - Utilidades y Helpers v2.5
import requests
import logging
from config import *

logger = logging.getLogger(__name__)

def send_telegram_message(chat_id, text, parse_mode=None):
    """Enviar mensaje optimizado"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        response = requests.post(url, json=data, timeout=TELEGRAM_TIMEOUT)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Telegram error: {e}")
        return False

def setup_webhook():
    """Configurar webhook optimizado"""
    try:
        # Delete webhook primero
        delete_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook"
        requests.post(delete_url, timeout=WEBHOOK_TIMEOUT)
        
        # Set nuevo webhook
        webhook_url = f"{WEBHOOK_URL}/telegram-webhook"
        set_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
        data = {"url": webhook_url}
        
        response = requests.post(set_url, json=data, timeout=WEBHOOK_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                logger.info(f"✅ Webhook configured: {webhook_url}")
                return True
        
        logger.error(f"❌ Webhook setup failed")
        return False
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return False

def validate_telegram_token():
    """Validar token de Telegram"""
    if not TELEGRAM_TOKEN:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
        response = requests.get(url, timeout=WEBHOOK_TIMEOUT)
        return response.status_code == 200 and response.json().get('ok', False)
    except:
        return False

def validate_groq_api():
    """Validar API de Groq"""
    if not GROQ_API_KEY:
        return False
    
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        response = requests.get(url, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

def truncate_text(text, max_length=MAX_MESSAGE_LENGTH):
    """Truncar texto para Telegram"""
    if len(text) <= max_length:
        return [text]
    
    # Dividir en chunks respetando palabras
    chunks = []
    current_chunk = ""
    
    words = text.split(' ')
    
    for word in words:
        if len(current_chunk) + len(word) + 1 <= max_length:
            current_chunk += word + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = word + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def format_error_message(error, context=""):
    """Formatear mensaje de error para usuario"""
    error_str = str(error)
    
    # Errores comunes y sus traducciones
    error_mappings = {
        "timeout": "⏱️ Tiempo de espera agotado. Intenta nuevamente.",
        "connection": "🔌 Error de conexión. Verifica tu internet.",
        "validation": "⚠️ Error de validación en los datos.",
        "unauthorized": "🔐 Error de autorización. Contacta soporte.",
        "not found": "🔍 Recurso no encontrado.",
        "server error": "🖥️ Error del servidor. Intenta más tarde."
    }
    
    for key, message in error_mappings.items():
        if key in error_str.lower():
            return f"{message}\n\n**Contexto:** {context}" if context else message
    
    return f"❌ Error: {error_str}\n\n**Contexto:** {context}" if context else f"❌ Error: {error_str}"

def get_priority_emoji(score):
    """Obtener emoji de prioridad basado en score"""
    if score >= 2.0:
        return "🔥"  # Alta prioridad
    elif score >= 1.0:
        return "⭐"  # Media prioridad
    else:
        return "📋"  # Baja prioridad

def get_priority_text(score):
    """Obtener texto de prioridad basado en score"""
    if score >= 2.0:
        return "Alta"
    elif score >= 1.0:
        return "Media"
    else:
        return "Baja"

def format_percentage(value, decimals=1):
    """Formatear porcentaje"""
    try:
        return f"{float(value):.{decimals}f}%"
    except:
        return "N/A"

def format_score(score, decimals=2):
    """Formatear score RICE"""
    try:
        return f"{float(score):.{decimals}f}"
    except:
        return "N/A"

def clean_text(text, max_length=None):
    """Limpiar y truncar texto"""
    if not text:
        return "N/A"
    
    # Limpiar caracteres especiales
    cleaned = str(text).strip()
    
    # Truncar si es necesario
    if max_length and len(cleaned) > max_length:
        return cleaned[:max_length-3] + "..."
    
    return cleaned

def validate_numeric_input(value, min_val=None, max_val=None, allow_zero=True):
    """Validar entrada numérica"""
    try:
        num = float(value)
        
        if not allow_zero and num == 0:
            return False, "El valor no puede ser cero"
        
        if min_val is not None and num < min_val:
            return False, f"El valor debe ser mayor o igual a {min_val}"
        
        if max_val is not None and num > max_val:
            return False, f"El valor debe ser menor o igual a {max_val}"
        
        return True, num
    except ValueError:
        return False, "Debe ser un número válido"

def format_time_ago(timestamp):
    """Formatear tiempo transcurrido"""
    import time
    from datetime import datetime
    
    try:
        if timestamp == 0:
            return "Nunca"
        
        now = time.time()
        diff = now - timestamp
        
        if diff < 60:
            return f"{int(diff)}s"
        elif diff < 3600:
            return f"{int(diff/60)}m"
        elif diff < 86400:
            return f"{int(diff/3600)}h"
        else:
            return f"{int(diff/86400)}d"
    except:
        return "N/A"

def get_team_emoji(team):
    """Obtener emoji para equipo"""
    team_emojis = {
        'Product': '🛠️',
        'Sales': '💼',
        'Ops': '⚙️',
        'CS': '🎧',
        'Controlling': '📊',
        'Growth': '📈'
    }
    return team_emojis.get(team, '👥')

def get_portal_emoji(portal):
    """Obtener emoji para portal"""
    portal_emojis = {
        'Seller': '🏪',
        'Droguista': '💊',
        'Admin': '🔧'
    }
    return portal_emojis.get(portal, '🖥️')

def log_performance(func_name, start_time, additional_info=""):
    """Log de performance para debugging"""
    import time
    end_time = time.time()
    duration = (end_time - start_time) * 1000  # en ms
    
    if duration > 1000:  # > 1 segundo
        logger.warning(f"⚠️ SLOW: {func_name} took {duration:.1f}ms {additional_info}")
    else:
        logger.info(f"✅ {func_name} completed in {duration:.1f}ms {additional_info}")
    
    return duration

def safe_get(dictionary, key, default="N/A"):
    """Obtener valor de diccionario de forma segura"""
    try:
        value = dictionary.get(key, default)
        return value if value is not None else default
    except:
        return default

def format_initiative_quick(initiative):
    """Formateo rápido de iniciativa para logs"""
    try:
        name = safe_get(initiative, 'initiative_name', 'Unknown')
        team = safe_get(initiative, 'team', 'No team')
        score = safe_get(initiative, 'score', 0)
        return f"{name} ({team}) - Score: {score}"
    except:
        return "Invalid initiative data"

def batch_process(items, batch_size=10):
    """Procesar items en lotes"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]