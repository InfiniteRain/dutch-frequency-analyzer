import os
import click
import nltk
import deepl
import uuid
import azure.cognitiveservices.speech as speechsdk
from .reverso import ReversoContextAPI
from nltk.corpus import stopwords
from .shared import (
    get_model,
    load_known_words,
    load_unknown_words,
    default_known_words_file_name,
    add_known_word,
    justify,
    term_lookup,
    load_sentences,
    output_file_name,
)
from typing import Dict, Tuple, List
from pathlib import Path

nltk.download("stopwords", quiet=True)

stopword_list = stopwords.words("dutch")
sentence_limit = 250
deepl_translator = deepl.Translator(os.environ.get("DEEPL_KEY") or "")
deepl_cache_file_name = ".deepl_cache.txt"
speech_config = speechsdk.SpeechConfig(
    subscription=os.environ.get("SPEECH_KEY"),
    region=os.environ.get("SPEECH_REGION"),
)
speech_config.speech_synthesis_voice_name = "nl-NL-MaartenNeural"
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Audio24Khz96KBitRateMonoMp3
)
indent = " " * 4


@click.command()
@click.argument("word-list")
@click.argument("output-dir")
@click.option("--resume/--no-resume", default=False, type=bool)
@click.option("--known-words-file", default=default_known_words_file_name)
def finder(word_list, output_dir, resume, known_words_file):
    if not resume and os.path.isdir(output_dir):
        click.echo(f"Directory '{output_dir}' already exists.")
        click.echo("Use --resume to continue earlier execution.")
        return

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    nlp = get_model()

    known_words = load_known_words(known_words_file)
    unknown_words = list(load_unknown_words(word_list).keys())
    existing_sentences = load_sentences(output_dir)
    deepl_cache = load_deepl_cache()

    for index, word in enumerate(unknown_words):
        if word in existing_sentences or word in known_words:
            continue

        candidates = find_candidates(nlp, word, known_words, existing_sentences)

        if len(candidates) == 0:
            continue

        current_index = 0
        deepl_translation = None
        etimologies = term_lookup(word)

        while True:
            sentence, translation, analysis = candidates[current_index]

            if deepl_translation is not None:
                translation = deepl_translation

            click.clear()

            click.echo("Known words:".ljust(justify), nl=False)
            click.echo(len(known_words))

            click.echo("Unknown words:".ljust(justify), nl=False)
            click.echo(len(unknown_words))

            click.echo("Generated sentences:".ljust(justify), nl=False)
            click.echo(len(existing_sentences))

            click.echo()
            click.echo("Word:".ljust(justify), nl=False)
            click.echo(f"{word} ({index + 1} out of {len(unknown_words)})")

            click.echo(f"Sentence:".ljust(justify), nl=False)

            last_text = None
            for text, text_analysis in analysis:
                fg = None

                match text_analysis:
                    case "unknown":
                        fg = "red"

                    case "future":
                        fg = "yellow"

                if (
                    last_text is not None
                    and (text == "(" or text[0].isalnum())
                    and last_text != "("
                ):
                    click.echo(" ", nl=False)

                click.secho(f"{text}", nl=False, fg=fg)
                last_text = text

            click.echo()

            click.echo(
                f"{'DeepL' if deepl_translation is not None else 'Reverso'} translation:".ljust(
                    justify
                ),
                nl=False,
            )
            click.echo(translation)

            click.echo("Candidate:".ljust(justify), nl=False)
            click.echo(f"{current_index + 1} out of {len(candidates)}")
            click.echo()

            if etimologies is not None:
                for etimology_index, etimology in enumerate(etimologies):
                    click.echo(f"Etimology {etimology_index + 1}:")

                    for definition_index, definition in enumerate(etimology):
                        click.echo(
                            f"{indent}- {definition["text"].replace("\n", f"\n{indent}  ")}"
                        )

                        if "form_words" not in definition:
                            continue

                        click.echo()

                        for form_word in definition["form_words"]:
                            for form_etimology_index, form_itemology in enumerate(
                                form_word["etimologies"]
                            ):
                                click.echo(
                                    f"{indent}  Etimology {form_etimology_index + 1} for {form_word["text"]}:"
                                )

                                for form_definition in form_itemology:
                                    click.echo(
                                        f"{indent}{indent}  - {form_definition["text"]}"
                                    )

                        if definition_index != len(etimology) - 1:
                            click.echo()

                click.echo()

            click.echo("y: accept the proposed candidate, go to the next word")
            click.echo("n: next suggestion for this word")
            click.echo("p: previous suggestion for this word")
            click.echo("t: swap between Reverso and DeepL translation")
            click.echo("k: mark word as known")
            click.echo(
                "a: abort the operation and exit the program (progress is saved)"
            )

            action = click.prompt(
                "Action",
                type=click.Choice(("y", "n", "p", "t", "k", "a"), case_sensitive=False),
            )

            match action:
                case "y":
                    output_sentence(
                        output_dir, word, sentence, translation, existing_sentences
                    )
                    click.echo()
                    break

                case "n":
                    current_index = (current_index + 1) % len(candidates)
                    deepl_translation = None

                case "p":
                    current_index -= 1
                    deepl_translation = None

                    if current_index < 0:
                        current_index = len(candidates) - 1

                case "t":
                    if deepl_translation is None:
                        deepl_translation = deepl_translate(sentence, deepl_cache)
                    else:
                        deepl_translation = None

                case "k":
                    add_known_word(known_words_file, word, known_words)
                    break

                case "a":
                    return

            click.echo()

    click.echo("Done!")


