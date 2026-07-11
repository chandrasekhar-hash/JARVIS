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

export default function Terminal({ terminalSettings, setTerminalSettings }) {
  const { assistantName, wakeWords, wakeWordRequired } = useAssistantConfig();
  const [rawLastFinalText, setRawLastFinalText] = useState('');
  const [rawInterim, setRawInterim]             = useState('');
  const [status, setStatus]                     = useState('paused');
  const [minimized, setMinimized]               = useState(false);
  const [noSupport, setNoSupport]               = useState(false);
  const [isFading, setIsFading]                 = useState(false);
  const [isOff, setIsOff]                       = useState(false);

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
  const typewriterTimer = useRef(null);
  const autoClearTimer = useRef(null);

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
    if (!text) return { hasWakeWord: false, command: '' };
    const textLower = text.toLowerCase();
    
    // Normalization helper: trim multiple spaces, ignore punctuation, case-insensitive
    const normalize = (str) => str.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").replace(/\s+/g, ' ').trim().toLowerCase();
    const normText = normalize(textLower);
    
    const sortedWakeWords = [...wakeWords].sort((a, b) => b.length - a.length);
    
    let matchedWakeWord = null;
    for (const wakeWord of sortedWakeWords) {
      const normWake = normalize(wakeWord);
      if (normText.startsWith(normWake)) {
        matchedWakeWord = wakeWord;
        break;
      }
    }
    
    if (matchedWakeWord) {
      const escapeReg = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      // Match the wake word at the start, accounting for optional punctuation and spaces
      const pattern = new RegExp("^[\\s.,\\/#!$%\\^&\\*;:{}=\\-_`~()?]*" + escapeReg(matchedWakeWord) + "[.,\\/#!$%\\^&\\*;:{}=\\-_`~()?]*\\s*", "i");
      const command = text.replace(pattern, '').trim();
      return {
        hasWakeWord: true,
        command
      };
    }
    
    return {
      hasWakeWord: false,
      command: text.trim()
    };
  };

  useEffect(() => {
    let active = true;
    async function format() {
      try {
        const finalFormatted = await formatTranscript(rawLastFinalText, listeningLang, displayLang);
        if (!active) return;
        
        const { hasWakeWord, command } = parseCommand(finalFormatted);
        if (hasWakeWord) {
          wakeWordDetectedRef.current = true;
        }

        if (wakeWordRequired) {
          if (wakeWordDetectedRef.current) {
            setFormattedFinalText(command);
          } else {
            setFormattedFinalText('');
          }
        } else {
          setFormattedFinalText(command);
        }
      } catch (err) {
        console.error("Failed formatting final text:", err);
      }
    }
    format();
    return () => {
      active = false;
    };
  }, [rawLastFinalText, listeningLang, displayLang, wakeWordRequired, wakeWords]);

  useEffect(() => {
    let active = true;
    if (!rawInterim) {
      setFormattedInterimText('');
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const combinedRaw = (rawLastFinalText.trim() + ' ' + rawInterim.trim()).trim();
        const combinedFormatted = await formatTranscript(combinedRaw, listeningLang, displayLang);
        if (!active) return;

        const { hasWakeWord, command } = parseCommand(combinedFormatted);
        if (hasWakeWord) {
          wakeWordDetectedRef.current = true;
        }

        if (wakeWordRequired) {
          if (wakeWordDetectedRef.current) {
            const finalClean = parseCommand(await formatTranscript(rawLastFinalText, listeningLang, displayLang)).command;
            const interimClean = command.slice(finalClean.length).trim();
            setFormattedInterimText(interimClean);
          } else {
            setFormattedInterimText('');
          }
        } else {
          const finalClean = parseCommand(await formatTranscript(rawLastFinalText, listeningLang, displayLang)).command;
          const interimClean = command.slice(finalClean.length).trim();
          setFormattedInterimText(interimClean);
        }
      } catch (err) {
        console.error("Failed formatting interim text:", err);
      }
    }, 150);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [rawInterim, rawLastFinalText, listeningLang, displayLang, wakeWordRequired, wakeWords]);


  const handleToggleTerminal = (e) => {
    e.stopPropagation();
    if (noSupport) return;
    setIsOff(prev => !prev);
  };

  const recognitionRef  = useRef(null);
  const restartTimer    = useRef(null);
  const startingRef     = useRef(false);
  const stoppedRef      = useRef(false);
  const startTimeRef    = useRef(0);

  const rawLastFinalTextRef = useRef('');
  const rawInterimRef       = useRef('');
  const statusRef           = useRef('paused');
  const speechEndTimer      = useRef(null);
  const fadeTimer           = useRef(null);
  const wakeWordDetectedRef = useRef(false);

  const updateStatus = (newStatus) => {
    statusRef.current = newStatus;
    setStatus(newStatus);
    if (newStatus === 'listening') {
      wakeWordDetectedRef.current = false;
    }
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
        
        if (autoClearTimer.current) clearTimeout(autoClearTimer.current);
        autoClearTimer.current = setTimeout(() => {
          updateStatus('clearing');
          setIsFading(true);
          
          if (fadeTimer.current) clearTimeout(fadeTimer.current);
          fadeTimer.current = setTimeout(() => {
            setIsFading(false);
            setLlmResponse('');
            updateStatus('listening');
          }, 500);
        }, 7000);
      }
    }, 20);
  };

  const fetchGroqResponse = async (query) => {
    updateStatus('thinking');
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
          max_tokens: 150
        })
      });

      if (!response.ok) {
        throw new Error(`Groq API returned status ${response.status}`);
      }

      const data = await response.json();
      const reply = data.choices?.[0]?.message?.content || "No response received.";
      
      updateStatus('responding');
      typewrite(reply);
    } catch (error) {
      console.error("[Groq API Error]", error);
      updateStatus('responding');
      typewrite(`Error connecting to ${assistantName} core.`);
    }
  };

  const handleSpeechEnded = (customCommand) => {
    const command = (customCommand !== undefined ? customCommand : editableTextRef.current).trim();
    if (!command) {
      updateStatus('listening');
      setEditableText('');
      return;
    }

    // Ignore command if wake word is required but not detected (and not manually typed)
    if (customCommand === undefined && wakeWordRequired && !wakeWordDetectedRef.current) {
      console.log(`[${assistantName} Assistant] Ignored: Wake word required but not detected.`);
      updateStatus('listening');
      setEditableText('');
      setFormattedFinalText('');
      setFormattedInterimText('');
      updateRawLastFinalText('');
      updateRawInterim('');
      return;
    }

    console.log(`[${assistantName} Assistant] Command ended: "${command}"`);
    
    // Clear speaking texts immediately
    updateRawLastFinalText('');
    updateRawInterim('');
    setEditableText('');
    setFormattedFinalText('');
    setFormattedInterimText('');
    
    // Trigger Groq query
    fetchGroqResponse(command);
  };

  const cancelSpeechTimers = () => {
    if (speechEndTimer.current) {
      clearTimeout(speechEndTimer.current);
      speechEndTimer.current = null;
    }
    if (fadeTimer.current) {
      clearTimeout(fadeTimer.current);
      fadeTimer.current = null;
    }
    if (typewriterTimer.current) {
      clearInterval(typewriterTimer.current);
      typewriterTimer.current = null;
    }
    if (autoClearTimer.current) {
      clearTimeout(autoClearTimer.current);
      autoClearTimer.current = null;
    }
    setIsFading(false);
  };

  const isMicPaused = isOff || isEditingText || status === 'thinking' || status === 'responding';

  useEffect(() => {
    if (isMicPaused) {
      updateStatus(statusRef.current === 'thinking' || statusRef.current === 'responding' ? statusRef.current : 'paused');
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
        // Do not force listening status if we are already thinking or responding
        if (statusRef.current !== 'thinking' && statusRef.current !== 'responding') {
          updateStatus('listening');
        }
      };

      r.onresult = (e) => {
        if (r !== recognitionRef.current) return;
        if (statusRef.current === 'processing' || statusRef.current === 'clearing' || statusRef.current === 'thinking' || statusRef.current === 'responding') return;

        cancelSpeechTimers();
        updateStatus('transcribing');

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
        }
        updateRawInterim(live);

        // Wait 1.5 seconds of inactivity before auto-erasing speech command
        speechEndTimer.current = setTimeout(() => {
          handleSpeechEnded();
        }, 1500);
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
        
        if (statusRef.current !== 'processing' && statusRef.current !== 'clearing' && statusRef.current !== 'thinking' && statusRef.current !== 'responding') {
          updateStatus('paused');
        }
 
        if (!stoppedRef.current) {
          const duration = Date.now() - startTimeRef.current;
          const restartDelay = duration < 2000 ? 3000 : 300;
          clearTimeout(restartTimer.current);
          restartTimer.current = setTimeout(tryStart, restartDelay);
        }
      };
 
      r.onerror = (e) => {
        if (r !== recognitionRef.current) return;
        
        startingRef.current = false;
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
          stoppedRef.current = true;
          setNoSupport(true);
          updateStatus('error');
          return;
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
      if (fadeTimer.current) clearTimeout(fadeTimer.current);
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

  const wrapperStyle = {
    width: `${terminalSettings.width}px`,
    maxWidth: 'calc(100vw - 20px)',
    fontFamily: terminalSettings.fontFamily || "'Share Tech Mono', 'Orbitron', monospace",
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
      className="jarvis-terminal-wrapper" 
      style={wrapperStyle}
    >
      <div 
        className={`jarvis-terminal-panel jarvis-terminal-capsule status-${status} ${isOff ? 'is-off' : ''}`} 
        style={panelStyle}
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
            ) : status === 'thinking' ? (
              <div className="terminal-live-text thinking" style={{ opacity: 0.8, color: activeColorHex }}>
                [ JARVIS IS THINKING... ]
              </div>
            ) : status === 'responding' ? (
              <div className={`terminal-live-text responding ${isFading ? 'fading' : ''}`}>
                <span className="terminal-text-response">{llmResponse}</span>
                <span className="terminal-cursor" />
              </div>
            ) : isEditingText ? (
              <div className={`terminal-live-text ${isFading ? 'fading' : ''}`} style={{ display: 'flex', width: '100%', alignItems: 'center' }}>
                <input
                  ref={inputRef}
                  type="text"
                  className="terminal-edit-input"
                  value={editableText}
                  onChange={handleInputChange}
                  onKeyDown={handleInputKeyDown}
                  onFocus={handleInputFocus}
                  onBlur={handleInputBlur}
                  disabled={isFading}
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
                  disabled={isFading}
                >
                  Continue ➔
                </button>
                <span className="terminal-cursor" />
              </div>
            ) : (formattedFinalText || formattedInterimText) ? (
              <div className={`terminal-live-text ${isFading ? 'fading' : ''}`}>
                {formattedFinalText && <span className="terminal-text-final">{formattedFinalText}</span>}
                {formattedInterimText && <span className="terminal-text-interim"> {formattedInterimText}</span>}
                <span className="terminal-cursor" />
              </div>
            ) : (status === 'listening' || status === 'transcribing') ? (
              <div className="terminal-empty listening">Listening...</div>
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
