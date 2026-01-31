# Web Speech API Research

## Overview
The **Web Speech API** is a browser-native JavaScript API that provides two distinct capabilities:
1. **Speech Recognition (STT)**: Convert spoken audio to text
2. **Speech Synthesis (TTS)**: Convert text to spoken audio

## Browser Support
| Browser | Speech Recognition | Speech Synthesis |
|---------|-------------------|------------------|
| Chrome | ✅ Full | ✅ Full |
| Edge | ✅ Full | ✅ Full |
| Safari | ✅ Full | ✅ Full |
| Firefox | ⚠️ Partial | ✅ Full |
| Opera | ✅ Full | ✅ Full |

## Speech Recognition (SpeechRecognition)

### Basic Setup
```javascript
// Handle vendor prefixes
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// Create instance
const recognition = new SpeechRecognition();

// Configure
recognition.continuous = false;        // Stop after single result
recognition.lang = 'en-US';            // Language
recognition.interimResults = false;    // Only final results
recognition.maxAlternatives = 1;       // Number of alternatives
```

### Event Handlers
```javascript
// Start recognition
recognition.start();

// Handle results
recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    const confidence = event.results[0][0].confidence;
    console.log(`Heard: ${transcript} (${confidence * 100}% confident)`);
};

// Handle errors
recognition.onerror = (event) => {
    console.error(`Error: ${event.error}`);
};

// Speech ended
recognition.onspeechend = () => {
    recognition.stop();
};
```

### Key Properties
| Property | Type | Description |
|----------|------|-------------|
| `continuous` | Boolean | Keep listening vs. single result |
| `lang` | String | BCP 47 language tag (e.g., 'en-US') |
| `interimResults` | Boolean | Return partial results |
| `maxAlternatives` | Number | Alt transcriptions to return |
| `processLocally` | Boolean | On-device processing (new) |

### Error Types
- `no-speech` - No speech detected
- `audio-capture` - Microphone unavailable
- `not-allowed` - Permission denied
- `network` - Network error (cloud processing)
- `language-not-supported` - Language unavailable

## On-Device Processing (Privacy Mode)
New feature for offline, private recognition:

```javascript
// Enable local processing
recognition.processLocally = true;

// Check/install language pack
SpeechRecognition.available({ 
    langs: ['en-US'], 
    processLocally: true 
}).then((result) => {
    if (result === 'available') {
        recognition.start();
    } else if (result === 'downloadable') {
        SpeechRecognition.install({ 
            langs: ['en-US'], 
            processLocally: true 
        });
    }
});
```

## Speech Synthesis (SpeechSynthesis)

### Basic Usage
```javascript
// Create utterance
const utterance = new SpeechSynthesisUtterance('Hello, world!');

// Configure
utterance.lang = 'en-US';
utterance.pitch = 1;      // 0-2
utterance.rate = 1;       // 0.1-10
utterance.volume = 1;     // 0-1

// Speak
speechSynthesis.speak(utterance);
```

### Get Available Voices
```javascript
// Voices load asynchronously
speechSynthesis.onvoiceschanged = () => {
    const voices = speechSynthesis.getVoices();
    voices.forEach(voice => {
        console.log(`${voice.name} (${voice.lang})`);
    });
};
```

## Advantages Over External APIs
1. **Free**: No API costs or quotas
2. **Fast**: Local processing, low latency
3. **Private**: No data leaves the browser (with processLocally)
4. **Simple**: No backend required
5. **Offline**: Works without internet (on-device mode)

## Limitations
1. **Browser Dependency**: Varies by browser
2. **Accuracy**: May be lower than commercial APIs
3. **Languages**: Limited language support
4. **No Training**: Can't customize for domain vocabulary
5. **No Diarization**: Single speaker only

## Comparison with Alternatives

| Feature | Web Speech API | Whisper | Cloud APIs |
|---------|---------------|---------|------------|
| Cost | Free | Free | Pay-per-use |
| Setup | Zero | Model download | API keys |
| Offline | Yes* | Yes | No |
| Accuracy | Good | Excellent | Excellent |
| Languages | ~50 | 99 | 100+ |
| Privacy | High* | High | Low |

*With processLocally enabled

## Use Cases
- Voice commands in web apps
- Dictation/note-taking
- Accessibility features
- Voice search
- Language learning apps
- Prototyping voice interfaces

## Resources
- MDN Docs: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
- Spec: https://webaudio.github.io/web-speech-api/
- Chrome Blog: https://developer.chrome.com/blog/voice-driven-web-apps-introduction-to-the-web-speech-api

---
*Research compiled: January 29, 2026*