def find_candidates(nlp, word, known_words, existing_sentences):
    example_sentences: Dict[str, Tuple[str, int, List[Tuple[str, str]]]] = {}
    dupes = 0
    iters = 0
    api = ReversoContextAPI(word, "", "nl", "en")
    best_found = 0

    for source, target in api.get_examples():
        if dupes >= 20:
            break

        if source.text in example_sentences:
            dupes += 1
            continue

        score, result = analyze_sentence(
            nlp,
            source.text,
            known_words,
            existing_sentences,
        )
        example_sentences[source.text] = (target.text, score, result)

        if score == 1:
            best_found += 1

        if best_found >= 10:
            break

        iters += 1

        if iters >= 300:
            break

    return [
        (s.replace("\t", " "), t.replace("\t", " "), a)
        for s, (t, _, a) in sorted(
            example_sentences.items(), key=lambda entry: (entry[1][1], len(entry[0]))
        )
    ]


def analyze_sentence(nlp, sentence, known_words, existing_sentences):
    unknown_count = 0
    result = []

    for lemma, text in lemmatize_and_map_text(nlp, sentence):
        if not lemma.isalpha():
            result.append((text, "known"))
            continue

        word_analysis = analyze_word(lemma, known_words, existing_sentences)

        if word_analysis == "unknown":
            unknown_count += 1

        result.append((text, word_analysis))

    return (unknown_count, result)


def analyze_word(word, known_words, existing_sentences):
    if word in known_words or word in stopword_list:
        return "known"

    if word in existing_sentences:
        return "future"

    return "unknown"


def load_deepl_cache():
    cache = {}

    try:
        file = open(deepl_cache_file_name, "r")
    except IOError:
        return cache

    with file:
        for line in file:
            line = line.strip()

            if line == "":
                continue

            split = line.split("\t")
            cache[split[0]] = split[1]

    return cache


def deepl_translate(sentence, deepl_cache):
    if sentence in deepl_cache:
        return deepl_cache[sentence]

    result: deepl.TextResult = deepl_translator.translate_text(
        sentence,
        source_lang="NL",
        target_lang="EN-US",
    )  # type: ignore
    translation = result.text.replace("\t", " ")
    deepl_cache[sentence] = translation

    with open(deepl_cache_file_name, "a") as file:
        file.write(f"{sentence}\t{translation}\n")

    return translation


def output_sentence(output_dir, word, sentence, translation, existing_sentences):
    audio_file_name = f"{uuid.uuid4()}.mp3"
    full_audio_file_name = f"{output_dir}/{audio_file_name}"
    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=full_audio_file_name
    )  # type: ignore
    speech_synth = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )

    synth_result = speech_synth.speak_text_async(sentence).get()

    if synth_result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:  # type: ignore
        raise Exception("Speech synthesis failed.")

    existing_sentences[word] = sentence

    with open(f"{output_dir}/{output_file_name}", "a") as file:
        file.write(f"{word}\t{sentence}\t{translation}\t{audio_file_name}\n")


def lemmatize_and_map_text(nlp, text):
    text = text.replace("\n", "").strip()
    docs = nlp.pipe([text])
    cleaned_lemmas = [[(t.lemma_, t.text) for t in doc] for doc in docs]
    return cleaned_lemmas[0]
