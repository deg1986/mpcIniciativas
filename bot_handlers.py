# 🔧 CÓDIGO PARA AGREGAR AL FINAL DEL ARCHIVO bot_handlers.py

# ===== FUNCIONES FALTANTES PARA EL COMANDO "crear" =====

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

# ===== INSTRUCCIONES DE IMPLEMENTACIÓN =====

"""
PASOS PARA IMPLEMENTAR:

1. Copia todo este código y agrégalo AL FINAL del archivo bot_handlers.py

2. Asegúrate de que las importaciones estén al inicio de bot_handlers.py:
   from database import create_initiative, calculate_score_fast
   from utils import send_telegram_message

3. El router en telegram_webhook() ya tiene las llamadas a estas funciones:
   - handle_create_command(chat_id, user_id)
   - handle_text_message(chat_id, user_id, message['text'])
   - handle_filter_by_status(chat_id, 'pending')
   - handle_status_info(chat_id)

4. La variable global user_states ya está definida al inicio del archivo.

5. Las constantes como MAX_INITIATIVE_NAME, VALID_TEAMS, etc. vienen de config.py

Después de agregar este código, el comando "crear" debería funcionar correctamente.
"""
