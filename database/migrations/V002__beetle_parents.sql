-- V002: parent (sire/dam) links for lineage tracking.
--
-- A parent is either another beetle in the collection (sire_id / dam_id) or,
-- when it was never kept here (bought adult, wild-caught, breeder's stock),
-- a free-text note such as "WD 125 mm, Sumatra". Both may be set.
-- Sex and ancestry-cycle rules are enforced by the API, which sees both rows.

ALTER TABLE beetles
  ADD COLUMN sire_id   UUID REFERENCES beetles (id),
  ADD COLUMN dam_id    UUID REFERENCES beetles (id),
  ADD COLUMN sire_note TEXT CHECK (char_length(sire_note) <= 200),
  ADD COLUMN dam_note  TEXT CHECK (char_length(dam_note) <= 200),
  ADD CONSTRAINT beetles_sire_not_self CHECK (sire_id <> id),
  ADD CONSTRAINT beetles_dam_not_self  CHECK (dam_id <> id),
  ADD CONSTRAINT beetles_sire_not_dam  CHECK (sire_id <> dam_id);

CREATE INDEX idx_beetles_sire ON beetles (sire_id) WHERE sire_id IS NOT NULL;
CREATE INDEX idx_beetles_dam  ON beetles (dam_id)  WHERE dam_id IS NOT NULL;
