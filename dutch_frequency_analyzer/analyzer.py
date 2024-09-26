import click
import nltk
from nltk.corpus import stopwords
from .shared import (
    get_model,
    lemmatize,
    load_known_words,
    load_unknown_words,
    add_known_word,
    load_dictionary,
    justify,
)

nltk.download("stopwords", quiet=True)

stopword_list = stopwords.words("dutch")


@click.command()
@click.argument("file-name")
@click.option("--known-words-file", default="known.txt")
@click.option("--unknown-words-file", default="unknown.txt")
def analyzer(file_name, known_words_file, unknown_words_file):
    try:
        file = open(file_name, "r")
    except IOError:
        click.echo(f"Unable to open {file_name}")
        return

    nlp = get_model()
    known_words = load_known_words(known_words_file)
    dutch_dictionary = load_dictionary()
    word_map = {}
    total = 0
    num_lines = sum(1 for _ in open(file_name))

    with file:
        with click.progressbar(
            file,
            label=f"Analyzing contents",
            length=num_lines,
        ) as bar:
            for line in bar:
                line = line.lower()
                for lemma in lemmatize(nlp, line):
                    lemma = lemma.lower()
                    if not is_allowed_word(lemma, dutch_dictionary, known_words):
                        continue

                    if lemma not in word_map:
                        word_map[lemma] = 0

                    word_map[lemma] += 1
                    total += 1

    result_total = 0
    unknown_words = load_unknown_words(unknown_words_file)

    for index, (word, frequency) in enumerate(
        sorted(
            word_map.items(),
            key=lambda entry: entry[1],
            reverse=True,
        )
    ):
        if result_total / total > 0.95 or frequency <= 4:
            return

        result_total += frequency

        if word in unknown_words:
            continue

        click.clear()

        click.echo("Known words:".ljust(justify), nl=False)
        click.echo(len(known_words))

        click.echo("Unknown words:".ljust(justify), nl=False)
        click.echo(len(unknown_words))

        click.echo("Words found in file:".ljust(justify), nl=False)
        click.echo(len(word_map))

        click.echo()

        click.echo("Word:".ljust(justify), nl=False)
        click.echo(word)

        click.echo("Frequency:".ljust(justify), nl=False)
        click.echo(frequency)

        click.echo("Index:".ljust(justify), nl=False)
        click.echo(index + 1)

        click.echo()

        click.echo(f"k: mark '{word}' as known")
        click.echo(f"u: mark '{word}' as unknown")
        click.echo(f"a: abort the operation and exit the program (progress is saved)")

        action = click.prompt(
            "Action",
            type=click.Choice(("k", "u", "a"), case_sensitive=False),
        )

        match action:
            case "k":
                add_known_word(known_words_file, word, known_words)

            case "u":
                add_unknown_word(unknown_words_file, word, frequency, unknown_words)

            case "a":
                return


def add_unknown_word(unknown_words_file_name, word, frequency, unknown_words):
    with open(f"./{unknown_words_file_name}", "a") as f:
        f.write(f"{word} {frequency}\n")
        unknown_words[word] = frequency


def is_allowed_word(word, dictionary, known_words):
    return (
        word not in stopword_list
        and word.isalpha()
        and word not in known_words
        and word in dictionary
    )
