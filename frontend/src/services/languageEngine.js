// Jarvis Multilingual Language System Engine

const OFFSET_MAP = {
  // Vowels
  0x05: 'a',
  0x06: 'aa',
  0x07: 'i',
  0x08: 'ee',
  0x09: 'u',
  0x0A: 'oo',
  0x0B: 'ri',
  0x0E: 'e',
  0x0F: 'e',
  0x10: 'ai',
  0x12: 'o',
  0x13: 'o',
  0x14: 'au',
  
  // Consonants
  0x15: 'k',
  0x16: 'kh',
  0x17: 'g',
  0x18: 'gh',
  0x19: 'ng',
  0x1A: 'ch',
  0x1B: 'chh',
  0x1C: 'j',
  0x1D: 'jh',
  0x1E: 'ny',
  0x1F: 't',
  0x20: 'th',
  0x21: 'd',
  0x22: 'dh',
  0x23: 'n',
  0x24: 't',
  0x25: 'th',
  0x26: 'd',
  0x27: 'dh',
  0x28: 'n',
  0x29: 'nn',
  0x2A: 'p',
  0x2B: 'ph',
  0x2C: 'b',
  0x2D: 'bh',
  0x2E: 'm',
  0x2F: 'y',
  0x30: 'r',
  0x31: 'rr',
  0x32: 'l',
  0x33: 'll',
  0x34: 'lll',
  0x35: 'v',
  0x36: 'sh',
  0x37: 'sh',
  0x38: 's',
  0x39: 'h',
  
  // Matras (Vowel signs)
  0x3E: 'aa',
  0x3F: 'i',
  0x40: 'ee',
  0x41: 'u',
  0x42: 'oo',
  0x43: 'ri',
  0x46: 'e',
  0x47: 'e',
  0x48: 'ai',
  0x4A: 'o',
  0x4B: 'o',
  0x4C: 'au',
  
  // Modifiers
  0x01: 'n',
  0x02: 'n',
  0x03: 'h',
};

const VIRAMA_OFFSET = 0x4D;

