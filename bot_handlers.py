def handle_sprint_initiatives(chat_id):
    """Mostrar iniciativas en sprint (desarrollo)"""
    logger.info(f"📱 Sprint initiatives from chat {chat_id}")
    
    send_telegram_message(chat_id, "⚡ **Cargando iniciativas en desarrollo...**")
    
    from database import get_sprint_initiatives
    data = get_sprint_initiatives()
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {data.get('error', 'Desconocido')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, "🔧 **No hay iniciativas en desarrollo actualmente.**\n\n💡 Las iniciativas en sprint son las que el equipo de tecnología está trabajando.")
        return
    
    text = f"🔧 **INICIATIVAS EN DESARROLLO** ({len(initiatives)} activas)\n\n"
    text += "⚡ **Equipo Tech trabajando en:**\n\n"
    
    for i, init in enumerate(initiatives[:MAX_RESULTS_LIST], 1):
        formatted = format_initiative_summary_fast(init, i)
        # Agregar info específica de sprint
        status = init.get('status', 'In Sprint')
        text += f"{formatted}\n🔧 Estado: {status}\n\n"
    
    if len(initiatives) > MAX_RESULTS_LIST:
        text += f"📌 **{len(initiatives) - MAX_RESULTS_LIST} iniciativas más en desarrollo...**"
    
    text += f"\n💡 **Tip:** Estas son las iniciativas que están siendo desarrolladas por el equipo técnico."
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_production_initiatives(chat_id):
    """Mostrar iniciativas en producción/monitoreo"""
    logger.info(f"📱 Production initiatives from chat {chat_id}")
    
    send_telegram_message(chat_id, "⚡ **Cargando iniciativas implementadas...**")
    
    from database import get_production_initiatives
    data = get_production_initiatives()
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {data.get('error', 'Desconocido')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, "🚀 **No hay iniciativas implementadas actualmente.**\n\n💡 Aquí aparecerán las iniciativas que ya están en producción o siendo monitoreadas.")
        return
    
    # Separar por estado
    production = [i for i in initiatives if i.get('status') == 'Production']
    monitoring = [i for i in initiatives if i.get('status') == 'Monitoring']
    
    text = f"🚀 **INICIATIVAS IMPLEMENTADAS** ({len(initiatives)} totales)\n\n"
    
    if production:
        text += f"✅ **EN PRODUCCIÓN** ({len(production)}):\n"
        for i, init in enumerate(production[:5], 1):
            formatted = format_initiative_summary_fast(init, i)
            text += f"{formatted}\n🚀 Estado: Production\n\n"
    
    if monitoring:
        text += f"📊 **EN MONITOREO** ({len(monitoring)}):\n"
        for i, init in enumerate(monitoring[:5], 1):
            formatted = format_initiative_summary_fast(init, i)
            text += f"{formatted}\n📊 Estado: Monitoring\n\n"
    
    if len(initiatives) > 10:
        text += f"📌 **{len(initiatives) - 10} iniciativas más implementadas...**\n"
    
    text += f"\n💡 **Tip:** Estas iniciativas ya están disponibles para usuarios o siendo monitoreadas."
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_status_info(chat_id):
    """Mostrar información sobre comandos de estado"""
    text = """📊 **Comandos de Estado Disponibles** 

**🔄 Filtros Rápidos:**
• pending - Ver iniciativas pendientes
• sprint - Ver las en desarrollo activo
• production - Ver las implementadas
• monitoring - Ver las en monitoreo
• cancelled - Ver las canceladas
• hold - Ver las pausadas

**📈 Estados del Flujo:**
⏳ Pending - Pendiente de iniciar
🔧 Sprint - En desarrollo activo
🚀 Production - Implementada y activa
📊 Monitoring - En monitoreo post-implementación
❌ Cancelled - Cancelada
⏸️ Hold - Pausada temporalmente

**📋 Flujo Típico:**
Pending → Sprint → Production → Monitoring

**💡 Ejemplos de uso:**
• Escribe: pending
• Escribe: sprint
• Escribe: production

**🔍 Para búsquedas específicas:**
• buscar Product sprint - Buscar en equipo + estado
• buscar API production - Buscar implementadas

**Tip:** Solo escribe la palabra del estado, sin símbolos ni comillas."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_filter_by_status(chat_id, status):
    """Filtrar iniciativas por estado específico - SIMPLIFICADO"""
    logger.info(f"📱 Filter by status '{status}' from chat {chat_id}")
    
    # Mapear comandos simples a filtros predefinidos
    status_mapping = {
        'pending': 'pending',
        'sprint': 'sprint', 
        'production': 'production',
        'monitoring': 'monitoring',
        'cancelled': 'cancelled',
        'hold': 'hold'
    }
    
    filter_key = status_mapping.get(status.lower())
    
    if not filter_key:
        send_telegram_message(chat_id, f"""❌ **Estado inválido:** {status}

