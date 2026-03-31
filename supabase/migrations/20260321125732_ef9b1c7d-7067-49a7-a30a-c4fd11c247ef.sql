INSERT INTO public.profiles (user_id, full_name)
VALUES 
  ('6a461cec-09ec-44ed-9f7a-dce9bf1ef3e8', 'T M'),
  ('c661bb7b-1391-455a-9b2f-d0d194bbdfd1', 'Paulius Minialga')
ON CONFLICT DO NOTHING;