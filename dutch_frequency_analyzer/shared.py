import subprocess
import spacy
import urllib.parse
import requests
from bs4 import BeautifulSoup

spacy_model_name = "nl_core_news_lg"
default_known_words_file_name = "known.txt"
justify = 25
wiktionary_api = "https://en.wiktionary.org/api/rest_v1/page/definition"


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


def term_lookup(term, lookup_form=True):
    encoded_term = urllib.parse.quote_plus(term.lower())
    request = requests.get(f"{wiktionary_api}/{encoded_term}")

    if request.status_code != 200:
        return None

    response_json = request.json()

    if "nl" not in response_json:
        return None

    out_etimologies = []

    for etimology in response_json["nl"]:
        out_definitions = []

        for definition in etimology["definitions"]:
            soup = BeautifulSoup(definition["definition"], "html.parser")
            definition_text = soup.get_text().strip()

            if definition_text == "":
                continue

            spans = soup.find_all("span", class_="form-of-definition-link")
            out_form_words = []
            out_examples = []

            if lookup_form:
                for span in spans:
                    previous_text = str(span.find_previous_sibling(string=True)).strip()

                    if previous_text[-2:] != "of":
                        continue

                    link = span.find("a")

                    if link is None:
                        continue

                    href = link["href"]

                    if href[-6:] != "#Dutch":
                        continue

                    form_word = link.get_text().strip()

                    # circular definition
                    if form_word == term:
                        continue

                    form_word_etimologies = term_lookup(
                        link.get_text().strip(), lookup_form=False
                    )

                    if form_word_etimologies is None:
                        continue

                    out_form_words.append(
                        {
                            "text": form_word,
                            "etimologies": form_word_etimologies,
                        }
                    )

            if "parsedExamples" in definition:
                for example in definition["parsedExamples"]:
                    out_example = {}

                    if "example" in example:
                        out_example["text"] = (
                            BeautifulSoup(example["example"], "html.parser")
                            .get_text()
                            .strip()
                        )

                    if "translation" in example:
                        out_example["translation"] = (
                            BeautifulSoup(example["translation"], "html.parser")
                            .get_text()
                            .strip()
                        )

                    if len(out_example) > 0:
                        out_examples.append(out_example)

            out_definition: dict = {
                "text": definition_text,
            }

            if len(out_examples) > 0:
                out_definition["examples"] = out_examples

            if len(out_form_words) > 0:
                out_definition["form_words"] = out_form_words

            out_definitions.append(out_definition)

        out_etimologies.append(out_definitions)

    return out_etimologies
