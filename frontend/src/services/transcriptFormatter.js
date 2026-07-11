import { transliterateIndianScript, parseIntent } from './languageEngine.js';

const GOOGLE_INPUT_TOOLS_MAP = {
  hindi: 'hi-t-i0-und',
  odia: 'or-t-i0-und',
  telugu: 'te-t-i0-und',
  tamil: 'ta-t-i0-und',
  kannada: 'kn-t-i0-und',
  malayalam: 'ml-t-i0-und',
  bengali: 'bn-t-i0-und',
  gujarati: 'gu-t-i0-und',
  punjabi: 'pa-t-i0-und',
  marathi: 'mr-t-i0-und'
};

const DISPLAY_LANG_KEYS = {
  'hinglish': 'hinglish',
  'english': 'english',
  'hindi': 'hindi',
  'हिन्दी': 'hindi',
  'odia': 'odia',
  'ଓଡ଼ିଆ': 'odia',
  'telugu': 'telugu',
  'తెలుగు': 'telugu',
  'tamil': 'tamil',
  'தமிழ்': 'tamil',
  'kannada': 'kannada',
  'ಕನ್ನಡ': 'kannada',
  'malayalam': 'malayalam',
  'മലയാളം': 'malayalam',
  'bengali': 'bengali',
  'বাংলা': 'bengali',
  'gujarati': 'gujarati',
  'ગુજરાતી': 'gujarati',
  'punjabi': 'punjabi',
  'ਪੰਜਾਬੀ': 'punjabi',
  'marathi': 'marathi',
  'मराठी': 'marathi'
};

const transliterationCaches = {};

function normalizeLangKey(lang) {
  if (!lang) return 'hinglish';
  const clean = lang.trim().toLowerCase();
  if (DISPLAY_LANG_KEYS[clean]) {
    return DISPLAY_LANG_KEYS[clean];
  }
  // Fallback / partial matching
  for (const [key, val] of Object.entries(DISPLAY_LANG_KEYS)) {
    if (key.includes(clean) || clean.includes(key)) {
      return val;
    }
  }
  return 'hinglish';
}

async function fetchTransliteration(text, itc) {
  const url = `https://inputtools.google.com/request?text=${encodeURIComponent(text)}&itc=${itc}&num=1&cp=0&cs=1&ie=utf-8&oe=utf-8&app=demopage`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Google Input Tools returned status ${response.status}`);
  }
  const data = await response.json();
  if (data && data[0] === 'SUCCESS') {
    return data[1]; // Array of segments
  }
  throw new Error("Transliteration failed");
}

async function transliterateToIndic(text, langKey) {
  if (!text) return '';
  const itc = GOOGLE_INPUT_TOOLS_MAP[langKey];
  if (!itc) return text;

  if (!transliterationCaches[langKey]) {
    transliterationCaches[langKey] = {};
  }
  const cache = transliterationCaches[langKey];

  const trimmedText = text.trim();
  if (!trimmedText) return text;

  const cacheKey = trimmedText.toLowerCase();
  if (cache[cacheKey]) {
    return cache[cacheKey];
  }

  try {
    const segments = await fetchTransliteration(trimmedText, itc);
    const transliterated = segments.map(seg => (seg[1] && seg[1].length > 0 ? seg[1][0] : seg[0])).join('');
    
    cache[cacheKey] = transliterated;
    return transliterated;
  } catch (err) {
    console.error(`[TranscriptFormatter] Transliteration API error for "${trimmedText}":`, err);
    return text;
  }
}

/**
 * Formats speech transcript according to display language preferences.
 * 
 * @param {string} rawTranscript - The raw transcript from speech recognition
 * @param {string} sourceLanguage - The active listening source language
 * @param {string} displayLanguage - The target display language (name or key)
 * @returns {Promise<string>} The formatted transcript
 */
export async function formatTranscript(rawTranscript, sourceLanguage, displayLanguage) {
  if (!rawTranscript) return '';

  const displayLangKey = normalizeLangKey(displayLanguage);

  // 1. Check intent dictionary for translations
  const matchedIntent = parseIntent(rawTranscript);
  if (matchedIntent) {
    const translation = matchedIntent.displays[displayLangKey];
    if (translation) {
      return translation;
    }
  }

  // 2. If display is English, we romanize it if it contains Indic characters
  if (displayLangKey === 'english') {
    const hasIndic = /[^\u0000-\u007F]/.test(rawTranscript);
    return hasIndic ? transliterateIndianScript(rawTranscript) : rawTranscript;
  }

  // 3. If display is Hinglish, we transliterate all Indic scripts to Roman
  if (displayLangKey === 'hinglish') {
    return transliterateIndianScript(rawTranscript);
  }

  // 4. Otherwise, display language is a native Indic script.
  // First, convert any existing Indic characters in raw transcript to Roman (phonetic)
  const romanizedInput = transliterateIndianScript(rawTranscript);

  // Then, transliterate from Roman script to the target native Indic script
  const transliterated = await transliterateToIndic(romanizedInput, displayLangKey);
  return transliterated;
}
