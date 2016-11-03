#!/bin/bash

pg_host=gcam-output-dev.cmusm4olucdj.us-west-2.rds.amazonaws.com

psql -d gcam -h $pg_host -U awsuser \
  -c "COPY price (run_id, region, price_item, price_type, year, value) \
      FROM STDIN csv header;" \
      < price.csv

psql -d gcam -h $pg_host -U awsuser \
  -c "COPY subsector_shareweight \
      (run_id, region, sector, subsector, is_transportation, is_agriculture, year, value) \
      FROM STDIN csv header;" \
      < subsector_shareweight.csv

psql -d gcam -h $pg_host -U awsuser \
  -c "COPY period \
      (run_id, region, sector, subsector, technology, is_transportation, is_agriculture,\
        year, share_weight, cal_value, yield, harvests_per_year, non_land_variable_cost,\
        fixed_output, input_capital, input_om_fixed, trial_market_price, load_factor,\
        ag_prod_change, item_name, renewable_input) \
        FROM STDIN csv header;" \
        < period.csv

psql -d gcam -h $pg_host -U awsuser \
  -c "COPY energy_demand \
      (run_id, region, demand_item, value_type, year, value) \
        FROM STDIN csv header;" \
        < energy_demand.csv

psql -d gcam -h $pg_host -U awsuser \
  -c "COPY tech_emission \
      (run_id, region, sector, subsector, technology, year, chem, emiss_coef)
        FROM STDIN csv header;" \
        < tech_emission.csv
