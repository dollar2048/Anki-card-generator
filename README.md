# Anki Card Generator

A script for automatically generating Anki cards from a markdown file with bold-highlighted words/phrases.

## Features

- Creates Anki cards from a markdown file
- Automatically translates words and sentences to Russian
- Generates audio pronunciation for words and sentences
- Creates images for sentences
- Adds expanded word explanations in Russian

## Card Structure

Each card contains the following fields:
1. Foreign - English word/phrase (bold-highlighted or entire sentence)
2. Foreign Sentence - original sentence
3. Russian - translation of the word/phrase to Russian
4. Russian Sentence - translation of the sentence to Russian
5. Audio - audio pronunciation of the word/phrase
6. Audio Sentence - audio pronunciation of the sentence
7. Expanded Meaning - extended explanation in Russian
8. Image - generated image
9. Url - (empty)
10. frequencies - (empty)
11. Tags - "openAPI" tag

## Requirements

- Python 3.x
- OpenAI API key
- Anki installed

## Installation

1. Clone the repository:
```bash
git clone [repository url]
cd Anki-card-generator
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Set your OpenAI API key environment variable:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Usage

1. Create an `input.md` file with sentences where target words are in bold:
```markdown
I'll give our **daughter** a ride
She was **kind** and polite
```

2. Run the script:
```bash
python3 anki_card_generator.py
```

3. Copy the generated audio files to your Anki media folder:
```bash
cp anki_media/*.mp3 "/Users/[your_username]/Library/Application Support/Anki2/[anki_profile]/collection.media/"
```

4. Import the cards into Anki:
   - Open Anki
   - File -> Import
   - Select `anki_cards.txt`
   - Set card type to "Basic"
   - Set field separator to "Tab"
   - Match fields with your card template
   - Click Import

## Project Structure

- `anki_card_generator.py` - main script
- `input.md` - input file with sentences
- `anki_media/` - folder with audio files
- `anki_cards.txt` - generated file for Anki import
- `requirements.txt` - Python dependencies

## Notes

- The script uses OpenAI API for translations and image generation
- Audio is generated using OpenAI TTS API
- All media files are saved in the `anki_media` folder
- Output file format is tab-separated text

## Troubleshooting

1. If Anki media folder path is different:
   - Find the correct path in Anki settings
   - Modify the file copy command accordingly

2. If API key is not set:
   - Make sure OPENAI_API_KEY environment variable is set
   - Verify API key validity

## License

MIT 