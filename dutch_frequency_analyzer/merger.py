import click
from .shared import get_model, lemmatize, load_known_words, add_known_word


@click.command()
@click.argument("deck-file")
@click.argument("known-words-file")
def merger(deck_file, known_words_file):
    nlp = get_model()

    sentences = load_deck_sentences(deck_file)
    known_words = load_known_words(known_words_file)
    new_words = 0

    for sentence in sentences:
        for lemma in lemmatize(nlp, sentence):
            if not lemma.isalpha():
                continue

            if lemma not in known_words:
                add_known_word(known_words_file, lemma, known_words)
                new_words += 1

    click.echo(f"Added {new_words} words into the known words file.")


def load_deck_sentences(deck_file_name):
    sentences = []

    with open(deck_file_name) as file:
        for line in file:
            line = line.strip()

            if line == "" or line[0] == "#":
                continue

            sentences.append(line.split("\t", 1)[0].strip().lower())

    return sentences
