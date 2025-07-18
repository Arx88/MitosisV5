import React, { useState, useEffect, useRef } from 'react';
import { Send, Paperclip, Mic, Globe, Layers, Zap } from 'lucide-react';
import { Button } from './MovingBorder';

interface VanishInputProps {
  onSendMessage: (message: string) => void | Promise<void>;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  showInternalButtons?: boolean;
  onAttachFiles?: () => void;
  onWebSearch?: (inputText: string) => void;
  onDeepSearch?: (inputText: string) => void;
  onVoiceInput?: () => void;
}

export const VanishInput: React.FC<VanishInputProps> = ({
  onSendMessage,
  placeholder = "Describe tu tarea...",
  disabled = false,
  className = "",
  showInternalButtons = false,
  onAttachFiles,
  onWebSearch,
  onDeepSearch,
  onVoiceInput
}) => {
  const [inputValue, setInputValue] = useState('');
  const [currentPlaceholder, setCurrentPlaceholder] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [webSearchActive, setWebSearchActive] = useState(false);
  const [deepSearchActive, setDeepSearchActive] = useState(false);
  const [isWebSearchProcessing, setIsWebSearchProcessing] = useState(false);
  const [isDeepSearchProcessing, setIsDeepSearchProcessing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const eraseTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const cycleTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Frases creativas que inspiran al usuario
  const inspirationalPhrases = [
    "Crea algo extraordinario hoy...",
    "¿Qué problema resolvemos juntos?",
    "Convierte tus ideas en realidad...",
    "¿Qué haremos posible hoy?",
    "Diseña el futuro que imaginas...",
    "¿Qué desafío enfrentaremos?",
    "Construye algo increíble...",
    "¿Cuál es tu próxima gran idea?",
    "Transforma tu visión en acción...",
    "¿Qué aventura comenzamos?",
    "Innova sin límites...",
    "¿Qué quieres lograr hoy?",
    "Haz que cada línea de código cuente...",
    "¿Qué sueño hacemos realidad?",
    "Crea, experimenta, descubre..."
  ];

  // Limpiar todos los timers
  const clearAllTimers = () => {
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
    if (eraseTimeoutRef.current) {
      clearTimeout(eraseTimeoutRef.current);
      eraseTimeoutRef.current = null;
    }
    if (cycleTimeoutRef.current) {
      clearTimeout(cycleTimeoutRef.current);
      cycleTimeoutRef.current = null;
    }
  };

  // Efecto de typing mejorado
  const startTypingEffect = (phrase: string) => {
    clearAllTimers();
    
    if (inputValue.length > 0 || disabled) {
      setCurrentPlaceholder(placeholder);
      return;
    }

    setCurrentPlaceholder('');
    setIsTyping(true);
    
    let charIndex = 0;
    
    const typeNextChar = () => {
      if (charIndex <= phrase.length && inputValue.length === 0 && !disabled) {
        setCurrentPlaceholder(phrase.substring(0, charIndex));
        charIndex++;
        
        if (charIndex <= phrase.length) {
          typingTimeoutRef.current = setTimeout(typeNextChar, 80); // Velocidad más lenta
        } else {
          setIsTyping(false);
          // Esperar más tiempo antes de borrar para reducir la frecuencia
          eraseTimeoutRef.current = setTimeout(() => {
            startErasingEffect(phrase);
          }, 3000); // Aumentado de 2000 a 3000ms
        }
      }
    };
    
    typeNextChar();
  };

  // Efecto de borrado mejorado
  const startErasingEffect = (phrase: string) => {
    if (inputValue.length > 0 || disabled) return;
    
    let eraseIndex = phrase.length;
    
    const eraseNextChar = () => {
      if (eraseIndex >= 0 && inputValue.length === 0 && !disabled) {
        setCurrentPlaceholder(phrase.substring(0, eraseIndex));
        eraseIndex--;
        
        if (eraseIndex >= 0) {
          eraseTimeoutRef.current = setTimeout(eraseNextChar, 50); // Velocidad más lenta
        } else {
          // Cycle completado, pasar a la siguiente frase con más delay
          cycleTimeoutRef.current = setTimeout(() => {
            setPlaceholderIndex((prev) => (prev + 1) % inspirationalPhrases.length);
          }, 1000); // Aumentado de 500 a 1000ms
        }
      }
    };
    
    eraseNextChar();
  };

  // Efecto para manejar el ciclo de placeholder
  useEffect(() => {
    if (inputValue.length > 0 || disabled) {
      clearAllTimers();
      setCurrentPlaceholder(placeholder);
      setIsTyping(false);
      return;
    }

    // Prevenir múltiples ejecuciones del mismo efecto
    const timeoutId = setTimeout(() => {
      const phrase = inspirationalPhrases[placeholderIndex];
      startTypingEffect(phrase);
    }, 100);

    // Cleanup al cambiar de efecto
    return () => {
      clearTimeout(timeoutId);
      clearAllTimers();
    };
  }, [placeholderIndex, inputValue.length, disabled]); // Dependencias optimizadas

  // Cleanup al desmontar el componente
  useEffect(() => {
    return () => {
      clearAllTimers();
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !disabled) {
      const messageToSend = inputValue.trim();
      await onSendMessage(messageToSend);
      // Mantener el texto en el input temporalmente para que el usuario vea que se está procesando
      // Solo limpiar después de un breve delay
      setTimeout(() => {
        setInputValue('');
        adjustTextareaHeight();
      }, 500);
    }
  };

  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleWebSearch = async () => {
    console.log('🌐 handleWebSearch called with inputValue:', inputValue.trim());
    if (inputValue.trim()) {
      // Procesar búsqueda web con el texto del input - APLICAR PREFIJO AQUÍ
      const searchQuery = `[WebSearch] ${inputValue.trim()}`;
      console.log('🌐 Setting isWebSearchProcessing to true');
      setIsWebSearchProcessing(true);
      setWebSearchActive(true);
      setDeepSearchActive(false);
      
      try {
        console.log('🌐 Calling onWebSearch with prefixed query:', searchQuery);
        if (onWebSearch) {
          await onWebSearch(searchQuery);
          console.log('🌐 onWebSearch completed successfully');
        } else {
          console.error('🌐 onWebSearch prop is undefined!');
        }
        // Limpiar input después del procesamiento exitoso con delay para mostrar feedback
        setTimeout(() => {
          setInputValue('');
          adjustTextareaHeight();
        }, 300);
      } catch (error) {
        console.error('🌐 Error in web search:', error);
      } finally {
        console.log('🌐 Setting isWebSearchProcessing to false');
        // Mantener el estado de procesamiento un poco más para mostrar el estado "Buscando..."
        setTimeout(() => {
          setIsWebSearchProcessing(false);
          setWebSearchActive(false);
        }, 1500); // Aumentar tiempo para que sea más visible
      }
    } else {
      console.log('🌐 No input text, just toggling state');
      // Solo toggle si no hay texto
      setWebSearchActive(!webSearchActive);
      setDeepSearchActive(false);
    }
  };

  const handleDeepSearch = async () => {
    console.log('🔬 handleDeepSearch called with inputValue:', inputValue.trim());
    if (inputValue.trim()) {
      // Procesar investigación profunda con el texto del input - APLICAR PREFIJO AQUÍ
      const searchQuery = `[DeepResearch] ${inputValue.trim()}`;
      console.log('🔬 Setting isDeepSearchProcessing to true');
      setIsDeepSearchProcessing(true);
      setDeepSearchActive(true);
      setWebSearchActive(false);
      
      try {
        console.log('🔬 Calling onDeepSearch with prefixed query:', searchQuery);
        if (onDeepSearch) {
          await onDeepSearch(searchQuery);
          console.log('🔬 onDeepSearch completed successfully');
        } else {
          console.error('🔬 onDeepSearch prop is undefined!');
        }
        // Limpiar input después del procesamiento exitoso con delay para mostrar feedback
        setTimeout(() => {
          setInputValue('');
          adjustTextareaHeight();
        }, 300);
      } catch (error) {
        console.error('🔬 Error in deep search:', error);
      } finally {
        console.log('🔬 Setting isDeepSearchProcessing to false');
        // Mantener el estado de procesamiento un poco más para mostrar el estado "Investigando..."
        setTimeout(() => {
          setIsDeepSearchProcessing(false);
          setDeepSearchActive(false);
        }, 1500); // Aumentar tiempo para que sea más visible
      }
    } else {
      console.log('🔬 No input text, just toggling state');
      // Solo toggle si no hay texto
      setDeepSearchActive(!deepSearchActive);
      setWebSearchActive(false);
    }
  };

  return (
    <Button 
      as="div"
      containerClassName="relative group w-full h-auto min-h-[60px] sm:min-h-[75px]"
      borderRadius="0.75rem"
      duration={5184} // 20% más suave (más lento) que 4320
      className="bg-[#363537] text-[#DADADA] border-[rgba(255,255,255,0.08)]"
      borderClassName="h-16 w-16 sm:h-20 sm:w-20 md:h-24 md:w-24 opacity-[0.9]"
    >
      <form onSubmit={handleSubmit} className={`w-full ${className}`}>
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              adjustTextareaHeight();
            }}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className={`w-full bg-transparent border-0 rounded-xl px-3 sm:px-4 py-3 pr-14 sm:pr-16 
              ${showInternalButtons ? 'pl-3 sm:pl-4 pb-14 sm:pb-16' : 'pl-3 sm:pl-4'} 
              min-h-[60px] max-h-[100px] sm:max-h-[120px] resize-none text-[#DADADA] placeholder-transparent
              focus:outline-none focus:ring-0 focus:border-0
              disabled:opacity-50 disabled:cursor-not-allowed
              relative z-10 overflow-y-auto vanish-input-scrollbar text-sm sm:text-base`}
            style={{
              caretColor: '#DADADA',
              minHeight: showInternalButtons ? '75px' : '60px',
              maxHeight: showInternalButtons ? '100px' : '150px',
              fontFamily: "'Segoe UI Variable Display', 'Segoe UI', system-ui, -apple-system, sans-serif",
              fontWeight: 400
            }}
          />
          
          {/* Custom placeholder with vanish effect - z-index más alto */}
          {inputValue.length === 0 && (
            <div className="absolute left-3 sm:left-4 top-3 pointer-events-none z-40">
              <span className="text-[#7F7F7F] text-xs sm:text-sm">
                {currentPlaceholder}
                {isTyping && (
                  <span className="ml-1 animate-pulse text-blue-400">|</span>
                )}
              </span>
            </div>
          )}
          
          {/* Internal buttons - responsive positioning con z-index corregido */}
          {showInternalButtons && (
            <div className="absolute bottom-2 left-3 sm:left-4 right-16 sm:right-20 flex items-center justify-between z-30">
              <div className="flex items-center gap-1 sm:gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={onAttachFiles}
                  className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-[rgba(255,255,255,0.06)] hover:bg-[rgba(255,255,255,0.1)] 
                    rounded-lg transition-all duration-200 group text-xs z-30"
                  title="Adjuntar archivos"
                >
                  <Paperclip className="w-3 h-3 text-[#ACACAC] group-hover:text-[#DADADA]" />
                  <span className="text-[#ACACAC] group-hover:text-[#DADADA] hidden sm:inline">Adjuntar</span>
                </button>
                
                <button
                  type="button"
                  onClick={handleWebSearch}
                  disabled={isWebSearchProcessing || isDeepSearchProcessing}
                  className={`flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg transition-all duration-200 group text-xs border z-30 ${
                    webSearchActive || isWebSearchProcessing 
                      ? 'bg-[rgba(59,130,246,0.2)] border-blue-400/50 text-blue-400' 
                      : 'bg-[rgba(255,255,255,0.06)] hover:bg-[rgba(59,130,246,0.2)] hover:border-blue-400/50 border-transparent text-[#ACACAC] hover:text-blue-400'
                  } ${(isWebSearchProcessing || isDeepSearchProcessing) ? 'opacity-50 cursor-not-allowed' : ''}`}
                  title="Búsqueda web"
                >
                  <Globe className={`w-3 h-3 ${
                    webSearchActive || isWebSearchProcessing
                      ? 'text-blue-400' 
                      : 'text-[#ACACAC] group-hover:text-blue-400'
                  } ${isWebSearchProcessing ? 'animate-pulse' : ''}`} />
                  <span className={`${
                    webSearchActive || isWebSearchProcessing
                      ? 'text-blue-400' 
                      : 'text-[#ACACAC] group-hover:text-blue-400'
                  } hidden sm:inline`}>
                    {isWebSearchProcessing ? 'Buscando...' : 'Web'}
                  </span>
                </button>
                
                <button
                  type="button"
                  onClick={handleDeepSearch}
                  disabled={isWebSearchProcessing || isDeepSearchProcessing}
                  className={`flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 transition-all duration-200 group text-xs z-30 rounded-lg border ${
                    deepSearchActive || isDeepSearchProcessing
                      ? 'bg-[rgba(168,85,247,0.2)] border-purple-400/50 text-purple-400' 
                      : 'bg-[rgba(255,255,255,0.06)] hover:bg-[rgba(168,85,247,0.2)] hover:border-purple-400/50 border-transparent text-[#ACACAC] hover:text-purple-400'
                  } ${(isWebSearchProcessing || isDeepSearchProcessing) ? 'opacity-50 cursor-not-allowed' : ''}`}
                  title="Investigación profunda"
                >
                  <Zap className={`w-3 h-3 ${
                    deepSearchActive || isDeepSearchProcessing
                      ? 'text-purple-400' 
                      : 'text-[#ACACAC] group-hover:text-purple-400'
                  } ${isDeepSearchProcessing ? 'animate-pulse' : ''}`} />
                  <span className={`${
                    deepSearchActive || isDeepSearchProcessing
                      ? 'text-purple-400' 
                      : 'text-[#ACACAC] group-hover:text-purple-400'
                  } hidden sm:inline`}>
                    {isDeepSearchProcessing ? 'Investigando...' : 'Deep'}
                  </span>
                </button>
                
                <button
                  type="button"
                  onClick={onVoiceInput}
                  className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-[rgba(255,255,255,0.06)] hover:bg-[rgba(255,255,255,0.1)] 
                    rounded-lg transition-all duration-200 group text-xs z-30"
                  title="Entrada de voz"
                >
                  <Mic className="w-3 h-3 text-[#ACACAC] group-hover:text-[#DADADA]" />
                  <span className="text-[#ACACAC] group-hover:text-[#DADADA] hidden sm:inline">Voz</span>
                </button>
              </div>
            </div>
          )}
          
          {/* Send button - responsive size con z-index correcto */}
          <button
            type="submit"
            disabled={!inputValue.trim() || disabled}
            className="absolute right-2 sm:right-3 top-3 z-40
              w-8 h-8 sm:w-9 sm:h-9 bg-blue-600 hover:bg-blue-700 disabled:bg-[#7F7F7F] 
              rounded-lg flex items-center justify-center
              disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          >
            <Send className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
          </button>
        </div>
      </form>
    </Button>
  );
};