**Comandos válidos:**
• pending - Ver pendientes
• sprint - Ver en desarrollo
• production - Ver implementadas
• monitoring - Ver en monitoreo
• cancelled - Ver canceladas
• hold - Ver pausadas

**Ejemplo:** Escribe solo: pending""", parse_mode='Markdown')
        return
    
    send_telegram_message(chat_id, f"⚡ **Filtrando por: {status}...**")
    
    from database import get_initiatives_by_status
    status_list = STATUS_FILTERS[filter_key]
    data = get_initiatives_by_status(status_list)
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {data.get('error', 'Desconocido')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, f"📭 **No hay iniciativas con estado '{status}'**\n\n💡 Prueba con otro estado o escribe: estados")
        return
    
    # Emoji para cada estado
    status_emojis = {
        'pending': '⏳',
        'sprint': '🔧',
        'production': '🚀',
        'monitoring': '📊',
        'cancelled': '❌',
        'hold': '⏸️'
    }
    
    emoji = status_emojis.get(status.lower(), '📋')
    
    text = f"{emoji} **INICIATIVAS - {status.upper()}** ({len(initiatives)} encontradas)\n\n"
    
    for i, init in enumerate(initiatives[:MAX_RESULTS_LIST], 1):
        formatted = format_initiative_summary_fast(init, i)
        text += f"{formatted}\n{emoji} Estado: {init.get('status', 'N/A')}\n\n"
    
    if len(initiatives) > MAX_RESULTS_LIST:
        text += f"📌 **{len(initiatives) - MAX_RESULTS_LIST} iniciativas más con este estado...**\n"
    
    text += f"\n💡 **Tip:** Escribe buscar para encontrar iniciativas específicas en este estado."
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')# 🤖 bot_handlers.py - Manejadores del Bot v2.5
import logging
from flask import request
from config import *
from database import get_initiatives, search_initiatives, create_initiative, calculate_score_fast
from analytics import calculate_statistics_fast, format_statistics_text_fast, analyze_initiatives_with_llm_fast
from utils import send_telegram_message

logger = logging.getLogger(__name__)

# Variables globales para estados de usuario
user_states = {}

def setup_telegram_routes(app):
    """Configurar rutas del bot de Telegram"""
    
    @app.route('/telegram-webhook', methods=['POST'])
    def telegram_webhook():
        """Webhook optimizado"""
        try:
            update_data = request.get_json()
            
            if not update_data or 'message' not in update_data:
                return "OK", 200
            
            message = update_data['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            
            if 'text' not in message:
                return "OK", 200
            
            text = message['text'].strip().lower()
            
            # Router optimizado
            if text in ['/start', 'start', 'inicio', 'hola']:
                handle_start_command(chat_id)
            elif text in ['/help', 'help', 'ayuda']:
                handle_help_command(chat_id)
            elif text in ['/iniciativas', 'iniciativas', 'lista']:
                handle_list_initiatives_fast(chat_id)
            elif text in ['/crear', 'crear', 'nueva']:
                handle_create_command(chat_id, user_id)
            elif text in ['/analizar', 'analizar', 'análisis']:
                handle_analyze_command_fast(chat_id)
            elif text.startswith(('buscar ', '/buscar ')):
                query = text.split(' ', 1)[1] if ' ' in text else ""
                if query:
                    handle_search_command_fast(chat_id, query)
                else:
                    send_telegram_message(chat_id, "🔍 **¿Qué quieres buscar?**\n\nEjemplos:\n• `buscar Product`\n• `buscar API`")
            elif text in ['/sprint', 'sprint', 'desarrollo', 'dev']:
                handle_sprint_initiatives(chat_id)
            elif text in ['/production', 'production', 'produccion', 'prod']:
                handle_production_initiatives(chat_id)
            elif text in ['/pending', 'pending', 'pendiente']:
                handle_filter_by_status(chat_id, 'pending')
            elif text in ['/monitoring', 'monitoring', 'monitoreo']:
                handle_filter_by_status(chat_id, 'monitoring')
            elif text in ['/cancelled', 'cancelled', 'canceladas']:
                handle_filter_by_status(chat_id, 'cancelled')
            elif text in ['/hold', 'hold', 'pausa', 'pausadas']:
                handle_filter_by_status(chat_id, 'hold')
            elif text in ['/estados', 'estados', 'status', 'comandos']:
                handle_status_info(chat_id)
            else:
                if user_id in user_states:
                    handle_text_message(chat_id, user_id, message['text'])
                else:
                    handle_natural_message_fast(chat_id, text)
            
            return "OK", 200
            
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
            return "ERROR", 500

def handle_natural_message_fast(chat_id, text):
    """Manejar mensajes naturales optimizado"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['iniciativa', 'proyecto', 'lista']):
        send_telegram_message(chat_id, "🎯 Ver iniciativas: iniciativas")
    elif any(word in text_lower for word in ['buscar', 'encontrar']):
        send_telegram_message(chat_id, "🔍 Buscar: buscar API")
    elif any(word in text_lower for word in ['crear', 'nueva']):
        send_telegram_message(chat_id, "🆕 Crear: crear")
    elif any(word in text_lower for word in ['análisis', 'analizar']):
        send_telegram_message(chat_id, "📊 Análisis: analizar")
    elif any(word in text_lower for word in ['sprint', 'desarrollo', 'dev']):
        send_telegram_message(chat_id, "🔧 En desarrollo: sprint")
    elif any(word in text_lower for word in ['producción', 'production', 'implementado']):
        send_telegram_message(chat_id, "🚀 Implementadas: production")
    elif any(word in text_lower for word in ['estado', 'status', 'comando']):
        send_telegram_message(chat_id, "📊 Estados: estados")
    else:
        send_telegram_message(chat_id, """👋 **Comandos disponibles:**

**📋 Básicos:** iniciativas, buscar, crear, analizar
**📊 Estados:** pending, sprint, production, monitoring

💡 **Tip:** Escribe ayuda para ver todos los comandos.""")

