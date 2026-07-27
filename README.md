# Andrić Letters → Knowledge Graph

This repository contains a semi-automatic technical pipeline for transforming a selected subset of Ivo Andrić’s correspondence into RDF/Linked Data.

The workflow starts from selected PDF pages of printed correspondence and produces structured letter records, named entity annotations, Wikidata-enriched entity tables, RDF/Turtle and JSON-LD files, SPARQL query results, and graph visualizations.

The intended workflow is:

```text
Selected PDF pages
→ Transkribus OCR/ATR
→ PAGE XML export
→ letter segmentation
→ NER-based entity extraction
→ post-processing and entity normalization
→ correspondence metadata correction
→ selective Wikidata linking
→ RDF/Turtle + JSON-LD generation
→ SPARQL queries + graph visualization
```

## 1. Installation

Create and activate a Python virtual environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\activate
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

If import errors occur when running scripts from the project root, set the Python path manually.

On Windows PowerShell:

```powershell
$env:PYTHONPATH = (Get-Location).Path
```

On Linux/macOS:

```bash
export PYTHONPATH=$(pwd)
```

For interactive HTML network visualization, install PyVis if it is not already included:

```bash
pip install pyvis
```

## 2. Prepare pages for Transkribus

If only selected pages from the source PDF should be processed, first extract them into a separate PDF file. The extraction script and page range are configured in `config.yaml`.

Example:

```bash
python .\scripts\00_extract_pdf_pages.py --config config.yaml
```

The resulting file should be uploaded to Transkribus. In Transkribus, run layout analysis and text recognition. In this project, the Transkribus model **Burgenland Croatian Typewritten 2010–2019** was used because it produced the best OCR/ATR results for the selected printed correspondence pages containing mixed Latin and Cyrillic material.

After OCR/ATR and light manual correction, export the result from Transkribus as PAGE XML.

Place the exported PAGE XML files into:

```text
data/transkribus/pagexml/
```

The expected structure is:

```text
data/
  transkribus/
    pagexml/
      0001_p001.xml
      0002_p002.xml
      ...
```

## 3. Run the pipeline

The complete pipeline can be run step by step. This is the recommended option, because each stage can be inspected and corrected if needed.

```bash
python .\scripts\01_pagexml_to_letters.py --config config.yaml
python .\scripts\02_run_ner.py --config config.yaml
python .\scripts\02b_clean_mentions.py
python .\scripts\03_enrich_and_link.py --config config.yaml
python .\scripts\03b_fix_letter_metadata.py
python .\scripts\04_build_rdf.py --config config.yaml
```

The steps perform the following operations:

```text
01_pagexml_to_letters.py      Converts PAGE XML into segmented letter records.
02_run_ner.py                 Runs NER and date extraction.
02b_clean_mentions.py         Cleans and normalizes raw NER output.
03_enrich_and_link.py         Creates entity tables and performs Wikidata lookup.
03b_fix_letter_metadata.py    Normalizes sender, recipient, date and place metadata.
04_build_rdf.py               Builds the RDF knowledge graph.
```

The current experimental corpus contains **15 segmented letters**.

## 4. Output files

The main outputs are written to:

```text
data/output/letters.csv
data/output/letters_fixed.csv
data/output/ner_entities.csv
data/output/ner_entities_cleaned.csv
data/output/ner_nel_entities.csv
data/output/andric_letters_kg.ttl
data/output/andric_letters_kg.jsonld
data/output/entity_network_edges.csv
data/output/entity_network.png
data/output/entity_network.html
```

The most important output files are:

```text
letters.csv                  Raw structured records for individual letters.
letters_fixed.csv            Letter records with corrected sender, recipient, date and place metadata.
ner_entities.csv             Raw entity mentions extracted from letters by NER.
ner_entities_cleaned.csv     Cleaned and normalized entity mentions.
ner_nel_entities.csv         Unique entities with type, mention count and Wikidata URI.
andric_letters_kg.ttl        RDF/Turtle representation of the knowledge graph.
andric_letters_kg.jsonld     JSON-LD representation of the knowledge graph.
entity_network_edges.csv     Edge list for network visualization.
entity_network.png           Static network visualization.
entity_network.html          Interactive network visualization.
```

## 5. SPARQL examples

After building `andric_letters_kg.ttl`, example SPARQL queries can be executed with:

```bash
python .\scripts\05_query_graph.py --ttl data/output/andric_letters_kg.ttl --query queries/letters_by_date.rq
python .\scripts\05_query_graph.py --ttl data/output/andric_letters_kg.ttl --query queries/mentioned_persons.rq
python .\scripts\05_query_graph.py --ttl data/output/andric_letters_kg.ttl --query queries/letters_mentioning_places.rq
```

