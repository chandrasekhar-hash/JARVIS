import React, { useState, useEffect, useRef } from 'react';
import { useAssistantConfig } from '../context/AssistantConfigContext';
import './Terminal.css';
import { formatTranscript } from '../services/transcriptFormatter';

const THEME_COLORS = {
  green: { hex: '#00ff66', glow: 'rgba(0, 255, 102, 0.45)' },
  cyan: { hex: '#00e5ff', glow: 'rgba(0, 229, 255, 0.45)' },
  gold: { hex: '#ffb400', glow: 'rgba(255, 180, 0, 0.45)' },
  pink: { hex: '#ff3366', glow: 'rgba(255, 51, 102, 0.45)' }
};

const LISTENING_LANGUAGES = [
  { name: 'Auto Detect', code: 'en-IN' },
  { name: 'English', code: 'en-US' },
  { name: 'Hindi', code: 'hi-IN' },
  { name: 'Telugu', code: 'te-IN' },
  { name: 'Tamil', code: 'ta-IN' },
  { name: 'Odia', code: 'or-IN' },
  { name: 'Kannada', code: 'kn-IN' },
  { name: 'Malayalam', code: 'ml-IN' },
  { name: 'Bengali', code: 'bn-IN' },
  { name: 'Gujarati', code: 'gu-IN' },
  { name: 'Punjabi', code: 'pa-IN' },
  { name: 'Marathi', code: 'mr-IN' }
];

const DISPLAY_LANGUAGES = [
  { name: 'Hinglish', key: 'hinglish' },
  { name: 'English', key: 'english' },
  { name: 'हिन्दी', key: 'hindi' },
  { name: 'ଓଡ଼ିଆ', key: 'odia' },
  { name: 'తెలుగు', key: 'telugu' },
  { name: 'தமிழ்', key: 'tamil' },
  { name: 'ಕನ್ನಡ', key: 'kannada' },
  { name: 'മലയാളം', key: 'malayalam' },
  { name: 'বাংলা', key: 'bengali' },
  { name: 'ગુજરાતી', key: 'gujarati' },
  { name: 'ਪੰਜਾਬੀ', key: 'punjabi' },
  { name: 'मराठी', key: 'marathi' }
];

