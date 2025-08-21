# 🚀 MCP Saludia MODULAR v2.5 - Archivo Principal
import os
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
import logging

# Imports modulares
from config import *
from database import get_initiatives, create_initiative
from analytics import calculate_statistics_fast, analyze_initiatives_with_llm_fast
from bot_handlers import setup_telegram_routes
from utils import setup_webhook

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app)

# Variables globales
bot_configured = False

# ===== ENDPOINTS PRINCIPALES =====

@app.route('/')
def home():
    """Endpoint principal"""
    return jsonify({
        "name": "Saludia Initiatives MCP Server MODULAR",
        "version": "2.6.0",
        "status": "running",
        "architecture": "modular",
        "modules": ["config", "database", "analytics", "bot_handlers", "utils"],
        "optimizations": ["cache_system", "fast_scoring", "reduced_timeouts", "compact_context"],
        "new_features": ["pagination", "status_filtering", "sprint_tracking", "production_monitoring"],
        "timestamp": datetime.now().isoformat(),
        "cache_status": {
            "enabled": True,
            "ttl_seconds": initiatives_cache["ttl"],
            "last_update": datetime.fromtimestamp(initiatives_cache["timestamp"]).isoformat() if initiatives_cache["timestamp"] > 0 else "never"
        },
        "telegram_bot": {
            "enabled": bool(TELEGRAM_TOKEN),
            "webhook_configured": bot_configured,
            "webhook_url": f"{WEBHOOK_URL}/telegram-webhook" if TELEGRAM_TOKEN else None
        },
        "ai_assistant": {
            "enabled": bool(GROQ_API_KEY),
            "model": GROQ_MODEL,
            "provider": "Groq"
        },
        "api_endpoints": {
            "initiatives": {
                "/api/initiatives": "Lista con paginación y filtros",
                "/api/initiatives/by-status/<status>": "Filtrar por estado específico",
                "/api/initiatives/sprint": "Iniciativas en desarrollo",
                "/api/initiatives/production": "Iniciativas implementadas",
                "/api/initiatives/active": "Todas las activas"
            },
            "analysis": {
                "/api/initiatives/statistics": "Estadísticas generales",
                "/ai/analyze-initiatives": "Análisis AI estratégico"
            }
        },
        "status_management": {
            "valid_statuses": VALID_STATUSES,
            "predefined_filters": list(STATUS_FILTERS.keys()),
            "sprint_statuses": SPRINT_STATUSES,
            "production_statuses": PRODUCTION_STATUSES
        },
        "pagination": {
            "default_limit": DEFAULT_LIMIT,
            "max_limit": MAX_LIMIT,
            "default_page_size": DEFAULT_PAGE_SIZE
        }
    })

@app.route('/health')
def health():
    """Health check optimizado"""
    import time
    start_time = time.time()
    nocodb_test = get_initiatives()
    response_time = time.time() - start_time
    
    return jsonify({
        "status": "healthy",
        "response_time_ms": round(response_time * 1000, 2),
        "cache_hit": nocodb_test.get('cached', False),
        "services": {
            "flask": "running",
            "nocodb": "ok" if nocodb_test.get('success') else "error",
            "cache": "active" if initiatives_cache["data"] else "empty",
            "telegram_bot": "configured" if bot_configured else "not_configured",
            "ai_assistant": "configured" if GROQ_API_KEY else "not_configured"
        },
        "modules_loaded": {
            "config": "✅",
            "database": "✅", 
            "analytics": "✅",
            "bot_handlers": "✅",
            "utils": "✅"
        }
    })

@app.route('/api/initiatives')
def api_initiatives():
    """API para obtener iniciativas con paginación y filtros"""
    from flask import request
    from database import sort_initiatives_by_score
    
    # Parámetros de consulta
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)
    status_filter = request.args.get('status')
    page = request.args.get('page', type=int)
    page_size = request.args.get('page_size', DEFAULT_PAGE_SIZE, type=int)
    
    # Convertir paginación por página a offset si se especifica
    if page is not None:
        offset = (page - 1) * page_size
        limit = page_size
    
    # Validar límites
    if limit and limit > MAX_LIMIT:
        limit = MAX_LIMIT
    
    # Convertir filtro de status predefinido
    if status_filter and status_filter in STATUS_FILTERS:
        status_filter = STATUS_FILTERS[status_filter]
    elif status_filter:
        # Convertir string a lista si es un status individual
        status_filter = [status_filter] if status_filter in VALID_STATUSES else None
    
    data = get_initiatives(limit, offset, status_filter)
    
    if data.get("success"):
        sorted_initiatives = sort_initiatives_by_score(data.get("data", []))
        data["data"] = sorted_initiatives
        data["performance"] = {"cached": data.get("cached", False)}
        
        # Agregar información de paginación
        if page is not None:
            data["pagination"] = {
                "page": page,
                "page_size": page_size,
                "total_pages": (data.get("total", 0) + page_size - 1) // page_size,
                "has_next": data.get("has_more", False)
            }
    
    return jsonify(data)

