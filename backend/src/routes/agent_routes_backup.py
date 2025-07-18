"""
Rutas API del agente - Versión limpia
Endpoints para comunicación con el frontend
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from datetime import datetime
import logging
import time
import uuid
import os
import json
import zipfile
import tempfile
import asyncio
from pathlib import Path
from werkzeug.utils import secure_filename
from src.utils.json_encoder import MongoJSONEncoder, mongo_json_serializer
from src.tools.environment_setup_manager import EnvironmentSetupManager
from src.tools.task_planner import TaskPlanner
from src.tools.execution_engine import ExecutionEngine
from src.tools.tool_manager import ToolManager
from src.orchestration.task_orchestrator import TaskOrchestrator, OrchestrationContext

logger = logging.getLogger(__name__)

agent_bp = Blueprint('agent', __name__)

# Almacenamiento temporal para compartir conversaciones
shared_conversations = {}

# Almacenamiento temporal para archivos por tarea
task_files = {}

# Inicializar componentes
tool_manager = ToolManager()
task_planner = TaskPlanner()
environment_setup_manager = EnvironmentSetupManager()
execution_engine = ExecutionEngine(tool_manager, environment_setup_manager)

# Nuevo sistema de orquestación avanzada
from src.services.ollama_service import OllamaService
from src.memory.advanced_memory_manager import AdvancedMemoryManager

ollama_service = OllamaService()

# Inicializar memoria avanzada
memory_manager = AdvancedMemoryManager({
    'working_memory_capacity': 100,
    'episodic_memory_capacity': 2000,
    'semantic_concepts_capacity': 20000,
    'semantic_facts_capacity': 100000,
    'procedural_capacity': 2000,
    'tool_strategies_capacity': 10000,
    'embedding_model': 'all-MiniLM-L6-v2',
    'embedding_storage': '/app/backend/embeddings'
})

task_orchestrator = TaskOrchestrator(
    tool_manager=tool_manager,
    memory_manager=memory_manager,
    llm_service=ollama_service
)

@agent_bp.route('/orchestrate', methods=['POST'])
async def orchestrate_task():
    """
    Endpoint para orquestar tareas usando el nuevo sistema de orquestación avanzada
    """
    try:
        data = request.get_json()
        
        if not data or 'task_description' not in data:
            return jsonify({
                'error': 'task_description es requerido'
            }), 400
        
        task_description = data['task_description']
        user_id = data.get('user_id', 'default_user')
        session_id = data.get('session_id', str(uuid.uuid4()))
        priority = data.get('priority', 1)
        constraints = data.get('constraints', {})
        preferences = data.get('preferences', {})
        
        # Crear contexto de orquestación
        context = OrchestrationContext(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            task_description=task_description,
            priority=priority,
            constraints=constraints,
            preferences=preferences,
            metadata=data.get('metadata', {})
        )
        
        # Ejecutar orquestación
        result = await task_orchestrator.orchestrate_task(context)
        
        # Preparar respuesta
        response = {
            'task_id': result.task_id,
            'success': result.success,
            'total_execution_time': result.total_execution_time,
            'steps_completed': result.steps_completed,
            'steps_failed': result.steps_failed,
            'adaptations_made': result.adaptations_made,
            'resource_usage': result.resource_usage,
            'metadata': result.metadata
        }
        
        if result.error_message:
            response['error'] = result.error_message
        
        if result.execution_plan:
            response['execution_plan'] = {
                'id': result.execution_plan.id,
                'title': result.execution_plan.title,
                'strategy': result.execution_plan.strategy.value,
                'total_steps': len(result.execution_plan.steps),
                'estimated_duration': result.execution_plan.total_estimated_duration,
                'complexity_score': result.execution_plan.complexity_score,
                'success_probability': result.execution_plan.success_probability
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error en orquestación: {str(e)}")
        return jsonify({
            'error': f'Error en orquestación: {str(e)}'
        }), 500

@agent_bp.route('/orchestration/status/<task_id>', methods=['GET'])
async def get_orchestration_status(task_id):
    """
    Obtiene el estado de una orquestación
    """
    try:
        status = task_orchestrator.get_orchestration_status(task_id)
        
        if status:
            return jsonify(status)
        else:
            return jsonify({
                'error': 'Orquestación no encontrada'
            }), 404
            
    except Exception as e:
        logger.error(f"Error obteniendo estado: {str(e)}")
        return jsonify({
            'error': f'Error obteniendo estado: {str(e)}'
        }), 500

@agent_bp.route('/orchestration/metrics', methods=['GET'])
async def get_orchestration_metrics():
    """
    Obtiene métricas de orquestación
    """
    try:
        metrics = task_orchestrator.get_orchestration_metrics()
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {str(e)}")
        return jsonify({
            'error': f'Error obteniendo métricas: {str(e)}'
        }), 500

@agent_bp.route('/orchestration/active', methods=['GET'])
async def get_active_orchestrations():
    """
    Obtiene todas las orquestaciones activas
    """
    try:
        active_orchestrations = task_orchestrator.get_active_orchestrations()
        return jsonify(active_orchestrations)
        
    except Exception as e:
        logger.error(f"Error obteniendo orquestaciones activas: {str(e)}")
        return jsonify({
            'error': f'Error obteniendo orquestaciones activas: {str(e)}'
        }), 500

@agent_bp.route('/orchestration/cancel/<task_id>', methods=['POST'])
async def cancel_orchestration(task_id):
    """
    Cancela una orquestación activa
    """
    try:
        cancelled = await task_orchestrator.cancel_orchestration(task_id)
        
        if cancelled:
            return jsonify({
                'success': True,
                'message': f'Orquestación {task_id} cancelada exitosamente'
            })
        else:
            return jsonify({
                'error': 'Orquestación no encontrada o ya finalizada'
            }), 404
            
    except Exception as e:
        logger.error(f"Error cancelando orquestación: {str(e)}")
        return jsonify({
            'error': f'Error cancelando orquestación: {str(e)}'
        }), 500

@agent_bp.route('/orchestration/recommendations', methods=['GET'])
async def get_orchestration_recommendations():
    """
    Obtiene recomendaciones de optimización
    """
    try:
        recommendations = task_orchestrator.get_recommendations()
        return jsonify(recommendations)
        
    except Exception as e:
        logger.error(f"Error obteniendo recomendaciones: {str(e)}")
        return jsonify({
            'error': f'Error obteniendo recomendaciones: {str(e)}'
        }), 500

@agent_bp.route('/chat', methods=['POST'])
async def chat():
    """
    Endpoint principal para chat con integración de TaskOrchestrator
    Mantiene compatibilidad con el frontend existente
    """
    try:
        data = request.get_json()
        message = data.get('message', '')
        context = data.get('context', {})
        search_mode = data.get('search_mode', None)
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Obtener task_id del contexto
        task_id = context.get('task_id', str(uuid.uuid4()))
        user_id = context.get('user_id', 'default_user')
        session_id = context.get('session_id', str(uuid.uuid4()))
        
        # Detectar modo de búsqueda desde el mensaje
        original_message = message
        if message.startswith('[WebSearch]'):
            search_mode = 'websearch'
            message = message.replace('[WebSearch]', '').strip()
        elif message.startswith('[DeepResearch]'):
            search_mode = 'deepsearch'
            message = message.replace('[DeepResearch]', '').strip()
        
        # 🧠 INTEGRACIÓN AUTOMÁTICA DE MEMORIA - Recuperar contexto relevante
        relevant_context = ""
        try:
            # Inicializar memoria si no está inicializada
            if not memory_manager.is_initialized:
                await memory_manager.initialize()
            
            # Buscar contexto relevante de conversaciones anteriores
            context_results = await memory_manager.retrieve_relevant_context(
                query=message,
                context_type="all",
                max_results=5
            )
            
            if context_results and context_results != "No se encontró contexto relevante previo":
                relevant_context = f"\n\n[CONTEXTO PREVIO RELEVANTE]:\n{context_results}\n[FIN CONTEXTO]"
                logger.info(f"🧠 Contexto relevante encontrado para mejorar respuesta")
        except Exception as e:
            logger.warning(f"Error recuperando contexto: {e}")

        # 🚀 NUEVO: Usar Enhanced Agent si está disponible
        if not search_mode:
            try:
                # Obtener servicios del contexto de aplicación
                from flask import current_app
                
                # Verificar si enhanced components están disponibles
                enhanced_agent = getattr(current_app, 'enhanced_agent', None)
                enhanced_memory = getattr(current_app, 'enhanced_memory', None)
                enhanced_task_manager = getattr(current_app, 'enhanced_task_manager', None)
                
                # Desactivar enhanced agent por ahora para usar el sistema simple
                if False and enhanced_agent and enhanced_memory and enhanced_task_manager:
                    logger.info(f"🧠 Usando Enhanced Agent para procesamiento avanzado")
                    
                    # Agregar contexto relevante al mensaje
                    enhanced_message = message + relevant_context
                    
                    # Usar enhanced agent para procesamiento cognitivo
                    enhanced_response = enhanced_agent.process_user_message_enhanced(
                        enhanced_message, context
                    )
                    
                    # 🧠 ALMACENAR EN MEMORIA EPISÓDICA
                    try:
                        from src.memory.episodic_memory_store import Episode
                        
                        # Asegurar que la memoria está inicializada
                        if not memory_manager.is_initialized:
                            await memory_manager.initialize()
                        
                        episode = Episode(
                            id=str(uuid.uuid4()),
                            title=f"Conversación con usuario",
                            description=f"Usuario: {message}\nAgente: {enhanced_response}",
                            context={
                                'user_message': message,
                                'agent_response': enhanced_response,
                                'session_id': session_id,
                                'task_id': task_id,
                                'enhanced_processing': True,
                                **context
                            },
                            actions=[{
                                'type': 'user_message',
                                'content': message,
                                'timestamp': datetime.now().isoformat()
                            }],
                            outcomes=[{
                                'type': 'agent_response',
                                'content': enhanced_response,
                                'timestamp': datetime.now().isoformat()
                            }],
                            timestamp=datetime.now(),
                            success=True,
                            importance=3,
                            tags=['chat', 'conversation', 'enhanced']
                        )
                        await memory_manager.episodic_memory.store_episode(episode)
                        logger.info(f"🧠 Episodio almacenado en memoria para aprendizaje futuro")
                    except Exception as e:
                        logger.warning(f"Error almacenando episodio: {e}")
                    
                    # Obtener estado cognitivo
                    cognitive_status = enhanced_agent.get_enhanced_status()
                    
                    return jsonify({
                        'response': enhanced_response,
                        'enhanced_processing': True,
                        'cognitive_mode': cognitive_status.get('cognitive_capabilities', {}).get('current_mode', 'adaptive'),
                        'task_id': task_id,
                        'execution_status': 'enhanced_completed',
                        'timestamp': datetime.now().isoformat(),
                        'model': 'enhanced-mitosis-agent',
                        'memory_used': bool(relevant_context)
                    })
                else:
                    # Si enhanced components no están disponibles, usar TaskOrchestrator
                    logger.info(f"⚠️ Enhanced components no disponibles, usando TaskOrchestrator")
                    
                # Crear contexto de orquestación (fallback)
                orchestration_context = OrchestrationContext(
                    task_id=task_id,
                    user_id=user_id,
                    session_id=session_id,
                    task_description=message,
                    priority=1,
                    constraints=context.get('constraints', {}),
                    preferences=context.get('preferences', {}),
                    metadata={
                        'original_message': original_message,
                        'frontend_context': context,
                        'execution_type': 'orchestrated'
                    }
                )
                
                # Configurar callbacks para WebSocket si está disponible
                try:
                    from src.websocket.websocket_manager import get_websocket_manager
                    websocket_manager = get_websocket_manager()
                    
                    # Crear callbacks para notificaciones en tiempo real
                    async def on_progress(step_id, result, execution_state):
                        websocket_manager.send_orchestration_progress(
                            task_id=task_id,
                            step_id=step_id,
                            progress=execution_state.get('progress', 0),
                            current_step=execution_state.get('current_step', 'Processing...'),
                            total_steps=execution_state.get('total_steps', 1)
                        )
                    
                    async def on_complete(result):
                        websocket_manager.send_task_completed(
                            task_id=task_id,
                            success_rate=result.success_rate if hasattr(result, 'success_rate') else 1.0,
                            total_execution_time=result.get('execution_time', 0),
                            summary=result
                        )
                    
                    async def on_error(error_data):
                        websocket_manager.send_task_failed(
                            task_id=task_id,
                            error=str(error_data.get('error', 'Unknown error')),
                            context={'execution_type': 'orchestrated'}
                        )
                    
                    # Configurar callbacks del orquestador
                    task_orchestrator.add_callback('on_progress', on_progress)
                    task_orchestrator.add_callback('on_complete', on_complete)
                    task_orchestrator.add_callback('on_error', on_error)
                    
                except ImportError:
                    logger.warning("WebSocket manager not available, continuing without real-time updates")
                
                # SOLUCIÓN: Obtener servicios ANTES del thread de background
                # Obtener servicios del contexto de aplicación
                from flask import current_app
                ollama_service = current_app.ollama_service
                tool_manager = current_app.tool_manager
                database_service = current_app.database_service
                
                # Ejecutar orquestación de manera síncrona con herramientas reales
                try:
                    # Función para detectar si es una TAREA específica que requiere herramientas
                    def is_task_requiring_tools(message):
                        """Detectar si el mensaje es una tarea específica que requiere herramientas"""
                        message_lower = message.lower()
                        
                        # Primero: Detectar saludos y conversación casual (retorna False inmediatamente)
                        casual_only_phrases = [
                            'hola', 'hello', 'hi', 'buenos días', 'buenas tardes', 'buenas noches',
                            'gracias', 'thank you', 'thanks', 'de nada', 'por favor',
                            'qué tal', 'cómo estás', 'how are you', 'adiós', 'bye', 'hasta luego',
                            'cómo te llamas', 'what is your name', 'quien eres', 'who are you'
                        ]
                        
                        # Si es SOLO una frase casual (sin más contenido), no es tarea
                        if any(phrase == message_lower.strip() for phrase in casual_only_phrases):
                            return False
                        
                        # Segundo: Detectar indicadores de TAREA (retorna True si encuentra)
                        task_indicators = [
                            # Comandos explícitos
                            'ejecuta', 'ejecutar', 'run', 'comando', 'command',
                            # Análisis y procesamiento
                            'analiza', 'analizar', 'analyze', 'procesa', 'procesar',
                            # Búsqueda activa
                            'busca', 'buscar', 'search', 'encuentra', 'encontrar',
                            # Creación/modificación/generación
                            'crea', 'crear', 'create', 'genera', 'generar', 'generate', 'modifica', 'modificar',
                            'haz', 'hacer', 'do', 'make', 'build', 'construye', 'construir',
                            'desarrolla', 'desarrollar', 'develop', 'programa', 'programar',
                            # Gestión de archivos
                            'lista', 'listar', 'list', 'mostrar archivos', 'show files',
                            'descarga', 'descargar', 'download', 'sube', 'subir', 'upload',
                            # Investigación y reportes
                            'investiga', 'investigar', 'research', 'explora', 'explorar',
                            'informe', 'report', 'reporte', 'estudio', 'study', 'análisis',
                            # Operaciones de sistema
                            'verifica', 'verificar', 'check', 'monitorea', 'monitorear', 'instala', 'instalar',
                            # Palabras clave de resultado
                            'sobre', 'acerca de', 'about', 'mejores prácticas', 'best practices'
                        ]
                        
                        # Verificar si contiene indicadores de tarea
                        has_task_indicator = any(indicator in message_lower for indicator in task_indicators)
                        
                        # Verificar comandos específicos de sistema
                        command_patterns = ['ls ', 'cd ', 'pwd', 'ps ', 'mkdir', 'rm ', 'cp ', 'mv ', 'chmod', 'grep']
                        has_command = any(cmd in message_lower for cmd in command_patterns)
                        
                        # Verificar patrones de solicitud de trabajo
                        work_patterns = [
                            'web sobre', 'sitio web', 'website', 'aplicación', 'app',
                            'base de datos', 'database', 'sistema', 'system'
                        ]
                        has_work_pattern = any(pattern in message_lower for pattern in work_patterns)
                        
                        return has_task_indicator or has_command or has_work_pattern
                    
                    # Verificar si es una tarea que requiere herramientas
                    if not is_task_requiring_tools(message):
                        # Es conversación normal - usar respuesta estándar del LLM
                        logger.info(f"💬 Conversación normal detectada - no ejecutar herramientas")
                        
                        # Generar respuesta normal usando Ollama
                        enhanced_message = message + relevant_context
                        response_data = ollama_service.generate_response(enhanced_message)
                        
                        if response_data.get('error'):
                            raise Exception(response_data['error'])
                        
                        agent_response = response_data.get('response', 'No se pudo generar respuesta')
                        
                        return jsonify({
                            'response': agent_response,
                            'task_id': task_id,
                            'model': response_data.get('model', 'unknown'),
                            'timestamp': datetime.now().isoformat(),
                            'memory_used': bool(relevant_context),
                            'conversation_mode': True
                        })
                    
                    # Es una tarea específica - ejecutar herramientas
                    logger.info(f"🛠️ Tarea específica detectada - ejecutar herramientas")
                    
                    # Crear un simple sistema de ejecución de herramientas
                    def execute_task_with_tools():
                        """Ejecutar tarea con herramientas automáticamente"""
                        # Analizar el mensaje para determinar qué herramientas usar
                        tools_to_use = []
                        
                        # Detectar si necesita ejecutar comandos shell
                        if any(keyword in message.lower() for keyword in ['comando', 'ejecuta', 'shell', 'ls', 'cd', 'mkdir', 'rm', 'cat', 'grep', 'find', 'chmod', 'chown', 'ps', 'kill', 'pwd']):
                            tools_to_use.append('shell')
                        
                        # Detectar si necesita gestión de archivos
                        if any(keyword in message.lower() for keyword in ['archivo', 'file', 'directorio', 'folder', 'lista', 'listar', 'mostrar', 'crear', 'eliminar', 'leer', 'escribir', 'copiar', 'mover']):
                            tools_to_use.append('file_manager')
                        
                        # Detectar si necesita búsqueda web (mejorado)
                        if any(keyword in message.lower() for keyword in ['buscar', 'busca', 'search', 'información', 'noticias', 'web', 'internet', 'google', 'investiga', 'investigar', 'informe', 'report', 'reporte', 'sobre', 'acerca de', 'about', 'mejores prácticas', 'best practices']):
                            tools_to_use.append('web_search')
                        
                        # Si no detecta herramientas específicas, usar herramientas por defecto según el contexto
                        if not tools_to_use:
                            if any(keyword in message.lower() for keyword in ['analiza', 'analizar', 'procesa', 'procesar', 'verifica', 'verificar', 'genera', 'generar', 'crea', 'crear', 'haz', 'hacer', 'informe', 'report']):
                                tools_to_use = ['web_search']  # Para tareas de investigación/generación
                            else:
                                tools_to_use = ['shell']  # Por defecto para tareas generales
                        
                        # Ejecutar herramientas detectadas
                        results = []
                        for tool_name in tools_to_use:
                            try:
                                # Preparar parámetros según el tipo de herramienta
                                if tool_name == 'shell':
                                    # Extraer comando del mensaje
                                    if 'ls' in message.lower():
                                        params = {'command': 'ls -la /app'}
                                    elif 'pwd' in message.lower():
                                        params = {'command': 'pwd'}
                                    elif 'ps' in message.lower():
                                        params = {'command': 'ps aux'}
                                    else:
                                        params = {'command': 'ls -la'}
                                elif tool_name == 'file_manager':
                                    params = {'action': 'list', 'path': '/app'}
                                elif tool_name == 'web_search':
                                    params = {'query': message}
                                else:
                                    params = {'input': message}
                                
                                # Ejecutar herramienta
                                result = tool_manager.execute_tool(tool_name, params, task_id=task_id)
                                results.append({
                                    'tool': tool_name,
                                    'result': result,
                                    'success': not result.get('error')
                                })
                                
                            except Exception as e:
                                results.append({
                                    'tool': tool_name,
                                    'result': {'error': str(e)},
                                    'success': False
                                })
                        
                        return results
                    
                    # Ejecutar tareas con herramientas
                    tool_results = execute_task_with_tools()
                    
                    # Generar respuesta basada en los resultados
                    response_parts = [f"🤖 **Ejecución Completada**\n\n**Tarea:** {message}\n"]
                    
                    if tool_results:
                        response_parts.append("🛠️ **Herramientas Ejecutadas:**\n")
                        for i, result in enumerate(tool_results, 1):
                            status = "✅ EXITOSO" if result['success'] else "❌ ERROR"
                            response_parts.append(f"{i}. **{result['tool']}**: {status}")
                            
                            if result['success'] and result['result']:
                                # Formatear resultado según el tipo de herramienta
                                if result['tool'] == 'shell':
                                    if 'output' in result['result']:
                                        response_parts.append(f"```\n{result['result']['output']}\n```")
                                elif result['tool'] == 'file_manager':
                                    if 'files' in result['result']:
                                        response_parts.append("📁 **Archivos encontrados:**")
                                        for file_info in result['result']['files'][:5]:  # Mostrar solo los primeros 5
                                            response_parts.append(f"• {file_info}")
                                elif result['tool'] == 'web_search':
                                    if 'results' in result['result']:
                                        response_parts.append("🔍 **Resultados de búsqueda:**")
                                        for search_result in result['result']['results'][:3]:  # Mostrar solo los primeros 3
                                            response_parts.append(f"• {search_result.get('title', 'Sin título')}")
                                else:
                                    response_parts.append(f"📊 **Resultado:** {str(result['result'])[:200]}...")
                            elif not result['success']:
                                response_parts.append(f"⚠️ **Error:** {result['result'].get('error', 'Error desconocido')}")
                            
                            response_parts.append("")  # Línea en blanco
                    
                    final_response = "\n".join(response_parts)
                    
                    return jsonify({
                        'response': final_response,
                        'tool_results': tool_results,
                        'tools_executed': len(tool_results),
                        'task_id': task_id,
                        'execution_status': 'completed',
                        'timestamp': datetime.now().isoformat(),
                        'model': 'tool-execution-agent',
                        'memory_used': bool(relevant_context)
                    })
                    
                except Exception as e:
                    logger.error(f"❌ Error executing tools: {str(e)}")
                    # Fallback a respuesta regular
                
            except Exception as e:
                logger.error(f"❌ Error in orchestration: {str(e)}")
                # Fallback a ejecución regular
                
        # 🔄 FALLBACK: Usar sistema anterior para WebSearch/DeepSearch o si falla orquestación
        
        # Obtener servicios del contexto de aplicación (necesario para todas las opciones)
        from flask import current_app
        ollama_service = current_app.ollama_service
        tool_manager = current_app.tool_manager
        database_service = current_app.database_service
        
        # Manejo de WebSearch
        if search_mode == 'websearch':
            try:
                # Ejecutar búsqueda web
                search_result = tool_manager.execute_tool(
                    'web_search',
                    {'query': message},
                    task_id=task_id
                )
                
                # Procesar resultado
                if search_result.get('error'):
                    raise Exception(search_result['error'])
                
                # Formatear respuesta
                response = f"🔍 **Resultados de Búsqueda Web**\n\n"
                response += f"**Consulta:** {message}\n\n"
                
                if search_result.get('results'):
                    response += "📋 **Resultados encontrados:**\n\n"
                    for i, result in enumerate(search_result['results'][:5], 1):
                        response += f"**{i}. {result.get('title', 'Sin título')}**\n"
                        response += f"🔗 {result.get('url', 'Sin URL')}\n"
                        response += f"📝 {result.get('snippet', 'Sin descripción')}\n\n"
                
                return jsonify({
                    'response': response,
                    'search_results': search_result.get('results', []),
                    'task_id': task_id,
                    'search_mode': 'websearch',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in web search: {str(e)}")
                return jsonify({
                    'error': f'Error en búsqueda web: {str(e)}'
                }), 500
        
        # Manejo de DeepSearch
        elif search_mode == 'deepsearch':
            try:
                # Ejecutar investigación profunda
                research_result = tool_manager.execute_tool(
                    'deep_research',
                    {'query': message},
                    task_id=task_id
                )
                
                # Procesar resultado
                if research_result.get('error'):
                    raise Exception(research_result['error'])
                
                # Formatear respuesta
                response = f"🔬 **Investigación Profunda Completada**\n\n"
                response += f"**Tema:** {message}\n\n"
                response += research_result.get('summary', 'No hay resumen disponible')
                
                return jsonify({
                    'response': response,
                    'research_data': research_result,
                    'task_id': task_id,
                    'search_mode': 'deepsearch',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in deep research: {str(e)}")
                return jsonify({
                    'error': f'Error en investigación profunda: {str(e)}'
                }), 500
        
        # Manejo de chat regular (fallback)
        else:
            try:
                # Agregar contexto relevante al mensaje
                enhanced_message = message + relevant_context
                
                # Generar respuesta usando Ollama
                response_data = ollama_service.generate_response(enhanced_message)
                
                if response_data.get('error'):
                    raise Exception(response_data['error'])
                
                agent_response = response_data.get('response', 'No se pudo generar respuesta')
                
                # 🧠 ALMACENAR EN MEMORIA EPISÓDICA
                try:
                    from src.memory.episodic_memory_store import Episode
                    
                    episode = Episode(
                        id=str(uuid.uuid4()),
                        title=f"Conversación con usuario",
                        description=f"Usuario: {message}\nAgente: {agent_response}",
                        context={
                            'user_message': message,
                            'agent_response': agent_response,
                            'session_id': session_id,
                            'task_id': task_id,
                            'fallback_mode': True,
                            **context
                        },
                        actions=[{
                            'type': 'user_message',
                            'content': message,
                            'timestamp': datetime.now().isoformat()
                        }],
                        outcomes=[{
                            'type': 'agent_response',
                            'content': agent_response,
                            'timestamp': datetime.now().isoformat()
                        }],
                        timestamp=datetime.now(),
                        success=True,
                        importance=2,
                        tags=['chat', 'conversation', 'fallback']
                    )
                    await memory_manager.episodic_memory.store_episode(episode)
                    logger.info(f"🧠 Episodio almacenado en memoria (modo fallback)")
                except Exception as e:
                    logger.warning(f"Error almacenando episodio: {e}")
                
                return jsonify({
                    'response': agent_response,
                    'task_id': task_id,
                    'model': response_data.get('model', 'unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'memory_used': bool(relevant_context)
                })
                
            except Exception as e:
                logger.error(f"Error in regular chat: {str(e)}")
                return jsonify({
                    'error': f'Error generando respuesta: {str(e)}'
                }), 500
        
    except Exception as e:
        logger.error(f"Error general en chat: {str(e)}")
        return jsonify({
            'error': f'Error interno del servidor: {str(e)}'
        }), 500

@agent_bp.route('/task/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    Obtiene el estado de una tarea específica
    Compatible con tanto orquestación como ejecución regular
    """
    try:
        # Verificar si es una orquestación activa
        orchestration_status = task_orchestrator.get_orchestration_status(task_id)
        
        if orchestration_status:
            return jsonify({
                'task_id': task_id,
                'type': 'orchestration',
                'status': orchestration_status.get('status', 'unknown'),
                'progress': orchestration_status.get('progress', 0),
                'start_time': orchestration_status.get('start_time', 0),
                'elapsed_time': orchestration_status.get('elapsed_time', 0),
                'context': orchestration_status.get('context', {})
            })
        
        # Si no hay orquestación, buscar en el sistema anterior
        # TODO: Integrar con el sistema de ejecución anterior si es necesario
        
        return jsonify({
            'task_id': task_id,
            'type': 'regular',
            'status': 'not_found',
            'message': 'Task not found in active orchestrations'
        }), 404
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de tarea: {str(e)}")
        return jsonify({
            'error': f'Error obteniendo estado: {str(e)}'
        }), 500

