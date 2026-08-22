# A1.11 Time-dependent Criticality

## Purpose

A1.11 integrates the A1.7 hourly resilience profile with the A1.8 route/trip leave-one-out method. It answers a narrower operational question:

> At each hourly departure time, which route and which trip would cause the largest modelled deterioration in hospital accessibility if removed?

The analysis remains an accessibility sensitivity test. It is not a failure probability, ridership ranking, cost-benefit score or dispatch recommendation.

## Scope

- Area: current Ozu Gururin Ozu GTFS analysis envelope
- Date: same service date as predecessor A1
- Time window: 06:00–21:00
- Step: 60 minutes
- Destination used for A1.11 ranking: hospitals only
- Route/trip outage: one service removed at a time (D stress-test assumption)
- Ranking: population with >1 minute increase descending, then mean travel-time degradation descending, then stable ID
- Walking transfer: A1.6 rules retained

A1.9 shelter accessibility and A1.10 destination switching are preserved but shelter destinations are not included in A1.11 criticality ranking.

## Candidate rule

At each slot, a route or trip is computationally evaluated only when at least one GTFS connection for that trip remains boardable at or after the analysis time. An already-finished service remains in the output with:

- `evaluated: false`
- `skip_reason: no_remaining_boardable_connection`
- zero impact

This avoids meaningless routing runs while preserving a stable matrix width across all 16 time slots.

## Outputs

`time_dependent_criticality.json` contains:

- 16 hourly rows
- complete route ranking for each hour
- complete trip ranking for each hour
- top material route/trip for each hour
- remaining boardable trip/route counts
- peak route and trip events over the day
- number of changes in the top-ranked service

The predecessor `criticality.json` remains the A1.8 08:00 reference result for regression comparison.

## Public UI

The Planning Canvas adds a `TIME × SERVICE CRITICALITY` panel with:

- peak route event
- peak trip event
- number of top-service changes
- all 16 hourly top route/trip results
- affected population and mean degradation bars

The UI clearly states that A1.11 uses hospital accessibility and modelled C/D classifications.

## Limitations

1. Hourly sampling can miss peaks between sampled times.
2. Outages are independent; cascading failures and vehicle circulation are not modelled.
3. Ridership, operating cost, vehicle availability and equity weights are not part of the rank.
4. Hospital access is the only destination used in this stage's criticality matrix.
5. GTFS timetable conditions and the A1 walking/network assumptions remain inherited limitations.
