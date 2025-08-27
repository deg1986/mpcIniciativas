# 🗄️ database.py - Gestión de Datos v2.6 - FIXED - NO HANGING
import requests
import logging
import time
import signal
from functools import wraps
from config import *

logger = logging.getLogger(__name__)

class TimeoutError(Exception):
    """Custom timeout exception"""
    pass

def timeout_handler(signum, frame):
    """Handler for timeout signal"""
    raise TimeoutError("Operation timed out")

def with_timeout(seconds=15):
    """Decorator to add timeout to functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set the signal handler
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
        logger.warning(f"Error getting {key}: {e}")
        return default

@with_timeout(NOCODB_TIMEOUT)
def get_cached_initiatives(limit=None, offset=None, status_filter=None):
    """Obtener iniciativas con cache, paginación y filtros optimizado - FIXED VERSION"""
    current_time = time.time()
    
    # Para requests con filtros específicos, no usar cache
    use_cache = (limit is None and offset is None and status_filter is None)
    
    # Verificar cache solo para requests completos
    if (use_cache and initiatives_cache["data"] is not None and 
        current_time - initiatives_cache["timestamp"] < initiatives_cache["ttl"]):
        logger.info("✅ Using cached initiatives data")
        return {"success": True, "data": initiatives_cache["data"], "cached": True, "total": len(initiatives_cache["data"])}
    
    # Fetch fresh data with timeout protection
    try:
        if not NOCODB_BASE_URL or not NOCODB_TABLE_ID or not NOCODB_TOKEN:
            logger.error("❌ NocoDB configuration missing")
            return {"success": False, "error": "NocoDB configuration missing"}
        
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {'accept': 'application/json', 'xc-token': NOCODB_TOKEN}
        
        # Parámetros de consulta
        params = {'limit': limit or DEFAULT_LIMIT}
        
        if offset:
            params['offset'] = offset
            
        # FIX: Filtro por status usando sintaxis correcta de NocoDB con URL encoding
        if status_filter:
            if isinstance(status_filter, list):
                if len(status_filter) == 1:
                    # Un solo estado - URL encoded
                    params['where'] = f"(status,eq,{status_filter[0]})"
                else:
                    # Múltiples estados - usar OR con paréntesis
                    conditions = []
                    for status in status_filter:
                        conditions.append(f"(status,eq,{status})")
                    params['where'] = "(" + ",or,".join(conditions) + ")"
            else:
                # Para un solo estado
                params['where'] = f"(status,eq,{status_filter})"
        
        logger.info(f"🔍 NocoDB Query: {url} with params: {params}")
        
        # REQUEST WITH SHORTER TIMEOUT TO AVOID HANGING
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        logger.info(f"📡 NocoDB Response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            initiatives = data.get('list', [])
            total_count = data.get('pageInfo', {}).get('totalRows', len(initiatives))
            
            # Process initiatives safely to avoid None.strip() errors
            processed_initiatives = []
            for init in initiatives:
                try:
                    if not isinstance(init, dict):
                        continue
                        
                    processed_init = {
                        'id': safe_get_value(init, 'id', 0, int),
                        'initiative_name': safe_get_value(init, 'initiative_name', 'Sin nombre', str),
                        'description': safe_get_value(init, 'description', 'Sin descripción', str),
                        'owner': safe_get_value(init, 'owner', 'Sin owner', str),
                        'team': safe_get_value(init, 'team', 'Sin equipo', str),
                        'portal': safe_get_value(init, 'portal', 'Sin portal', str),
                        'main_kpi': safe_get_value(init, 'main_kpi', 'Sin KPI', str),
                        'reach': safe_get_value(init, 'reach', 0.0, float),
                        'impact': safe_get_value(init, 'impact', 1, int),
                        'confidence': safe_get_value(init, 'confidence', 0.0, float),
                        'effort': safe_get_value(init, 'effort', 1.0, float),
                        'status': safe_get_value(init, 'status', 'Pending', str),
                        'must_have': safe_get_value(init, 'must_have', False, bool)
                    }
                    
                    # Calculate RICE score safely
                    processed_init['score'] = calculate_score_fast(processed_init)
                    processed_init['calculated_score'] = processed_init['score']
                    
                    processed_initiatives.append(processed_init)
                    
                except Exception as e:
                    logger.warning(f"Error processing initiative {init}: {e}")
                    continue
            
            # Actualizar cache solo para requests completos sin filtros
            if use_cache:
                initiatives_cache["data"] = processed_initiatives
                initiatives_cache["timestamp"] = current_time
                logger.info(f"✅ Retrieved {len(processed_initiatives)} initiatives from NocoDB (fresh, cached)")
            else:
                logger.info(f"✅ Retrieved {len(processed_initiatives)} initiatives from NocoDB (fresh, filtered)")
            
            return {
                "success": True, 
                "data": processed_initiatives, 
                "cached": False,
                "total": total_count,
                "limit": params.get('limit'),
                "offset": params.get('offset', 0),
                "has_more": len(processed_initiatives) == params.get('limit', DEFAULT_LIMIT),
                "filter_applied": status_filter
            }
        else:
            logger.error(f"❌ NocoDB HTTP {response.status_code}: {response.text}")
            # Fallback a cache solo para requests completos
            if use_cache and initiatives_cache["data"] is not None:
                logger.info("⚠️ Using expired cache due to API error")
                return {"success": True, "data": initiatives_cache["data"], "cached": True, "total": len(initiatives_cache["data"])}
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except requests.exceptions.Timeout:
        logger.error("❌ NocoDB request timeout")
        # Fallback a cache expirado solo para requests completos
        if use_cache and initiatives_cache["data"] is not None:
            logger.info("⚠️ Using expired cache due to timeout")
            return {"success": True, "data": initiatives_cache["data"], "cached": True, "total": len(initiatives_cache["data"])}
        return {"success": False, "error": "Request timeout"}
        
    except TimeoutError:
        logger.error("❌ NocoDB operation timeout")
        if use_cache and initiatives_cache["data"] is not None:
            logger.info("⚠️ Using expired cache due to operation timeout")
            return {"success": True, "data": initiatives_cache["data"], "cached": True, "total": len(initiatives_cache["data"])}
        return {"success": False, "error": "Operation timeout"}
        
    except Exception as e:
        logger.error(f"❌ Error fetching initiatives: {e}")
        # Fallback a cache expirado solo para requests completos
        if use_cache and initiatives_cache["data"] is not None:
            logger.info("⚠️ Using expired cache due to exception")
            return {"success": True, "data": initiatives_cache["data"], "cached": True, "total": len(initiatives_cache["data"])}
        return {"success": False, "error": str(e)}

# Alias para compatibilidad - ahora soporta parámetros con timeout
def get_initiatives(limit=None, offset=None, status_filter=None):
    """Get initiatives with timeout protection"""
    try:
        return get_cached_initiatives(limit, offset, status_filter)
    except Exception as e:
        logger.error(f"❌ get_initiatives error: {e}")
        return {"success": False, "error": str(e)}

def calculate_score_fast(initiative):
    """Calcular score RICE optimizado y seguro"""
    try:
        if not initiative or not isinstance(initiative, dict):
            return 0.0
            
        # Si ya tiene score, usarlo
        existing_score = safe_get_value(initiative, 'score', None, float)
        if existing_score is not None and existing_score > 0:
            return existing_score
        
        # Calcular rápido con valores seguros
        reach = safe_get_value(initiative, 'reach', 0.0, float)
        impact = safe_get_value(initiative, 'impact', 1.0, float)
        confidence = safe_get_value(initiative, 'confidence', 0.0, float)
        effort = safe_get_value(initiative, 'effort', 1.0, float)
        
        # Ensure effort is never zero
        if effort <= 0:
            effort = 1.0
        
        if reach > 0 and impact > 0 and confidence > 0:
            score = (reach * impact * confidence) / effort
            initiative['calculated_score'] = round(score, 4)
            return round(score, 4)
        else:
            initiative['calculated_score'] = 0.0
            return 0.0
            
    except Exception as e:
        logger.warning(f"Error calculating score: {e}")
        if isinstance(initiative, dict):
            initiative['calculated_score'] = 0.0
        return 0.0

def sort_initiatives_by_score(initiatives):
    """Ordenar iniciativas por score optimizado y seguro"""
    try:
        if not initiatives:
            return []
        
        # Filter out invalid initiatives
        valid_initiatives = [init for init in initiatives if isinstance(init, dict)]
        
        # Sort by score (descending)
        return sorted(valid_initiatives, key=lambda x: calculate_score_fast(x), reverse=True)
        
    except Exception as e:
        logger.error(f"❌ Error sorting initiatives: {e}")
        return initiatives if initiatives else []

@with_timeout(NOCODB_TIMEOUT)
def get_initiatives_by_status(status_list):
    """Obtener iniciativas filtradas por estado(s) con timeout"""
    try:
        if isinstance(status_list, str):
            status_list = [status_list]
        
        # Validar estados
        valid_statuses = [s for s in status_list if s in VALID_STATUSES]
        
        if not valid_statuses:
            return {"success": False, "error": f"Estados inválidos. Válidos: {VALID_STATUSES}", "results": []}
        
        return get_cached_initiatives(status_filter=valid_statuses)
        
    except Exception as e:
        logger.error(f"❌ Error getting initiatives by status: {e}")
        return {"success": False, "error": str(e)}

def get_sprint_initiatives():
    """Obtener iniciativas en sprint (desarrollo activo) con timeout"""
    return get_initiatives_by_status(SPRINT_STATUSES)

def get_production_initiatives():
    """Obtener iniciativas en producción/monitoreo con timeout"""
    return get_initiatives_by_status(PRODUCTION_STATUSES)

def get_active_initiatives():
    """Obtener todas las iniciativas activas con timeout"""
    return get_initiatives_by_status(ACTIVE_STATUSES)

def validate_initiative_data(data):
    """Validar datos de iniciativa optimizado y seguro"""
    try:
        if not data or not isinstance(data, dict):
            return {"valid": False, "errors": ["Datos inválidos"]}
        
        errors = []
        
        # Campos requeridos
        required_fields = ['initiative_name', 'description', 'portal', 'owner', 'team', 'reach', 'impact', 'confidence']
        
        for field in required_fields:
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Campo '{field}' es requerido")
        
        if errors:
            return {"valid": False, "errors": errors}
        
        # Validaciones rápidas y seguras
        validations = [
            (len(safe_get_value(data, 'initiative_name', '', str)) <= MAX_INITIATIVE_NAME, f"Nombre debe tener máximo {MAX_INITIATIVE_NAME} caracteres"),
            (len(safe_get_value(data, 'description', '', str)) <= MAX_DESCRIPTION, f"Descripción debe tener máximo {MAX_DESCRIPTION} caracteres"),
            (len(safe_get_value(data, 'owner', '', str)) <= MAX_OWNER_NAME, f"Owner debe tener máximo {MAX_OWNER_NAME} caracteres"),
            (safe_get_value(data, 'portal', '', str) in VALID_PORTALS, f"Portal debe ser: {', '.join(VALID_PORTALS)}"),
            (safe_get_value(data, 'team', '', str) in VALID_TEAMS, f"Equipo debe ser: {', '.join(VALID_TEAMS)}")
        ]
        
        for condition, error_msg in validations:
            if not condition:
                errors.append(error_msg)
        
        # Validar métricas numéricas de forma segura
        try:
            reach = safe_get_value(data, 'reach', 0.0, float)
            if not (0 <= reach <= 1):
                errors.append("Reach debe estar entre 0 y 1")
            data['reach'] = reach
        except:
            errors.append("Reach debe ser un número entre 0 y 1")
        
        try:
            impact = safe_get_value(data, 'impact', 1, int)
            if impact not in [1, 2, 3]:
                errors.append("Impact debe ser 1, 2 o 3")
            data['impact'] = impact
        except:
            errors.append("Impact debe ser 1, 2 o 3")
        
        try:
            confidence = safe_get_value(data, 'confidence', 0.0, float)
            if not (0 <= confidence <= 1):
                errors.append("Confidence debe estar entre 0 y 1")
            data['confidence'] = confidence
        except:
            errors.append("Confidence debe ser un número entre 0 y 1")
        
        # Valores opcionales
        data['effort'] = safe_get_value(data, 'effort', 1.0, float)
        if data['effort'] <= 0:
            data['effort'] = 1.0
            
        data['must_have'] = safe_get_value(data, 'must_have', False, bool)
        
        return {"valid": len(errors) == 0, "errors": errors, "data": data}
        
    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        return {"valid": False, "errors": [f"Error de validación: {str(e)}"]}

@with_timeout(NOCODB_TIMEOUT)
def create_initiative(data):
    """Crear iniciativa optimizada con timeout"""
    try:
        validation_result = validate_initiative_data(data)
        
        if not validation_result["valid"]:
            return {
                "success": False, 
                "error": "Datos inválidos", 
                "validation_errors": validation_result["errors"]
            }
        
        validated_data = validation_result["data"]
        
        # Preparar datos para NocoDB de forma segura
        nocodb_data = {
            "initiative_name": safe_get_value(validated_data, "initiative_name", "", str),
            "description": safe_get_value(validated_data, "description", "", str),
            "portal": safe_get_value(validated_data, "portal", "", str),
            "owner": safe_get_value(validated_data, "owner", "", str),
            "team": safe_get_value(validated_data, "team", "", str),
            "reach": safe_get_value(validated_data, "reach", 0.0, float),
            "impact": safe_get_value(validated_data, "impact", 1, int),
            "confidence": safe_get_value(validated_data, "confidence", 0.0, float),
            "effort": safe_get_value(validated_data, "effort", 1.0, float),
            "must_have": safe_get_value(validated_data, "must_have", False, bool)
        }
        
        if validated_data.get("main_kpi"):
            nocodb_data["main_kpi"] = safe_get_value(validated_data, "main_kpi", "", str)
        
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {
            'accept': 'application/json',
            'xc-token': NOCODB_TOKEN,
            'Content-Type': 'application/json'
        }
        
        # Request with timeout
        response = requests.post(url, headers=headers, json=nocodb_data, timeout=10)
        
        if response.status_code in [200, 201]:
            # Invalidar cache
            initiatives_cache["timestamp"] = 0
            logger.info(f"✅ Created initiative: {validated_data.get('initiative_name', 'Unknown')}")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"❌ Create failed HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except requests.exceptions.Timeout:
        logger.error("❌ Create initiative timeout")
        return {"success": False, "error": "Request timeout"}
        
    except TimeoutError:
        logger.error("❌ Create initiative operation timeout")
        return {"success": False, "error": "Operation timeout"}
        
    except Exception as e:
        logger.error(f"❌ Error creating initiative: {e}")
        return {"success": False, "error": str(e)}

def search_initiatives(query, field="all"):
    """Buscar iniciativas optimizado con timeout protection"""
    try:
        start_time = time.time()
        
        data = get_initiatives()
        
        if not data.get("success"):
            return {"success": False, "error": data.get("error"), "results": []}
        
        initiatives = data.get("data", [])
        if not initiatives:
            return {"success": True, "results": [], "total": 0}
        
        query_lower = query.lower()
        
        search_fields = {
            "all": ['initiative_name', 'description', 'owner', 'team', 'main_kpi', 'portal'],
            "name": ['initiative_name'],
            "owner": ['owner'],
            "team": ['team'],
            "kpi": ['main_kpi'],
            "portal": ['portal'],
            "description": ['description']
        }
        
        fields_to_search = search_fields.get(field, search_fields["all"])
        
        # Búsqueda optimizada y segura
        matching = []
        for initiative in initiatives:
            if not isinstance(initiative, dict):
                continue
            
            try:
                for field_name in fields_to_search:
                    field_value = safe_get_value(initiative, field_name, "", str)
                    if query_lower in field_value.lower():
                        matching.append(initiative)
                        break
            except Exception as e:
                logger.warning(f"Error searching in initiative: {e}")
                continue
        
        sorted_matching = sort_initiatives_by_score(matching)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Search '{query}' found {len(sorted_matching)} results in {elapsed:.2f}s")
        
        return {"success": True, "results": sorted_matching, "total": len(sorted_matching)}
        
    except Exception as e:
        logger.error(f"❌ Error searching initiatives: {e}")
        return {"success": False, "error": str(e), "results": []}

# Health check functions
def test_nocodb_connection():
    """Test NocoDB connection with timeout"""
    try:
        if not NOCODB_BASE_URL or not NOCODB_TOKEN:
            return {"success": False, "error": "Missing configuration"}
        
        # Simple health check with short timeout
        response = requests.get(
            f"{NOCODB_BASE_URL}/health", 
            headers={'xc-token': NOCODB_TOKEN},
            timeout=5
        )
        
        return {"success": response.status_code == 200, "status_code": response.status_code}
        
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Connection timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_database_stats():
    """Get basic database statistics with timeout protection"""
    try:
        data = get_initiatives()
        
        if not data.get("success"):
            return {"success": False, "error": data.get("error")}
        
        initiatives = data.get("data", [])
        
        return {
            "success": True,
            "total_initiatives": len(initiatives),
            "cached": data.get("cached", False),
            "last_updated": initiatives_cache.get("timestamp", 0)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting database stats: {e}")
        return {"success": False, "error": str(e)}

# Cache management
def clear_cache():
    """Clear initiatives cache"""
    try:
        initiatives_cache["data"] = None
        initiatives_cache["timestamp"] = 0
        logger.info("✅ Cache cleared")
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}")
        return {"success": False, "error": str(e)}

def refresh_cache():
    """Force refresh cache"""
    try:
        clear_cache()
        data = get_initiatives()
        return {"success": data.get("success", False), "total": len(data.get("data", []))}
    except Exception as e:
        logger.error(f"❌ Error refreshing cache: {e}")
        return {"success": False, "error": str(e)} TimeoutError:
                logger.error(f"❌ {func.__name__} timed out after {seconds}s")
                return {"success": False, "error": f"Timeout after {seconds}s"}
            finally:
                # Reset the alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                
        return wrapper
    return decorator

def safe_get_value(obj, key, default=None, value_type=str):
    """Safely get value from object with type conversion"""
    try:
        if not obj or not isinstance(obj, dict):
            return default
        
        value = obj.get(key, default)
        if value is None:
            return default
            
        if value_type == str:
            return str(value).strip() if str(value).strip() else default
        elif value_type == float:
            return float(value) if value != '' else (default if default is not None else 0.0)
        elif value_type == int:
            return int(value) if value != '' else (default if default is not None else 0)
        elif value_type == bool:
            return bool(value) if isinstance(value, bool) else str(value).lower() in ['true', '1', 'yes']
        else:
            return value
            
    except
