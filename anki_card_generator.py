import re
import json
from openai import OpenAI
import base64
import os
import random
import argparse
from tqdm import tqdm  # For progress indication
import requests
from striprtf.striprtf import rtf_to_text  # Add RTF support
import pypandoc
from bs4 import BeautifulSoup

class AnkiCardGenerator:
    def __init__(self, api_key, source_lang="English", target_lang="Russian"):
        self.client = OpenAI(
            api_key=api_key
        )
        self.generate_media = False
        self.source_lang = source_lang
        self.target_lang = target_lang
        # Create media directory if it doesn't exist
        self.media_dir = os.path.join(os.getcwd(), "anki_media")
        os.makedirs(self.media_dir, exist_ok=True)
        print(f"Media directory: {self.media_dir}")
        
        # List to store media files
        self.media_files = []
        
        # Store notes for later export
        self.notes = []
        
    def extract_italic_text(self, line):
        # Change pattern to look for bold text instead of italic
        bold_pattern = r'\*\*(.*?)\*\*'
        matches = re.findall(bold_pattern, line)
        return matches if matches else [line.strip()]
    
    def translate_text(self, text, is_sentence=False):
        if is_sentence:
            prompt = f"Translate the following sentence from {self.source_lang} to {self.target_lang}: {text}"
        else:
            prompt = f"Translate this {self.source_lang} word/phrase to {self.target_lang}. Give ONLY the shortest possible translation, no explanations: {text}"
            
        response = self.client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    
    def get_expanded_meaning(self, word):
        prompt = f"Give a short explanation in {self.target_lang} for the {self.source_lang} word/phrase: {word}"
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
                input=text,
                speed=0.8  # Slower speech rate
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
        
        bold_texts = self.extract_italic_text(line)

        # If only one word/phrase is in bold
        if len(bold_texts) == 1 and bold_texts[0] == line.strip().replace('**', ''):
            foreign = bold_texts[0]
            russian = self.translate_text(foreign)  # Translate only the highlighted word
            
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
                    "",                      # Russian Sentence with bold
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
            
        # If there is no bold text in the sentence
        if not bold_texts:
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
                    "",                      # Russian Sentence with bold
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
            
        print("\nIt's a sentence with bold text")

        # Original logic for sentences with bold text
        foreign = bold_texts[0] if bold_texts else line.strip()
        
        # Replace markdown with HTML for highlighting
        foreign_sentence = line.strip()
        for bold_text in bold_texts:
            foreign_sentence = foreign_sentence.replace(
                f"**{bold_text}**",
                f'<span style="color: rgb(234, 78, 0);"><b>{bold_text}</b></span>'
            )
        
        # Translate only the highlighted word/phrase
        print("Generating translations...")
        russian = self.translate_text(foreign)
        
        # Translate the whole sentence
        print("Formatting Russian sentence...")
        russian_sentence_full = self.translate_text(line.strip().replace('**', ''), is_sentence=True)
        # Highlight the translation of the bold word in the translated sentence
        if russian and russian in russian_sentence_full:
            russian_sentence = russian_sentence_full.replace(russian, f'<b>{russian}</b>')
        else:
            russian_sentence = russian_sentence_full
        
        # Generate audio files
        print("Generating word audio...")
        audio = self.generate_audio(foreign)
        print("Generating sentence audio...")
        audio_sentence = self.generate_audio(line.strip().replace('**', ''), is_sentence=True)
        
        # Generate image
        print("Generating image...")
        image = self.generate_image(line.strip().replace('**', ''))
        
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
                russian,                 # Russian (only highlighted word)
                russian_sentence,        # Russian Sentence (whole sentence, highlighted word in bold)
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

    def extract_bold_from_rtf(self, rtf_content):
        html = pypandoc.convert_text(rtf_content, 'html', format='rtf')
        soup = BeautifulSoup(html, 'html.parser')
        lines = []
        for p in soup.find_all(['p', 'div']):
            line = ''
            for elem in p.children:
                if getattr(elem, 'name', None) in ['b', 'strong']:
                    line += f"**{elem.get_text()}**"
                elif getattr(elem, 'name', None) == 'span' and elem.has_attr('style') and 'bold' in elem['style']:
                    line += f"**{elem.get_text()}**"
                elif elem.name is None:
                    line += str(elem)
            if line.strip():
                lines.append(line.strip())
        print("DEBUG RTF->MD:", lines)
        return '\n'.join(lines)

    def generate_cards(self, input_file):
        # Process all lines
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check if file is RTF
            if input_file.lower().endswith('.rtf'):
                try:
                    content = self.extract_bold_from_rtf(content)
                except Exception as e:
                    print(f"Error parsing RTF: {e}")
                    content = ''
            
            # Split content into lines and process
            for line in content.splitlines():
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
                      default='input.rtf',
                      help='Input file path (default: input.rtf). Supports .md and .rtf files')
    parser.add_argument('--generate-media', '-m',
                      action='store_true',
                      default=False,
                      help='Generate images (default: False)')
    parser.add_argument('--source-lang', '-s',
                      default='English',
                      help='Source language (default: English)')
    parser.add_argument('--target-lang', '-t',
                      default='Russian',
                      help='Target language (default: Russian)')
    
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
        print("  python anki_card_generator.py --source-lang German --target-lang French --input words.md")
        exit(1)
    
    generator = AnkiCardGenerator(api_key, args.source_lang, args.target_lang)
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