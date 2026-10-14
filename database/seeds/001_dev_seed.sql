-- DEVELOPMENT ONLY. Applied by `python migrate.py --seed` / `make db-seed`.
-- Never run against a real keeper's data. Records are clearly marked as seed data.
INSERT INTO beetles (id, code, species_id, sex, status, notes) VALUES
  ('00000000-0000-4000-8000-0000000000a1', 'DHH-901', '5c1d6b0e-0d1a-4c7e-9a00-000000000001', 'male', 'active', '[dev seed]'),
  ('00000000-0000-4000-8000-0000000000a2', 'CCK-901', '5c1d6b0e-0d1a-4c7e-9a00-000000000002', 'female', 'active', '[dev seed]')
ON CONFLICT (id) DO NOTHING;

INSERT INTO weight_records (id, beetle_id, measured_at, weight_grams, notes) VALUES
  ('00000000-0000-4000-8000-0000000000b1', '00000000-0000-4000-8000-0000000000a1', '2026-01-01T00:00:00Z', 10.0, '[dev seed]'),
  ('00000000-0000-4000-8000-0000000000b2', '00000000-0000-4000-8000-0000000000a1', '2026-01-31T00:00:00Z', 25.0, '[dev seed]')
ON CONFLICT (id) DO NOTHING;
