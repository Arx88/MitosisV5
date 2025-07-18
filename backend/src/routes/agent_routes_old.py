"""
Rutas API del agente
Endpoints para comunicación con el frontend
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from datetime import datetime
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

agent_bp = Blueprint('agent', __name__)

# Almacenamiento temporal para compartir conversaciones
shared_conversations = {}

# Almacenamiento temporal para archivos por tarea
task_files = {}

# Inicializar Environment Setup Manager
environment_setup_manager = EnvironmentSetupManager()

# Inicializar Task Planner
task_planner = TaskPlanner()

# Inicializar Execution Engine
execution_engine = ExecutionEngine(
    tool_manager=current_app.tool_manager if current_app else None,
    environment_manager=environment_setup_manager
)

@agent_bp.route('/setup-environment', methods=['POST'])
def setup_environment():
    """Endpoint para configurar entorno de una tarea"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        task_title = data.get('task_title', '')
        task_type = data.get('task_type', 'general')
        
        if not task_id:
            return jsonify({'error': 'task_id is required'}), 400
        
        # Iniciar setup de manera asíncrona (simulamos con threading)
        import threading
        
        def run_async_setup():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    environment_setup_manager.setup_environment(task_id, task_title, task_type)
                )
            finally:
                loop.close()
        
        setup_thread = threading.Thread(target=run_async_setup)
        setup_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Environment setup started',
            'task_id': task_id,
            'estimated_duration': '1-2 minutes',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/setup-status/<task_id>', methods=['GET'])