// Intent dictionary mapping for high-frequency voice assistant commands
const COMMAND_DICTIONARY = [
  {
    intent: "OPEN_SPOTIFY",
    displays: {
      english: "Open Spotify",
      hinglish: "Spotify khol do",
      hindi: "स्पॉटिफाय खोल दो",
      odia: "ସ୍ପୋଟିଫାଇ ଖୋଲ",
      telugu: "స్పాటిఫై ఓపెన్ చెయ్యి",
      tamil: "ஸ்பாட்டிஃபை திறக்கவும்",
      kannada: "ಸ್ಪಾಟಿಫೈ ಓಪನ್ ಮಾಡು",
      malayalam: "സ്പോട്ടിഫൈ തുറക്കുക",
      bengali: "স্পটিফাই খোলো",
      gujarati: "સ્પોટિફાય ખોલો",
      punjabi: "ਸਪੋਟੀਫਾਈ ਖੋਲ੍ਹੋ",
      marathi: "स्पॉटिफाय उघडा"
    }
  },
  {
    intent: "SET_REMINDER",
    displays: {
      english: "Set a reminder",
      hinglish: "Reminder laga do",
      hindi: "रिमाइंडर लगा दो",
      odia: "ରିମାଇଣ୍ଡର ଲଗା",
      telugu: "రిమైండర్ పెట్టు",
      tamil: "ரிமைண்டர் வை",
      kannada: "ಜ್ಞಾಪನೆ ಹೊಂದಿಸು",
      malayalam: "ഓർമ്മപ്പെടുത്തൽ സജ്జമാക്കുക",
      bengali: "রিমাইন্ডার সেট করো",
      gujarati: "રિમાઇન્ડર സેટ કરો",
      punjabi: "ਰਿਮਾਈਂਡਰ ਲਗਾਓ",
      marathi: "रिमाइंडर लावा"
    }
  },
  {
    intent: "HOW_ARE_YOU",
    displays: {
      english: "How are you?",
      hinglish: "Aap kaise ho",
      hindi: "आप कैसे हो",
      odia: "ଆପଣ କେମିତି ଅଛନ୍ତି",
      telugu: "మీరు ఎలా ఉన్నారు?",
      tamil: "எப்படி இருக்கீங்க?",
      kannada: "ಹೇಗಿದ್ದೀರಾ?",
      malayalam: "സുഖമാണോ?",
      bengali: "আপনি কেমন আছেন?",
      gujarati: "તમે કેમ છો?",
      punjabi: "ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ?",
      marathi: "तुम्ही कसे आहात?"
    }
  },
  {
    intent: "WEATHER_UPDATE",
    displays: {
      english: "Show weather update",
      hinglish: "Mausam kaisa hai",
      hindi: "मौसम कैसा है",
      odia: "ପାଣିପାଗ କେମିତି ଅଛି",
      telugu: "వాతావరణం ఎలా ఉంది?",
      tamil: "வானிலை எப்படி இருக்கிறது?",
      kannada: "ಹವಾಮಾನ ಹೇಗಿದೆ?",
      malayalam: "കാലാവസ്ഥ എങ്ങനെയുണ്ട്?",
      bengali: "আবহাওয়া কেমন?",
      gujarati: "હવામાન કેવું છે?",
      punjabi: "ਮੌਸਮ ਕਿਵੇਂ ਹੈ?",
      marathi: "हवामान कसे आहे?"
    }
  },
  {
    intent: "HELLO_GREETING",
    displays: {
      english: "Hello Jarvis",
      hinglish: "Namaste Jarvis",
      hindi: "नमस्ते जार्विस",
      odia: "ନମସ୍କାର ଜାର୍ଭିସ",
      telugu: "నమస్కారం జార్విస్",
      tamil: "வணக்கம் ஜார்விஸ்",
      kannada: "ನಮಸ್ಕಾರ జార్విస్",
      malayalam: "നമസ്കാരം ജാർവിസ്",
      bengali: "নমস্কার জার্ভিস",
      gujarati: "નમસ્તે જાર્વિસ",
      punjabi: "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ ਜਾਰਵਿਸ",
      marathi: "नमस्कार जार्विस"
    }
  },
  {
    intent: "SCHEDULE_MEETING",
    displays: {
      english: "Schedule a meeting for tomorrow",
      hinglish: "Kal meeting schedule kar do",
      hindi: "कल मीटिंग शेड्यूल कर दो",
      odia: "କାଲି ମିଟିଂ ସେଡ୍ୟୁଲ କର",
      telugu: "రేపు మీటింగ్ షెడ్యూల్ చెయ్యి",
      tamil: "நாளைக்கு மீட்டிங் ஷெட்யூல் செய்",
      kannada: "ನಾಳೆ ಮೀಟಿಂಗ್ ಶೆಡ್ಯೂಲ್ ಮಾಡು",
      malayalam: "നാളെ മീറ്റിംഗ് ഷെഡ്യൂൾ ചെയ്യുക",
      bengali: "কাল মিটিং শিডিউল করো",
      gujarati: "કાલે મીટિંગ શેડ્યૂલ કરો",
      punjabi: "ਕੱਲ੍ਹ ਮੀਟਿੰਗ ਸ਼ਡਿਊਲ ਕਰੋ",
      marathi: "उद्या मीटिंग शेड्यूल करा"
    }
  }
];

// Universal Indian Script phonetic transliteration engine to Roman (Hinglish/Tamilish/etc.)
export function transliterateIndianScript(text) {
  if (!text) return '';
  let result = '';
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const cp = char.charCodeAt(0);
    
    // Check if character is within Indic script ranges (U+0900 to U+0D7F)
    if (cp >= 0x0900 && cp <= 0x0D7F) {
      const offset = cp & 0x7F;
      
      // Check if it's a consonant (0x15 to 0x39)
      if (offset >= 0x15 && offset <= 0x39) {
        const translit = OFFSET_MAP[offset] || '';
        
        // Peek ahead to check modifiers, halants, or matras
        let nextChar = text[i + 1];
        let nextCp = nextChar ? nextChar.charCodeAt(0) : 0;
        
        if (nextCp >= 0x0900 && nextCp <= 0x0D7F) {
          const nextOffset = nextCp & 0x7F;
          
          if (nextOffset === VIRAMA_OFFSET) {
            // Suppress the inherent vowel
            result += translit;
            i++; // skip halant/virama
          } else if (nextOffset >= 0x3E && nextOffset <= 0x4C) {
            // Apply the matra vowel sound
            const matraTranslit = OFFSET_MAP[nextOffset] || '';
            result += translit + matraTranslit;
            i++; // skip matra
          } else {
            // Inherent vowel 'a' is preserved between consonant boundaries
            result += translit + 'a';
          }
        } else {
          // Word ending or boundary: drop inherent 'a' sound for Hinglish style readability
          result += translit;
        }
      } else {
        // standalone vowels, modifiers
        result += OFFSET_MAP[offset] || char;
      }
    } else {
      // Non-Indic scripts (English / Latin symbols) remain as-is
      result += char;
    }
  }
  
  // Clean up double/triple letters caused by composite matras or duplicates
  return result
    .replace(/aaa/g, 'aa')
    .replace(/eee/g, 'ee')
    .replace(/ooo/g, 'oo')
    .replace(/uuu/g, 'uu')
    .replace(/\s+/g, ' ');
}