def handle_start_command(chat_id):
    """Comando start optimizado"""
    logger.info(f"📱 /start from chat {chat_id}")
    
    text = """🎯 **Bot Saludia v2.6** ⚡ GESTIÓN DE ESTADOS

🔹 Asistente de gestión de iniciativas para equipos Saludia.

**📋 Comandos principales:**
• iniciativas - Lista ordenada por score RICE
• buscar Product - Búsqueda por equipo
• crear - Nueva iniciativa con RICE
• analizar - Análisis AI del portfolio

**📊 Filtros por Estado:**
• pending - Iniciativas pendientes
• sprint - En desarrollo activo
• production - Implementadas y activas
• monitoring - En monitoreo
• cancelled - Canceladas
• hold - Pausadas temporalmente

**🔍 Ejemplos de búsqueda:**
• buscar Product - Por equipo
• buscar API - Por tecnología
• buscar Juan - Por responsable

**⚡ Nuevo en v2.6:**
• Comandos simples sin símbolos raros
• Filtros claros por estado
• API con paginación avanzada
• Cache optimizado

💡 **Tip:** Escribe solo la palabra, sin barras ni comillas."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_help_command(chat_id):
    """Comando help optimizado"""
    text = """📚 **Comandos Disponibles** ⚡ v2.5

**🏃‍♂️ Comandos Rápidos:**
• `iniciativas` - Lista completa por score RICE
• `buscar <término>` - Búsqueda optimizada
• `crear` - Nueva iniciativa (validaciones RICE)
• `analizar` - Análisis AI estratégico

**🔍 Búsquedas:**
• `buscar Product` - Por equipo
• `buscar drogería` - Por descripción
• `buscar API` - Por tecnología

**🏆 Score RICE:**
• 🔥 Score ≥ 2.0 (Alta prioridad)
• ⭐ Score ≥ 1.0 (Media prioridad)
• 📋 Score < 1.0 (Baja prioridad)

**🏗️ Arquitectura Modular v2.5:**
✅ Código organizado en módulos especializados
✅ Fácil debug y mantenimiento
✅ Performance optimizado
✅ Cache inteligente de 5min

