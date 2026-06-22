CREATE INDEX IF NOT EXISTS idx_avis_conjunction ON avis(conjunction);
CREATE INDEX IF NOT EXISTS idx_avis_word1 ON avis(word1);
CREATE INDEX IF NOT EXISTS idx_avis_word2 ON avis(word2);

CREATE INDEX IF NOT EXISTS idx_bok_conjunction ON bok(conjunction);
CREATE INDEX IF NOT EXISTS idx_bok_word1 ON bok(word1);
CREATE INDEX IF NOT EXISTS idx_bok_word2 ON bok(word2);
CREATE INDEX IF NOT EXISTS idx_bok_lang ON bok(lang);