// Parses input text to match common assistant command intents using unified transliterated keywords
export function parseIntent(text) {
  if (!text) return null;
  const clean = text.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g,"").replace(/\s+/g, ' ').trim();
  if (!clean) return null;

  // Transliterate all inputs to Latin to run single unified keyword filters
  const latinClean = transliterateIndianScript(clean).toLowerCase();

  if (latinClean.includes("spotify")) {
    if (latinClean.includes("open") || latinClean.includes("khol") || latinClean.includes("chala") || latinClean.includes("play") || latinClean.includes("tira") || latinClean.includes("teru") || latinClean.includes("khola") || latinClean.includes("pannu") || latinClean.includes("cheyyi")) {
      return COMMAND_DICTIONARY.find(c => c.intent === "OPEN_SPOTIFY");
    }
  }
  
  if (latinClean.includes("reminder") || latinClean.includes("remainder") || latinClean.includes("remind") || latinClean.includes("laga") || latinClean.includes("pettu") || latinClean.includes("vai")) {
    return COMMAND_DICTIONARY.find(c => c.intent === "SET_REMINDER");
  }
  
  if (latinClean.includes("meeting") || latinClean.includes("miting")) {
    if (latinClean.includes("schedule") || latinClean.includes("shedule") || latinClean.includes("rakh") || latinClean.includes("kar do") || latinClean.includes("kera")) {
      return COMMAND_DICTIONARY.find(c => c.intent === "SCHEDULE_MEETING");
    }
  }

  if (latinClean.includes("weather") || latinClean.includes("mausam") || latinClean.includes("panipaga") || latinClean.includes("vaathavaranam") || latinClean.includes("vanilai") || latinClean.includes("havamana") || latinClean.includes("kalavastha")) {
    return COMMAND_DICTIONARY.find(c => c.intent === "WEATHER_UPDATE");
  }

  if (latinClean.includes("kaise ho") || latinClean.includes("kaisa hai") || latinClean.includes("ela unnav") || latinClean.includes("ela unnar") || latinClean.includes("eppadi iruk") || latinClean.includes("kemiti achh") || latinClean.includes("kemon ach") || latinClean.includes("how are you") || latinClean.includes("hegidd") || latinClean.includes("sukhamano")) {
    return COMMAND_DICTIONARY.find(c => c.intent === "HOW_ARE_YOU");
  }

  if (latinClean.includes("hello") || latinClean.includes("hi") || latinClean.includes("namaste") || latinClean.includes("vanakkam") || latinClean.includes("namaskaram") || latinClean.includes("namaskar") || latinClean.includes("sat sri akal")) {
    return COMMAND_DICTIONARY.find(c => c.intent === "HELLO_GREETING");
  }

  return null;
}

// Global Multilingual Translation and Transliteration Processor
export function translateAndTransliterate(text, targetDisplayLang) {
  if (!text) return '';
  const langKey = targetDisplayLang.toLowerCase();

  // 1. If target display mode is Hinglish, transliterate phonetically directly
  if (langKey === 'hinglish') {
    return transliterateIndianScript(text);
  }

  // 2. Try to parse intent for translations to other scripts
  const matchedIntent = parseIntent(text);
  if (matchedIntent) {
    const translation = matchedIntent.displays[langKey];
    if (translation) return translation;
  }

  // 3. Fallback for English (if no intent matched): Romanize the text so it's readable
  if (langKey === 'english') {
    const hasIndic = /[^\u0000-\u007F]/.test(text);
    return hasIndic ? transliterateIndianScript(text) : text;
  }

  // 4. Default: Return text as-is
  return text;
}