@agent_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint con información de orquestación
    """
    try:
        # Obtener métricas de orquestación
        orchestration_metrics = task_orchestrator.get_orchestration_metrics()
        active_orchestrations = task_orchestrator.get_active_orchestrations()
        
        # Obtener información de herramientas
        tool_manager = current_app.tool_manager
        available_tools = tool_manager.get_available_tools()
        
        # Obtener estado de Ollama
        ollama_service = current_app.ollama_service
        ollama_status = ollama_service.check_connection()
        
        # Obtener estado de base de datos
        database_service = current_app.database_service
        db_status = database_service.check_connection()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'orchestration': {
                    'active_tasks': len(active_orchestrations),
                    'total_tasks': orchestration_metrics.get('total_tasks', 0),
                    'success_rate': orchestration_metrics.get('successful_tasks', 0) / max(orchestration_metrics.get('total_tasks', 1), 1),
                    'avg_execution_time': orchestration_metrics.get('avg_execution_time', 0)
                },
                'ollama': ollama_status,
                'database': db_status,
                'tools': {
                    'available': len(available_tools),
                    'list': [tool.get('name', 'unknown') for tool in available_tools]
                }
            },
            'version': '2.0.0-orchestrated'
        })
        
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/ollama/check', methods=['POST'])
def check_ollama_connection():
    """Verificar conexión con un endpoint de Ollama específico"""
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return jsonify({'error': 'endpoint is required'}), 400
        
        # Crear servicio temporal para verificar conexión
        from src.services.ollama_service import OllamaService
        temp_service = OllamaService(base_url=endpoint)
        
        is_healthy = temp_service.is_healthy()
        
        return jsonify({
            'is_connected': is_healthy,
            'endpoint': endpoint,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error verificando conexión Ollama: {str(e)}")
        return jsonify({
            'error': str(e),
            'is_connected': False,
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/ollama/models', methods=['POST'])
def get_ollama_models():
    """Obtener modelos de un endpoint de Ollama específico"""
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return jsonify({'error': 'endpoint is required'}), 400
        
        # Crear servicio temporal para obtener modelos
        from src.services.ollama_service import OllamaService
        temp_service = OllamaService(base_url=endpoint)
        
        if not temp_service.is_healthy():
            return jsonify({
                'error': 'Cannot connect to Ollama endpoint',
                'models': [],
                'timestamp': datetime.now().isoformat()
            }), 503
        
        models = temp_service.get_available_models()
        
        return jsonify({
            'models': models,
            'endpoint': endpoint,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo modelos Ollama: {str(e)}")
        return jsonify({
            'error': str(e),
            'models': [],
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/memory/stats', methods=['GET'])
def get_memory_stats():
    """Obtiene estadísticas del sistema de memoria autónoma"""
    try:
        async def get_stats():
            # Inicializar memoria si no está inicializada
            if not memory_manager.is_initialized:
                await memory_manager.initialize()
            
            # Obtener estadísticas completas
            stats = await memory_manager.get_memory_stats()
            
            # Agregar estadísticas adicionales
            stats['total_orchestrations'] = len(task_orchestrator.orchestration_history)
            stats['active_orchestrations'] = len(task_orchestrator.active_orchestrations)
            
            return stats
        
        # Ejecutar función asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(get_stats())
        loop.close()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de memoria: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/memory/learning-insights', methods=['GET'])
def get_learning_insights():
    """Obtiene insights de aprendizaje del agente"""
    try:
        async def get_insights():
            # Inicializar memoria si no está inicializada
            if not memory_manager.is_initialized:
                await memory_manager.initialize()
            
            # Obtener insights de aprendizaje
            insights = memory_manager.procedural_memory.get_learning_insights()
            
            # Agregar métricas de orquestación
            orchestration_metrics = task_orchestrator.get_orchestration_metrics()
            
            return {
                'learning_insights': insights,
                'orchestration_metrics': orchestration_metrics,
                'timestamp': datetime.now().isoformat()
            }
        
        # Ejecutar función asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        insights = loop.run_until_complete(get_insights())
        loop.close()
        
        return jsonify(insights)
        
    except Exception as e:
        logger.error(f"Error obteniendo insights de aprendizaje: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/memory/search', methods=['POST'])
def search_memory():
    """Busca en la memoria autónoma del agente"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        context_type = data.get('context_type', 'all')
        max_results = data.get('max_results', 10)
        
        if not query:
            return jsonify({'error': 'query is required'}), 400
        
        async def search():
            # Inicializar memoria si no está inicializada
            if not memory_manager.is_initialized:
                await memory_manager.initialize()
            
            # Buscar en memoria
            results = await memory_manager.retrieve_relevant_context(
                query, 
                context_type, 
                max_results
            )
            
            return results
        
        # Ejecutar función asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(search())
        loop.close()
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error buscando en memoria: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/memory/compress', methods=['POST'])
def compress_memory():
    """Comprime memoria antigua para optimizar almacenamiento"""
    try:
        data = request.get_json() or {}
        compression_threshold_days = data.get('compression_threshold_days', 30)
        compression_ratio = data.get('compression_ratio', 0.5)
        
        async def compress():
            # Inicializar memoria si no está inicializada
            if not memory_manager.is_initialized:
                await memory_manager.initialize()
            
            # Comprimir memoria
            result = await memory_manager.compress_old_memory(
                compression_threshold_days=compression_threshold_days,
                compression_ratio=compression_ratio
            )
            
            return result
        
        # Ejecutar función asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(compress())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error comprimiendo memoria: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/memory/export', methods=['POST'])