@app.route('/api/initiatives/by-status/<status>')
def api_initiatives_by_status(status):
    """API para obtener iniciativas por estado específico"""
    from database import get_initiatives_by_status, sort_initiatives_by_score
    
    # Manejar filtros predefinidos
    if status in STATUS_FILTERS:
        status_list = STATUS_FILTERS[status]
    elif status in VALID_STATUSES:
        status_list = [status]
    else:
        return jsonify({
            "error": f"Estado inválido: {status}",
            "valid_statuses": VALID_STATUSES,
            "predefined_filters": list(STATUS_FILTERS.keys())
        }), 400
    
    data = get_initiatives_by_status(status_list)
    
    if data.get("success"):
        sorted_initiatives = sort_initiatives_by_score(data.get("data", []))
        data["data"] = sorted_initiatives
        data["filter_applied"] = status_list
        data["performance"] = {"cached": data.get("cached", False)}
    
    return jsonify(data)

@app.route('/api/initiatives/sprint')
def api_sprint_initiatives():
    """API para obtener iniciativas en sprint (desarrollo activo)"""
    from database import get_sprint_initiatives, sort_initiatives_by_score
    
    data = get_sprint_initiatives()
    
    if data.get("success"):
        sorted_initiatives = sort_initiatives_by_score(data.get("data", []))
        data["data"] = sorted_initiatives
        data["filter_applied"] = SPRINT_STATUSES
        data["description"] = "Iniciativas en desarrollo activo"
        data["performance"] = {"cached": data.get("cached", False)}
    
    return jsonify(data)

@app.route('/api/initiatives/production')
def api_production_initiatives():
    """API para obtener iniciativas en producción/monitoreo"""
    from database import get_production_initiatives, sort_initiatives_by_score
    
    data = get_production_initiatives()
    
    if data.get("success"):
        sorted_initiatives = sort_initiatives_by_score(data.get("data", []))
        data["data"] = sorted_initiatives
        data["filter_applied"] = PRODUCTION_STATUSES
        data["description"] = "Iniciativas implementadas y en monitoreo"
        data["performance"] = {"cached": data.get("cached", False)}
    
    return jsonify(data)

@app.route('/api/initiatives/active')
def api_active_initiatives():
    """API para obtener todas las iniciativas activas"""
    from database import get_active_initiatives, sort_initiatives_by_score
    
    data = get_active_initiatives()
    
    if data.get("success"):
        sorted_initiatives = sort_initiatives_by_score(data.get("data", []))
        data["data"] = sorted_initiatives
        data["filter_applied"] = ACTIVE_STATUSES
        data["description"] = "Todas las iniciativas activas (excluye canceladas y en pausa)"
        data["performance"] = {"cached": data.get("cached", False)}
    
    return jsonify(data)

@app.route('/api/initiatives/search', methods=['GET'])
def api_search_initiatives():
    """API para buscar iniciativas"""
    from flask import request
    from database import search_initiatives
    
    query = request.args.get('q', '').strip()
    field = request.args.get('field', 'all')
    
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    
    result = search_initiatives(query, field)
    return jsonify(result)

@app.route('/api/initiatives/statistics', methods=['GET'])
def api_statistics():
    """API estadísticas optimizada"""
    data = get_initiatives()
    
    if not data.get("success"):
        return jsonify({"error": "Could not fetch initiatives"}), 500
    
    stats = calculate_statistics_fast(data.get("data", []))
    stats["performance"] = {"cached": data.get("cached", False)}
    return jsonify(stats)

@app.route('/api/create', methods=['POST'])
def api_create():
    """API crear iniciativa"""
    from flask import request
    
    if not request.json:
        return jsonify({"error": "JSON required"}), 400
    
    result = create_initiative(request.json)
    return jsonify(result)

@app.route('/ai/analyze-initiatives', methods=['POST'])
def analyze_initiatives_endpoint():
    """Endpoint análisis optimizado"""
    import time
    
    try:
        start_time = time.time()
        data = get_initiatives()
        
        if not data.get("success"):
            return jsonify({
                "success": False,
                "error": "No se pudieron obtener las iniciativas"
            }), 500
        
        initiatives = data.get("data", [])
        
        analysis = analyze_initiatives_with_llm_fast(initiatives)
        stats = calculate_statistics_fast(initiatives)
        
        response_time = time.time() - start_time
        
        return jsonify({
            "success": True,
            "initiatives_count": len(initiatives),
            "analysis": analysis,
            "statistics": stats,
            "performance": {
                "response_time_ms": round(response_time * 1000, 2),
                "cached": data.get("cached", False),
                "optimized": True
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "analysis": "Error técnico durante el análisis."
        }), 500

@app.route('/setup-webhook', methods=['POST'])
def setup_webhook_endpoint():
    """Endpoint para configurar webhook"""
    global bot_configured
    
    try:
        success = setup_webhook()
        bot_configured = success
        
        return jsonify({
            "success": success,
            "webhook_configured": bot_configured,
            "webhook_url": f"{WEBHOOK_URL}/telegram-webhook",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# ===== CONFIGURACIÓN BOT =====

# Registrar rutas del bot
setup_telegram_routes(app)

# ===== MAIN =====

if __name__ == '__main__':
    logger.info("🚀 Starting Saludia MCP Server MODULAR v2.5")
    
    # Configurar webhook
    if TELEGRAM_TOKEN:
        bot_configured = setup_webhook()
        logger.info(f"🤖 Bot webhook: {bot_configured}")
    
    # Pre-cargar cache
    try:
        logger.info("📊 Pre-loading initiatives cache...")
        get_initiatives()
        logger.info("✅ Cache pre-loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Cache pre-load failed: {e}")
    
    # Ejecutar Flask
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Starting modular Flask app on port {port}")
    logger.info("📁 Architecture: Modular with 5 specialized modules")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
