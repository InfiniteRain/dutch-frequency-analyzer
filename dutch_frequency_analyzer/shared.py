import subprocess
import spacy
import json

spacy_model_name = "nl_core_news_lg"
dictionary_file_name = "dutch-dictionary.json"
default_known_words_file_name = "known.txt"
justify = 25


def lemmatize(nlp: spacy.language.Language, text):
    text = text.replace("\n", "").strip()
    docs = nlp.pipe([text])
    cleaned_lemmas = [[t.lemma_ for t in doc] for doc in docs]
    return cleaned_lemmas[0]


def get_model():
    try:
        return spacy.load(spacy_model_name)
    except IOError:
        subprocess.run(["spacy", "download", spacy_model_name])
        return spacy.load(spacy_model_name)


def load_known_words(known_words_file_name):
    known_words = set()

    try:
        file = open(known_words_file_name)
    except IOError:
        return known_words

    with file:
        for line in file:
            line = line.strip()

            if line == "":
                continue

            known_words.add(line)

    return known_words


def load_unknown_words(unknown_words_file_name):
    words = {}

    try:
        file = open(unknown_words_file_name)
    except IOError:
        return words

    with file:
        for line in file:
            line = line.strip()

            if line == "":
                continue

            split = line.split(" ")
            words[split[0]] = split[1]

    return words


def add_known_word(known_words_file_name, word, known_words):
    if word in known_words:
        return

    with open(f"./{known_words_file_name}", "a") as f:
        f.write(f"{word}\n")
        known_words.add(word)


def load_dictionary():
    with open(dictionary_file_name, "r") as f:
        return json.load(f)
