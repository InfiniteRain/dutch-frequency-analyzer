import click
import genanki
import random
import time
from .shared import load_sentences, term_lookup

template_front_file_name = "assets/front.html"
template_back_file_name = "assets/back.html"
template_style_file_name = "assets/style.css"


with open(template_front_file_name, "r") as file:
    front = file.read()

with open(template_back_file_name, "r") as file:
    back = file.read()

with open(template_style_file_name, "r") as file:
    style = file.read()

model_id = 1553975981
model = genanki.Model(
    model_id,
    "Generated Dutch Sentence",
    fields=[
        {"name": "Sentence"},
        {"name": "Sentence Translation"},
        {"name": "Word"},
        {"name": "Word Definition"},
        {"name": "Sentence Audio"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": front,
            "afmt": back,
        }
    ],
    css=style,
)

output_deck_file_name = "out.deck.apkg"
wiktionary_request_backoff = 0.66  # in seconds


@click.command()
@click.argument("input-dir")
@click.argument("deck-name")
@click.argument("output-dir", default=".")
def generator(input_dir, deck_name, output_dir):
    sentences = load_sentences(input_dir, extended=True)

    deck = genanki.Deck(random.randrange(1 << 30, 1 << 31), deck_name)
    package = genanki.Package(deck)
    package.media_files = []

    with click.progressbar(
        sentences, label="Generating deck", length=len(sentences), show_pos=True
    ) as bar:
        for sentence in bar:
            time.sleep(wiktionary_request_backoff)
            sentence = sentences[sentence]
            package.media_files.append(f"{input_dir}/{sentence["audio"]}")
            deck.add_note(
                genanki.Note(
                    model=model,
                    fields=[
                        sentence["sentence"],
                        sentence["translation"],
                        sentence["word"],
                        get_definition_html(sentence["word"]),
                        f"[sound:{sentence["audio"]}]",
                    ],
                )
            )

    package.write_to_file(f"{output_dir}/out.deck.apkg")


def get_definition_html(term):
    etimologies = term_lookup(term)

    if etimologies is None:
        return ""

    html = ""

    for etimology_index, etimology in enumerate(etimologies):
        html += f'<div class="etimology">Etimology {etimology_index + 1}</div><ul>'

        for definition in etimology:
            html += "<li>"

            for line in definition["text"].split("\n"):
                html += f"<div>{line.strip()}</div>"

            if "form_words" in definition:
                for form_word in definition["form_words"]:
                    for form_etimology_index, form_itemology in enumerate(
                        form_word["etimologies"]
                    ):
                        html += f'<div><div class="etimology">Etimology {form_etimology_index + 1} for {form_word["text"]}</div><ul>'

                        for form_definition in form_itemology:
                            html += "<li>"

                            for line in form_definition["text"].split("\n"):
                                html += f"<div>{line.strip()}</div>"

                            html += "</li>"

                        html += "</ul></div>"

            html += "</li>"

        html += "</ul>"

    return html