🤖 **IA:** Análisis estratégico especializado en Saludia con insights priorizados por score RICE."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_list_initiatives_fast(chat_id):
    """Listar iniciativas optimizado"""
    logger.info(f"📱 List initiatives FAST from chat {chat_id}")
    
    send_telegram_message(chat_id, "⚡ **Cargando iniciativas...**")
    
    data = get_initiatives()
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {data.get('error', 'Desconocido')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, "📭 No hay iniciativas.")
        return
    
    # Estadísticas rápidas
    stats = calculate_statistics_fast(initiatives)
    stats_text = format_statistics_text_fast(stats)
    send_telegram_message(chat_id, stats_text, parse_mode='Markdown')
    
    # Lista rápida - solo top 10
    sorted_initiatives = stats.get('sorted_initiatives', initiatives)
    
    text = f"📋 **TOP {MAX_RESULTS_LIST} INICIATIVAS POR SCORE:**\n\n"
    for i, init in enumerate(sorted_initiatives[:MAX_RESULTS_LIST], 1):
        formatted = format_initiative_summary_fast(init, i)
        text += f"{formatted}\n\n"
    
    if len(sorted_initiatives) > MAX_RESULTS_LIST:
        text += f"📌 **{len(sorted_initiatives) - MAX_RESULTS_LIST} iniciativas más...**\nUsa `buscar` para encontrar específicas."
    
    cache_info = " (Cache)" if data.get("cached") else " (Fresh)"
    text += f"\n💡 **Tip:** Datos actualizados{cache_info}"
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_search_command_fast(chat_id, query):
    """Búsqueda optimizada"""
    logger.info(f"📱 Search FAST '{query}' from chat {chat_id}")
    
    result = search_initiatives(query)
    
    if not result.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {result.get('error')}")
        return
    
    results = result.get("results", [])
    total = result.get("total", 0)
    
    if not results:
        send_telegram_message(chat_id, f"""🔍 **Sin resultados:** "{query}"

💡 **Sugerencias:**
• `buscar Product` - Por equipo
• `buscar API` - Por tecnología
• `iniciativas` - Ver todas""")
        return
    
    text = f"🔍 **RESULTADOS:** {query} ({total} encontrados)\n\n"
    
    # Mostrar solo primeros MAX_RESULTS_SEARCH resultados
    for i, init in enumerate(results[:MAX_RESULTS_SEARCH], 1):
        name = init.get('initiative_name', 'Sin nombre')
        team = init.get('team', 'Sin equipo')
        score = calculate_score_fast(init)
        priority = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
        
        text += f"**{i}.** {priority} **{name}** (Score: {score:.2f})\n"
        text += f"👥 {team} | 👤 {init.get('owner', 'Sin owner')}\n"
        text += f"📝 {init.get('description', 'Sin descripción')[:100]}...\n\n"
    
    if total > MAX_RESULTS_SEARCH:
        text += f"📌 **{total - MAX_RESULTS_SEARCH} resultados más...** Refina tu búsqueda."
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_analyze_command_fast(chat_id):
    """Análisis optimizado"""
    logger.info(f"📱 Analyze FAST from chat {chat_id}")
    
    send_telegram_message(chat_id, "🤖 **Analizando portfolio...** ⚡")
    
    import time
    start_time = time.time()
    data = get_initiatives()
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {data.get('error')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, "📭 No hay iniciativas.")
        return
    
    # Estadísticas rápidas primero
    stats = calculate_statistics_fast(initiatives)
    stats_text = format_statistics_text_fast(stats)
    
    cache_info = " (Cache)" if data.get("cached") else " (Fresh)"
    stats_text += f"\n⚡ **Datos{cache_info}**"
    
    send_telegram_message(chat_id, stats_text, parse_mode='Markdown')
    
    # Análisis AI optimizado
    if GROQ_API_KEY:
        send_telegram_message(chat_id, "🧠 **Generando análisis estratégico...**")
        
        analysis = analyze_initiatives_with_llm_fast(initiatives)
        analysis_time = time.time() - start_time
        
        analysis_text = f"🤖 **ANÁLISIS ESTRATÉGICO** ⚡\n\n{analysis}"
        analysis_text += f"\n\n⏱️ **Tiempo:** {analysis_time:.1f}s"
        
        if len(analysis_text) > MAX_MESSAGE_LENGTH:
            chunks = [analysis_text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(analysis_text), MAX_MESSAGE_LENGTH)]
            for chunk in chunks:
                send_telegram_message(chat_id, chunk, parse_mode='Markdown')
        else:
            send_telegram_message(chat_id, analysis_text, parse_mode='Markdown')
    else:
        send_telegram_message(chat_id, "⚠️ Análisis AI no disponible.")

