#!/usr/bin/env python
from pathlib import Path
import pandas as pd


ENTITIES_CSV = Path("data/output/entities.csv")


FORCED_WIKIDATA = {
    # Persons
    "Ivo Andrić": "http://www.wikidata.org/entity/Q47561",
    "Zdenka Marković": "http://www.wikidata.org/entity/Q9389418",
    "Ivo Vojnović": "http://www.wikidata.org/entity/Q553440",
    "Miroslav Krleža": "http://www.wikidata.org/entity/Q325428",
    "Endre Ady": "http://www.wikidata.org/entity/Q211392",
    "Tadeusz Boy-Żeleński": "http://www.wikidata.org/entity/Q699597",
    "Bronisław Grabowski": "http://www.wikidata.org/entity/Q9179905",
    "Tugomir Alaupović": "http://www.wikidata.org/entity/Q110227319",

    # Places
    "Sarajevo": "http://www.wikidata.org/entity/Q11194",
    "Beograd": "http://www.wikidata.org/entity/Q3711",
    "Zagreb": "http://www.wikidata.org/entity/Q1435",
    "Dubrovnik": "http://www.wikidata.org/entity/Q1722",
    "Marseille": "http://www.wikidata.org/entity/Q23482",
    "Ženeva": "http://www.wikidata.org/entity/Q71",
    "Berlin": "http://www.wikidata.org/entity/Q64",
    "Atina": "http://www.wikidata.org/entity/Q1524",
    "Višegrad": "http://www.wikidata.org/entity/Q239266",
    "Avignon": "http://www.wikidata.org/entity/Q6397",
    "Grenoble": "http://www.wikidata.org/entity/Q1289",
    "Frankfurt": "http://www.wikidata.org/entity/Q1794",
    "Weimar": "http://www.wikidata.org/entity/Q38965",
    "Krakow": "http://www.wikidata.org/entity/Q31487",
    "Villach": "http://www.wikidata.org/entity/Q483522",
    "Austrija": "http://www.wikidata.org/entity/Q40",
    "Poljska": "http://www.wikidata.org/entity/Q36",
    "Alpi": "http://www.wikidata.org/entity/Q1286",
    "Nîmes": "http://www.wikidata.org/entity/Q42807",
    "Arles": "http://www.wikidata.org/entity/Q48292",
}


# These are address-like or ambiguous labels; better not to link them automatically.
REMOVE_WIKIDATA_LINK = {
    "St. Jacques",
    "Jurjevska ul. 19",
    "Dežmanova ul. 3 / 1",
    "Akademije",
}


def main():
    df = pd.read_csv(ENTITIES_CSV, encoding="utf-8")

    for label, uri in FORCED_WIKIDATA.items():
        df.loc[df["label"] == label, "wikidata_uri"] = uri

    for label in REMOVE_WIKIDATA_LINK:
        df.loc[df["label"] == label, "wikidata_uri"] = ""

    df.to_csv(ENTITIES_CSV, index=False, encoding="utf-8")

    print("Saved fixed entity links to:", ENTITIES_CSV)
    print(df[df["label"].isin(["Ivo Andrić", "Arles", "Nîmes", "ArlesNîmes", "St. Jacques", "Alpi"])].to_string())


if __name__ == "__main__":
    main()