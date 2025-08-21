# 🗄️ database.py - Gestión de Datos v2.5
import requests
import logging
import time
from config import *

logger = logging.getLogger(__name__)

def get_cached_initiatives(limit=None, offset=None, status_filter=None):
    """Obtener iniciativas con cache, paginación y filtros optimizado"""
    current_time = time.time()
    
    # Para requests con filtros específicos, no usar cache
    use_cache = (limit is None and offset is None and status_filter is None)
    
    # Verificar cache solo para requests completos
    if (use_cache and initiatives_cache["data"] is not None and 
        current_time - initiatives_cache["timestamp"] < initiatives_cache["ttl"]):
        logger.info("✅ Using cached initiatives data")
        return {"success": True, "data": initiatives_cache["data"], "cached": True, "total": len(initiatives_cache["data"])}
    
    # Fetch fresh data
    try:
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {'accept': 'application/json', 'xc-token': NOCODB_TOKEN}
        
        # Parámetros de consulta
        params = {'limit': limit or DEFAULT_LIMIT}
        
        if offset:
            params['offset'] = offset
            
        # Filtro por status usando where clause de NocoDB
        if status_filter:
            if isinstance(status_filter, list):
                # Para múltiples estados, usar operador IN
                status_list = "','".join(status_filter)
                params['where'] = f"(status,in,'{status_list}')"
            else:
                # Para un solo estado
                params['where'] = f"(status,eq,{status_filter})"
        
        response = requests.get(url, headers=headers, params=params, timeout=NOCODB_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            initiatives = data.get('list', [])
            total_count = data.get('pageInfo', {}).get('totalRows', len(initiatives))
            
            # Actualizar cache solo para requests completos sin filtros
            if use_cache:
                initiatives_cache["data"] = initiatives
                initiatives_cache["timestamp"] = current_time
                logger.info(f"✅ Retrieved {len(initiatives)} initiatives from NocoDB (fresh, cached)")
            else:
                logger.info(f"✅ Retrieved {len(initiatives)} initiatives from NocoDB (fresh, filtered)")
            
            return {
                "success": True, 
                "data": initiatives, 
                "cached": False,
                "total": total_count,
                "limit": params.get('limit'),
                "offset": params.get('offset', 0),
                "has_more": len(initiatives) == params.get('limit', DEFAULT_LIMIT)
            }
        else:
            logger.error(f"❌ NocoDB HTTP {response.status_code}")
            # Fallback a cache solo para requests completos
            if use_cache and initiatives_cache["data"] is not None:
                logger.info("⚠️ Using expired cache due to API error")
                return {"success": True, "data": initiatives_cache["data"], "cached": True, "total": len(initiatives_cache["data"])}
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ Error fetching initiatives: {e}")
        # Fallback a cache solo para requests completos
        if use_cache and initiatives_cache["data"] is not None:
            logger.info("⚠️ Using expired cache due to exception")
            return {"success": True, "data": initiatives_cache["data"], "cached": True, "total": len(initiatives_cache["data"])}
        return {"success": False, "error": str(e)}

# Alias para compatibilidad - ahora soporta parámetros
def get_initiatives(limit=None, offset=None, status_filter=None):
    return get_cached_initiatives(limit, offset, status_filter)

def get_initiatives_by_status(status_list):
    """Obtener iniciativas filtradas por estado(s)"""
    if isinstance(status_list, str):
        status_list = [status_list]
    
    # Validar estados
    valid_statuses = [s for s in status_list if s in VALID_STATUSES]
    
    if not valid_statuses:
        return {"success": False, "error": f"Estados inválidos. Válidos: {VALID_STATUSES}", "results": []}
    
    return get_cached_initiatives(status_filter=valid_statuses)

def get_sprint_initiatives():
    """Obtener iniciativas en sprint (desarrollo activo)"""
    return get_initiatives_by_status(SPRINT_STATUSES)

def get_production_initiatives():
    """Obtener iniciativas en producción/monitoreo"""
    return get_initiatives_by_status(PRODUCTION_STATUSES)

def get_active_initiatives():
    """Obtener todas las iniciativas activas"""
    return get_initiatives_by_status(ACTIVE_STATUSES)

def calculate_score_fast(initiative):
    """Calcular score RICE optimizado"""
    try:
        # Si ya tiene score, usarlo
        if 'score' in initiative and initiative['score'] is not None:
            return float(initiative['score'])
        
        # Calcular rápido
        reach = float(initiative.get('reach', 0)) or 0
        impact = float(initiative.get('impact', 0)) or 0
        confidence = float(initiative.get('confidence', 0)) or 0
        effort = float(initiative.get('effort', 1)) or 1
        
        if reach > 0 and impact > 0 and confidence > 0 and effort > 0:
            score = (reach * impact * confidence) / effort
            initiative['calculated_score'] = score
            return score
        else:
            initiative['calculated_score'] = 0
            return 0
    except:
        initiative['calculated_score'] = 0
        return 0

def sort_initiatives_by_score(initiatives):
    """Ordenar iniciativas por score optimizado"""
    return sorted(initiatives, key=calculate_score_fast, reverse=True)

def validate_initiative_data(data):
    """Validar datos de iniciativa optimizado"""
    errors = []
    
    # Campos requeridos
    required_fields = ['initiative_name', 'description', 'portal', 'owner', 'team', 'reach', 'impact', 'confidence']
    
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Campo '{field}' es requerido")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    # Validaciones rápidas
    validations = [
        (len(data['initiative_name']) <= MAX_INITIATIVE_NAME, f"Nombre debe tener máximo {MAX_INITIATIVE_NAME} caracteres"),
        (len(data['description']) <= MAX_DESCRIPTION, f"Descripción debe tener máximo {MAX_DESCRIPTION} caracteres"),
        (len(data['owner']) <= MAX_OWNER_NAME, f"Owner debe tener máximo {MAX_OWNER_NAME} caracteres"),
        (data['portal'] in VALID_PORTALS, f"Portal debe ser: {', '.join(VALID_PORTALS)}"),
        (data['team'] in VALID_TEAMS, f"Equipo debe ser: {', '.join(VALID_TEAMS)}")
    ]
    
    for condition, error_msg in validations:
        if not condition:
            errors.append(error_msg)
    
    # Validar métricas numéricas
    try:
        reach = float(data['reach'])
        if not (0 <= reach <= 1):
            errors.append("Reach debe estar entre 0 y 1")
        data['reach'] = reach
    except:
        errors.append("Reach debe ser un número entre 0 y 1")
    
    try:
        impact = int(data['impact'])
        if impact not in [1, 2, 3]:
            errors.append("Impact debe ser 1, 2 o 3")
        data['impact'] = impact
    except:
        errors.append("Impact debe ser 1, 2 o 3")
    
    try:
        confidence = float(data['confidence'])
        if not (0 <= confidence <= 1):
            errors.append("Confidence debe estar entre 0 y 1")
        data['confidence'] = confidence
    except:
        errors.append("Confidence debe ser un número entre 0 y 1")
    
    # Valores opcionales
    data['effort'] = float(data.get('effort', 1.0)) if data.get('effort') else 1.0
    data['must_have'] = bool(data.get('must_have', False))
    
    return {"valid": len(errors) == 0, "errors": errors, "data": data}

def create_initiative(data):
    """Crear iniciativa optimizada"""
    try:
        validation_result = validate_initiative_data(data)
        
        if not validation_result["valid"]:
            return {
                "success": False, 
                "error": "Datos inválidos", 
                "validation_errors": validation_result["errors"]
            }
        
        validated_data = validation_result["data"]
        
        # Preparar datos para NocoDB
        nocodb_data = {
            "initiative_name": validated_data["initiative_name"],
            "description": validated_data["description"],
            "portal": validated_data["portal"],
            "owner": validated_data["owner"],
            "team": validated_data["team"],
            "reach": validated_data["reach"],
            "impact": validated_data["impact"],
            "confidence": validated_data["confidence"],
            "effort": validated_data["effort"],
            "must_have": validated_data["must_have"]
        }
        
        if validated_data.get("main_kpi"):
            nocodb_data["main_kpi"] = validated_data["main_kpi"]
        
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {
            'accept': 'application/json',
            'xc-token': NOCODB_TOKEN,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json=nocodb_data, timeout=NOCODB_TIMEOUT)
        
        if response.status_code in [200, 201]:
            # Invalidar cache
            initiatives_cache["timestamp"] = 0
            logger.info(f"✅ Created initiative: {validated_data.get('initiative_name', 'Unknown')}")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"❌ Create failed HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ Error creating initiative: {e}")
        return {"success": False, "error": str(e)}

def search_initiatives(query, field="all"):
    """Buscar iniciativas optimizado"""
    try:
        data = get_initiatives()
        
        if not data.get("success"):
            return {"success": False, "error": data.get("error"), "results": []}
        
        initiatives = data.get("data", [])
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
        
        # Búsqueda optimizada
        matching = []
        for initiative in initiatives:
            if not isinstance(initiative, dict):
                continue
            
            for field_name in fields_to_search:
                if field_name in initiative and initiative[field_name]:
                    if query_lower in str(initiative[field_name]).lower():
                        matching.append(initiative)
                        break
        
        sorted_matching = sort_initiatives_by_score(matching)
        
        logger.info(f"✅ Search '{query}' found {len(sorted_matching)} results")
        return {"success": True, "results": sorted_matching, "total": len(sorted_matching)}
        
    except Exception as e:
        logger.error(f"❌ Error searching initiatives: {e}")
        return {"success": False, "error": str(e), "results": []}
