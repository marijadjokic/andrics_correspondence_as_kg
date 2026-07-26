from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, XSD

from .utils import canonical_label, make_slug

SCHEMA = Namespace("https://schema.org/")
PROV = Namespace("http://www.w3.org/ns/prov#")

TYPE_TO_SCHEMA = {
    "PER": SCHEMA.Person,
    "LOC": SCHEMA.Place,
    "ORG": SCHEMA.Organization,
    "WORK": SCHEMA.CreativeWork,
    "PUBLICATION": SCHEMA.CreativeWork,
    "DATE": SCHEMA.Date,
    "MISC": SCHEMA.Thing,
}


def _lit(value: Any, lang: str | None = None, datatype=None):
    if value is None or value == "":
        return None
    return Literal(value, lang=lang, datatype=datatype)


def build_rdf_graph(
    letters: List[Dict[str, Any]],
    entities: List[Dict[str, Any]],
    mentions: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Graph:
    project_cfg = config.get("project", {})
    extraction_cfg = config.get("extraction", {})
    base_uri = project_cfg.get("base_uri", "https://example.org/andric-letters/")
    lang = project_cfg.get("language", "sr-Latn")
    keep_text = bool(extraction_cfg.get("keep_transcription_text_in_rdf", True))

    EX = Namespace(base_uri)
    g = Graph()
    g.bind("andric", EX)
    g.bind("schema", SCHEMA)
    g.bind("dcterms", DCTERMS)
    g.bind("prov", PROV)
    g.bind("foaf", FOAF)
    g.bind("owl", OWL)
    g.bind("skos", SKOS)
    g.bind("xsd", XSD)

    collection_uri = EX[project_cfg.get("collection_id", "collection")]
    g.add((collection_uri, RDF.type, SCHEMA.Collection))
    if project_cfg.get("collection_label"):
        g.add((collection_uri, RDFS.label, Literal(project_cfg["collection_label"], lang=lang)))
    if project_cfg.get("source_label"):
        g.add((collection_uri, DCTERMS.source, Literal(project_cfg["source_label"], lang=lang)))

    # Entity index
    entity_uri_by_key: Dict[tuple[str, str], URIRef] = {}
    for ent in entities:
        label = canonical_label(ent.get("label", ""))
        typ = (ent.get("type", "MISC") or "MISC").upper()
        if not label:
            continue
        uri = EX["entity/" + make_slug(f"{typ}_{label}")]
        entity_uri_by_key[(label.lower(), typ)] = uri
        ent["entity_id"] = str(uri)
        g.add((uri, RDF.type, TYPE_TO_SCHEMA.get(typ, SCHEMA.Thing)))
        g.add((uri, RDFS.label, Literal(label, lang=lang)))
        g.add((uri, DCTERMS.type, Literal(typ)))
        if ent.get("wikidata_uri"):
            g.add((uri, SKOS.exactMatch, URIRef(ent["wikidata_uri"])))
            g.add((uri, DCTERMS.source, URIRef(ent["wikidata_uri"])))

    def entity_uri(label: str, typ: str) -> URIRef:
        key = (canonical_label(label).lower(), typ.upper())
        if key in entity_uri_by_key:
            return entity_uri_by_key[key]
        uri = EX["entity/" + make_slug(f"{typ}_{label}")]
        entity_uri_by_key[key] = uri
        g.add((uri, RDF.type, TYPE_TO_SCHEMA.get(typ.upper(), SCHEMA.Thing)))
        g.add((uri, RDFS.label, Literal(canonical_label(label), lang=lang)))
        g.add((uri, DCTERMS.type, Literal(typ.upper())))
        return uri

    # Letters
    for letter in letters:
        letter_uri = EX["letter/" + make_slug(letter.get("letter_id", "letter"))]
        g.add((letter_uri, RDF.type, EX.Letter))
        g.add((letter_uri, RDF.type, SCHEMA.Message))
        g.add((letter_uri, DCTERMS.isPartOf, collection_uri))
        g.add((letter_uri, DCTERMS.identifier, Literal(letter.get("letter_id", ""))))

        if letter.get("source_page_files"):
            g.add((letter_uri, PROV.hadPrimarySource, Literal(letter["source_page_files"])))
        if letter.get("source_pages"):
            g.add((letter_uri, SCHEMA.pagination, Literal(letter["source_pages"])))
        if letter.get("date_iso"):
            g.add((letter_uri, SCHEMA.dateSent, Literal(letter["date_iso"], datatype=XSD.date)))
        if keep_text and letter.get("text"):
            g.add((letter_uri, SCHEMA.text, Literal(letter["text"], lang=lang)))

        sender = canonical_label(letter.get("sender", ""))
        if sender:
            sender_uri = entity_uri(sender, "PER")
            g.add((letter_uri, SCHEMA.sender, sender_uri))

        recipient = canonical_label(letter.get("recipient", ""))
        if recipient:
            recipient_uri = entity_uri(recipient, "PER")
            g.add((letter_uri, SCHEMA.recipient, recipient_uri))

        place = canonical_label(letter.get("place_written", ""))
        if place:
            place_uri = entity_uri(place, "LOC")
            g.add((letter_uri, SCHEMA.locationCreated, place_uri))

    # Mentions
    for idx, mention in enumerate(mentions, start=1):
        label = canonical_label(mention.get("text", ""))
        typ = (mention.get("label", "MISC") or "MISC").upper()
        if not label:
            continue
        letter_uri = EX["letter/" + make_slug(mention.get("letter_id", "letter"))]
        ent_uri = entity_uri(label, typ)
        mention_uri = EX[f"mention/{make_slug(mention.get('letter_id','letter'))}/{idx}"]

        g.add((letter_uri, SCHEMA.mentions, ent_uri))
        g.add((letter_uri, EX.hasMention, mention_uri))
        g.add((mention_uri, RDF.type, EX.EntityMention))
        g.add((mention_uri, EX.mentionOf, ent_uri))
        g.add((mention_uri, EX.mentionText, Literal(label, lang=lang)))
        g.add((mention_uri, DCTERMS.type, Literal(typ)))
        if mention.get("start") is not None:
            g.add((mention_uri, EX.startOffset, Literal(int(mention["start"]), datatype=XSD.integer)))
        if mention.get("end") is not None:
            g.add((mention_uri, EX.endOffset, Literal(int(mention["end"]), datatype=XSD.integer)))
        if mention.get("score") is not None:
            try:
                g.add((mention_uri, EX.confidence, Literal(float(mention["score"]), datatype=XSD.float)))
            except ValueError:
                pass
        if mention.get("model"):
            g.add((mention_uri, PROV.wasGeneratedBy, Literal(mention["model"])))

    return g


def serialize_graph(g: Graph, output_dir: str | Path, ttl_name: str, jsonld_name: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    g.serialize(out / ttl_name, format="turtle")
    g.serialize(out / jsonld_name, format="json-ld", indent=2)
