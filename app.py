import streamlit as st
import edge_tts
import asyncio
import re
from datetime import datetime
import tempfile
import os
import base64
import time

# Initialize session state for storing history
if 'text_history' not in st.session_state:
    st.session_state.text_history = []

# App title and configuration
st.title("Text-to-Speech Reader with Word Highlighting")
st.subheader("Powered by Edge TTS engine with British voices")

# British voices only
british_voices = [
    "en-GB-SoniaNeural",
    "en-GB-RyanNeural", 
    "en-GB-LibbyNeural",
    "en-GB-AbbiNeural",
    "en-GB-AlfieNeural",
    "en-GB-BellaNeural",
    "en-GB-ElliotNeural",
    "en-GB-EthanNeural",
    "en-GB-HollieNeural",
    "en-GB-MaisieNeural",
    "en-GB-NoahNeural",
    "en-GB-OliverNeural",
    "en-GB-ThomasNeural"
]

# Voice selection
selected_voice = st.selectbox(
    "Select a British voice:",
    british_voices,
    index=0
)

# Split the layout into two columns
col1, col2 = st.columns([3, 2])

with col1:
    # Subtitle box (top) - displays current sentence and highlights current word
    st.subheader("Current Sentence")
    current_sentence_container = st.empty()
    
    # Text input area (bottom)
    st.subheader("Input Text")
    text_input = st.text_area("Paste your text here:", height=200)

with col2:
    # History section
    st.subheader("Text History")
    history_container = st.container()

# Function to split text into sentences
def split_into_sentences(text):
    # Simple sentence splitting using regex
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

# Function to split sentence into words
def split_into_words(sentence):
    return re.findall(r'\b\w+\b|[.,!?;:]', sentence)

# Function to generate speech audio for a sentence
async def generate_speech_and_timing(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    
    # Create a temporary file for audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
        audio_path = audio_file.name
    
    # Collect word boundary data for timing
    word_boundaries = []
    async for chunk in communicate.stream():
        if chunk["type"] == "WordBoundary":
            word_boundaries.append(chunk)
    
    # Save audio file
    await communicate.save(audio_path)
    
    return audio_path, word_boundaries

# Function to get audio HTML with autoplay
def get_audio_html(audio_path):
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    
    audio_b64 = base64.b64encode(audio_bytes).decode()
    return f'<audio autoplay><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio>'

# Function to create HTML with highlighted word
def highlight_word_in_sentence(sentence, word_offset, word_length):
    # Create HTML with the word highlighted
    highlighted = (
        sentence[:word_offset] + 
        f"<span style='background-color: yellow;'>{sentence[word_offset:word_offset+word_length]}</span>" + 
        sentence[word_offset+word_length:]
    )
    return highlighted

# Read button
if st.button("Read Text"):
    if not text_input:
        st.warning("Please enter text.")
    else:
        # Add to history
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.text_history.append({"text": text_input, "timestamp": timestamp})
        
        # Update history display
        with history_container:
            for idx, item in enumerate(reversed(st.session_state.text_history)):
                with st.expander(f"Text {idx+1} - {item['timestamp']}"):
                    st.text(item["text"])
        
        # Split into sentences
        sentences = split_into_sentences(text_input)
        
        for sentence in sentences:
            # Display current sentence (without highlighting initially)
            current_sentence_container.markdown(sentence)
            
            # Generate speech and get word timing information
            audio_path, word_boundaries = asyncio.run(generate_speech_and_timing(sentence, selected_voice))
            
            # Display audio with autoplay
            st.markdown(get_audio_html(audio_path), unsafe_allow_html=True)
            
            # Track start time for timing calculation
            start_time = time.time()
            
            # Highlight words as they're spoken
            for i, boundary in enumerate(word_boundaries):
                # Calculate when this word should be highlighted
                word_time = boundary["Time"] / 10000000  # Convert from 100-nanosecond units to seconds
                
                # Wait until it's time to highlight this word
                elapsed = time.time() - start_time
                if word_time > elapsed:
                    time.sleep(word_time - elapsed)
                
                # Highlight the current word
                highlighted_sentence = highlight_word_in_sentence(
                    sentence,
                    boundary["TextOffset"],
                    boundary["WordLength"]
                )
                current_sentence_container.markdown(highlighted_sentence, unsafe_allow_html=True)
            
            # Clean up temporary file
            os.unlink(audio_path)
            
            # Small pause between sentences
            time.sleep(0.5)

# Display history
with history_container:
    for idx, item in enumerate(reversed(st.session_state.text_history)):
        with st.expander(f"Text {idx+1} - {item['timestamp']}"):
            st.text(item["text"])