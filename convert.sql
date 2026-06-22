.mode csv
.separator "|"

CREATE TABLE avis (
    freq INTEGER,
    word1 TEXT,
    conjunction TEXT,
    word2 TEXT,
    data JSON
);

CREATE TABLE bok (
    freq INTEGER,
    lang TEXT,
    word1 TEXT,
    conjunction TEXT,
    word2 TEXT,
    data JSON
);

.import koordinasjoner-avis.tsv avis
.import koordinasjoner-bok.tsv bok
