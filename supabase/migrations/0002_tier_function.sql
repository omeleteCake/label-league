create or replace function compute_tier(listeners integer)
returns text
language sql
immutable
as $$
  select case
    when listeners is null or listeners < 10000 then null
    when listeners < 100000 then 'underground'
    when listeners < 1000000 then 'rising'
    when listeners < 10000000 then 'emerging'
    else 'established'
  end;
$$;

comment on function compute_tier(integer) is
  'Returns the tier bucket for a given monthly listener count, or NULL if below the 10k floor.';
