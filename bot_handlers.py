# 🤖 bot_handlers.py - Manejadores del Bot v2.6 - FIXED - NO FREEZING
import logging
import time
from flask import request
from config import *
from database import get_initiatives, search_initiatives, create_initiative, calculate_score_fast
from analytics import calculate_statistics_fast, format_statistics_text_fast, analyze_initiatives_with_llm_fast
from utils import send_telegram_message

logger = logging.getLogger(__name__)

# Variables globales para estados de usuario
user_states = {}

def setup_telegram_routes(app):
    """Configurar rutas del bot de Telegram - FIXED VERSION"""
    
    @app.route('/telegram-webhook', methods=['POST'])
    def telegram_webhook():
        """Webhook optimizado con timeout protection"""
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
            
            # Timeout wrapper para evitar colgado
            start_time = time.time()
            
            try:
                # Router optimizado - CON TIMEOUT PROTECTION
                if text in ['/start', 'start', 'inicio', 'hola']:
                    handle_start_command(chat_id)
                elif text in ['/help', 'help', 'ayuda']:
                    handle_help_command(chat_id)
                elif text in ['/iniciativas', 'iniciativas', 'lista']:
                    handle_list_initiatives_safe(chat_id)  # FIXED VERSION
                elif text in ['/crear', 'crear', 'nueva']:
                    handle_create_command(chat_id, user_id)
                elif text in ['/analizar', 'analizar', 'análisis']:
                    handle_analyze_command_safe(chat_id)  # FIXED VERSION
                elif text.startswith(('buscar ', '/buscar ')):
                    query = text.split(' ', 1)[1] if ' ' in text else ""
                    if query:
                        handle_search_command_fast(chat_id, query)
                    else:
                        send_telegram_message(chat_id, "🔍 **¿Qué quieres buscar?**\n\nEjemplos:\n• buscar Product\n• buscar API")
                
                # ESTADOS REALES DE LA DB
                elif text in ['/pending', 'pending', 'pendiente']:
                    handle_filter_by_status(chat_id, 'pending')
                elif text in ['/reviewed', 'reviewed', 'revisadas']:
                    handle_filter_by_status(chat_id, 'reviewed')
                elif text in ['/prioritized', 'prioritized', 'priorizadas']:
                    handle_filter_by_status(chat_id, 'prioritized')
                elif text in ['/backlog', 'backlog']:
                    handle_filter_by_status(chat_id, 'backlog')
                elif text in ['/sprint', 'sprint', 'desarrollo', 'dev']:
                    handle_filter_by_status(chat_id, 'sprint')
                elif text in ['/production', 'production', 'produccion', 'prod']:
                    handle_filter_by_status(chat_id, 'production')
                elif text in ['/monitoring', 'monitoring', 'monitoreo']:
                    handle_filter_by_status(chat_id, 'monitoring')
                elif text in ['/discarded', 'discarded', 'descartadas']:
                    handle_filter_by_status(chat_id, 'discarded')
                elif text in ['/estados', 'estados', 'status', 'comandos']:
                    handle_status_info(chat_id)
                elif text in ['/growth', 'growth', 'crecimiento']:  # NUEVO: Comando específico Growth
                    handle_growth_analysis(chat_id)
                else:
                    if user_id in user_states:
                        handle_text_message(chat_id, user_id, message['text'])
                    else:
                        handle_natural_message_fast(chat_id, text)
                
                # Check for timeout
                elapsed_time = time.time() - start_time
                if elapsed_time > 25:  # 25 seconds timeout
                    logger.warning(f"⚠️ Command took too long: {elapsed_time:.1f}s")
                    send_telegram_message(chat_id, "⚠️ Comando tardó más de lo esperado. Reintenta.")
                
            except Exception as e:
                logger.error(f"❌ Command processing error: {e}")
                send_telegram_message(chat_id, f"❌ Error procesando comando: {str(e)}")
            
            return "OK", 200
            
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
            return "Handled with error", 200