function SearchableDropdown({ label, options, selected, onSelect, placeholder }) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredOptions = options.filter(opt => 
    opt.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="jarvis-dropdown-container" ref={dropdownRef}>
      <button 
        className={`jarvis-dropdown-trigger ${isOpen ? 'active' : ''}`}
        onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); setSearch(''); }}
      >
        <span className="dropdown-label">{label}:</span>
        <span className="dropdown-selected">{selected}</span>
        <span className="dropdown-arrow">▼</span>
      </button>
      
      {isOpen && (
        <div className="jarvis-dropdown-menu" onClick={(e) => e.stopPropagation()}>
          <div className="dropdown-search-wrapper">
            <input 
              type="text" 
              className="dropdown-search-input"
              placeholder={placeholder || "Search language..."}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>
          <div className="dropdown-options-list">
            {filteredOptions.length > 0 ? (
              filteredOptions.map((opt) => (
                <button
                  key={opt.name}
                  className={`dropdown-option ${opt.name === selected ? 'selected' : ''}`}
                  onClick={() => {
                    onSelect(opt.name);
                    setIsOpen(false);
                  }}
                >
                  {opt.name}
                </button>
              ))
            ) : (
              <div className="dropdown-no-results">No results</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Configurable option: Set to true to pause SpeechRecognition when assistant is responding/processing,
// or false to keep SpeechRecognition continuously listening (ideal for future barge-in).
const PAUSE_MIC_ON_RESPONSE = true;

export default function Terminal({ terminalSettings, setTerminalSettings }) {
  const { assistantName, wakeWords, wakeWordRequired, voiceStatus, setVoiceStatus } = useAssistantConfig();
  const [rawLastFinalText, setRawLastFinalText] = useState('');
  const [rawInterim, setRawInterim]             = useState('');
  const status = voiceStatus;
  const setStatus = setVoiceStatus;
  const [minimized, setMinimized]               = useState(false);
  const [noSupport, setNoSupport]               = useState(false);
  const [isOff, setIsOff]                       = useState(false);

  // Cleanup all timers on component unmount
  useEffect(() => {
    return () => {
      if (typewriterTimer.current) clearInterval(typewriterTimer.current);
      if (autoClearTimer.current) clearTimeout(autoClearTimer.current);
      if (speechEndTimer.current) clearTimeout(speechEndTimer.current);
      if (restartTimer.current) clearTimeout(restartTimer.current);
      if (activeCountdownIntervalRef.current) clearInterval(activeCountdownIntervalRef.current);
    };
  }, []);


  const [listeningLang, setListeningLang] = useState(() => {
    return localStorage.getItem('jarvis-listening-lang') || 'Auto Detect';
  });

  const [displayLang, setDisplayLang] = useState(() => {
    return localStorage.getItem('jarvis-display-lang') || 'Hinglish';
  });

  const [formattedFinalText, setFormattedFinalText] = useState('');
  const [formattedInterimText, setFormattedInterimText] = useState('');

  const [editableText, setEditableText] = useState('');
  const [isEditingText, setIsEditingText] = useState(false);
  const editableTextRef = useRef('');
  const inputRef = useRef(null);
  const [llmResponse, setLlmResponse] = useState('');
  const [responseState, setResponseState] = useState('hidden'); // 'hidden', 'visible', 'pinned'
  const responseStateRef = useRef('hidden');

  const updateResponseState = (nextState) => {
    responseStateRef.current = nextState;
    setResponseState(nextState);
  };

  const scheduleAutoClear = () => {
    if (autoClearTimer.current) clearTimeout(autoClearTimer.current);
    updateResponseState('visible');
    
    autoClearTimer.current = setTimeout(() => {
      if (responseStateRef.current === 'visible') {
        updateResponseState('hidden');
        setLlmResponse('');
      }
    }, 10000);
  };

  const handleVoiceHubClick = (e) => {
    if (e.target.closest('.terminal-edit-input') || 
        e.target.closest('.terminal-continue-btn') || 
        e.target.closest('.searchable-dropdown-container') || 
        e.target.closest('.terminal-minimize-btn') ||
        e.target.closest('.terminal-status-indicator')) return;

    if (responseStateRef.current === 'visible') {
      updateResponseState('pinned');
      if (autoClearTimer.current) {
        clearTimeout(autoClearTimer.current);
        autoClearTimer.current = null;
      }
    }
  };

  const typewriterTimer = useRef(null);
  const autoClearTimer = useRef(null);

  // Simplified Wake Word States & References
  const [activeSecondsLeft, setActiveSecondsLeft] = useState(0);
  const activeCountdownIntervalRef = useRef(null);

  const recognitionRef  = useRef(null);
  const restartTimer    = useRef(null);
  const startingRef     = useRef(false);
  const stoppedRef      = useRef(false);
  const startTimeRef    = useRef(0);

  const rawLastFinalTextRef = useRef('');
  const rawInterimRef       = useRef('');
  const statusRef           = useRef('standby');
  const speechEndTimer      = useRef(null);
  const wakeWordDetectedRef = useRef(false);
  const retryCountRef         = useRef(0);
  const hasTransientErrorRef  = useRef(false);

  const updateStatus = (newStatus) => {
    statusRef.current = newStatus;
    setStatus(newStatus);
    if (newStatus === 'listening' || newStatus === 'active') {
      wakeWordDetectedRef.current = false;
    }
  };

  const startActiveTimeout = () => {
    clearActiveTimeout();
    setActiveSecondsLeft(2);

    activeCountdownIntervalRef.current = setInterval(() => {
      setActiveSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(activeCountdownIntervalRef.current);
          activeCountdownIntervalRef.current = null;
          console.log(`[${assistantName} Assistant] Inactivity timeout: returning to STANDBY`);
          updateStatus('standby');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const clearActiveTimeout = () => {
    if (activeCountdownIntervalRef.current) {
      clearInterval(activeCountdownIntervalRef.current);
      activeCountdownIntervalRef.current = null;
    }
  };

  useEffect(() => {
    if (!isEditingText) {
      setEditableText(formattedFinalText);
      editableTextRef.current = formattedFinalText;
    }
  }, [formattedFinalText, isEditingText]);

  const handleInputChange = (e) => {
    const val = e.target.value;
    setEditableText(val);
    editableTextRef.current = val;
    
    cancelSpeechTimers();
    speechEndTimer.current = setTimeout(() => {
      setIsEditingText(false);
      handleSpeechEnded();
    }, 60000);
  };

  const handleInputFocus = () => {
    cancelSpeechTimers();
    setIsEditingText(true);
    setLlmResponse('');
    
    const combined = (formattedFinalText.trim() + ' ' + formattedInterimText.trim()).trim();
    setEditableText(combined);
    editableTextRef.current = combined;
  };

  const handleInputBlur = () => {
    cancelSpeechTimers();
    speechEndTimer.current = setTimeout(() => {
      setIsEditingText(false);
      handleSpeechEnded();
    }, 1500);
  };

  const handleInputKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      cancelSpeechTimers();
      setIsEditingText(false);
      handleSpeechEnded(editableText);
    }
  };

  const parseCommand = (text) => {
    if (!text) return { hasWakeWord: false, isWakeOnly: false, command: '' };
    const textLower = text.toLowerCase();
    
    const normalize = (str) => str.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").replace(/\s+/g, ' ').trim().toLowerCase();
    const normText = normalize(textLower);
    
    const sortedWakeWords = [...wakeWords].sort((a, b) => b.length - a.length);
    
    let matchedWakeWord = null;
    for (const wakeWord of sortedWakeWords) {
      const normWake = normalize(wakeWord);
      if (normText === normWake) {
        return {
          hasWakeWord: true,
          isWakeOnly: true,
          command: ''
        };
      }
      if (normText.startsWith(normWake + ' ')) {
        matchedWakeWord = wakeWord;
        break;
      }
    }
    
    if (matchedWakeWord) {
      const escapeReg = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const pattern = new RegExp("^[\\s.,\\/#!$%\\^&\\*;:{}=\\-_`~()?]*" + escapeReg(matchedWakeWord) + "[.,\\/#!$%\\^&\\*;:{}=\\-_`~()?]*\\s*", "i");
      const command = text.replace(pattern, '').trim();
      return {
        hasWakeWord: true,
        isWakeOnly: false,
        command
      };
    }
    
    return {
      hasWakeWord: false,
      isWakeOnly: false,
      command: text.trim()
    };
  };

  const isSessionAwake = status === 'listening' || status === 'active' || status === 'processing' || status === 'responding';

  useEffect(() => {
    const controller = new AbortController();
    async function format() {
      try {
        const finalFormatted = await formatTranscript(rawLastFinalText, listeningLang, displayLang, controller.signal);
        
        const { hasWakeWord, command } = parseCommand(finalFormatted);
        if (hasWakeWord) {
          wakeWordDetectedRef.current = true;
        }

        const isAwake = isSessionAwake || wakeWordDetectedRef.current;

        if (wakeWordRequired) {
          if (isAwake) {
            setFormattedFinalText(command);
          } else {
            setFormattedFinalText('');
          }
        } else {
          setFormattedFinalText(command);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error("Failed formatting final text:", err);
        }
      }
    }
    format();
    return () => {
      controller.abort();
    };
  }, [rawLastFinalText, listeningLang, displayLang, wakeWordRequired, wakeWords, status]);

  useEffect(() => {
    let active = true;
    if (!rawInterim) {
      setFormattedInterimText('');
      return;
    }
    
    // Optimize network load: 50ms for local transliteration, 300ms for network API
    const displayLangLower = displayLang ? displayLang.toLowerCase() : 'hinglish';
    const isLocalFormatter = displayLangLower === 'english' || displayLangLower === 'hinglish';
    const debounceDelay = isLocalFormatter ? 50 : 300;

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const combinedRaw = (rawLastFinalText.trim() + ' ' + rawInterim.trim()).trim();
        const combinedFormatted = await formatTranscript(combinedRaw, listeningLang, displayLang, controller.signal);
        if (!active) return;

        const { hasWakeWord, command } = parseCommand(combinedFormatted);
        if (hasWakeWord) {
          wakeWordDetectedRef.current = true;
        }

        const isAwake = isSessionAwake || wakeWordDetectedRef.current;

        if (wakeWordRequired) {
          if (isAwake) {
            const finalClean = parseCommand(await formatTranscript(rawLastFinalText, listeningLang, displayLang, controller.signal)).command;
            const interimClean = command.slice(finalClean.length).trim();
            setFormattedInterimText(interimClean);
          } else {
            setFormattedInterimText('');
          }
        } else {
          const finalClean = parseCommand(await formatTranscript(rawLastFinalText, listeningLang, displayLang, controller.signal)).command;
          const interimClean = command.slice(finalClean.length).trim();
          setFormattedInterimText(interimClean);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error("Failed formatting interim text:", err);
        }
      }
    }, debounceDelay);
    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [rawInterim, rawLastFinalText, listeningLang, displayLang, wakeWordRequired, wakeWords, status]);

  const handleToggleTerminal = (e) => {
    e.stopPropagation();
    if (noSupport) return;
    setIsOff(prev => !prev);
  };

  const updateRawLastFinalText = (valOrFn) => {
    setRawLastFinalText(prev => {
      const nextVal = typeof valOrFn === 'function' ? valOrFn(prev) : valOrFn;
      rawLastFinalTextRef.current = nextVal;
      return nextVal;
    });
  };

  const updateRawInterim = (val) => {
    rawInterimRef.current = val;
    setRawInterim(val);
  };

  const typewrite = (text) => {
    updateResponseState('visible');
    setLlmResponse('');
    let idx = 0;
    
    if (typewriterTimer.current) clearInterval(typewriterTimer.current);
    
    typewriterTimer.current = setInterval(() => {
      if (idx < text.length) {
        setLlmResponse(text.slice(0, idx + 1));
        idx++;
      } else {
        clearInterval(typewriterTimer.current);
        typewriterTimer.current = null;
        
        // Transition to active state and start countdown when typewriter is finished
        updateStatus('active');
        startActiveTimeout();
        scheduleAutoClear();
      }
    }, 20);
  };

  const fetchGroqResponse = async (query) => {
    updateStatus('processing');
    try {
      const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${import.meta.env.VITE_GROQ_API_KEY}`
        },
        body: JSON.stringify({
          model: "llama-3.1-8b-instant",
          messages: [
            {
              role: "system",
              content: `You are ${assistantName}, a highly advanced, intelligent, and helpful AI assistant. Answer the user's question clearly, concisely, and directly. Keep responses short and conversational, suitable for a terminal interface (typically 1-3 sentences). Refer to yourself using your configured name "${assistantName}".`
            },
            {
              role: "user",
              content: query
            }
          ],
          temperature: 0.7,
          max_tokens: 150,
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error(`Groq API returned status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      updateStatus('responding');
      updateResponseState('visible');
      setLlmResponse('');
      
      let accumulatedText = "";
      let buffer = "";
      let lastUpdateTime = 0;
      const THROTTLE_MS = 16; // Throttle to 16ms (60 FPS) for smooth rendering

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        
        buffer = lines.pop() || "";
        
        let hasNewTokens = false;
        for (const line of lines) {
          const cleanLine = line.trim();
          if (!cleanLine) continue;
          if (cleanLine === "data: [DONE]") break;
          
          if (cleanLine.startsWith("data: ")) {
            try {
              const json = JSON.parse(cleanLine.slice(6));
              const token = json.choices?.[0]?.delta?.content || "";
              if (token) {
                accumulatedText += token;
                hasNewTokens = true;
              }
            } catch (e) {
              // Ignore partial JSON parsing errors
            }
          }
        }

        if (hasNewTokens) {
          const now = Date.now();
          if (now - lastUpdateTime > THROTTLE_MS) {
            setLlmResponse(accumulatedText);
            lastUpdateTime = now;
          }
        }
      }

      if (buffer && buffer.startsWith("data: ")) {
        try {
          const json = JSON.parse(buffer.slice(6));
          const token = json.choices?.[0]?.delta?.content || "";
          if (token) {
            accumulatedText += token;
          }
        } catch (_) {}
      }

      // Ensure final state update is applied immediately
      setLlmResponse(accumulatedText);

      // Transition to active state for follow-up command
      updateStatus('active');
      startActiveTimeout();
      scheduleAutoClear();
    } catch (error) {
      console.error("[Groq API Error]", error);
      updateStatus('responding');
      const errReply = `Error connecting to ${assistantName} core.`;
      typewrite(errReply);
    }
  };

  const handleWakeEvent = () => {
    const greetingText = "Yes, Sir. How can I help you?";
    updateStatus('responding');
    typewrite(greetingText);
  };

  const processCommand = (command) => {
    fetchGroqResponse(command);
  };

  const handleSpeechEnded = (customCommand) => {
    const fullInput = (customCommand !== undefined ? customCommand : editableTextRef.current).trim();
    
    // Clear previous response when new command is processed
    if (responseStateRef.current !== 'hidden') {
      updateResponseState('hidden');
      setLlmResponse('');
      if (autoClearTimer.current) {
        clearTimeout(autoClearTimer.current);
        autoClearTimer.current = null;
      }
    }

    updateRawLastFinalText('');
    updateRawInterim('');
    setEditableText('');
    setFormattedFinalText('');
    setFormattedInterimText('');

    if (!fullInput) {
      if (statusRef.current === 'active' || statusRef.current === 'listening') {
        updateStatus('listening');
        startActiveTimeout();
      } else {
        updateStatus('standby');
      }
      return;
    }

    console.log(`[${assistantName} Assistant] Processing speech input: "${fullInput}"`);

    const parsed = parseCommand(fullInput);
    clearActiveTimeout();

    const isKeyboardOverride = customCommand !== undefined;
    const currentState = statusRef.current;

    if (wakeWordRequired && !isKeyboardOverride) {
      if (currentState === 'standby' || currentState === 'paused') {
        if (parsed.hasWakeWord) {
          if (parsed.isWakeOnly) {
            handleWakeEvent();
          } else {
            processCommand(parsed.command);
          }
        } else {
          console.log(`[${assistantName} Assistant] Ignored: Wake word required but not detected in standby.`);
          updateStatus('standby');
        }
      } else {
        // We are already wake-active
        if (parsed.hasWakeWord && parsed.isWakeOnly) {
          handleWakeEvent();
        } else {
          const finalCommand = parsed.hasWakeWord ? parsed.command : fullInput;
          processCommand(finalCommand);
        }
      }
    } else {
      // Wake word not required or manual typed input
      if (parsed.hasWakeWord) {
        if (parsed.isWakeOnly) {
          handleWakeEvent();
        } else {
          processCommand(parsed.command);
        }
      } else {
        processCommand(fullInput);
      }
    }
  };

  const cancelSpeechTimers = () => {
    if (speechEndTimer.current) {
      clearTimeout(speechEndTimer.current);
      speechEndTimer.current = null;
    }
    if (typewriterTimer.current) {
      clearInterval(typewriterTimer.current);
      typewriterTimer.current = null;
    }
    if (autoClearTimer.current) {
      clearTimeout(autoClearTimer.current);
      autoClearTimer.current = null;
    }
  };

  const isMicPaused = isOff || isEditingText || (PAUSE_MIC_ON_RESPONSE && (status === 'processing' || status === 'responding'));

  useEffect(() => {
    if (isMicPaused) {
      updateStatus('paused');
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch (_) {}
        recognitionRef.current = null;
      }
      return;
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setNoSupport(true);
      updateStatus('error');
      return;
    }

    stoppedRef.current  = false;
    startingRef.current = false;

    function buildRecognition() {
      const r = new SR();
      r.continuous     = true;
      r.interimResults = true;
      
      const selected = LISTENING_LANGUAGES.find(l => l.name === listeningLang) || LISTENING_LANGUAGES[0];
      r.lang           = selected.code;

      r.onstart = () => {
        if (r !== recognitionRef.current) return;
        startTimeRef.current = Date.now();
        if (failsafeTimer) clearTimeout(failsafeTimer);
        cancelSpeechTimers();
        startingRef.current = false;
        
        // Reset retry states on successful start
        retryCountRef.current = 0;
        hasTransientErrorRef.current = false;
        
        const current = statusRef.current;
        if (current !== 'processing' && current !== 'responding') {
          if (current !== 'standby' && current !== 'active' && current !== 'listening') {
            updateStatus('standby');
          }
        }
      };

      r.onresult = (e) => {
        if (r !== recognitionRef.current) return;
        const current = statusRef.current;
        if (current === 'processing' || current === 'clearing' || current === 'responding') return;

        // Reset response state and clear previous reply on user speaking
        if (responseStateRef.current !== 'hidden') {
          updateResponseState('hidden');
          setLlmResponse('');
          if (autoClearTimer.current) {
            clearTimeout(autoClearTimer.current);
            autoClearTimer.current = null;
          }
        }

        cancelSpeechTimers();

        if (current === 'active') {
          startActiveTimeout();
        }

        let live = '';
        let final = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) {
            final += e.results[i][0].transcript;
          } else {
            live += e.results[i][0].transcript;
          }
        }
        if (final) {
          updateRawLastFinalText(prev => {
            const trimmedPrev = prev.trim();
            const trimmedFinal = final.trim();
            if (!trimmedPrev) return trimmedFinal;
            if (!trimmedFinal) return trimmedPrev;
            return trimmedPrev + ' ' + trimmedFinal;
          });

          const parsed = parseCommand(final);
          if (parsed.hasWakeWord && parsed.isWakeOnly && (statusRef.current === 'standby' || statusRef.current === 'listening' || statusRef.current === 'active')) {
            cancelSpeechTimers();
            handleSpeechEnded(final);
            return;
          }
        }
        updateRawInterim(live);

        // Wait 600ms of inactivity before auto-erasing speech command
        speechEndTimer.current = setTimeout(() => {
          handleSpeechEnded();
        }, 600);
      };
 
      r.onspeechend = () => {
        if (r !== recognitionRef.current) return;
        updateRawInterim('');
      };
 
      r.onend = () => {
        if (r !== recognitionRef.current) return;
        
        // Clear reference since the session has ended naturally
        recognitionRef.current = null;
        startingRef.current = false;
        
        const current = statusRef.current;
        if (current !== 'processing' && current !== 'responding' && current !== 'clearing') {
          if (isMicPaused) {
            updateStatus('paused');
          }
        }
 
        if (!stoppedRef.current) {
          const duration = Date.now() - startTimeRef.current;
          let restartDelay = 100;
          
          if (hasTransientErrorRef.current || duration < 2000) {
            // Apply exponential backoff for quick failures or transient errors
            const baseDelay = 300;
            const delay = baseDelay * Math.pow(2, retryCountRef.current);
            retryCountRef.current++;
            restartDelay = Math.min(delay, 3000); // capped at 3s max
            console.log(`[SpeechRecognition] Retry #${retryCountRef.current} scheduled in ${restartDelay}ms`);
          } else if (duration < 5000) {
            restartDelay = 300;
          }
          
          clearTimeout(restartTimer.current);
          restartTimer.current = setTimeout(tryStart, restartDelay);
        }
      };
 
      r.onerror = (e) => {
        if (r !== recognitionRef.current) return;
        
        console.warn(`[SpeechRecognition Error] ${e.error}`);
        startingRef.current = false;
        
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
          stoppedRef.current = true;
          setNoSupport(true);
          updateStatus('error');
          return;
        }

        // Flag transient errors so onend can apply backoff retry delay
        if (e.error === 'no-speech' || e.error === 'network' || e.error === 'aborted') {
          hasTransientErrorRef.current = true;
        }
      };

      return r;
    }

    let failsafeTimer = null;

    function tryStart() {
      if (stoppedRef.current || startingRef.current) return;
      startingRef.current = true;
      try {
        if (recognitionRef.current) {
          try { recognitionRef.current.abort(); } catch (_) {}
        }
        const r = buildRecognition();
        recognitionRef.current = r;
        startTimeRef.current = Date.now();
        
        if (failsafeTimer) clearTimeout(failsafeTimer);
        failsafeTimer = setTimeout(() => {
          if (startingRef.current && recognitionRef.current === r) {
            console.warn("[SpeechRecognition] Failsafe: Resetting starting state due to timeout.");
            startingRef.current = false;
          }
        }, 3500);

        r.start();
      } catch (_) {
        startingRef.current = false;
        clearTimeout(restartTimer.current);
        restartTimer.current = setTimeout(tryStart, 3000); // 3-second cooldown on error
      }
    }

    tryStart();

    return () => {
      stoppedRef.current = true;
      clearTimeout(restartTimer.current);
      if (failsafeTimer) clearTimeout(failsafeTimer);
      if (speechEndTimer.current) clearTimeout(speechEndTimer.current);
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch (_) {}
        recognitionRef.current = null;
      }
    };
  }, [isOff, listeningLang, isMicPaused]);

  const hasCustomColor = terminalSettings.colorTheme && terminalSettings.colorTheme.startsWith('#');
  const activeColorHex = hasCustomColor ? terminalSettings.colorTheme : (THEME_COLORS[terminalSettings.colorTheme]?.hex || '#00ff66');

  // Convert hex color to custom opacity RGBA string for glows
  const hexToRgbaStr = (hex, opacity) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return `rgba(0, 255, 102, ${opacity})`;
    const r = parseInt(result[1], 16);
    const g = parseInt(result[2], 16);
    const b = parseInt(result[3], 16);
    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
  };

  const glowColorStr = hexToRgbaStr(activeColorHex, 0.45);

  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e) => {
    if (!terminalSettings.draggable) return;
    if (e.target.closest('.terminal-edit-input') || 
        e.target.closest('.terminal-continue-btn') || 
        e.target.closest('.searchable-dropdown-container') || 
        e.target.closest('.terminal-minimize-btn')) return;

    setIsDragging(true);

    const wrapper = document.querySelector('.jarvis-terminal-wrapper');
    const currentX = terminalSettings.position ? terminalSettings.position.x : (wrapper ? wrapper.getBoundingClientRect().left : (window.innerWidth - terminalSettings.width) / 2);
    const currentY = terminalSettings.position ? terminalSettings.position.y : (wrapper ? wrapper.getBoundingClientRect().top : (window.innerHeight - 60 - 28));

    setDragStart({
      x: e.clientX - currentX,
      y: e.clientY - currentY
    });

    e.preventDefault();
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      const x = e.clientX - dragStart.x;
      const y = e.clientY - dragStart.y;
      setTerminalSettings(prev => ({ ...prev, position: { x, y } }));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setTerminalSettings(prev => {
        localStorage.setItem('jarvis-terminal-settings', JSON.stringify(prev));
        return prev;
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragStart, setTerminalSettings]);

  const positionStyle = terminalSettings.position
    ? {
        position: 'fixed',
        left: `${terminalSettings.position.x}px`,
        top: `${terminalSettings.position.y}px`,
        bottom: 'auto',
        transform: 'none'
      }
    : {};

  const dragCursorStyle = terminalSettings.draggable
    ? { cursor: isDragging ? 'grabbing' : 'grab' }
    : {};

  const wrapperStyle = {
    width: `${terminalSettings.width}px`,
    maxWidth: 'calc(100vw - 20px)',
    fontFamily: terminalSettings.fontFamily || "'Share Tech Mono', 'Orbitron', monospace",
    ...positionStyle,
    ...dragCursorStyle
  };

  const panelStyle = {
    borderRadius: `${terminalSettings.borderRadius}px`,
    backgroundColor: `rgba(6, 12, 8, ${terminalSettings.bgOpacity})`,
    '--terminal-theme-color': activeColorHex,
    '--terminal-glow-color': glowColorStr,
    '--terminal-bg-opacity': terminalSettings.bgOpacity,
    '--terminal-border-glow': terminalSettings.borderGlow,
    '--terminal-font-family': terminalSettings.fontFamily || "'Share Tech Mono', monospace",
    boxShadow: `
      0 0 0 1.5px rgba(255, 255, 255, 0.02) inset,
      0 20px 50px rgba(0, 0, 0, 0.65),
      0 0 ${terminalSettings.borderGlow * 35}px ${glowColorStr}
    `
  };

  return (
    <div 
      className={`jarvis-terminal-wrapper ${terminalSettings.draggable ? 'draggable-active' : ''}`}
      style={wrapperStyle}
      onMouseDown={handleMouseDown}
    >
      <div 
        className={`jarvis-terminal-panel jarvis-terminal-capsule status-${status} ${isOff ? 'is-off' : ''} ${terminalSettings.draggable ? 'draggable-active' : ''} ${isDragging ? 'dragging' : ''}`} 
        style={panelStyle}
        onClick={handleVoiceHubClick}
      >
        <div className="terminal-scanline" />

        {/* Terminal Header */}
        <div className="terminal-header">
          <div className="terminal-header-left">
            <span className="terminal-header-title">{assistantName} VOICE HUB</span>
            <div className={`terminal-header-status-dot ${status} ${isOff ? 'off' : ''}`} />
          </div>
          
          <div className="terminal-header-right">
            <SearchableDropdown 
              label="🌐 Listening" 
              options={LISTENING_LANGUAGES} 
              selected={listeningLang} 
              onSelect={(val) => {
                setListeningLang(val);
                localStorage.setItem('jarvis-listening-lang', val);
              }}
              placeholder="Search..."
            />
            <SearchableDropdown 
              label="🌐 Display" 
              options={DISPLAY_LANGUAGES} 
              selected={displayLang} 
              onSelect={(val) => {
                setDisplayLang(val);
                localStorage.setItem('jarvis-display-lang', val);
              }}
              placeholder="Search..."
            />
          </div>
        </div>

        {/* Floating controls panel inside capsule, active on hover */}
        <div className="terminal-hover-controls">
          <button
            className="terminal-minimize-btn"
            onClick={() => setMinimized(m => !m)}
          >
            <span className={`terminal-chevron ${minimized ? 'minimized' : ''}`}>⌄</span>
          </button>
        </div>

        {/* Capsule content block */}
        <div 
          className={`terminal-capsule-content ${minimized ? 'minimized' : ''}`}
          style={{ 
            height: minimized ? '0px' : 'auto',
            minHeight: minimized ? '0px' : `${terminalSettings.height}px`,
            paddingTop: minimized ? '0px' : '',
            paddingBottom: minimized ? '0px' : ''
          }}
        >
          <div className="terminal-prompt-prefix">
            {isEditingText ? (
              <span className="terminal-prompt-override">[ OVERRIDE ] &gt;</span>
            ) : (
              <>{assistantName} &gt;</>
            )}
          </div>

          <div 
            className="terminal-live-container"
            onClick={() => {
              setIsEditingText(true);
              setTimeout(() => {
                if (inputRef.current) inputRef.current.focus();
              }, 0);
            }}
            style={{ cursor: 'text' }}
          >
            {noSupport ? (
              <div className="terminal-empty error">
                {(window.SpeechRecognition || window.webkitSpeechRecognition)
                  ? '[ MIC ACCESS DENIED ]'
                  : '[ BROWSER NOT SUPPORTED ]'}
              </div>
            ) : isOff ? (
              <div className="terminal-empty offline">[ TERMINAL OFFLINE ]</div>
            ) : isEditingText ? (
              <div className="terminal-live-text" style={{ display: 'flex', width: '100%', alignItems: 'center' }}>
                <input
                  ref={inputRef}
                  type="text"
                  className="terminal-edit-input"
                  value={editableText}
                  onChange={handleInputChange}
                  onKeyDown={handleInputKeyDown}
                  onFocus={handleInputFocus}
                  onBlur={handleInputBlur}
                  placeholder="Type command..."
                  style={{ flex: 1 }}
                />
                <button 
                  className="terminal-continue-btn"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    cancelSpeechTimers();
                    setIsEditingText(false);
                    handleSpeechEnded(editableText);
                  }}
                >
                  Continue ➔
                </button>
                <span className="terminal-cursor" />
              </div>
            ) : status === 'processing' ? (
              <div className="terminal-live-text thinking" style={{ opacity: 0.8, color: activeColorHex }}>
                [ {assistantName.toUpperCase()} IS PROCESSING... ]
              </div>
            ) : (formattedFinalText || formattedInterimText) ? (
              <div className="terminal-live-text">
                {formattedFinalText && <span className="terminal-text-final">{formattedFinalText}</span>}
                {formattedInterimText && <span className="terminal-text-interim"> {formattedInterimText}</span>}
                <span className="terminal-cursor" />
              </div>
            ) : (responseState === 'visible' || responseState === 'pinned') ? (
              <div className="terminal-live-text responding">
                <span className="terminal-text-response">{llmResponse}</span>
                <span className="terminal-cursor" />
              </div>
            ) : status === 'active' ? (
              <div className="terminal-empty listening">Active (listening for follow-up)... {activeSecondsLeft}s</div>
            ) : status === 'listening' ? (
              <div className="terminal-empty listening">Listening...</div>
            ) : status === 'standby' ? (
              <div className="terminal-empty">[ STANDBY - Say "{assistantName}" ]</div>
            ) : (
              <div className="terminal-empty">[ SPEAK TO BEGIN ]</div>
            )}
          </div>

          <div className={`terminal-waveform ${status} ${isOff ? 'off' : ''} ${noSupport ? 'error' : ''}`}>
            <div className="waveform-bar bar-1"></div>
            <div className="waveform-bar bar-2"></div>
            <div className="waveform-bar bar-3"></div>
            <div className="waveform-bar bar-4"></div>
            <div className="waveform-bar bar-5"></div>
          </div>

          <button 
            className={`terminal-status-indicator ${status} ${noSupport ? 'error' : ''} ${isOff ? 'off' : ''}`}
            onClick={handleToggleTerminal}
            title={isOff ? "Turn On Terminal" : "Turn Off Terminal"}
          />
        </div>
      </div>
    </div>
  );
}
