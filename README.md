# dutch-frequency-analyzer

A tool that:

- Can analyze text of a book and interactively generate a list of known and
  unknown words
  - Every word is turned into its base form (i.e. deconjugated)
  - The interactive process will repeat until a certain threshold of frequency
    is reached or until the checked words cover over 95% of all the words used in
    the book.
- Can generate an Anki deck with sentences that contain the unknown words
  - All sentences are ordered in i+1 (also known as 1T) fashion, i.e. the tool
    will make sure that the sentences consist of only known words, with the only
    unknown word in the sentence being the target word itself. It will make
    use of the generated known words file to do that.
  - The tool lets you select an appropriate sentence (it shows the simplest
    sentences first).
  - The tool will also translate the sentence for you, either by grabbing the
    translation from Reverso or requesting it from DeepL.
  - After a sentence is selected, the tool will request a text-to-speech audio
    of that sentence from Azure's cutting edge TTS service.

# Documentation

TBD