def handle_list_initiatives_safe(chat_id):
    """Listar iniciativas con protección contra colgado - FIXED VERSION"""
    logger.info(f"📱 List initiatives SAFE from chat {chat_id}")
    
    try:
        # Mensaje inmediato para mostrar que está funcionando
        send_telegram_message(chat_id, "⚡ **Cargando iniciativas...** (esto puede tardar 10-15s)")
        
        # Timeout protection
        start_time = time.time()
        
        # Intentar obtener datos con timeout
        data = None
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{max_attempts} to fetch initiatives")
                data = get_initiatives()
                
                if data and data.get("success"):
                    break
                else:
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed: {data.get('error') if data else 'No data'}")
                    if attempt < max_attempts - 1:
                        time.sleep(2)  # Wait 2 seconds before retry
                        
            except Exception as e:
                logger.error(f"❌ Attempt {attempt + 1} exception: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(2)
                else:
                    send_telegram_message(chat_id, f"❌ Error después de {max_attempts} intentos: {str(e)}")
                    return
        
        # Check timeout
        elapsed_time = time.time() - start_time
        if elapsed_time > 20:  # 20 second timeout
            send_telegram_message(chat_id, "⚠️ **Timeout** - El comando tardó demasiado. Reintenta en unos momentos.")
            return
        
        if not data or not data.get("success"):
            error_msg = data.get('error', 'Error desconocido') if data else 'No se obtuvieron datos'
            send_telegram_message(chat_id, f"❌ Error: {error_msg}")
            return
        
        initiatives = data.get("data", [])
        
        if not initiatives:
            send_telegram_message(chat_id, "🔭 **No hay iniciativas disponibles.**\n\n💡 Usa el comando `crear` para agregar nuevas iniciativas.")
            return
        
        logger.info(f"✅ Successfully fetched {len(initiatives)} initiatives in {elapsed_time:.1f}s")
        
        # Procesar estadísticas de forma segura
        try:
            send_telegram_message(chat_id, "📊 **Generando estadísticas...**")
            stats = calculate_statistics_fast(initiatives)
            stats_text = format_statistics_text_fast(stats)
            
            # Enviar estadísticas en chunks si es muy largo
            if len(stats_text) > MAX_MESSAGE_LENGTH:
                chunks = [stats_text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(stats_text), MAX_MESSAGE_LENGTH)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        send_telegram_message(chat_id, chunk, parse_mode='Markdown')
                    else:
                        send_telegram_message(chat_id, f"**Continuación {i+1}:**\n\n{chunk}", parse_mode='Markdown')
                    time.sleep(1)  # Delay between chunks
            else:
                send_telegram_message(chat_id, stats_text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"❌ Error generating stats: {e}")
            send_telegram_message(chat_id, f"❌ Error generando estadísticas: {str(e)}")
        
        # Lista rápida - solo top 10 para evitar saturación
        try:
            send_telegram_message(chat_id, "📋 **Generando lista top...**")
            
            # Usar las iniciativas ya ordenadas de stats si están disponibles
            sorted_initiatives = stats.get('sorted_initiatives', initiatives) if 'stats' in locals() else initiatives
            
            text = f"📋 **TOP {min(MAX_RESULTS_LIST, len(sorted_initiatives))} INICIATIVAS POR SCORE RICE:**\n\n"
            
            for i, init in enumerate(sorted_initiatives[:MAX_RESULTS_LIST], 1):
                try:
                    formatted = format_initiative_summary_safe(init, i)
                    text += f"{formatted}\n\n"
                except Exception as e:
                    logger.warning(f"Error formatting initiative {i}: {e}")
                    text += f"{i}. ❌ **Error formateando iniciativa**\n\n"
            
            if len(sorted_initiatives) > MAX_RESULTS_LIST:
                text += f"📌 **{len(sorted_initiatives) - MAX_RESULTS_LIST} iniciativas más...**\nUsa `buscar` para encontrar específicas."
            
            # Info de cache
            cache_info = " (Cache)" if data.get("cached") else " (Fresh)"
            text += f"\n💡 **Datos actualizados{cache_info}** - Tiempo: {elapsed_time:.1f}s"
            
            # Enviar lista en chunks si es necesario
            if len(text) > MAX_MESSAGE_LENGTH:
                chunks = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
                for chunk in chunks:
                    send_telegram_message(chat_id, chunk, parse_mode='Markdown')
                    time.sleep(1)
            else:
                send_telegram_message(chat_id, text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"❌ Error generating list: {e}")
            send_telegram_message(chat_id, f"❌ Error generando lista: {str(e)}")
        
        # Comandos de seguimiento
        try:
            follow_up = """💡 **Comandos útiles:**
• `analizar` - Análisis estratégico Growth
• `growth` - Análisis específico de crecimiento
• `buscar <término>` - Buscar iniciativas
• `sprint` - Ver iniciativas en desarrollo"""
            send_telegram_message(chat_id, follow_up, parse_mode='Markdown')
        except:
            pass  # No critical if this fails
            
    except Exception as e:
        logger.error(f"❌ Fatal error in handle_list_initiatives_safe: {e}")
        send_telegram_message(chat_id, f"❌ Error crítico: {str(e)}\n\n💡 Intenta nuevamente en unos momentos.")

def handle_analyze_command_safe(chat_id):
    """Análisis con protección contra colgado y enfoque Growth - FIXED VERSION"""
    logger.info(f"📱 Analyze SAFE with Growth focus from chat {chat_id}")
    
    try:
        send_telegram_message(chat_id, "🤖 **Iniciando análisis estratégico...** ⚡")
        
        start_time = time.time()
        
        # Obtener datos con timeout protection
        data = None
        max_attempts = 2  # Menos intentos para análisis
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔄 Analysis attempt {attempt + 1}/{max_attempts}")
                data = get_initiatives()
                
                if data and data.get("success"):
                    break
                else:
                    logger.warning(f"⚠️ Analysis attempt {attempt + 1} failed")
                    if attempt < max_attempts - 1:
                        time.sleep(3)
                        
            except Exception as e:
                logger.error(f"❌ Analysis attempt {attempt + 1} exception: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(3)
        
        if not data or not data.get("success"):
            error_msg = data.get('error', 'Error desconocido') if data else 'No se obtuvieron datos'
            send_telegram_message(chat_id, f"❌ Error obteniendo datos para análisis: {error_msg}")
            return
        
        initiatives = data.get("data", [])
        
        if not initiatives:
            send_telegram_message(chat_id, "🔭 **No hay iniciativas para analizar.**")
            return
        
        # Estadísticas rápidas primero
        try:
            send_telegram_message(chat_id, "📊 **Calculando métricas...**")
            stats = calculate_statistics_fast(initiatives)
            stats_text = format_statistics_text_fast(stats)
            
            cache_info = " (Cache)" if data.get("cached") else " (Fresh)"
            stats_text += f"\n⚡ **Datos{cache_info}**"
            
            # Enviar estadísticas
            if len(stats_text) > MAX_MESSAGE_LENGTH:
                chunks = [stats_text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(stats_text), MAX_MESSAGE_LENGTH)]
                for chunk in chunks:
                    send_telegram_message(chat_id, chunk, parse_mode='Markdown')
                    time.sleep(1)
            else:
                send_telegram_message(chat_id, stats_text, parse_mode='Markdown')
                
            logger.info(f"✅ Statistics sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Statistics error: {e}")
            send_telegram_message(chat_id, f"❌ Error en estadísticas: {str(e)}")
            return
        
        # Check timeout before AI analysis
        elapsed_time = time.time() - start_time
        if elapsed_time > 15:
            send_telegram_message(chat_id, "⚠️ **Proceso tardando más de lo esperado** - Continuando con análisis IA...")
        
        # Análisis AI optimizado con mejor error handling
        if not GROQ_API_KEY:
            send_telegram_message(chat_id, "⚠️ **Análisis AI no disponible**\n\nEl sistema no tiene configurada la API key de Groq. Las estadísticas están disponibles arriba.")
            return
        
        try:
            send_telegram_message(chat_id, "🧠 **Generando análisis estratégico Growth...** (10-20s)")
            
            logger.info(f"🤖 Starting Growth-focused AI analysis with {len(initiatives)} initiatives")
            
            # Timeout para el análisis IA
            ai_start = time.time()
            analysis = analyze_initiatives_with_llm_fast(initiatives)
            ai_elapsed = time.time() - ai_start
            
            if not analysis or analysis.strip() == "":
                send_telegram_message(chat_id, "❌ **Análisis vacío**\n\nEl AI no generó respuesta. Las estadísticas están disponibles arriba.")
                return
            
            total_elapsed = time.time() - start_time
            
            analysis_text = f"🤖 **ANÁLISIS ESTRATÉGICO GROWTH - SALUDIA** 🚀\n\n{analysis}"
            analysis_text += f"\n\n⏱️ **Tiempo:** Datos: {elapsed_time:.1f}s | IA: {ai_elapsed:.1f}s | Total: {total_elapsed:.1f}s"
            
            # Enviar análisis (dividir si es muy largo)
            if len(analysis_text) > MAX_MESSAGE_LENGTH:
                chunks = [analysis_text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(analysis_text), MAX_MESSAGE_LENGTH)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        send_telegram_message(chat_id, chunk, parse_mode='Markdown')
                    else:
                        send_telegram_message(chat_id, f"**Continuación {i+1}:**\n\n{chunk}", parse_mode='Markdown')
                    time.sleep(1)
            else:
                send_telegram_message(chat_id, analysis_text, parse_mode='Markdown')
            
            logger.info(f"✅ Growth analysis completed and sent in {total_elapsed:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ AI Analysis error: {e}")
            error_msg = f"❌ **Error en análisis AI:**\n\n{str(e)}\n\n💡 Las estadísticas básicas están disponibles arriba."
            send_telegram_message(chat_id, error_msg, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"❌ Fatal error in analyze command: {e}")
        send_telegram_message(chat_id, f"❌ Error crítico en análisis: {str(e)}")

def handle_growth_analysis(chat_id):
    """Nuevo comando específico para análisis de Growth"""
    logger.info(f"📱 Growth-specific analysis from chat {chat_id}")
    
    try:
        send_telegram_message(chat_id, "🚀 **ANÁLISIS ESPECÍFICO DE GROWTH** 🚀")
        
        data = get_initiatives()
        
        if not data or not data.get("success"):
            send_telegram_message(chat_id, "❌ Error obteniendo datos para análisis Growth.")
            return
        
        initiatives = data.get("data", [])
        
        if not initiatives:
            send_telegram_message(chat_id, "🔭 No hay iniciativas para analizar.")
            return
        
        # Filtrar iniciativas de Growth
        growth_initiatives = [init for init in initiatives if 
                            str(init.get('team', '')).strip().lower() == 'growth']
        
        total_initiatives = len(initiatives)
        growth_count = len(growth_initiatives)
        
        # Calcular métricas específicas de Growth
        if growth_initiatives:
            growth_scores = [calculate_score_fast(init) for init in growth_initiatives]
            avg_growth_score = sum(growth_scores) / len(growth_scores)
            high_priority_growth = len([s for s in growth_scores if s >= 2.0])
            
            # Ordenar por score
            growth_initiatives.sort(key=calculate_score_fast, reverse=True)
            
            analysis = f"""🚀 **ANÁLISIS ESPECÍFICO GROWTH - SALUDIA**

📊 **MÉTRICAS GROWTH:**
• Iniciativas Growth: {growth_count} de {total_initiatives} ({(growth_count/total_initiatives)*100:.1f}%)
• Score promedio Growth: {avg_growth_score:.2f}
• Alta prioridad (≥2.0): {high_priority_growth} iniciativas

🏆 **TOP INICIATIVAS GROWTH:**
"""
            
            for i, init in enumerate(growth_initiatives[:5], 1):
                score = calculate_score_fast(init)
                priority_emoji = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
                
                analysis += f"""
{i}. {priority_emoji} **{init.get('initiative_name', 'Sin nombre')}** (Score: {score:.2f})
   👤 {init.get('owner', 'Sin owner')} | 🖥️ {init.get('portal', 'Sin portal')}
   📊 KPI: {init.get('main_kpi', 'Sin KPI')}
   📝 {init.get('description', 'Sin descripción')[:100]}...
"""
            
            analysis += f"""

💡 **RECOMENDACIONES GROWTH:**
"""
            
            if high_priority_growth == 0:
                analysis += "• ⚠️ No hay iniciativas Growth de alta prioridad (Score ≥ 2.0)"
            else:
                analysis += f"• ✅ {high_priority_growth} iniciativas Growth de alta prioridad - Ejecutar inmediatamente"
            
            if avg_growth_score < 1.0:
                analysis += "\n• ⚠️ Score promedio Growth bajo - Revisar estimaciones RICE"
            else:
                analysis += f"\n• ✅ Score promedio Growth saludable: {avg_growth_score:.2f}"
            
            if growth_count < 3:
                analysis += "\n• ⚠️ Pocas iniciativas Growth - Considerar más proyectos de crecimiento"
            
        else:
            analysis = f"""🚀 **ANÁLISIS ESPECÍFICO GROWTH - SALUDIA**

⚠️ **NO HAY INICIATIVAS DE GROWTH IDENTIFICADAS**

📊 **Estado actual:**
• Total iniciativas: {total_initiatives}
• Iniciativas Growth: 0 (0%)

💡 **RECOMENDACIONES CRÍTICAS:**
• 🚨 URGENTE: Crear iniciativas específicas para el equipo Growth
• 🎯 Enfocar en: Adquisición de usuarios, Retention, Conversion Rate
• 📈 KPIs sugeridos: GMV, Take Rate, User Acquisition Cost
• 🚀 Considerar iniciativas de marketing, onboarding, referral programs

🎯 **Próximos pasos:**
1. Usar comando `crear` para agregar iniciativas Growth
2. Balancear portfolio con iniciativas de crecimiento
3. Establecer KPIs claros de Growth para Saludia marketplace"""
        
        send_telegram_message(chat_id, analysis, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Growth analysis error: {e}")
        send_telegram_message(chat_id, f"❌ Error en análisis Growth: {str(e)}")

def format_initiative_summary_safe(initiative, index=None):
    """Formatear iniciativa optimizado y seguro - FIXED VERSION"""
    try:
        # Usar safe_get para evitar errores con None
        name = safe_get_string_local(initiative, 'initiative_name', 'Sin nombre')
        owner = safe_get_string_local(initiative, 'owner', 'Sin owner')
        team = safe_get_string_local(initiative, 'team', 'Sin equipo')
        
        # Calcular score de forma segura
        score = 0.0
        try:
            score = calculate_score_fast(initiative)
        except Exception as e:
            logger.warning(f"Error calculating score: {e}")
            score = 0.0
        
        priority_emoji = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
        prefix = f"**{index}.** " if index else ""
        
        # Emoji especial para Growth
        team_emoji = "🚀" if team.lower() == "growth" else "👥"
        
        return f"{prefix}{priority_emoji} **{name}** (Score: {score:.2f})\n{team_emoji} {team} | 👤 {owner}"
        
    except Exception as e:
        logger.error(f"Format error: {e}")
        return f"{index}. ❌ **Error de formato**" if index else "❌ **Error de formato**"

def safe_get_string_local(obj, key, default=''):
    """Helper local para obtener strings de forma segura"""
    try:
        value = obj.get(key, default) if obj else default
        if value is None:
            return default
        return str(value).strip() if str(value).strip() else default
    except:
        return default

def handle_start_command(chat_id):
    """Comando start optimizado"""
    logger.info(f"📱 /start from chat {chat_id}")
    
    text = """🎯 **Bot Saludia v2.6** ⚡ GESTIÓN DE INICIATIVAS

🥼 **Saludia Marketplace Farmacéutico**
Asistente especializado en gestión de iniciativas con metodología RICE, enfocado en **GROWTH** y crecimiento del negocio.

**📋 Comandos principales:**
• `iniciativas` - Lista ordenada por score RICE
• `analizar` - Análisis AI estratégico completo  
• `growth` - 🚀 Análisis específico de crecimiento
• `buscar <término>` - Búsqueda por equipo/proyecto
• `crear` - Nueva iniciativa con RICE

**📊 Filtros por Estado:**
• `pending` - Pendientes de revisión
• `sprint` - En desarrollo activo  
• `production` - Implementadas
• `monitoring` - En monitoreo

**🚀 Enfoque Growth:**
• Maximizar GMV del marketplace
• Optimizar adquisición y retención
• Balancear Droguerías ↔ Sellers
• Métricas: Conversion Rate, Take Rate, NPS

**⚡ Nuevo en v2.6:**
• Análisis específico Growth
• Protección contra timeouts
• Error handling mejorado
• Cache inteligente

💡 **Tip:** Comandos simples, ej: `growth` o `sprint`"""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_help_command(chat_id):
    """Comando help optimizado con enfoque Growth"""
    text = """📚 **Comandos Disponibles** ⚡ v2.6 - GROWTH FOCUSED

**🚀 Comandos Growth:**
• `growth` - Análisis específico de crecimiento
• `analizar` - Análisis AI estratégico completo

**📊 Comandos Básicos:**
• `iniciativas` - Lista completa por score RICE
• `buscar <término>` - Búsqueda optimizada
• `crear` - Nueva iniciativa con validaciones RICE

**📈 Filtros por Estado:**
• `pending` - Pendientes | `sprint` - En desarrollo  
• `production` - Implementadas | `monitoring` - En monitoreo

**🔍 Ejemplos de Búsqueda:**
• `buscar Growth` - Iniciativas de crecimiento
• `buscar GMV` - Por KPI específico
• `buscar Juan` - Por responsable

**🏆 Sistema RICE (Reach × Impact × Confidence / Effort):**
• 🔥 Score ≥ 2.0 - Alta prioridad (ejecutar YA)
• ⭐ Score ≥ 1.0 - Media prioridad (próximos sprints)
• 📋 Score < 1.0 - Baja prioridad (re-evaluar)

**🎯 Flujo de Estados:**
Pending → Reviewed → Prioritized → Backlog → Sprint → Production → Monitoring

**🚀 Especialización Growth:**
• Análisis enfocado en crecimiento del marketplace
• KPIs: GMV, Take Rate, User Acquisition, Retention
• Balance Droguerías ↔ Sellers/Laboratorios
• Optimización de conversión y experiencia

💡 **Tip:** Usa `growth` para análisis específico de crecimiento"""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_natural_message_fast(chat_id, text):
    """Manejar mensajes naturales optimizado con sugerencias Growth"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['crecimiento', 'growth', 'crecer']):
        send_telegram_message(chat_id, "🚀 Análisis Growth: `growth`")
    elif any(word in text_lower for word in ['iniciativa', 'proyecto', 'lista']):
        send_telegram_message(chat_id, "🎯 Ver iniciativas: `iniciativas`")
    elif any(word in text_lower for word in ['buscar', 'encontrar']):
        send_telegram_message(chat_id, "🔍 Buscar: `buscar Growth`")
    elif any(word in text_lower for word in ['crear', 'nueva']):
        send_telegram_message(chat_id, "🆕 Crear: `crear`")
    elif any(word in text_lower for word in ['análisis', 'analizar']):
        send_telegram_message(chat_id, "📊 Análisis: `analizar`")
    elif any(word in text_lower for word in ['sprint', 'desarrollo', 'dev']):
        send_telegram_message(chat_id, "🔧 En desarrollo: `sprint`")
    elif any(word in text_lower for word in ['producción', 'production', 'implementado']):
        send_telegram_message(chat_id, "🚀 Implementadas: `production`")
    else:
        send_telegram_message(chat_id, """💬 **Comandos disponibles:**

**🚀 Growth:** `growth`, `analizar`
**📋 Básicos:** `iniciativas`, `buscar`, `crear`  
**📊 Estados:** `pending`, `sprint`, `production`

💡 **Tip:** Escribe `help` para ver todos los comandos.""")

def handle_search_command_fast(chat_id, query):
    """Búsqueda optimizada con timeout protection"""
    logger.info(f"📱 Search FAST '{query}' from chat {chat_id}")
    
    try:
        start_time = time.time()
        result = search_initiatives(query)
        elapsed = time.time() - start_time
        
        if elapsed > 10:
            logger.warning(f"⚠️ Search took {elapsed:.1f}s")
        
        if not result.get("success"):
            send_telegram_message(chat_id, f"❌ Error: {result.get('error')}")
            return
        
        results = result.get("results", [])
        total = result.get("total", 0)
        
        if not results:
            send_telegram_message(chat_id, f"""🔍 **Sin resultados:** "{query}"

💡 **Sugerencias:**
• `buscar Growth` - Por equipo Growth
• `buscar GMV` - Por KPI
• `iniciativas` - Ver todas""")
            return
        
        text = f"🔍 **RESULTADOS:** {query} ({total} encontrados)\n\n"
        
        for i, init in enumerate(results[:MAX_RESULTS_SEARCH], 1):
            try:
                name = safe_get_string_local(init, 'initiative_name', 'Sin nombre')
                team = safe_get_string_local(init, 'team', 'Sin equipo')
                score = calculate_score_fast(init)
                priority = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
                team_emoji = "🚀" if team.lower() == "growth" else "👥"
                
                text += f"**{i}.** {priority} **{name}** (Score: {score:.2f})\n"
                text += f"{team_emoji} {team} | 👤 {safe_get_string_local(init, 'owner', 'Sin owner')}\n"
                text += f"📝 {safe_get_string_local(init, 'description', 'Sin descripción')[:100]}...\n\n"
            except Exception as e:
                logger.warning(f"Error formatting search result {i}: {e}")
                continue
        
        if total > MAX_RESULTS_SEARCH:
            text += f"📌 **{total - MAX_RESULTS_SEARCH} resultados más...** Refina tu búsqueda."
        
        text += f"\n⚡ Búsqueda completada en {elapsed:.1f}s"
        
        send_telegram_message(chat_id, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        send_telegram_message(chat_id, f"❌ Error en búsqueda: {str(e)}")

# ===== FUNCIONES DEL COMANDO "crear" =====

def handle_create_command(chat_id, user_id):
    """Iniciar proceso de creación de iniciativa - 8 pasos"""
    logger.info(f"📱 Create command from chat {chat_id}, user {user_id}")
    
    try:
        # Inicializar estado del usuario
        user_states[user_id] = {
            'state': 'creating_initiative',
            'step': 1,
            'data': {}
        }
        
        text = """🆕 **CREAR NUEVA INICIATIVA** 🎯

**Metodología RICE:** Reach × Impact × Confidence / Effort

**📋 Proceso (8 pasos):**
1. Nombre de la iniciativa
2. Descripción detallada  
3. Responsable (owner)
4. Equipo asignado
5. Portal objetivo
6. KPI principal (opcional)
7. Métricas RICE
8. Confirmación

**💡 Tips:**
• Sé específico en nombre y descripción
• Las métricas RICE determinan la prioridad
• Puedes cancelar escribiendo "cancelar"

**➡️ PASO 1/8: Nombre de la Iniciativa**
Escribe un nombre claro y descriptivo (máximo 255 caracteres):

*Ejemplo: "Integración API de pagos PSE"*"""
        
        send_telegram_message(chat_id, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error starting create command: {e}")
        send_telegram_message(chat_id, f"❌ Error iniciando creación: {str(e)}")

def handle_text_message(chat_id, user_id, text):
    """Manejar mensajes de texto en estado de creación"""
    try:
        if user_id not in user_states:
            # Usuario no está en proceso de creación
            handle_natural_message_fast(chat_id, text.lower())
            return
        
        user_state = user_states[user_id]
        
        if user_state['state'] != 'creating_initiative':
            # Estado no válido
            del user_states[user_id]
            handle_natural_message_fast(chat_id, text.lower())
            return
        
        # Verificar comando de cancelación
        if text.lower().strip() in ['cancelar', 'cancel', 'salir', 'exit']:
            del user_states[user_id]
            send_telegram_message(chat_id, "❌ **Creación cancelada.**\n\n💡 Usa `crear` para intentar nuevamente.")
            return
        
        step = user_state['step']
        
        # Procesar cada paso
        if step == 1:
            handle_step_1_name(chat_id, user_id, text)
        elif step == 2:
            handle_step_2_description(chat_id, user_id, text)
        elif step == 3:
            handle_step_3_owner(chat_id, user_id, text)
        elif step == 4:
            handle_step_4_team(chat_id, user_id, text)
        elif step == 5:
            handle_step_5_portal(chat_id, user_id, text)
        elif step == 6:
            handle_step_6_kpi(chat_id, user_id, text)
        elif step == 7:
            handle_step_7_rice(chat_id, user_id, text)
        elif step == 8:
            handle_step_8_confirmation(chat_id, user_id, text)
        else:
            # Estado inválido, resetear
            del user_states[user_id]
            send_telegram_message(chat_id, "❌ **Estado inválido.** Proceso reiniciado.\n\nUsa `crear` para comenzar nuevamente.")
            
    except Exception as e:
        logger.error(f"❌ Error handling text message: {e}")
        if user_id in user_states:
            del user_states[user_id]
        send_telegram_message(chat_id, f"❌ Error procesando mensaje: {str(e)}\n\nUsa `crear` para intentar nuevamente.")

def handle_step_1_name(chat_id, user_id, text):
    """PASO 1: Nombre de la iniciativa"""
    try:
        name = text.strip()
        
        # Validaciones
        if not name:
            send_telegram_message(chat_id, "❌ **El nombre no puede estar vacío.**\n\nEscribe un nombre claro:")
            return
        
        if len(name) > MAX_INITIATIVE_NAME:
            send_telegram_message(chat_id, f"❌ **Nombre muy largo.** Máximo {MAX_INITIATIVE_NAME} caracteres.\n\nActual: {len(name)} caracteres. Intenta uno más corto:")
            return
        
        # Guardar y continuar
        user_states[user_id]['data']['initiative_name'] = name
        user_states[user_id]['step'] = 2
        
        text_response = f"""✅ **Nombre guardado:** {name}

**➡️ PASO 2/8: Descripción Detallada**
Describe qué hace esta iniciativa, por qué es importante y cómo impacta el negocio (máximo {MAX_DESCRIPTION} caracteres):

*Ejemplo: "Implementar integración con PSE y tarjetas de crédito para mejorar la conversión de checkout en el portal de droguerías. Reducirá abandono del carrito y aumentará GMV."*"""
        
        send_telegram_message(chat_id, text_response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Step 1 error: {e}")
        send_telegram_message(chat_id, f"❌ Error en paso 1: {str(e)}")

def handle_step_2_description(chat_id, user_id, text):
    """PASO 2: Descripción detallada"""
    try:
        description = text.strip()
        
        # Validaciones
        if not description:
            send_telegram_message(chat_id, "❌ **La descripción no puede estar vacía.**\n\nDescribe detalladamente la iniciativa:")
            return
        
        if len(description) > MAX_DESCRIPTION:
            send_telegram_message(chat_id, f"❌ **Descripción muy larga.** Máximo {MAX_DESCRIPTION} caracteres.\n\nActual: {len(description)} caracteres. Resume:")
            return
        
        # Guardar y continuar
        user_states[user_id]['data']['description'] = description
        user_states[user_id]['step'] = 3
        
        text_response = f"""✅ **Descripción guardada:** {description[:100]}{'...' if len(description) > 100 else ''}

**➡️ PASO 3/8: Responsable (Owner)**
¿Quién será el responsable principal de esta iniciativa? Escribe el nombre completo (máximo {MAX_OWNER_NAME} caracteres):

*Ejemplo: "Juan Pérez"*"""
        
        send_telegram_message(chat_id, text_response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Step 2 error: {e}")
        send_telegram_message(chat_id, f"❌ Error en paso 2: {str(e)}")

def handle_step_3_owner(chat_id, user_id, text):
    """PASO 3: Responsable"""
    try:
        owner = text.strip()
        
        # Validaciones
        if not owner:
            send_telegram_message(chat_id, "❌ **El responsable no puede estar vacío.**\n\nEscribe el nombre del responsable:")
            return
        
        if len(owner) > MAX_OWNER_NAME:
            send_telegram_message(chat_id, f"❌ **Nombre muy largo.** Máximo {MAX_OWNER_NAME} caracteres.\n\nActual: {len(owner)} caracteres:")
            return
        
        # Guardar y continuar
        user_states[user_id]['data']['owner'] = owner
        user_states[user_id]['step'] = 4
        
        teams_text = "• " + "\n• ".join(VALID_TEAMS)
        
        text_response = f"""✅ **Responsable guardado:** {owner}

**➡️ PASO 4/8: Equipo Asignado**
Selecciona el equipo responsable. Escribe exactamente uno de estos equipos:

{teams_text}

*Escribe solo el nombre del equipo, ejemplo: "Product"*"""
        
        send_telegram_message(chat_id, text_response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Step 3 error: {e}")
        send_telegram_message(chat_id, f"❌ Error en paso 3: {str(e)}")

def handle_step_4_team(chat_id, user_id, text):
    """PASO 4: Equipo"""
    try:
        team = text.strip()
        
        # Validar equipo
        if team not in VALID_TEAMS:
            teams_text = "• " + "\n• ".join(VALID_TEAMS)
            send_telegram_message(chat_id, f"""❌ **Equipo inválido:** {team}

**Equipos válidos:**
{teams_text}

Escribe exactamente uno de los equipos listados:""", parse_mode='Markdown')
            return
        
        # Guardar y continuar
        user_states[user_id]['data']['team'] = team
        user_states[user_id]['step'] = 5
        
        portals_text = "• " + "\n• ".join(VALID_PORTALS)
        
        text_response = f"""✅ **Equipo guardado:** {team}

**➡️ PASO 5/8: Portal Objetivo**
¿En qué portal se implementará esta iniciativa? Escribe exactamente uno:

{portals_text}

*Ejemplo: "Droguista" para iniciativas del portal de droguerías*"""
        
        send_telegram_message(chat_id, text_response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Step 4 error: {e}")
        send_telegram_message(chat_id, f"❌ Error en paso 4: {str(e)}")

def handle_step_5_portal(chat_id, user_id, text):
    """PASO 5: Portal"""
    try:
        portal = text.strip()
        
        # Validar portal
        if portal not in VALID_PORTALS:
            portals_text = "• " + "\n• ".join(VALID_PORTALS)
            send_telegram_message(chat_id, f"""❌ **Portal inválido:** {portal}

**Portales válidos:**
{portals_text}

Escribe exactamente uno de los portales listados:""", parse_mode='Markdown')
            return
        
        # Guardar y continuar
        user_states[user_id]['data']['portal'] = portal
        user_states[user_id]['step'] = 6
        
        text_response = f"""✅ **Portal guardado:** {portal}

**➡️ PASO 6/8: KPI Principal (Opcional)**
¿Cuál es el KPI principal que esta iniciativa mejorará? 

Escribe el KPI o "ninguno" si no aplica (máximo {MAX_KPI_LENGTH} caracteres):

*Ejemplos: "Conversion Rate", "GMV", "User Retention", "ninguno"*"""
        
        send_telegram_message(chat_id, text_response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Step 5 error: {e}")
        send_telegram_message(chat_id, f"❌ Error en paso 5: {str(e)}")

def handle_step_6_kpi(chat_id, user_id, text):
    """PASO 6: KPI Principal"""
    try:
        kpi_input = text.strip()
        
        # Validar longitud
        if len(kpi_input) > MAX_KPI_LENGTH:
            send_telegram_message(chat_id, f"❌ **KPI muy largo.** Máximo {MAX_KPI_LENGTH} caracteres.\n\nActual: {len(kpi_input)} caracteres:")
            return
        
        # Procesar KPI
        if kpi_input.lower() in ['ninguno', 'none', 'na', 'n/a', '']:
            kpi = None
        else:
            kpi = kpi_input
        
        # Guardar KPI (puede ser None)
        if kpi:
            user_states[user_id]['data']['main_kpi'] = kpi
        
        user_states[user_id]['step'] = 7
        
        kpi_text = kpi if kpi else "Ninguno"
        
        text_response = f"""✅ **KPI guardado:** {kpi_text}

**➡️ PASO 7/8: Métricas RICE** 📊
Ahora vamos a calcular el score RICE. Responde las 4 métricas en este formato:

**Formato:** `reach impact confidence effort`

**📏 Definiciones:**
• **Reach (Alcance):** % de usuarios impactados (0-100)
• **Impact (Impacto):** Nivel de impacto (1=Bajo, 2=Medio, 3=Alto)  
• **Confidence (Confianza):** % de confianza en estimación (0-100)
• **Effort (Esfuerzo):** Sprints de desarrollo (ej: 1.5)

**💡 Ejemplo:** `85 3 90 2` 
*85% reach, impacto alto, 90% confianza, 2 sprints*

Escribe los 4 números separados por espacios:"""
        
        send_telegram_message(chat_id, text_response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Step 6 error: {e}")
        send_telegram_message(chat_id, f"❌ Error en paso 6: {str(e)}")

def handle_step_7_rice(chat_id, user_id, text):
    """PASO 7: Métricas RICE"""
    try:
        # Parsear entrada
        parts = text.strip().split()
        
        if len(parts) != 4:
            send_telegram_message(chat_id, f"""❌ **Formato incorrecto.** Necesito exactamente 4 números.

**Recibido:** {len(parts)} valores
**Esperado:** reach impact confidence effort

**Ejemplo:** `85 3 90 2`

Intenta nuevamente:""", parse_mode='Markdown')
            return
        
        try:
            # Convertir valores
            reach_pct = float(parts[0])
            impact = int(parts[1])  
            confidence_pct = float(parts[2])
            effort = float(parts[3])
            
            # Validar rangos
            validations = []
            
            if not (0 <= reach_pct <= 100):
                validations.append("• Reach debe estar entre 0-100")
            
            if impact not in [1, 2, 3]:
                validations.append("• Impact debe ser 1, 2 o 3")
                
            if not (0 <= confidence_pct <= 100):
                validations.append("• Confidence debe estar entre 0-100")
                
            if effort <= 0:
                validations.append("• Effort debe ser mayor que 0")
            
            if validations:
                error_text = "❌ **Errores de validación:**\n" + "\n".join(validations)
                error_text += "\n\n**Formato:** `reach impact confidence effort`\n**Ejemplo:** `85 3 90 2`"
                send_telegram_message(chat_id, error_text, parse_mode='Markdown')
                return
            
            # Convertir a formato interno
            reach = reach_pct / 100.0  # 0.0-1.0
            confidence = confidence_pct / 100.0  # 0.0-1.0
            
            # Calcular score
            score = (reach * impact * confidence) / effort
            
            # Guardar métricas
            user_states[user_id]['data'].update({
                'reach': reach,
                'impact': impact,
                'confidence': confidence,
                'effort': effort
            })
            
            user_states[user_id]['step'] = 8
            
            # Determinar prioridad
            if score >= 2.0:
                priority = "🔥 **ALTA PRIORIDAD** - Ejecutar inmediatamente"
                priority_class = "alta"
            elif score >= 1.0:
                priority = "⭐ **MEDIA PRIORIDAD** - Próximos sprints"
                priority_class = "media"
            else:
                priority = "📋 **BAJA PRIORIDAD** - Re-evaluar necesidad"
                priority_class = "baja"
            
            # Resumen completo
            data = user_states[user_id]['data']
            
            text_response = f"""✅ **Métricas RICE calculadas:**

📊 **Score RICE: {score:.3f}** - {priority}

**📋 RESUMEN COMPLETO:**
• **Nombre:** {data['initiative_name']}
• **Responsable:** {data['owner']}
• **Equipo:** {data['team']}
• **Portal:** {data['portal']}
• **KPI:** {data.get('main_kpi', 'Ninguno')}

**📏 Métricas:**
• **Alcance:** {reach_pct}% de usuarios
• **Impacto:** {impact}/3 ({"Bajo" if impact == 1 else "Medio" if impact == 2 else "Alto"})
• **Confianza:** {confidence_pct}% 
• **Esfuerzo:** {effort} sprints

**📊 Score = ({reach_pct}% × {impact} × {confidence_pct}%) ÷ {effort} = {score:.3f}**

**➡️ PASO 8/8: Confirmación**
¿Todo está correcto? Escribe:
• **"confirmar"** - Crear la iniciativa
• **"cancelar"** - Cancelar proceso
• **"editar"** - Corregir datos"""
            
            send_telegram_message(chat_id, text_response, parse_mode='Markdown')
            
        except ValueError as e:
            send_telegram_message(chat_id, f"""❌ **Error de formato.** Todos deben ser números válidos.

**Error:** {str(e)}

**Formato correcto:** `reach impact confidence effort`
**Ejemplo:** `85 3 90 2`

Intenta nuevamente:""", parse_mode='Markdown')
            return
        
    except Exception as e:
        logger.error(f"❌ Step 7 error: {e}")
        send_telegram_message(chat_id, f"❌ Error en paso 7: {str(e)}")

def handle_step_8_confirmation(chat_id, user_id, text):
    """PASO 8: Confirmación final"""
    try:
        command = text.strip().lower()
        
        if command in ['confirmar', 'confirm', 'sí', 'si', 'yes', 'ok']:
            # Crear la iniciativa
            data = user_states[user_id]['data']
            
            send_telegram_message(chat_id, "⚡ **Creando iniciativa...** Esto puede tardar unos segundos.")
            
            # Llamar a la función de creación
            result = create_initiative(data)
            
            if result.get('success'):
                # Calcular score para mostrar
                score = calculate_score_fast(data)
                priority_emoji = get_priority_emoji_safe(score)
                
                success_text = f"""✅ **¡INICIATIVA CREADA EXITOSAMENTE!** 🎉

{priority_emoji} **{data['initiative_name']}**
📊 **Score RICE:** {score:.3f}

**Datos guardados:**
👤 **Responsable:** {data['owner']}
👥 **Equipo:** {data['team']}  
🖥️ **Portal:** {data['portal']}
📈 **KPI:** {data.get('main_kpi', 'Ninguno')}

**Métricas RICE:**
• Alcance: {data['reach']*100:.0f}%
• Impacto: {data['impact']}/3
• Confianza: {data['confidence']*100:.0f}%
• Esfuerzo: {data['effort']} sprints

**🚀 Próximos pasos:**
• Aparecerá en lista principal: `iniciativas`
• Incluida en análisis AI: `analizar`
• Buscar por equipo: `buscar {data['team']}`"""
                
                send_telegram_message(chat_id, success_text, parse_mode='Markdown')
                
                # Limpiar estado
                del user_states[user_id]
                
            else:
                error_msg = result.get('error', 'Error desconocido')
                validation_errors = result.get('validation_errors', [])
                
                error_text = f"❌ **Error creando iniciativa:** {error_msg}"
                
                if validation_errors:
                    error_text += "\n\n**Errores de validación:**"
                    for error in validation_errors:
                        error_text += f"\n• {error}"
                
                error_text += "\n\n**🔄 El proceso sigue activo.** Puedes:"
                error_text += "\n• **'editar'** - Corregir datos"
                error_text += "\n• **'cancelar'** - Cancelar proceso"
                error_text += "\n• **'confirmar'** - Reintentar creación"
                
                send_telegram_message(chat_id, error_text, parse_mode='Markdown')
                
        elif command in ['cancelar', 'cancel', 'no']:
            # Cancelar proceso
            del user_states[user_id]
            send_telegram_message(chat_id, """❌ **Proceso cancelado.**

💾 **Datos no guardados.** La iniciativa no fue creada.

💡 **Para crear otra iniciativa:** `crear`""", parse_mode='Markdown')
            
        elif command in ['editar', 'edit', 'corregir']:
            # Opción de edición (simplificada - volver al inicio)
            del user_states[user_id]
            send_telegram_message(chat_id, """📝 **Edición solicitada.**

🔄 **Proceso reiniciado.** Tendrás que ingresar todos los datos nuevamente.

💡 **Para comenzar:** `crear`""", parse_mode='Markdown')
            
        else:
            # Comando no reconocido
            send_telegram_message(chat_id, f"""❓ **Comando no reconocido:** "{command}"

**Opciones disponibles:**
• **"confirmar"** - Crear la iniciativa  
• **"cancelar"** - Cancelar proceso
• **"editar"** - Reiniciar proceso

Escribe una de las opciones:""", parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"❌ Step 8 error: {e}")
        if user_id in user_states:
            del user_states[user_id]
        send_telegram_message(chat_id, f"❌ Error en confirmación: {str(e)}\n\nProceso cancelado. Usa `crear` para intentar nuevamente.")

# ===== FUNCIONES AUXILIARES ADICIONALES =====

def get_priority_emoji_safe(score):
    """Obtener emoji de prioridad de forma segura"""
    try:
        score_val = float(score) if score else 0
        if score_val >= 2.0:
            return "🔥"  # Alta prioridad
        elif score_val >= 1.0:
            return "⭐"  # Media prioridad
        else:
            return "📋"  # Baja prioridad
    except:
        return "📋"

def handle_filter_by_status(chat_id, status):
    """Filtrar iniciativas por estado"""
    try:
        send_telegram_message(chat_id, f"⏳ **Filtrando por estado:** {status}")
        
        from database import get_initiatives_by_status
        data = get_initiatives_by_status([status.title()])
        
        if not data.get("success"):
            send_telegram_message(chat_id, f"❌ Error: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])
        
        if not initiatives:
            send_telegram_message(chat_id, f"📭 **No hay iniciativas con estado:** {status}")
            return
        
        text = f"📊 **INICIATIVAS - {status.upper()}** ({len(initiatives)} encontradas)\n\n"
        
        for i, init in enumerate(initiatives[:10], 1):
            try:
                formatted = format_initiative_summary_safe(init, i)
                text += f"{formatted}\n\n"
            except Exception as e:
                logger.warning(f"Error formatting initiative {i}: {e}")
                continue
        
        if len(initiatives) > 10:
            text += f"📌 **{len(initiatives) - 10} iniciativas más...** Usa `buscar` para filtrar."
        
        send_telegram_message(chat_id, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Filter by status error: {e}")
        send_telegram_message(chat_id, f"❌ Error filtrando: {str(e)}")

def handle_status_info(chat_id):
    """Mostrar información de estados disponibles"""
    text = """📋 **ESTADOS DE INICIATIVAS** - Flujo Real

**🔄 Estados Disponibles:**
• ⏳ `Pending` - Pendiente de revisión  
• 👁️ `Reviewed` - Revisada
• ⭐ `Prioritized` - Priorizada
• 📂 `Backlog` - En backlog
• 🔧 `Sprint` - En desarrollo
• 🚀 `Production` - En producción
• 📊 `Monitoring` - En monitoreo
• ❌ `Discarded` - Descartada

**📱 Comandos de Filtro:**
• `pending` - Ver pendientes
• `sprint` - Ver en desarrollo
• `production` - Ver implementadas
• `monitoring` - Ver monitoreadas

**➡️ Flujo Típico:**
Pending → Reviewed → Prioritized → Backlog → Sprint → Production → Monitoring

💡 **Tip:** Usa `iniciativas` para ver todas ordenadas por score RICE."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')