def format_initiative_summary_fast(initiative, index=None):
    """Formatear iniciativa optimizado"""
    try:
        name = initiative.get('initiative_name', 'Sin nombre')
        owner = initiative.get('owner', 'Sin owner')
        team = initiative.get('team', 'Sin equipo')
        score = calculate_score_fast(initiative)
        
        priority_emoji = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
        prefix = f"**{index}.** " if index else ""
        
        return f"{prefix}{priority_emoji} **{name}** (Score: {score:.2f})\n👤 {owner} | 👥 {team}"
        
    except Exception as e:
        logger.error(f"Format error: {e}")
        return f"{index}. **Error de formato**"

def handle_create_command(chat_id, user_id):
    """Crear iniciativa"""
    logger.info(f"📱 Create command from chat {chat_id}")
    
    user_states[user_id] = {
        'step': 'name',
        'data': {},
        'chat_id': chat_id
    }
    
    text = """🆕 **CREAR INICIATIVA** ⚡

📝 **Paso 1/8:** Nombre de la iniciativa

Envía el nombre (máximo 255 caracteres).

**Ejemplos:**
• "Integración API de pagos"
• "Optimización del checkout"
• "Dashboard analytics v2"

💡 **Tip:** Nombre descriptivo para mejor score RICE."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_text_message(chat_id, user_id, text):
    """Manejar mensajes de creación - versión optimizada"""
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    step = state['step']
    
    try:
        if step == 'name':
            if len(text) > MAX_INITIATIVE_NAME:
                send_telegram_message(chat_id, f"❌ Máximo {MAX_INITIATIVE_NAME} caracteres.")
                return
            
            state['data']['initiative_name'] = text.strip()
            state['step'] = 'description'
            send_telegram_message(chat_id, f"""📝 **Paso 2/8:** Descripción

Describe la iniciativa (máximo {MAX_DESCRIPTION} caracteres).

💡 **Tip:** Incluye problema y beneficio esperado.""", parse_mode='Markdown')
        
        elif step == 'description':
            if len(text) > MAX_DESCRIPTION:
                send_telegram_message(chat_id, f"❌ Máximo {MAX_DESCRIPTION} caracteres.")
                return
                
            state['data']['description'] = text.strip()
            state['step'] = 'owner'
            send_telegram_message(chat_id, f"""👤 **Paso 3/8:** Responsable

¿Quién es el owner? (máximo {MAX_OWNER_NAME} caracteres)

**Ejemplo:** Juan Pérez""", parse_mode='Markdown')
        
        elif step == 'owner':
            if len(text) > MAX_OWNER_NAME:
                send_telegram_message(chat_id, f"❌ Máximo {MAX_OWNER_NAME} caracteres.")
                return
                
            state['data']['owner'] = text.strip()
            state['step'] = 'team'
            send_telegram_message(chat_id, f"""👥 **Paso 4/8:** Equipo

**Opciones:** {', '.join(VALID_TEAMS)}""", parse_mode='Markdown')
        
        elif step == 'team':
            matched_team = next((t for t in VALID_TEAMS if t.lower() == text.strip().lower()), None)
            
            if not matched_team:
                send_telegram_message(chat_id, f"❌ Debe ser: {', '.join(VALID_TEAMS)}")
                return
            
            state['data']['team'] = matched_team
            state['step'] = 'portal'
            send_telegram_message(chat_id, f"""🖥️ **Paso 5/8:** Portal

**Opciones:** {', '.join(VALID_PORTALS)}""", parse_mode='Markdown')
        
        elif step == 'portal':
            matched_portal = next((p for p in VALID_PORTALS if p.lower() == text.strip().lower()), None)
            
            if not matched_portal:
                send_telegram_message(chat_id, f"❌ Debe ser: {', '.join(VALID_PORTALS)}")
                return
            
            state['data']['portal'] = matched_portal
            state['step'] = 'kpi'
            send_telegram_message(chat_id, f"""📊 **Paso 6/8:** KPI Principal (Opcional)

**Ejemplos:** Conversion Rate, GMV, User Retention

