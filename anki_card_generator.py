import re
import json
from openai import OpenAI
import base64
import os
import random
import argparse
from tqdm import tqdm  # For progress indication
import requests

class AnkiCardGenerator:
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key
        )
        self.generate_media = False
        # Create media directory if it doesn't exist
        self.media_dir = os.path.join(os.getcwd(), "anki_media")
        os.makedirs(self.media_dir, exist_ok=True)
        print(f"Media directory: {self.media_dir}")
        
        # List to store media files
        self.media_files = []
        
        # Store notes for later export
        self.notes = []
        
    def extract_italic_text(self, line):
        italic_pattern = r'\*(.*?)\*'
        matches = re.findall(italic_pattern, line)
        return matches if matches else [line.strip()]
    
    def translate_text(self, text, is_sentence=False):
        if is_sentence:
            prompt = f"Translate the following sentence to Russian: {text}"
        else:
            prompt = f"Translate this English word/phrase to Russian. Give ONLY the shortest possible translation, no explanations: {text}"
            
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    
    def get_expanded_meaning(self, word):
        prompt = f"Give a short explanation in Russian for the English word/phrase: {word}"
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    
    def generate_audio(self, text, is_sentence=False):           
        try:
            print(f"Generating audio for: {text}")
            filename = f"audio_{'sentence' if is_sentence else 'word'}_{base64.b64encode(text.encode()).decode()[:10]}.mp3"
            filepath = os.path.join(self.media_dir, filename)
            print(f"Will save audio to: {filepath}")
            
            # Use with_streaming_response instead of stream_to_file
            with self.client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice="alloy",
                input=text
            ) as response:
                # Save the audio file
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
                print(f"Audio saved successfully to {filepath}")
            
            # Add to media files list
            self.media_files.append(filepath)
            
            # Return sound tag for Anki
            return f"[sound:{filename}]"
            
        except Exception as e:
            print(f"Error in generate_audio: {str(e)}")
            return ""
    
    def generate_image(self, sentence):
        if not self.generate_media:
            return ""
            
        try:
            print(f"Generating image for: {sentence}")
            response = self.client.images.generate(
                model="dall-e-3",  # Upgrade to DALL-E 3
                prompt=f"Create a simple illustration for the sentence: {sentence}",
                size="1024x1024",  # Higher quality
                quality="standard",
                n=1,
            )
            
            # Get image URL and download it
            image_url = response.data[0].url
            print(f"Image URL received: {image_url}")
            
            # Generate unique filename
            safe_sentence = re.sub(r'[^a-zA-Z0-9]', '', sentence)[:30]
            filename = f"img_{safe_sentence}.jpg"
            filepath = os.path.join(self.media_dir, filename)
            print(f"Saving image to: {filepath}")
            
            # Download image
            img_response = requests.get(image_url, stream=True)
            if img_response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in img_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"Image saved successfully to {filepath}")
                
                # Add to media files list for Anki package
                self.media_files.append(filepath)
                
                # Return only the filename for Anki
                return f'<img src="{filename}">'
            else:
                print(f"Failed to download image. Status code: {img_response.status_code}")
                return ""
                
        except Exception as e:
            print(f"Error in generate_image: {str(e)}")
            return ""
    
    def process_line(self, line):
        print("\nProcessing:", line.strip())
        
        italic_texts = self.extract_italic_text(line)

        # If it's just a single word/phrase in italic
        if len(italic_texts) == 1 and italic_texts[0] == line.strip().replace('*', ''):
            foreign = italic_texts[0]
            russian = self.translate_text(foreign)
            
            # Generate audio for foreign text
            print("Generating word audio...")
            audio = self.generate_audio(foreign)
            
            # Generate image if needed
            print("Generating image...")
            image = self.generate_image(foreign) if self.generate_media else ""
            
            # Get expanded meaning
            print("Getting expanded meaning...")
            expanded_meaning = self.get_expanded_meaning(foreign)
            
            # Create note with only essential fields
            guid = f"card_{len(self.notes)}_{random.randrange(1 << 30, 1 << 31)}"
            note = {
                'guid': guid,
                'notetype': 'Dollar_Type',
                'deck': 'English',
                'fields': [
                    foreign,                 # Foreign
                    "",                      # Foreign Sentence with highlighting
                    russian,                 # Russian
                    "",                      # Russian Sentence with italic
                    audio,                   # Audio
                    "",                      # Audio Sentence
                    expanded_meaning,        # Expanded Meaning
                    image,                   # Image
                    "",                      # Url
                    "",                      # frequencies
                    "openAI"                 # Tags
                ]
            }
            
            self.notes.append(note)
            print("Note created successfully!")
            return
            
        # If no italic text in the sentence
        if not italic_texts:
            foreign = line.strip()
            russian = self.translate_text(foreign, is_sentence=True)
            
            # Generate audio for foreign text
            audio = self.generate_audio(foreign)
            
            # Generate image if needed
            image = self.generate_image(foreign) if self.generate_media else ""
            
            # Create note with only essential fields
            guid = f"card_{len(self.notes)}_{random.randrange(1 << 30, 1 << 31)}"
            note = {
                'guid': guid,
                'notetype': 'Dollar_Type',
                'deck': 'English',
                'fields': [
                    foreign,                 # Foreign
                    "",                      # Foreign Sentence with highlighting
                    russian,                 # Russian
                    "",                      # Russian Sentence with italic
                    audio,                   # Audio
                    "",                      # Audio Sentence
                    "",                      # Expanded Meaning
                    image,                   # Image
                    "",                      # Url
                    "",                      # frequencies
                    "openAI"                 # Tags
                ]
            }
            
            self.notes.append(note)
            print("Note created successfully!")
            return
            
        print("\nIt's a sentence with italic text")

        # Original logic for sentences with italic text
        foreign = italic_texts[0] if italic_texts else line.strip()
        
        # Replace markdown with HTML matching the sample format
        foreign_sentence = line.strip()
        for italic_text in italic_texts:
            foreign_sentence = foreign_sentence.replace(
                f"*{italic_text}*",
                f'<span style="color: rgb(234, 78, 0);"><b>{italic_text}</b></span>'
            )
        
        # Generate translations
        print("Generating translations...")
        russian = self.translate_text(foreign)
        
        # Format Russian sentence with italic text for translations
        print("Formatting Russian sentence...")
        russian_sentence = self.translate_text(line.strip().replace('*', ''), is_sentence=True)
        if italic_texts and russian:
            russian_sentence = russian_sentence.replace(russian, f'<b>{russian}</b>')
        
        # Generate audio files
        print("Generating word audio...")
        audio = self.generate_audio(foreign)
        print("Generating sentence audio...")
        audio_sentence = self.generate_audio(line.strip().replace('*', ''), is_sentence=True)
        
        # Generate image
        print("Generating image...")
        image = self.generate_image(line.strip().replace('*', ''))
        
        # Get expanded meaning
        print("Getting expanded meaning...")
        expanded_meaning = self.get_expanded_meaning(foreign)
        
        # Create note in the format matching sample.txt
        guid = f"card_{len(self.notes)}_{random.randrange(1 << 30, 1 << 31)}"
        note = {
            'guid': guid,
            'notetype': 'Dollar_Type',
            'deck': 'English',
            'fields': [
                foreign,                 # Foreign
                foreign_sentence,        # Foreign Sentence with highlighting
                russian,                 # Russian
                russian_sentence,        # Russian Sentence with italic
                audio,                   # Audio
                audio_sentence,          # Audio Sentence
                expanded_meaning,        # Expanded Meaning
                image,                   # Image
                "",                      # Url
                "",                      # frequencies
                "openAI"                # Tags
            ]
        }
        
        self.notes.append(note)
        print("Note created successfully!")

    def generate_cards(self, input_file):
        # Process all lines
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    self.process_line(line)
        
        # Export notes in the format matching sample.txt
        output_file = 'vocabulary_cards.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write headers
            f.write("#separator:tab\n")
            f.write("#html:true\n")
            f.write("#guid column:1\n")
            f.write("#notetype column:2\n")
            f.write("#deck column:3\n")
            f.write("#tags column:15\n")
            
            # Write notes
            for note in self.notes:
                fields = '\t'.join(note['fields'])
                line = f"{note['guid']}\t{note['notetype']}\t{note['deck']}\t{fields}\n"
                f.write(line)
        
        return len(self.notes)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate Anki cards with OpenAI integration')
    parser.add_argument('--api-key', '-k', 
                      help='OpenAI API key (optional, can use OPENAI_API_KEY environment variable)')
    parser.add_argument('--input', '-i',
                      default='input.md',
                      help='Input file path (default: input.md)')
    parser.add_argument('--generate-media', '-m',
                      action='store_true',
                      default=False,
                      help='Generate images (default: False)')
    
    args = parser.parse_args()
    
    # Get API key from command line or environment variable
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\nError: OpenAI API key is required!")
        print("Either set OPENAI_API_KEY environment variable or provide --api-key parameter")
        print("\nExample usage:")
        print("  python anki_card_generator.py --input words.md")
        print("  python anki_card_generator.py --input words.md --generate-media")
        print("  python anki_card_generator.py --api-key sk-... --input words.md")
        exit(1)
    
    generator = AnkiCardGenerator(api_key)
    generator.generate_media = args.generate_media
    num_cards = generator.generate_cards(args.input)
    
    print(f"""\nSuccess! Generated {num_cards} notes!

Instructions:
1. Open Anki
2. File -> Import
3. Select the generated file 'vocabulary_cards.txt'
4. Make sure to select:
   - Type: 'Dollar_Type'
   - Deck: 'English'
   - Fields separated by: Tab
   - Allow HTML in fields
5. Click Import""") 