def export_memory():
    """Exporta datos de memoria para respaldo o análisis"""
    try:
        data = request.get_json() or {}
        export_format = data.get('export_format', 'json')
        include_compressed = data.get('include_compressed', False)
        output_file = data.get('output_file', None)
        
        async def export():
            # Inicializar memoria si no está inicializada
            if not memory_manager.is_initialized:
                await memory_manager.initialize()
            
            # Exportar memoria
            result = await memory_manager.export_memory_data(
                export_format=export_format,
                include_compressed=include_compressed,
                output_file=output_file
            )
            
            return result
        
        # Ejecutar función asíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(export())
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error exportando memoria: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Enhanced Agent Endpoints
@agent_bp.route('/enhanced/status', methods=['GET'])
def get_enhanced_status():
    """Obtiene el estado avanzado del enhanced agent"""
    try:
        enhanced_agent = current_app.enhanced_agent
        if not enhanced_agent:
            return jsonify({'error': 'Enhanced agent not available'}), 503
        
        status = enhanced_agent.get_enhanced_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error obteniendo estado enhanced: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/enhanced/cognitive-mode', methods=['GET'])
def get_cognitive_mode():
    """Obtiene el modo cognitivo actual del enhanced agent"""
    try:
        enhanced_agent = current_app.enhanced_agent
        if not enhanced_agent:
            return jsonify({'error': 'Enhanced agent not available'}), 503
        
        return jsonify({
            'cognitive_mode': enhanced_agent.cognitive_mode.value,
            'learning_enabled': enhanced_agent.learning_enabled,
            'reflection_threshold': enhanced_agent.reflection_threshold,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo modo cognitivo: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/enhanced/memory/semantic-search', methods=['POST'])
def enhanced_semantic_search():
    """Búsqueda semántica usando enhanced memory manager"""
    try:
        enhanced_memory = current_app.enhanced_memory
        if not enhanced_memory:
            return jsonify({'error': 'Enhanced memory not available'}), 503
        
        data = request.get_json()
        query = data.get('query', '')
        n_results = data.get('n_results', 10)
        category = data.get('category', None)
        min_confidence = data.get('min_confidence', 0.5)
        
        if not query:
            return jsonify({'error': 'query is required'}), 400
        
        # Realizar búsqueda semántica
        results = enhanced_memory.search_knowledge_semantic(
            query=query,
            n_results=n_results,
            category=category,
            min_confidence=min_confidence
        )
        
        # Convertir resultados a formato JSON serializable
        serialized_results = []
        for result in results:
            serialized_results.append({
                'id': result.id,
                'content': result.content,
                'category': result.category,
                'source': result.source,
                'confidence': result.confidence,
                'created_at': result.created_at,
                'accessed_count': result.accessed_count,
                'tags': result.tags
            })
        
        return jsonify({
            'results': serialized_results,
            'query': query,
            'total_results': len(serialized_results),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en búsqueda semántica: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/enhanced/memory/stats', methods=['GET'])
def get_enhanced_memory_stats():
    """Obtiene estadísticas de la memoria mejorada"""
    try:
        enhanced_memory = current_app.enhanced_memory
        if not enhanced_memory:
            return jsonify({'error': 'Enhanced memory not available'}), 503
        
        stats = enhanced_memory.get_enhanced_memory_stats()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de memoria mejorada: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/enhanced/learning/patterns', methods=['GET'])
def get_learned_patterns():
    """Obtiene los patrones aprendidos por el enhanced agent"""
    try:
        enhanced_agent = current_app.enhanced_agent
        if not enhanced_agent:
            return jsonify({'error': 'Enhanced agent not available'}), 503
        
        return jsonify({
            'learned_patterns': enhanced_agent.learned_patterns,
            'total_patterns': len(enhanced_agent.learned_patterns),
            'learning_metrics': enhanced_agent.learning_metrics.__dict__,
            'cognitive_stats': enhanced_agent.cognitive_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo patrones aprendidos: {str(e)}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500