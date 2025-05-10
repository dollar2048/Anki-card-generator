import re
import json
from pathlib import Path
from openai import OpenAI
import base64
import os
import csv

class AnkiCardGenerator:
    def __init__(self):
        self.client = OpenAI()
        self.media_dir = "anki_media"
        os.makedirs(self.media_dir, exist_ok=True)
        
    def extract_bold_text(self, line):
        bold_pattern = r'\*\*(.*?)\*\*'
        matches = re.findall(bold_pattern, line)
        return matches if matches else [line.strip()]
    
    def translate_text(self, text, is_sentence=False):
        prompt = f"Translate the following {'sentence' if is_sentence else 'word/phrase'} to Russian: {text}"
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    
    def get_expanded_meaning(self, word):
        prompt = f"Give a short explanation in Russian for the English word/phrase: {word}"
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    
    def generate_audio(self, text, is_sentence=False):
        filename = f"audio_{'sentence' if is_sentence else 'word'}_{base64.b64encode(text.encode()).decode()[:10]}.mp3"
        filepath = os.path.join(self.media_dir, filename)
        
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        response.stream_to_file(filepath)
        return f"[sound:{filename}]"  # Anki sound tag format
    
    def generate_image(self, sentence):
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=f"Create a simple illustration for the sentence: {sentence}",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        # Save the image
        image_url = response.data[0].url
        return f"<img src='{image_url}'>"  # Anki HTML image tag
    
    def process_line(self, line):
        bold_texts = self.extract_bold_text(line)
        foreign = bold_texts[0] if bold_texts else line.strip()
        foreign_sentence = line.strip().replace('*', '')
        
        # Generate translations
        russian = self.translate_text(foreign)
        russian_sentence = self.translate_text(foreign_sentence, is_sentence=True)
        
        # Generate audio files
        audio = self.generate_audio(foreign)
        audio_sentence = self.generate_audio(foreign_sentence, is_sentence=True)
        
        # Generate image
        image = self.generate_image(foreign_sentence)
        
        # Get expanded meaning
        expanded_meaning = self.get_expanded_meaning(foreign)
        
        return [
            foreign,                 # Foreign
            foreign_sentence,        # Foreign Sentence
            russian,                 # Russian
            russian_sentence,        # Russian Sentence
            audio,                   # Audio
            audio_sentence,          # Audio Sentence
            expanded_meaning,        # Expanded Meaning
            image,                   # Image
            "",                      # Url
            "",                      # frequencies
            "openAPI"               # Tags
        ]
    
    def generate_cards(self, input_file):
        cards = []
        # Define headers for Anki import
        headers = [
            "Foreign",
            "Foreign Sentence",
            "Russian",
            "Russian Sentence",
            "Audio",
            "Audio Sentence",
            "Expanded Meaning",
            "Image",
            "Url",
            "frequencies",
            "Tags"
        ]
        
        # Generate cards
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    card = self.process_line(line)
                    cards.append(card)
        
        # Save as tab-separated file
        output_file = 'anki_cards.txt'
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(headers)  # Write headers
            writer.writerows(cards)   # Write cards
        
        return len(cards)

if __name__ == "__main__":
    generator = AnkiCardGenerator()
    num_cards = generator.generate_cards('input.md')
    print(f"""Generated {num_cards} Anki cards!

Instructions for importing into Anki:
1. Copy all .mp3 files from the 'anki_media' folder to your Anki media collection folder:
   - On Mac: ~/Library/Application Support/Anki2/User 1/collection.media/
2. Import anki_cards.txt in Anki:
   - File -> Import
   - Select anki_cards.txt
   - Set Type to "Basic"
   - Set Field separator to "Tab"
   - Match fields as needed
   - Click Import""") 