def get_setup_status(task_id):
    """Obtener estado del setup de environment"""
    try:
        status = environment_setup_manager.get_setup_status(task_id)
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/container/execute/<task_id>', methods=['POST'])
def execute_in_container(task_id):
    """Ejecutar comando en el contenedor de una tarea"""
    try:
        data = request.get_json()
        command = data.get('command')
        timeout = data.get('timeout', 30)
        
        if not command:
            return jsonify({'error': 'command is required'}), 400
        
        # Ejecutar comando a través del environment setup manager
        result = environment_setup_manager.execute_in_container(task_id, command, timeout)
        
        return jsonify({
            'success': result.get('success', False),
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/container/info/<task_id>', methods=['GET'])
def get_container_info(task_id):
    """Obtener información del contenedor de una tarea"""
    try:
        container_manager = environment_setup_manager.get_container_manager()
        info = container_manager.get_container_info(task_id)
        
        return jsonify({
            'container_info': info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/container/list', methods=['GET'])
def list_containers():
    """Listar todos los contenedores activos"""
    try:
        container_manager = environment_setup_manager.get_container_manager()
        containers = container_manager.list_containers()
        
        return jsonify({
            'containers': containers,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/container/cleanup/<task_id>', methods=['DELETE'])
def cleanup_container(task_id):
    """Limpiar contenedor de una tarea"""
    try:
        # Limpiar a través del environment setup manager
        environment_setup_manager.cleanup_session(task_id)
        
        return jsonify({
            'success': True,
            'message': f'Container for task {task_id} cleaned up',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud del agente"""
    try:
        # Obtener servicios
        ollama_service = current_app.ollama_service
        tool_manager = current_app.tool_manager
        database_service = current_app.database_service
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'ollama': ollama_service.is_healthy(),
                'tools': len(tool_manager.get_available_tools()),
                'database': database_service.is_connected()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        return jsonify({
            'error': str(e),
            'models': [],
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/deep-research/progress/<task_id>', methods=['GET'])
def get_deep_research_progress(task_id):
    """Endpoint para obtener progreso de DeepResearch en tiempo real"""
    try:
        # Obtener tool manager
        tool_manager = current_app.tool_manager
        
        # Obtener la herramienta de investigación profunda
        enhanced_tool = tool_manager.tools.get('enhanced_deep_research')
        
        if not enhanced_tool:
            return jsonify({'error': 'Enhanced Deep Research tool not found'}), 404
        
        # Obtener estado del progreso
        progress_status = enhanced_tool.get_progress_status()
        
        # Obtener los pasos predefinidos
        steps = enhanced_tool.get_progress_steps()
        
        return jsonify({
            'task_id': task_id,
            'is_active': progress_status.get('is_active', False),
            'current_progress': progress_status.get('current_progress', 0),
            'current_step': progress_status.get('current_step', -1),
            'latest_update': progress_status.get('latest_update'),
            'steps': steps
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/chat', methods=['POST'])
def chat():
    """Endpoint principal para chat con el agente - CON EJECUCIÓN AUTÓNOMA"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        context = data.get('context', {})
        search_mode = data.get('search_mode', None)
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Obtener servicios
        ollama_service = current_app.ollama_service
        tool_manager = current_app.tool_manager
        database_service = current_app.database_service
        
        # Obtener task_id del contexto
        task_id = context.get('task_id')
        
        # Detectar modo de búsqueda desde el mensaje
        original_message = message
        if message.startswith('[WebSearch]'):
            search_mode = 'websearch'
            message = message.replace('[WebSearch]', '').strip()
        elif message.startswith('[DeepResearch]'):
            search_mode = 'deepsearch'
            message = message.replace('[DeepResearch]', '').strip()
        
        # 🚀 NUEVO: Usar ExecutionEngine para tareas regulares (no WebSearch/DeepSearch)
        # ENABLED FOR AUTONOMOUS EXECUTION
        if not search_mode and task_id:
            try:
                # Inicializar execution engine
                global execution_engine
                execution_engine = ExecutionEngine(
                    tool_manager=tool_manager,
                    environment_manager=environment_setup_manager
                )
                
                # 🔌 Obtener WebSocket manager y crear callbacks
                from src.websocket.websocket_manager import get_websocket_manager
                websocket_manager = get_websocket_manager()
                
                # Crear callbacks para WebSocket
                callbacks = websocket_manager.create_execution_callbacks(task_id)
                
                # 🎯 EJECUCIÓN AUTÓNOMA: Ejecutar tarea con ExecutionEngine
                # Ejecutar de manera asíncrona en un thread separado
                import threading
                
                def run_autonomous_execution():
                    """Ejecutar tarea autónoma en thread separado"""
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Configurar callbacks del ExecutionEngine
                        execution_engine.progress_callback = callbacks['progress_callback']
                        execution_engine.completion_callback = callbacks['completion_callback']
                        execution_engine.error_callback = callbacks['error_callback']
                        
                        # Ejecutar la tarea
                        result = loop.run_until_complete(
                            execution_engine.execute_task(task_id, message, message)
                        )
                        print(f"✅ Autonomous execution completed for task {task_id}")
                        print(f"📊 Status: {result.status.value}, Success rate: {result.success_rate}")
                        
                        # Enviar notificación de finalización via WebSocket
                        websocket_manager.send_task_completed(
                            task_id=task_id,
                            success_rate=result.success_rate,
                            total_execution_time=result.total_execution_time,
                            summary=result.to_dict()
                        )
                    except Exception as e:
                        print(f"❌ Autonomous execution failed for task {task_id}: {str(e)}")
                        # Enviar notificación de error via WebSocket
                        websocket_manager.send_task_failed(
                            task_id=task_id,
                            error=str(e),
                            context={'execution_type': 'autonomous'}
                        )
                    finally:
                        loop.close()
                
                # Iniciar ejecución autónoma en background
                execution_thread = threading.Thread(target=run_autonomous_execution)
                execution_thread.daemon = True
                execution_thread.start()
                
                # Respuesta inmediata para el frontend
                return jsonify({
                    'response': f'🤖 **Ejecución Autónoma Iniciada**\n\n**Tarea:** {message}\n\n🔄 El agente está analizando tu solicitud y ejecutando las acciones necesarias de forma autónoma...\n\n📋 **Proceso:**\n• Análisis de la tarea\n• Generación de plan de ejecución\n• Ejecución automática de pasos\n• Validación de resultados\n\n⏱️ **Estado:** Ejecutando en segundo plano\n\n*Los resultados aparecerán automáticamente cuando se complete la ejecución.*\n\n🔔 **Nota:** Los updates en tiempo real se mostrarán automáticamente en la interfaz.',
                    'autonomous_execution': True,
                    'task_id': task_id,
                    'execution_status': 'started',
                    'websocket_enabled': True,
                    'timestamp': datetime.now().isoformat(),
                    'model': 'autonomous-agent'
                })
                
            except Exception as e:
                print(f"❌ Error in autonomous execution: {str(e)}")
                # Fallback a ejecución regular
                
        # Ejecutar herramientas directamente según el modo de búsqueda
        tool_results = []
        created_files = []
        
        if search_mode == 'websearch':
            # Usar web_search para WebSearch
            try:
                result = tool_manager.execute_tool('web_search', {
                    'query': message,
                    'max_results': 10
                })
                tool_results.append({
                    'tool': 'web_search',
                    'parameters': {'query': message, 'max_results': 10},
                    'result': result
                })
            except Exception as e:
                tool_results.append({
                    'tool': 'web_search',
                    'parameters': {'query': message},
                    'result': {'error': str(e)}
                })
        
        elif search_mode == 'deepsearch':
            # Usar deep_research para DeepResearch
            try:
                result = tool_manager.execute_tool('deep_research', {
                    'query': message,
                    'max_sources': 20,
                    'research_depth': 'comprehensive'
                })
                tool_results.append({
                    'tool': 'deep_research',
                    'parameters': {'query': message, 'max_sources': 20, 'research_depth': 'comprehensive'},
                    'result': result
                })
                
                # Si hay un archivo de informe, agregarlo a los archivos de la tarea
                if result.get('success') and result.get('report_file'):
                    report_file_path = result['report_file']
                    file_info = {
                        'id': str(uuid.uuid4()),
                        'file_id': str(uuid.uuid4()),
                        'task_id': task_id,
                        'name': f'informe_{message.replace(" ", "_")[:30]}.md',
                        'path': report_file_path,
                        'size': os.path.getsize(report_file_path) if os.path.exists(report_file_path) else 0,
                        'type': 'file',
                        'mime_type': 'text/markdown',
                        'source': 'agent',
                        'created_at': datetime.now().isoformat()
                    }
                    
                    # Agregar archivo a la tarea
                    if task_id not in task_files:
                        task_files[task_id] = []
                    task_files[task_id].append(file_info)
                    created_files.append(file_info)
                    
            except Exception as e:
                tool_results.append({
                    'tool': 'deep_research',
                    'parameters': {'query': message, 'max_sources': 20, 'research_depth': 'comprehensive'},
                    'result': {'error': str(e)}
                })
        
        # Generar respuesta con Ollama si no hay modo de búsqueda específico
        if not search_mode:
            response = ollama_service.generate_response(message, context, use_tools=True)
            
            # Ejecutar herramientas adicionales si Ollama las solicita
            if response.get('tool_calls'):
                for tool_call in response['tool_calls']:
                    tool_name = tool_call.get('tool')
                    parameters = tool_call.get('parameters', {})
                    
                    try:
                        result = tool_manager.execute_tool(tool_name, parameters)
                        tool_results.append({
                            'tool': tool_name,
                            'parameters': parameters,
                            'result': result
                        })
                        
                        # Rastrear archivos creados
                        if (tool_name == 'file_manager' and 
                            parameters.get('action') in ['create', 'write'] and
                            result.get('success')):
                            
                            file_path = result.get('path')
                            if file_path:
                                file_info = {
                                    'file_id': str(uuid.uuid4()),
                                    'task_id': task_id,
                                    'name': os.path.basename(file_path),
                                    'path': file_path,
                                    'size': result.get('size', 0),
                                    'type': 'file',
                                    'mime_type': 'text/plain',
                                    'source': 'agent'
                                }
                                
                                # Guardar en la base de datos
                                if database_service.is_connected():
                                    database_service.save_file(file_info)
                                
                                # Mantener compatibilidad con sistema actual
                                if task_id:
                                    if task_id not in task_files:
                                        task_files[task_id] = []
                                    task_files[task_id].append(file_info)
                                    created_files.append(file_info)
                        
                    except Exception as e:
                        tool_results.append({
                            'tool': tool_name,
                            'parameters': parameters,
                            'result': {'error': str(e)}
                        })
        else:
            # Crear respuesta estructurada basada en los resultados de búsqueda
            if tool_results and tool_results[0]['result'].get('success'):
                tool_result = tool_results[0]['result']
                
                if search_mode == 'websearch':
                    # Datos estructurados para WebSearch
                    search_results = tool_result.get('search_results', [])
                    summary = tool_result.get('summary', '')
                    
                    # Formatear fuentes para el componente SearchResults
                    formatted_sources = []
                    for i, result in enumerate(search_results[:5]):
                        formatted_sources.append({
                            'title': result.get('title', f'Resultado {i+1}'),
                            'content': result.get('snippet', 'Sin descripción'),
                            'url': result.get('url', ''),
                            'domain': result.get('domain', ''),
                            'score': result.get('score', 0)
                        })
                    
                    response = {
                        'response': f"🌐 **Búsqueda Web**\n\n**Pregunta:** {message}\n\n**Resumen:**\n{summary}\n\n**Resultados encontrados:** {len(search_results)}\n\n**Fuentes principales:**\n" + 
                                  "\n".join([f"{i+1}. **{result.get('title', 'Sin título')}**\n   {result.get('snippet', 'Sin descripción')[:150]}...\n   🔗 {result.get('url', '')}" 
                                            for i, result in enumerate(search_results[:3])]),
                        'model': 'web-search',
                        'search_data': {
                            'query': message,
                            'directAnswer': summary,
                            'sources': formatted_sources,
                            'images': [],
                            'summary': summary,
                            'search_stats': {'total_sources': len(search_results)},
                            'type': 'websearch'
                        }
                    }
                
                elif search_mode == 'deepsearch':
                    # Datos estructurados para DeepResearch
                    analysis = tool_result.get('analysis', '')
                    key_findings = tool_result.get('key_findings', [])
                    recommendations = tool_result.get('recommendations', [])
                    sources = tool_result.get('sources', [])
                    
                    # Formatear fuentes para el componente SearchResults
                    formatted_sources = []
                    for i, source in enumerate(sources[:5]):
                        formatted_sources.append({
                            'title': f'Fuente {i+1}',
                            'content': source if isinstance(source, str) else str(source),
                            'url': ''
                        })
                    
                    response = {
                        'response': f"🔬 **Investigación Profunda**\n\n**Tema:** {message}\n\n**Análisis Comprehensivo:**\n{analysis}\n\n**Hallazgos Clave:**\n" + 
                                  "\n".join([f"• {finding}" for finding in key_findings[:3]]) + 
                                  "\n\n**Recomendaciones:**\n" + 
                                  "\n".join([f"• {rec}" for rec in recommendations[:3]]),
                        'model': 'deep-research',
                        'search_data': {
                            'query': message,
                            'directAnswer': analysis,
                            'sources': formatted_sources,
                            'type': 'deepsearch',
                            'key_findings': key_findings,
                            'recommendations': recommendations
                        }
                    }
            else:
                # Error en la búsqueda
                error_msg = tool_results[0]['result'].get('error', 'Error desconocido') if tool_results else 'No se pudo realizar la búsqueda'
                response = {
                    'response': f"❌ Error en la búsqueda: {error_msg}",
                    'model': f'{search_mode}-error'
                }
        
        # Guardar la conversación en la base de datos
        if task_id and database_service.is_connected():
            message_data = {
                'message_id': str(uuid.uuid4()),
                'task_id': task_id,
                'content': message,
                'sender': 'user',
                'tool_results': tool_results,
                'search_mode': search_mode
            }
            database_service.add_message_to_conversation(task_id, message_data)
            
            # Guardar también la respuesta del agente
            response_data = {
                'message_id': str(uuid.uuid4()),
                'task_id': task_id,
                'content': response.get('response', ''),
                'sender': 'agent',
                'tool_results': tool_results,
                'search_mode': search_mode
            }
            database_service.add_message_to_conversation(task_id, response_data)
        
        return jsonify({
            'response': response.get('response', 'Sin respuesta'),
            'tool_calls': response.get('tool_calls', []),
            'tool_results': tool_results,
            'created_files': created_files,
            'search_mode': search_mode,
            'search_data': response.get('search_data'),  # Datos estructurados para frontend
            'autonomous_execution': response.get('autonomous_execution', False),
            'execution_status': response.get('execution_status'),
            'timestamp': datetime.now().isoformat(),
            'model': response.get('model', 'unknown')
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/status', methods=['GET'])
def status():
    """Obtener estado del agente y servicios"""
    try:
        ollama_service = current_app.ollama_service
        tool_manager = current_app.tool_manager
        
        # Verificar estado de Ollama
        ollama_healthy = ollama_service.is_healthy()
        available_models = ollama_service.get_available_models() if ollama_healthy else []
        current_model = ollama_service.get_current_model()
        
        # Obtener herramientas disponibles
        tools = tool_manager.get_available_tools()
        
        return jsonify({
            'status': 'healthy' if ollama_healthy else 'degraded',
            'ollama_status': 'connected' if ollama_healthy else 'disconnected',
            'available_models': available_models,
            'current_model': current_model,
            'tools_count': len(tools),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/tools', methods=['GET'])
def tools():
    """Obtener lista de herramientas disponibles"""
    try:
        tool_manager = current_app.tool_manager
        available_tools = tool_manager.get_available_tools()
        
        return jsonify({
            'tools': available_tools,
            'count': len(available_tools),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/models', methods=['GET'])
def models():
    """Obtener modelos disponibles en Ollama"""
    try:
        ollama_service = current_app.ollama_service
        available_models = ollama_service.get_available_models()
        current_model = ollama_service.get_current_model()
        
        return jsonify({
            'models': available_models,
            'current_model': current_model,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/models', methods=['POST'])
def set_model():
    """Cambiar modelo activo"""
    try:
        data = request.get_json()
        model_name = data.get('model')
        
        if not model_name:
            return jsonify({'error': 'Model name is required'}), 400
        
        ollama_service = current_app.ollama_service
        success = ollama_service.set_model(model_name)
        
        if success:
            return jsonify({
                'message': f'Model changed to {model_name}',
                'current_model': model_name,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': f'Model {model_name} not available',
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ==========================================
# NUEVOS ENDPOINTS - ORQUESTADOR INTELIGENTE
# ==========================================

@agent_bp.route('/task/analyze', methods=['POST'])
def analyze_task():
    """Analizar una tarea y generar plan de ejecución"""
    try:
        data = request.get_json()
        task_title = data.get('task_title', '')
        task_description = data.get('task_description', '')
        
        if not task_title:
            return jsonify({'error': 'task_title is required'}), 400
        
        # Analizar tarea
        analysis = task_planner.analyze_task(task_title, task_description)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/task/plan', methods=['POST'])
def generate_task_plan():
    """Generar plan de ejecución detallado para una tarea"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        task_title = data.get('task_title', '')
        task_description = data.get('task_description', '')
        
        if not task_id or not task_title:
            return jsonify({'error': 'task_id and task_title are required'}), 400
        
        # Generar plan de ejecución
        execution_plan = task_planner.generate_execution_plan(task_id, task_title, task_description)
        
        # Convertir a diccionario para JSON
        plan_dict = {
            'task_id': execution_plan.task_id,
            'title': execution_plan.title,
            'steps': [
                {
                    'id': step.id,
                    'title': step.title,
                    'description': step.description,
                    'tool': step.tool,
                    'parameters': step.parameters,
                    'dependencies': step.dependencies,
                    'estimated_duration': step.estimated_duration,
                    'complexity': step.complexity,
                    'required_skills': step.required_skills
                }
                for step in execution_plan.steps
            ],
            'total_estimated_duration': execution_plan.total_estimated_duration,
            'complexity_score': execution_plan.complexity_score,
            'required_tools': execution_plan.required_tools,
            'success_probability': execution_plan.success_probability,
            'risk_factors': execution_plan.risk_factors,
            'prerequisites': execution_plan.prerequisites
        }
        
        return jsonify({
            'success': True,
            'execution_plan': plan_dict,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/task/execute', methods=['POST'])
def execute_task():
    """Ejecutar una tarea de manera autónoma usando el Execution Engine"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        task_title = data.get('task_title', '')
        task_description = data.get('task_description', '')
        config = data.get('config', {})
        
        if not task_id or not task_title:
            return jsonify({'error': 'task_id and task_title are required'}), 400
        
        # Inicializar execution engine con tool_manager
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        # Ejecutar tarea de manera asíncrona
        import threading
        
        def run_async_execution():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    execution_engine.execute_task(task_id, task_title, task_description, config)
                )
                # Aquí podrías guardar el resultado en una base de datos o storage
                print(f"Task {task_id} execution completed with status: {result.status}")
            except Exception as e:
                print(f"Task {task_id} execution failed: {str(e)}")
            finally:
                loop.close()
        
        execution_thread = threading.Thread(target=run_async_execution)
        execution_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Task execution started',
            'task_id': task_id,
            'status': 'executing',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/task/execution-status/<task_id>', methods=['GET'])
def get_execution_status(task_id):
    """Obtener estado de ejecución de una tarea"""
    try:
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        status = execution_engine.get_execution_status(task_id)
        
        return jsonify({
            'success': True,
            'execution_status': status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/task/stop/<task_id>', methods=['POST'])
def stop_task_execution(task_id):
    """Detener ejecución de una tarea"""
    try:
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        success = execution_engine.stop_execution(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Task {task_id} execution stopped',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Task {task_id} not found or already stopped',
                'timestamp': datetime.now().isoformat()
            })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/task/cleanup/<task_id>', methods=['DELETE'])
def cleanup_task_execution(task_id):
    """Limpiar recursos de ejecución de una tarea"""
    try:
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        # Limpiar execution engine
        execution_engine.cleanup_execution(task_id)
        
        # Limpiar environment setup
        environment_setup_manager.cleanup_session(task_id)
        
        return jsonify({
            'success': True,
            'message': f'Task {task_id} resources cleaned up',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ==========================================
# ENDPOINTS PARA GESTIÓN DE PLANES
# ==========================================

@agent_bp.route('/plans/templates', methods=['GET'])
def get_plan_templates():
    """Obtener templates de planes disponibles"""
    try:
        templates = {
            'web_development': {
                'name': 'Desarrollo Web',
                'description': 'Template para proyectos de desarrollo web',
                'steps': 5,
                'estimated_duration': 600,
                'complexity': 'medium',
                'required_tools': ['file_manager', 'shell', 'web_search']
            },
            'data_analysis': {
                'name': 'Análisis de Datos',
                'description': 'Template para análisis y procesamiento de datos',
                'steps': 5,
                'estimated_duration': 660,
                'complexity': 'high',
                'required_tools': ['file_manager', 'shell', 'web_search', 'enhanced_deep_research']
            },
            'file_processing': {
                'name': 'Procesamiento de Archivos',
                'description': 'Template para procesamiento y manipulación de archivos',
                'steps': 3,
                'estimated_duration': 165,
                'complexity': 'low',
                'required_tools': ['file_manager', 'shell']
            },
            'system_administration': {
                'name': 'Administración de Sistema',
                'description': 'Template para tareas de administración del sistema',
                'steps': 3,
                'estimated_duration': 270,
                'complexity': 'medium',
                'required_tools': ['shell', 'file_manager']
            },
            'research': {
                'name': 'Investigación',
                'description': 'Template para investigación y recopilación de información',
                'steps': 3,
                'estimated_duration': 450,
                'complexity': 'medium',
                'required_tools': ['web_search', 'enhanced_deep_research', 'tavily_search']
            },
            'automation': {
                'name': 'Automatización',
                'description': 'Template para tareas de automatización y scripting',
                'steps': 3,
                'estimated_duration': 330,
                'complexity': 'high',
                'required_tools': ['shell', 'file_manager', 'playwright']
            },
            'general': {
                'name': 'General',
                'description': 'Template genérico para tareas no clasificadas',
                'steps': 4,
                'estimated_duration': 300,
                'complexity': 'medium',
                'required_tools': ['enhanced_web_search', 'enhanced_deep_research', 'file_manager']
            }
        }
        
        return jsonify({
            'success': True,
            'templates': templates,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/share', methods=['POST'])
def share_conversation():
    """Crear enlace compartible para una conversación"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        task_title = data.get('task_title', 'Conversación')
        messages = data.get('messages', [])
        
        if not task_id:
            return jsonify({'error': 'task_id is required'}), 400
        
        # Generar ID único para el enlace compartido
        share_id = str(uuid.uuid4())
        
        # Guardar conversación
        shared_conversations[share_id] = {
            'task_id': task_id,
            'task_title': task_title,
            'messages': messages,
            'created_at': datetime.now().isoformat(),
            'share_id': share_id
        }
        
        # Generar enlace (en producción sería tu dominio)
        share_link = f"{request.host_url}shared/{share_id}"
        
        return jsonify({
            'share_id': share_id,
            'share_link': share_link,
            'success': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/shared/<share_id>', methods=['GET'])
def get_shared_conversation(share_id):
    """Obtener conversación compartida"""
    try:
        if share_id not in shared_conversations:
            return jsonify({'error': 'Shared conversation not found'}), 404
        
        conversation = shared_conversations[share_id]
        return jsonify({
            'conversation': conversation,
            'success': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/files/<task_id>', methods=['GET'])
def get_task_files(task_id):
    """Obtener archivos de una tarea específica"""
    try:
        # Convertir ObjectId a string en los archivos
        files = task_files.get(task_id, [])
        
        # Asegurarse de que todos los archivos tienen un ID
        for file in files:
            if 'id' not in file and 'file_id' in file:
                file['id'] = file['file_id']
            if '_id' in file:
                file['_id'] = str(file['_id'])
        
        return jsonify({
            'files': files,
            'count': len(files),
            'task_id': task_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """Descargar un archivo específico"""
    try:
        # Buscar archivo por ID en todos los tasks
        found_file = None
        for task_id, files in task_files.items():
            for file_info in files:
                if file_info['id'] == file_id:
                    found_file = file_info
                    break
            if found_file:
                break
        
        if not found_file:
            return jsonify({'error': 'File not found'}), 404
        
        file_path = found_file['path']
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found on disk'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=found_file['name']
        )
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/download-selected', methods=['POST'])
def download_selected_files():
    """Descargar archivos seleccionados como ZIP"""
    try:
        data = request.get_json()
        file_ids = data.get('file_ids', [])
        
        if not file_ids:
            return jsonify({'error': 'No file IDs provided'}), 400
        
        # Buscar archivos por IDs
        found_files = []
        for task_id, files in task_files.items():
            for file_info in files:
                if file_info['id'] in file_ids:
                    found_files.append(file_info)
        
        if not found_files:
            return jsonify({'error': 'No files found'}), 404
        
        # Crear archivo ZIP temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_info in found_files:
                    file_path = file_info['path']
                    if os.path.exists(file_path):
                        zip_file.write(file_path, file_info['name'])
            
            zip_path = tmp_zip.name
        
        # Enviar archivo ZIP
        return send_file(
            zip_path,
            as_attachment=True,
            download_name='selected-files.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/download-all/<task_id>', methods=['GET'])
def download_all_files(task_id):
    """Descargar todos los archivos de una tarea como ZIP"""
    try:
        files = task_files.get(task_id, [])
        
        if not files:
            return jsonify({'error': 'No files found for this task'}), 404
        
        # Crear archivo ZIP temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_info in files:
                    file_path = file_info['path']
                    if os.path.exists(file_path):
                        zip_file.write(file_path, file_info['name'])
            
            zip_path = tmp_zip.name
        
        # Enviar archivo ZIP
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f'task-{task_id}-files.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
# ==========================================
# ENDPOINTS PARA GESTIÓN DE PLANES
# ==========================================

# ==========================================
# ENDPOINTS - CONTEXT MANAGER
# ==========================================

@agent_bp.route('/context/info/<task_id>', methods=['GET'])
def get_context_info(task_id):
    """Obtener información del contexto de una tarea"""
    try:
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        context_info = execution_engine.get_context_info(task_id)
        
        return jsonify({
            'success': True,
            'context_info': context_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/context/variables/<task_id>', methods=['GET'])
def get_context_variables(task_id):
    """Obtener variables del contexto"""
    try:
        scope = request.args.get('scope', None)
        
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        variables = execution_engine.get_context_variables(task_id, scope)
        
        return jsonify({
            'success': True,
            'variables': variables,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/context/variables/<task_id>', methods=['POST'])
def set_context_variable(task_id):
    """Establecer variable en el contexto"""
    try:
        data = request.get_json()
        key = data.get('key')
        value = data.get('value')
        var_type = data.get('type', 'object')
        scope = data.get('scope', 'task')
        
        if not key:
            return jsonify({'error': 'key is required'}), 400
        
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        result = execution_engine.set_context_variable(task_id, key, value, var_type, scope)
        
        return jsonify({
            'success': result.get('success', False),
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/context/checkpoints/<task_id>', methods=['GET'])
def get_checkpoints(task_id):
    """Obtener lista de checkpoints"""
    try:
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        checkpoints = execution_engine.get_checkpoints(task_id)
        
        return jsonify({
            'success': True,
            'checkpoints': checkpoints,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/context/checkpoints/<task_id>', methods=['POST'])
def create_checkpoint(task_id):
    """Crear checkpoint manual"""
    try:
        data = request.get_json()
        description = data.get('description', '')
        
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        result = execution_engine.create_manual_checkpoint(task_id, description)
        
        return jsonify({
            'success': result.get('success', False),
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/context/checkpoints/<task_id>/restore', methods=['POST'])
def restore_checkpoint(task_id):
    """Restaurar checkpoint"""
    try:
        data = request.get_json()
        checkpoint_id = data.get('checkpoint_id')
        
        if not checkpoint_id:
            return jsonify({'error': 'checkpoint_id is required'}), 400
        
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        result = execution_engine.restore_checkpoint(task_id, checkpoint_id)
        
        return jsonify({
            'success': result.get('success', False),
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/context/statistics', methods=['GET'])
def get_context_statistics():
    """Obtener estadísticas del context manager"""
    try:
        if hasattr(current_app, 'tool_manager'):
            global execution_engine
            execution_engine = ExecutionEngine(
                tool_manager=current_app.tool_manager,
                environment_manager=environment_setup_manager
            )
        
        stats = execution_engine.get_context_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
@agent_bp.route('/upload-files', methods=['POST'])
def upload_files():
    """Subir archivos para una tarea específica"""
    try:
        task_id = request.form.get('task_id')
        if not task_id:
            return jsonify({'error': 'task_id is required'}), 400
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({'error': 'No files provided'}), 400
        
        # Obtener servicios
        database_service = current_app.database_service
        
        # Crear directorio para la tarea si no existe
        task_dir = Path(tempfile.gettempdir()) / 'task_files' / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
                
            # Asegurar nombre de archivo seguro
            filename = secure_filename(file.filename)
            file_path = task_dir / filename
            
            # Guardar archivo
            file.save(str(file_path))
            
            # Obtener información del archivo
            file_stats = os.stat(file_path)
            
            # Crear información del archivo
            file_id = str(uuid.uuid4())
            file_info = {
                'id': file_id,
                'file_id': file_id,
                'task_id': task_id,
                'name': filename,
                'path': str(file_path),
                'size': file_stats.st_size,
                'type': 'file',
                'mime_type': file.content_type or 'application/octet-stream',
                'source': 'uploaded',
                'created_at': datetime.now().isoformat()
            }
            
            # Guardar en la base de datos - DESACTIVADO TEMPORALMENTE
            # if database_service.is_connected():
            #     try:
            #         # Convertir ObjectId a string antes de devolver la respuesta
            #         mongo_id = database_service.save_file(file_info)
            #         if mongo_id:
            #             file_info['mongo_id'] = str(mongo_id)
            #     except Exception as e:
            #         print(f"Error saving file to database: {e}")
            
            uploaded_files.append(file_info)
        
        # Mantener compatibilidad con sistema actual
        if task_id not in task_files:
            task_files[task_id] = []
        
        # Agregar archivos a la memoria temporal para compatibilidad
        task_files[task_id].extend(uploaded_files)
        
        # Crear respuesta estructurada para el frontend
        response_data = {
            'success': True,
            'message': f'Uploaded {len(uploaded_files)} files',
            'files': uploaded_files,
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'upload_data': {
                'files': uploaded_files,
                'count': len(uploaded_files),
                'total_size': sum(f['size'] for f in uploaded_files)
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def upload_files_old():
    """Subir archivos para una tarea específica - OLD VERSION"""
    try:
        task_id = request.form.get('task_id')
        if not task_id:
            return jsonify({'error': 'task_id is required'}), 400
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({'error': 'No files provided'}), 400
        
        # Obtener servicios
        database_service = current_app.database_service
        
        # Crear directorio para la tarea si no existe
        task_dir = Path(tempfile.gettempdir()) / 'task_files' / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        
        for file in files:
            if file.filename == '':
                continue
                
            # Asegurar nombre de archivo seguro
            filename = secure_filename(file.filename)
            file_path = task_dir / filename
            
            # Guardar archivo
            file.save(str(file_path))
            
            # Obtener información del archivo
            file_stats = os.stat(file_path)
            
            # Crear información del archivo
            file_id = str(uuid.uuid4())
            file_info = {
                'id': file_id,
                'file_id': file_id,
                'task_id': task_id,
                'name': filename,
                'path': str(file_path),
                'size': file_stats.st_size,
                'type': 'file',
                'mime_type': file.content_type or 'application/octet-stream',
                'source': 'uploaded',
                'created_at': datetime.now().isoformat()
            }
            
            # Guardar en la base de datos - DESACTIVADO TEMPORALMENTE
            # if database_service.is_connected():
            #     try:
            #         # Convertir ObjectId a string antes de devolver la respuesta
            #         mongo_id = database_service.save_file(file_info)
            #         if mongo_id:
            #             file_info['mongo_id'] = str(mongo_id)
            #     except Exception as e:
            #         print(f"Error saving file to database: {e}")
            
            uploaded_files.append(file_info)
        
        # Mantener compatibilidad con sistema actual
        if task_id not in task_files:
            task_files[task_id] = []
        
        # Agregar archivos a la memoria temporal para compatibilidad
        task_files[task_id].extend(uploaded_files)
        
        # Crear respuesta estructurada para el frontend
        response_data = {
            'success': True,
            'message': f'Uploaded {len(uploaded_files)} files',
            'files': uploaded_files,
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'upload_data': {
                'files': uploaded_files,
                'count': len(uploaded_files),
                'total_size': sum(f['size'] for f in uploaded_files)
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/create-test-files/<task_id>', methods=['POST'])
def create_test_files(task_id):
    """Crear archivos de prueba para testing de la funcionalidad de descarga"""
    try:
        # Crear directorio de archivos de prueba
        test_dir = Path(tempfile.gettempdir()) / 'task_files' / task_id
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear archivos de prueba
        test_files_data = [
            {
                'name': 'reporte.txt',
                'content': '''Reporte de Análisis de Datos
============================

Fecha: 2025-01-15
Autor: Agente IA

Resumen Ejecutivo:
- Se procesaron 1,000 registros
- Se identificaron 3 patrones principales
- Tasa de éxito: 98.5%

Conclusiones:
El análisis muestra tendencias positivas en los datos procesados.
Se recomienda continuar con la estrategia actual.''',
                'mime_type': 'text/plain'
            },
            {
                'name': 'datos.json',
                'content': '''{
  "analisis": {
    "total_registros": 1000,
    "procesados": 985,
    "errores": 15,
    "tasa_exito": 0.985
  },
  "patrones": [
    {"tipo": "temporal", "frecuencia": 45},
    {"tipo": "geografico", "frecuencia": 32},
    {"tipo": "demografico", "frecuencia": 28}
  ],
  "recomendaciones": [
    "Optimizar proceso de validación",
    "Ampliar conjunto de datos",
    "Implementar alertas automatizadas"
  ]
}''',
                'mime_type': 'application/json'
            },
            {
                'name': 'configuracion.csv',
                'content': '''parametro,valor,descripcion
timeout,30,Tiempo limite en segundos
max_intentos,3,Numero maximo de reintentos
debug,true,Activar modo debug
formato_salida,json,Formato de respuesta
idioma,es,Idioma de la interfaz''',
                'mime_type': 'text/csv'
            },
            {
                'name': 'log_sistema.log',
                'content': '''[2025-01-15 10:30:15] INFO: Sistema iniciado correctamente
[2025-01-15 10:30:16] INFO: Cargando configuración desde archivo
[2025-01-15 10:30:17] INFO: Conectando a base de datos
[2025-01-15 10:30:18] INFO: Base de datos conectada exitosamente
[2025-01-15 10:30:19] INFO: Iniciando procesamiento de datos
[2025-01-15 10:31:45] INFO: Procesamiento completado - 985/1000 registros
[2025-01-15 10:31:46] WARN: 15 registros fallaron en validación
[2025-01-15 10:31:47] INFO: Generando reporte final
[2025-01-15 10:31:48] INFO: Reporte guardado en /tmp/reporte.txt''',
                'mime_type': 'text/plain'
            },
            {
                'name': 'script.py',
                'content': '''#!/usr/bin/env python3
"""
Script de análisis automatizado
Procesa datos y genera reportes
"""

import json
import csv
from datetime import datetime

def procesar_datos(archivo_entrada):
    """Procesa datos desde archivo de entrada"""
    resultados = {
        'total': 0,
        'procesados': 0,
        'errores': 0
    }
    
    print(f"Procesando archivo: {archivo_entrada}")
    
    # Simular procesamiento
    for i in range(1000):
        resultados['total'] += 1
        if i % 67 != 0:  # Simular algunos errores
            resultados['procesados'] += 1
        else:
            resultados['errores'] += 1
    
    return resultados

def generar_reporte(resultados):
    """Genera reporte en formato JSON"""
    reporte = {
        'timestamp': datetime.now().isoformat(),
        'resultados': resultados,
        'tasa_exito': resultados['procesados'] / resultados['total']
    }
    
    with open('reporte_final.json', 'w') as f:
        json.dump(reporte, f, indent=2)
    
    print("Reporte generado exitosamente")

if __name__ == "__main__":
    datos = procesar_datos("datos_entrada.csv")
    generar_reporte(datos)
    print("Procesamiento completado")''',
                'mime_type': 'text/x-python'
            }
        ]
        
        created_files = []
        
        for file_data in test_files_data:
            file_path = test_dir / file_data['name']
            
            # Escribir contenido del archivo
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_data['content'])
            
            # Crear información del archivo
            file_info = {
                'id': str(uuid.uuid4()),
                'name': file_data['name'],
                'path': str(file_path),
                'size': len(file_data['content'].encode('utf-8')),
                'type': 'file',
                'mime_type': file_data['mime_type'],
                'created_at': datetime.now().isoformat()
            }
            
            created_files.append(file_info)
        
        # Agregar archivos a la tarea
        if task_id not in task_files:
            task_files[task_id] = []
        
        # Marcar archivos del agente con source='agent'
        for file_info in created_files:
            file_info['source'] = 'agent'
        
        task_files[task_id].extend(created_files)
        
        return jsonify({
            'success': True,
            'message': f'Created {len(created_files)} test files',
            'files': created_files,
            'task_id': task_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@agent_bp.route('/generate-plan', methods=['POST'])
def generate_dynamic_plan():
    """Generar plan dinámico para una tarea usando IA"""
    try:
        data = request.get_json()
        task_title = data.get('task_title', '')
        
        if not task_title:
            return jsonify({'error': 'task_title is required'}), 400
        
        # Obtener servicios
        ollama_service = current_app.ollama_service
        
        # Generar plan específico usando IA
        plan_prompt = f"""
        Genera un plan de acción específico para la tarea: "{task_title}"
        
        Devuelve exactamente 5 pasos específicos para esta tarea, no genéricos.
        Formato JSON estricto:
        {{
            "plan": [
                {{"id": "step-1", "title": "Paso específico 1", "completed": false, "active": true}},
                {{"id": "step-2", "title": "Paso específico 2", "completed": false, "active": false}},
                {{"id": "step-3", "title": "Paso específico 3", "completed": false, "active": false}},
                {{"id": "step-4", "title": "Paso específico 4", "completed": false, "active": false}},
                {{"id": "step-5", "title": "Paso específico 5", "completed": false, "active": false}}
            ]
        }}
        """
        
        response = ollama_service.generate_response(plan_prompt)
        
        # Parsear respuesta JSON
        import json
        try:
            if response and 'response' in response:
                # Buscar JSON en la respuesta
                response_text = response['response']
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    plan_data = json.loads(json_str)
                    
                    if 'plan' in plan_data:
                        return jsonify(plan_data)
        except:
            pass
        
        # Plan de fallback
        return jsonify({
            'plan': [
                {'id': 'step-1', 'title': 'Analizando la tarea', 'completed': False, 'active': True},
                {'id': 'step-2', 'title': 'Generando plan de acción', 'completed': False, 'active': False},
                {'id': 'step-3', 'title': 'Ejecutando acciones necesarias', 'completed': False, 'active': False},
                {'id': 'step-4', 'title': 'Verificando resultados', 'completed': False, 'active': False},
                {'id': 'step-5', 'title': 'Finalizando tarea', 'completed': False, 'active': False}
            ]
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'plan': [
                {'id': 'step-1', 'title': 'Analizando la tarea', 'completed': False, 'active': True},
                {'id': 'step-2', 'title': 'Generando plan de acción', 'completed': False, 'active': False},
                {'id': 'step-3', 'title': 'Ejecutando acciones necesarias', 'completed': False, 'active': False},
                {'id': 'step-4', 'title': 'Verificando resultados', 'completed': False, 'active': False},
                {'id': 'step-5', 'title': 'Finalizando tarea', 'completed': False, 'active': False}
            ]
        }), 200

@agent_bp.route('/generate-suggestions', methods=['POST'])
def generate_dynamic_suggestions():
    """Generar sugerencias dinámicas usando IA"""
    try:
        # Obtener servicios
        ollama_service = current_app.ollama_service
        
        # Generar sugerencias específicas usando IA
        suggestions_prompt = """
        Genera 3 sugerencias de tareas útiles y variadas para un usuario.
        
        Devuelve exactamente 3 sugerencias específicas y diferentes.
        Formato JSON estricto:
        {
            "suggestions": [
                {"title": "Sugerencia específica 1"},
                {"title": "Sugerencia específica 2"},
                {"title": "Sugerencia específica 3"}
            ]
        }
        """
        
        response = ollama_service.generate_response(suggestions_prompt)
        
        # Parsear respuesta JSON
        import json
        try:
            if response and 'response' in response:
                # Buscar JSON en la respuesta
                response_text = response['response']
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    suggestions_data = json.loads(json_str)
                    
                    if 'suggestions' in suggestions_data:
                        return jsonify(suggestions_data)
        except:
            pass
        
        # Sugerencias de fallback (vacías para no mostrar placeholders)
        return jsonify({
            'suggestions': []
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'suggestions': []
        }), 200