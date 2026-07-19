import React, { useState, useEffect, useRef } from 'react';
import { useAssistantConfig } from '../context/AssistantConfigContext';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
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
const PAUSE_MIC_ON_RESPONSE = false;

// Conversation mode: how long (seconds) of complete inactivity before returning to Wake Mode
const CONVERSATION_TIMEOUT_SECS = 12;

export default function Terminal({ terminalSettings, setTerminalSettings }) {
  const { assistantName, wakeWords, wakeWordRequired, voiceStatus, setVoiceStatus, voiceGender, creator, voiceLanguage } = useAssistantConfig();
  const [rawLastFinalText, setRawLastFinalText] = useState('');
  const [rawInterim, setRawInterim]             = useState('');
  const status = voiceStatus;
  const setStatus = setVoiceStatus;
  const [minimized, setMinimized]               = useState(false);
  const [noSupport, setNoSupport]               = useState(false);
  const [isOff, setIsOff]                       = useState(false);

  const handleBridgeRequest = async (request) => {
    const { id, op, args } = request;
    console.log(`[Bridge] Received request: id=${id}, op=${op}`, args);
    const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
    const callbackUrl = `${baseUrl}/api/bridge/callback`;
    try {
      let result = null;
      if (isTauri) {
        result = await invoke("dispatch_desktop_operation", { op, args });
      } else {
        throw new Error("Platform operations are only supported when running inside Tauri.");
      }
      await fetch(callbackUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, data: result })
      });
      console.log(`[Bridge] Request ${id} successfully resolved with data:`, result);
    } catch (err) {
      console.error(`[Bridge] Error handling request ${id}:`, err);
      try {
        await fetch(callbackUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, error: err.message || String(err) })
        });
      } catch (e) {
        console.error("[Bridge] Failed to post error callback:", e);
      }
    }
  };

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

  // Listen to Tauri events (Runtime State changes and SSE streaming tokens)
  useEffect(() => {
    if (!isTauri) return;

    let unlistenState = null;
    let unlistenToken = null;

    const setupListeners = async () => {
      try {
        unlistenState = await listen('runtime-state-change', (event) => {
          const { state, previous } = event.payload;
          console.log(`[Tauri Runtime] State changed from ${previous} to ${state}`);
          
          switch (state) {
            case 'BOOT':
            case 'LAUNCHINGBACKEND':
            case 'WAITINGFORHEALTH':
              updateStatus('processing');
              setLlmResponse('System Initializing: Spawning core backend services...');
              break;
            case 'READY':
              updateStatus('standby');
              setLlmResponse('');
              break;
            case 'RESTARTING':
              updateStatus('paused');
              setLlmResponse('System Alert: Backend process died. Reconnecting...');
              break;
            case 'FAILED':
              updateStatus('error');
              setLlmResponse('CRITICAL ERROR: Backend failed to start after maximum retry attempts.');
              break;
            case 'SHUTDOWN':
              updateStatus('standby');
              break;
            default:
              break;
          }
        });

        unlistenToken = await listen('chat-token', (event) => {
          const json = event.payload;
          if (json.type === 'text') {
            const token = json.content || "";
            if (token) {
              accumulatedTextRef.current += token;
              setLlmResponse(accumulatedTextRef.current);
              updateStatus('responding');
              updateResponseState('visible');
            }
          } else if (json.type === 'audio_url') {
            const audioUrl = json.url;
            const sentenceText = json.text || "";
            if (audioUrl) {
              receivedAudioUrlRef.current = true;
              playAssistantAudio(audioUrl, sentenceText);
            }
          } else if (json.type === 'bridge_request') {
            handleBridgeRequest(json);
          } else if (json.type === 'error') {
            console.error("[Tauri Backend Error]", json.content);
          }
        });
      } catch (err) {
        console.error("Failed to establish Tauri event listeners:", err);
      }
    };

    setupListeners();

    return () => {
      if (unlistenState) unlistenState();
      if (unlistenToken) unlistenToken();
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
  const [llmResponse, setLlmResponseState] = useState('');
  const llmResponseRef = useRef('');
  const setLlmResponse = (valOrFn) => {
    if (typeof valOrFn === 'function') {
      setLlmResponseState(prev => {
        const next = valOrFn(prev);
        llmResponseRef.current = next;
        return next;
      });
    } else {
      llmResponseRef.current = valOrFn;
      setLlmResponseState(valOrFn);
    }
  };
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
  const activeAudioRef      = useRef(null);
  const activeRequestControllerRef = useRef(null);
  const activeReaderRef     = useRef(null); // tracks the active SSE ReadableStreamDefaultReader
  const isRequestActiveRef  = useRef(false); // mutex: prevents overlapping fetchGroqResponse calls
  const audioQueueRef       = useRef([]);   // array of cached audio chunk URLs
  const isPlayingAudioRef   = useRef(false); // flag representing active audio queue playback
  const lastQueryRef        = useRef({ text: '', time: 0 });
  const wakeWordDetectedRef = useRef(false);
  const retryCountRef         = useRef(0);
  const hasTransientErrorRef  = useRef(false);
  const accumulatedTextRef    = useRef('');
  const receivedAudioUrlRef   = useRef(false);
  const isTauri = typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__;

  const updateStatus = (newStatus) => {
    statusRef.current = newStatus;
    setStatus(newStatus);
    if (newStatus === 'listening' || newStatus === 'active') {
      wakeWordDetectedRef.current = false;
    }
  };

  const startActiveTimeout = () => {
    clearActiveTimeout();
    setActiveSecondsLeft(CONVERSATION_TIMEOUT_SECS);

    activeCountdownIntervalRef.current = setInterval(() => {
      setActiveSecondsLeft((prev) => {
        // Never expire while the assistant is actively doing something
        const s = statusRef.current;
        if (s === 'responding' || s === 'processing' || s === 'listening') {
          return prev; // hold, don't count down
        }
        if (prev <= 1) {
          clearInterval(activeCountdownIntervalRef.current);
          activeCountdownIntervalRef.current = null;
          setTimeout(() => {
            console.log(`[${assistantName} Assistant] Inactivity timeout: returning to STANDBY`);
            updateStatus('standby');
          }, 0);
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

  const handleManualBargeIn = () => {
    const current = statusRef.current;
    if (current === 'responding' || current === 'processing') {
      console.log("[Barge-in] Manual override barge-in. Aborting active stream and queue.");
      stopAllAudio();
      if (activeRequestControllerRef.current) {
        activeRequestControllerRef.current.abort();
        activeRequestControllerRef.current = null;
      }
      if (activeReaderRef.current) {
        try { activeReaderRef.current.cancel(); } catch (_) {}
        activeReaderRef.current = null;
      }
      setLlmResponse('');
      if (autoClearTimer.current) {
        clearTimeout(autoClearTimer.current);
        autoClearTimer.current = null;
      }
      updateResponseState('hidden');
      updateStatus('active');
      clearActiveTimeout();
    }
  };

  const handleInputFocus = () => {
    handleManualBargeIn();
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

    const originalTrimmed = text.trim();

    // Strip punctuation & normalise whitespace — used for detection only (not sent to LLM)
    const normalize = (str) =>
      str.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?'"]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();

    const normText = normalize(originalTrimmed);

    // Sort longest first so "hey jarvis" is tried before bare "jarvis"
    const sortedWakeWords = [...wakeWords].sort((a, b) => b.length - a.length);

    // ── PASS 1: Detection on normalised text ─────────────────────────────
    // Punctuation has already been stripped, so we use positional anchors.
    // "(?:^|(?<=\s))" + "(?=\s|$)" gives complete-word matching without \b
    // (which breaks on multi-word phrases like "hey jarvis").
    let matchedWakeWord = null;

    for (const wakeWord of sortedWakeWords) {
      const normWake = normalize(wakeWord);
      if (!normWake) continue;

      // Exact full-string → pure wake event (no command)
      if (normText === normWake) {
        return { hasWakeWord: true, isWakeOnly: true, command: '' };
      }

      // Match as a complete phrase anywhere in the normalised sentence
      const escaped = normWake.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const boundaryRe = new RegExp(`(?:^|(?<=\\s))${escaped}(?=\\s|$)`);
      if (boundaryRe.test(normText)) {
        matchedWakeWord = wakeWord;
        break;
      }
    }

    if (!matchedWakeWord) {
      return { hasWakeWord: false, isWakeOnly: false, command: originalTrimmed };
    }

    // ── PASS 2: Extraction from the original text ─────────────────────────
    // Remove the matched wake phrase plus any immediately adjacent punctuation
    // and whitespace so the remaining command is clean.
    const escapeReg = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const cleanPattern = new RegExp(
      `(^|\\s)[\\s.,!?;:'"]*${escapeReg(matchedWakeWord)}[\\s.,!?;:'"]*($|\\s)`,
      'gi'
    );

    let command = originalTrimmed.replace(cleanPattern, ' ').replace(/\s+/g, ' ').trim();
    // Drop any leftover leading/trailing punctuation the pattern may have missed
    command = command.replace(/^[\s.,!?;:'"]+|[\s.,!?;:'"]+$/g, '').trim();

    if (!normalize(command)) {
      return { hasWakeWord: true, isWakeOnly: true, command: '' };
    }

    return { hasWakeWord: true, isWakeOnly: false, command };
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

  const playNextAudio = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingAudioRef.current = false;
      activeAudioRef.current = null;
      console.log("[Assistant Voice Queue] All audio chunks finished playing.");
      if (statusRef.current === 'responding') {
        updateStatus('active');
        // Reset conversation timer — assistant just finished speaking
        startActiveTimeout();
        scheduleAutoClear();
      }
      return;
    }

    const nextChunk = audioQueueRef.current[0];
    if (!nextChunk.waitStart) {
      nextChunk.waitStart = Date.now();
    }
    const textToMatch = nextChunk.text ? nextChunk.text.trim() : "";

    if (textToMatch) {
      const cleanText = (str) => str.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").replace(/\s+/g, "").toLowerCase();
      const cleanNextText = cleanText(textToMatch);
      const cleanLlmResponse = cleanText(llmResponseRef.current || "");

      // Wait until the text is fully printed on screen before speaking, but cap at 150ms max wait
      const timeWaiting = Date.now() - nextChunk.waitStart;
      if (!cleanLlmResponse.includes(cleanNextText) && timeWaiting < 150) {
        console.log(`[Assistant Voice Queue] Waiting for text to display: "${textToMatch}" (waiting ${timeWaiting}ms)`);
        setTimeout(playNextAudio, 20); // Poll faster (20ms) for low-latency dispatch
        return;
      }
    }

    audioQueueRef.current.shift();
    isPlayingAudioRef.current = true;
    const url = nextChunk.url;
    const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
    const fullUrl = `${baseUrl}${url}`;

    console.log(`[Assistant Voice Queue] Playing segment: ${fullUrl}`);
    console.log(`DEBUG_LOG: [Frontend] Started playing audio segment.`);
    const audio = new Audio(fullUrl);
    activeAudioRef.current = audio;

    updateStatus('responding');

    audio.play().catch(err => {
      console.warn("[Assistant Voice Queue] Segment playback failed or was interrupted:", err);
      playNextAudio();
    });

    audio.onerror = (e) => {
      console.warn("[Assistant Voice Queue] Segment load error encountered:", e);
      if (activeAudioRef.current === audio) {
        activeAudioRef.current = null;
      }
      playNextAudio();
    };

    audio.onended = () => {
      console.log("[Assistant Voice Queue] Segment playback finished.");
      if (activeAudioRef.current === audio) {
        activeAudioRef.current = null;
      }
      playNextAudio();
    };
  };

  const playAssistantAudio = (url, text = "") => {
    const cleanChunk = text.replace(/[^\w\s]/g, "").trim();
    if (!cleanChunk && text) {
      console.log(`[Assistant Voice Queue] Skipping punctuation/empty audio chunk: "${text}"`);
      return;
    }
    audioQueueRef.current.push({ url, text });
    console.log(`DEBUG_LOG: [Frontend] Queued TTS audio for playback. Text: "${text}"`);
    console.log(`[Assistant Voice Queue] Added segment to queue, text: "${text}", current length: ${audioQueueRef.current.length}`);

    if (!isPlayingAudioRef.current) {
      playNextAudio();
    }
  };

  const stopAllAudio = () => {
    if (activeAudioRef.current) {
      activeAudioRef.current.onended = null;
      activeAudioRef.current.onerror = null;
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingAudioRef.current = false;
    console.log("[Assistant Voice Queue] Cleared all audio playback queue and stopped current audio.");
  };

  const fetchGroqResponse = async (query) => {
    const trimmedQuery = query.trim();
    console.log(`DEBUG_LOG: [Frontend] fetchGroqResponse called with query: "${trimmedQuery}"`);
    if (!trimmedQuery) return;

    const now = Date.now();
    if (lastQueryRef.current.text === trimmedQuery && (now - lastQueryRef.current.time) < 1000) {
      console.warn(`[${assistantName} Assistant] Duplicate query ignored within 1s: "${trimmedQuery}"`);
      return;
    }
    lastQueryRef.current = { text: trimmedQuery, time: now };

    // --- Stop and clear all audio queue immediately ---
    stopAllAudio();

    // --- Cancel any previous SSE stream reader ---
    if (activeReaderRef.current) {
      try { activeReaderRef.current.cancel(); } catch (_) {}
      activeReaderRef.current = null;
    }

    // --- Abort any previous fetch request ---
    if (activeRequestControllerRef.current) {
      activeRequestControllerRef.current.abort();
      activeRequestControllerRef.current = null;
    }

    // Mark as active so any concurrent call that slipped through is blocked
    isRequestActiveRef.current = true;

    // Hold the conversation — clear the inactivity timer while we're actively processing
    clearActiveTimeout();
    updateStatus('processing');

    const controller = new AbortController();
    activeRequestControllerRef.current = controller;

    if (isTauri) {
      console.log("DEBUG_LOG: [Frontend] Diverting fetchGroqResponse request to Tauri IPC...");
      try {
        const langMap = {
          'Hinglish': 'hinglish',
          'English': 'english',
          'हिन्दी': 'hindi',
          'ଓଡ଼ିଆ': 'odia',
          'తెలుగు': 'telugu',
          'தமிழ்': 'tamil',
          'ಕನ್ನಡ': 'kannada',
          'മലയാളം': 'malayalam',
          'বাংলা': 'bengali',
          'ગુજરાતી': 'gujarati',
          'ਪੰਜਾਬੀ': 'punjabi',
          'मराठी': 'marathi'
        };
        const selectedLangKey = langMap[displayLang] || 'english';
        const ttsLangKey = (voiceLanguage && voiceLanguage !== 'auto') ? voiceLanguage : selectedLangKey;

        setLlmResponse('');
        updateResponseState('visible');
        accumulatedTextRef.current = "";
        receivedAudioUrlRef.current = false;

        await invoke("send_chat_message", {
          payload: {
            message: trimmedQuery,
            voice: voiceGender,
            language: selectedLangKey,
            tts_language: ttsLangKey,
            assistant_name: assistantName,
            creator: creator
          }
        });

        console.log("DEBUG_LOG: [Frontend] Tauri IPC chat message call completed.");
        if (!receivedAudioUrlRef.current) {
          updateStatus('active');
          startActiveTimeout();
          scheduleAutoClear();
        }
      } catch (err) {
        console.error("[Tauri IPC Chat Error]", err);
        updateStatus('responding');
        const errReply = `Error connecting to ${assistantName} core.`;
        typewrite(errReply);
        setTimeout(() => {
          updateStatus('active');
          startActiveTimeout();
          scheduleAutoClear();
        }, 3000);
      } finally {
        isRequestActiveRef.current = false;
      }
      return;
    }

    try {
      const langMap = {
        'Hinglish': 'hinglish',
        'English': 'english',
        'हिन्दी': 'hindi',
        'ଓଡ଼ିଆ': 'odia',
        'తెలుగు': 'telugu',
        'தமிழ்': 'tamil',
        'ಕನ್ನಡ': 'kannada',
        'മലയാളം': 'malayalam',
        'বাংলা': 'bengali',
        'ગુજરાતી': 'gujarati',
        'ਪੰਜਾਬੀ': 'punjabi',
        'मराठी': 'marathi'
      };
      // display language key — used for both LLM context and TTS when voiceLanguage is 'auto'
      const selectedLangKey = langMap[displayLang] || 'english';
      // tts_language: explicit selection or auto (= follow display language)
      const ttsLangKey = (voiceLanguage && voiceLanguage !== 'auto') ? voiceLanguage : selectedLangKey;
      const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

      console.log(`DEBUG_LOG: [Frontend] Sending request to backend /api/chat...`);
      const response = await fetch(`${baseUrl}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: trimmedQuery,
          voice: voiceGender,
          language: selectedLangKey,
          tts_language: ttsLangKey,
          assistant_name: assistantName,
          creator: creator
        }),
        signal: controller.signal
      });

      console.log(`DEBUG_LOG: [Frontend] Backend response received, status: ${response.status}`);
      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }

      const reader = response.body.getReader();
      activeReaderRef.current = reader;
      const decoder = new TextDecoder("utf-8");
      console.log(`DEBUG_LOG: [Frontend] Received response stream from backend, starting reader loop...`);
      
      updateStatus('responding');
      updateResponseState('visible');
      setLlmResponse('');
      
      let accumulatedText = "";
      let buffer = "";
      let lastUpdateTime = 0;
      const THROTTLE_MS = 16; // Throttle to 16ms (60 FPS) for smooth rendering
      let receivedAudioUrl = false;

      while (true) {
        // Bail out if this request was superseded by a newer one
        if (controller.signal.aborted || activeRequestControllerRef.current !== controller) {
          try { reader.cancel(); } catch (_) {}
          return;
        }

        const { done, value } = await reader.read();
        console.log(`DEBUG_LOG: [Frontend] Stream reader chunk received. done: ${done}`);
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        
        buffer = lines.pop() || "";
        
        let hasNewTokens = false;
        for (const line of lines) {
          const cleanLine = line.trim();
          if (!cleanLine) continue;
          
          if (cleanLine.startsWith("data: ")) {
            try {
              const json = JSON.parse(cleanLine.slice(6));
              if (json.type === 'text') {
                const token = json.content || "";
                if (token) {
                  accumulatedText += token;
                  hasNewTokens = true;
                }
              } else if (json.type === 'audio_url') {
                const audioUrl = json.url;
                const sentenceText = json.text || "";
                if (audioUrl) {
                  receivedAudioUrl = true;
                  playAssistantAudio(audioUrl, sentenceText);
                }
              } else if (json.type === 'bridge_request') {
                handleBridgeRequest(json);
              } else if (json.type === 'error') {
                console.error("[Backend TTS Error]", json.content);
              }
            } catch (e) {
              // Ignore partial JSON parsing errors
            }
          }
        }

        if (hasNewTokens) {
          const nowMs = Date.now();
          if (nowMs - lastUpdateTime > THROTTLE_MS) {
            setLlmResponse(accumulatedText);
            lastUpdateTime = nowMs;
          }
        }
      }

      if (buffer && buffer.startsWith("data: ")) {
        try {
          const json = JSON.parse(buffer.slice(6));
          if (json.type === 'text') {
            const token = json.content || "";
            if (token) {
              accumulatedText += token;
            }
          } else if (json.type === 'audio_url') {
            const audioUrl = json.url;
            const sentenceText = json.text || "";
            if (audioUrl) {
              receivedAudioUrl = true;
              playAssistantAudio(audioUrl, sentenceText);
            }
          } else if (json.type === 'bridge_request') {
            handleBridgeRequest(json);
          }
        } catch (_) {}
      }

      // Ensure final state update is applied immediately
      setLlmResponse(accumulatedText);

      // Clean up refs if this is still the active request
      if (activeRequestControllerRef.current === controller) {
        activeRequestControllerRef.current = null;
      }
      if (activeReaderRef.current === reader) {
        activeReaderRef.current = null;
      }

      // Transition to active state only if no audio url was received (if received, the audio.onended handles transition)
      if (!receivedAudioUrl) {
        updateStatus('active');
        startActiveTimeout();
        scheduleAutoClear();
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log(`[${assistantName} Assistant] Request stream aborted successfully.`);
        return;
      }
      console.error("[API Error]", error);
      updateStatus('responding');
      const errReply = `Error connecting to ${assistantName} core.`;
      typewrite(errReply);
      
      // Fallback transition
      setTimeout(() => {
        updateStatus('active');
        startActiveTimeout();
        scheduleAutoClear();
      }, 3000);
    } finally {
      isRequestActiveRef.current = false;
    }
  };

  const handleWakeEvent = async () => {
    const currentState = statusRef.current;
    const isInConversation = currentState === 'active' || currentState === 'listening' || currentState === 'responding' || currentState === 'processing';

    let responseText;

    if (isInConversation) {
      // Already in Conversation Mode — just acknowledge, no time-based greeting
      const acks = [
        "Yes?",
        "I'm listening.",
        "Go ahead.",
        "How can I help?",
        "Ready.",
        "Tell me."
      ];
      responseText = acks[Math.floor(Math.random() * acks.length)];
      console.log(`[${assistantName} Assistant] Wake word in Conversation Mode — short ack: "${responseText}"`);
    } else {
      // Entering from Wake Mode — full time-based greeting
      const hours = new Date().getHours();
      let greetingPrefix = "Hello";
      if (hours >= 5 && hours < 12) {
        greetingPrefix = "Good Morning";
      } else if (hours >= 12 && hours < 17) {
        greetingPrefix = "Good Afternoon";
      } else if (hours >= 17 && hours < 22) {
        greetingPrefix = "Good Evening";
      }

      const creatorName = creator || "Sir";
      const followUps = [
        "How can I help you?",
        "What can I do for you?",
        "I'm listening."
      ];
      const followUp = followUps[Math.floor(Math.random() * followUps.length)];
      responseText = `${greetingPrefix}, ${creatorName}. ${followUp}`;
    }

    // Clear previous responses and stop ongoing audio; hold conversation timer during wake greeting
    stopAllAudio();
    clearActiveTimeout();
    updateStatus('responding');
    updateResponseState('visible');
    setLlmResponse(responseText);

    try {
      if (isTauri) {
        console.log("DEBUG_LOG: [Frontend] Diverting local wake greeting TTS to Tauri IPC...");
        const data = await invoke("get_tts_audio", {
          payload: {
            text: responseText,
            voice: voiceGender,
            language: voiceLanguage && voiceLanguage !== 'auto' ? voiceLanguage : 'english'
          }
        });
        if (data && data.url) {
          playAssistantAudio(data.url, responseText);
        } else {
          updateStatus('active');
          startActiveTimeout();
          scheduleAutoClear();
        }
        return;
      }

      const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/api/tts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text: responseText,
          voice: voiceGender,
          language: voiceLanguage && voiceLanguage !== 'auto' ? voiceLanguage : 'english'
        })
      });
      if (response.ok) {
        const data = await response.json();
        if (data.url) {
          playAssistantAudio(data.url, responseText);
        }
      } else {
        updateStatus('active');
        startActiveTimeout();
        scheduleAutoClear();
      }
    } catch (e) {
      console.error("Local wake greeting TTS failed:", e);
      updateStatus('active');
      startActiveTimeout();
      scheduleAutoClear();
    }
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

    console.log(`DEBUG_LOG: [Frontend] Speech ended, fullInput: "${fullInput}"`);
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
          console.log(`[${assistantName} Assistant] Ignored: Wake word not detected in transcript.`);
          updateStatus('standby');
        }
      } else {
        // Conversation mode: wake word not strictly required for follow-ups
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
        let current = statusRef.current;
        
        // Barge-in Interruption: Stop active speaker and stream immediately when user speaks
        if (current === 'responding' || current === 'processing') {
          const cleanForEcho = (str) => str.replace(/[^\w\s]/g, "").replace(/\s+/g, " ").trim().toLowerCase();
          const userClean = cleanForEcho(final + ' ' + live);
          const assistantClean = cleanForEcho((llmResponseRef.current || "") + " " + (audioQueueRef.current.map(q => q.text).join(" ")));
          
          if (userClean && assistantClean.includes(userClean)) {
            console.log(`[Echo Filter] Suppressed feedback echo: "${userClean}"`);
            return;
          }
          
          console.log("[Barge-in] Interruption detected. Aborting active stream and queue.");
          stopAllAudio();
          if (activeRequestControllerRef.current) {
            activeRequestControllerRef.current.abort();
            activeRequestControllerRef.current = null;
          }
          if (activeReaderRef.current) {
            try { activeReaderRef.current.cancel(); } catch (_) {}
            activeReaderRef.current = null;
          }
          setLlmResponse('');
          if (autoClearTimer.current) {
            clearTimeout(autoClearTimer.current);
            autoClearTimer.current = null;
          }
          
          // Stay in conversation mode — barge-in does NOT reset to standby
          updateStatus('listening');
          clearActiveTimeout(); // hold — user is actively speaking
          updateRawLastFinalText('');
          updateRawInterim('');
          setFormattedFinalText('');
          setFormattedInterimText('');
          
          current = 'listening';
        }

        if (current === 'clearing') return;

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

        // User is actively speaking — hold conversation timer regardless of mode
        clearActiveTimeout();
        if (current === 'standby') {
          // Wake word mode: keep standby until wake word confirmed
        } else {
          updateStatus('listening');
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
        console.log(`DEBUG_LOG: [Frontend] Speech Recognition onresult. final: "${final}", live: "${live}"`);
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

        // Adaptive timeout: 450ms for longer speech, 550ms for short speech to prevent cutoff
        const combinedRawText = (final + ' ' + live).trim();
        const wordCount = combinedRawText.split(/\s+/).filter(Boolean).length;
        const adaptiveTimeout = wordCount < 4 ? 550 : 450;

        speechEndTimer.current = setTimeout(() => {
          handleSpeechEnded();
        }, adaptiveTimeout);
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

  useEffect(() => {
    if (!terminalSettings.draggable && isDragging) {
      setIsDragging(false);
    }
  }, [terminalSettings.draggable, isDragging]);

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
              <div className="terminal-empty listening">
                <span className="conv-mode-badge">💬 CONVERSATION MODE</span>
                {' '}Listening for follow-up…
              </div>
            ) : status === 'listening' ? (
              <div className="terminal-empty listening">🎙️ Listening…</div>
            ) : status === 'standby' ? (
              <div className="terminal-empty">🔴 WAKE MODE — Say <em>&ldquo;{assistantName}&rdquo;</em> to begin</div>
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