The example queries retrieve:

```text
letters_by_date.rq              Letters ordered by normalized date.
mentioned_persons.rq            Persons mentioned in the correspondence.
letters_mentioning_places.rq    Letters and the places mentioned in them.
```

## 6. Visualizations

To generate a static PNG network and an interactive HTML network, run:

```bash
python .\scripts\06_visualize_graph.py --config config.yaml
```

For larger node labels, useful for papers or posters, run:

```bash
python .\scripts\06_visualize_graph.py --config config.yaml --png-label-font-size 18 --html-label-font-size 30 --node-size 1300
```

The visualization outputs are:

```text
data/output/entity_network_edges.csv
data/output/entity_network.png
data/output/entity_network.html
```

## 7. Evaluation

The quality of NER and NEL (entity linking) can be measured against manually annotated gold-standard datasets. Before running, activate the virtual environment.

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

**NER evaluation** (entity recognition: PER, LOC, ORG, MISC) compares extracted entity text and type, regardless of span/position in the letter:

```bash
python .\evaluation\eval_ner.py --gold .\evaluation\gold_dataset_ner.csv --pred .\data\output\ner_entities.csv --out .\evaluation\ner_evaluation.csv --errors .\evaluation\ner_errors.csv
```

**NEL evaluation** (entity linking to Wikidata) checks whether an entity is linked to the correct `wikidata_uri`:

```bash
python .\evaluation\eval_nel.py --gold .\evaluation\gold_dataset_nel.csv --pred .\data\output\ner_nel_entities.csv --out .\evaluation\nel_evaluation.csv --errors .\evaluation\nel_errors.csv
```

Arguments:

```text
--gold      Gold (manually annotated) dataset.
--pred      System output being evaluated.
--out       (optional) Saves the results table (Precision/Recall/F1[/Accuracy]) per type as CSV.
--errors    (optional) Saves the error analysis (false negatives / false positives per text) as CSV.
```

Run `eval_ner.py` first to check recognition quality, then `eval_nel.py` to check linking quality.

## 8. Methodological notes

The extraction is intentionally semi-automatic. The pipeline combines automatic processing with controlled post-processing rules.

The main steps are:

```text
Transkribus OCR/ATR             Produces PAGE XML from selected correspondence pages.
Letter segmentation             Converts PAGE XML lines into individual letter records.
NER extraction                  Extracts persons, locations, organizations and miscellaneous entities.
Date extraction                 Uses regular expressions for historical and abbreviated date formats.
Post-processing                 Removes false positives, joins split entities and normalizes variants.
Entity normalization            Maps surface forms to stable labels, e.g. I. Andrić → Ivo Andrić.
Wikidata linking                Adds Wikidata URIs for selected high-confidence entities.
Metadata correction             Normalizes sender, recipient, date and place of writing.
RDF generation                  Converts letters, entities and mentions into a queryable knowledge graph.
SPARQL querying                 Enables structured exploration of the graph.
Network visualization           Provides exploratory views of letters and extracted entities.
```

Examples of normalization include:

```text
I. Andrić / Ivo Andric       → Ivo Andrić
Београд / Beogradu           → Beograd
Zagrebu / Zagreba            → Zagreb
Marseilla / Mарсеј           → Marseille
Zden + ##ka Marković         → Zdenka Marković
Ta + ##gbla + ##tta          → Agramer Tagblatt
```

Selected entities are linked to Wikidata using a combination of Wikidata API lookup and manually controlled high-confidence mappings. For example:

```text
Ivo Andrić        → http://www.wikidata.org/entity/Q47561
Zdenka Marković   → http://www.wikidata.org/entity/Q9389418
Beograd           → http://www.wikidata.org/entity/Q3711
Zagreb            → http://www.wikidata.org/entity/Q1435
Marseille         → http://www.wikidata.org/entity/Q23482
```

## 9. Use in the paper

This work will be presented at the [SEMANTiCS 2026](https://2026-eu.semantics.cc/) conference, at the [Poster session](https://2026-eu.semantics.cc/page/accepted_posters.html).

Currently, please cite this work as this GitHub repository. After the conference, please cite the corresponding SEMANTiCS 2026 poster paper (citation details will be added here once available).


## 10. Online resources

The source code and supporting materials required to reproduce the pipeline are available in this GitHub repository.

The Transkribus model used in this work is available at [https://www.transkribus.org/models/burgenland-croatian-typewritten-2010-2019](https://www.transkribus.org/models/burgenland-croatian-typewritten-2010-2019). 