💡 Escribe `ninguno` si no tienes KPI específico.""", parse_mode='Markdown')
        
        elif step == 'kpi':
            if text.strip().lower() not in ['ninguno', 'no', 'n/a', '']:
                if len(text.strip()) > MAX_KPI_LENGTH:
                    send_telegram_message(chat_id, f"❌ Máximo {MAX_KPI_LENGTH} caracteres.")
                    return
                state['data']['main_kpi'] = text.strip()
            
            state['step'] = 'reach'
            send_telegram_message(chat_id, """📈 **Paso 7/8:** Métricas RICE

**REACH:** ¿Qué % de usuarios impacta?
Envía número entre 0-100.

**Ejemplos:** 85, 25, 100""", parse_mode='Markdown')
        
        elif step == 'reach':
            try:
                reach = float(text.strip())
                if not (0 <= reach <= 100):
                    send_telegram_message(chat_id, "❌ Entre 0 y 100.")
                    return
                
                state['data']['reach'] = reach / 100
                state['step'] = 'impact'
                send_telegram_message(chat_id, """💥 **IMPACT:** ¿Qué tanto impacto?

**Opciones:** 1 (bajo), 2 (medio), 3 (alto)""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Número válido entre 0-100.")
                return
        
        elif step == 'impact':
            try:
                impact = int(text.strip())
                if impact not in [1, 2, 3]:
                    send_telegram_message(chat_id, "❌ Debe ser 1, 2 o 3.")
                    return
                
                state['data']['impact'] = impact
                state['step'] = 'confidence'
                send_telegram_message(chat_id, """🎯 **CONFIDENCE:** ¿% de confianza en el impacto?

Número entre 0-100.

**Ejemplos:** 90, 70, 50""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Número válido: 1, 2 o 3.")
                return
        
        elif step == 'confidence':
            try:
                confidence = float(text.strip())
                if not (0 <= confidence <= 100):
                    send_telegram_message(chat_id, "❌ Entre 0 y 100.")
                    return
                
                state['data']['confidence'] = confidence / 100
                state['step'] = 'effort'
                send_telegram_message(chat_id, """⚡ **EFFORT:** ¿Cuántos sprints de desarrollo?

**Ejemplos:** 1, 2.5, 0.5

💡 Escribe `default` para 1 sprint.""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Número válido entre 0-100.")
                return
        
        elif step == 'effort':
            if text.strip().lower() in ['default', '']:
                state['data']['effort'] = 1.0
            else:
                try:
                    effort = float(text.strip())
                    if effort <= 0:
                        send_telegram_message(chat_id, "❌ Mayor a 0.")
                        return
                    state['data']['effort'] = effort
                except ValueError:
                    send_telegram_message(chat_id, "❌ Número válido o 'default'.")
                    return
            
            # Crear iniciativa
            create_result = create_initiative(state['data'])
            
            if create_result.get('success'):
                data = state['data']
                score = (data['reach'] * data['impact'] * data['confidence']) / data['effort']
                
                priority_emoji = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
                priority_text = "Alta" if score >= 2.0 else "Media" if score >= 1.0 else "Baja"
                
                confirmation = f"""✅ **INICIATIVA CREADA** ⚡

{priority_emoji} **{data['initiative_name']}**

👤 **Owner:** {data['owner']}
👥 **Equipo:** {data['team']}
🖥️ **Portal:** {data['portal']}

📈 **Métricas RICE:**
• **Reach:** {data['reach']*100:.0f}%
• **Impact:** {data['impact']}/3
• **Confidence:** {data['confidence']*100:.0f}%
• **Effort:** {data['effort']} sprints
• **Score:** {score:.2f}

🏆 **Prioridad:** {priority_text} ({priority_emoji})

💡 **Siguiente:** `buscar {data['initiative_name'][:20]}`"""
                
                send_telegram_message(chat_id, confirmation, parse_mode='Markdown')
            else:
                error_msg = f"❌ Error: {create_result.get('error', 'Desconocido')}"
                if 'validation_errors' in create_result:
                    error_msg += f"\n\n**Errores:**\n• " + "\n• ".join(create_result['validation_errors'])
                send_telegram_message(chat_id, error_msg, parse_mode='Markdown')
            
            del user_states[user_id]
    
    except Exception as e:
        logger.error(f"❌ Text message error: {e}")
        send_telegram_message(chat_id, "❌ Error procesando mensaje.")
        if user_id in user_states:
            del user_states[user_id]
