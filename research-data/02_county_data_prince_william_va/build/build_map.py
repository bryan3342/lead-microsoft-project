"""Rebuild prince_william_banking_access.html from the CSVs in the parent folder."""
import json, math, os
import pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
def clean(df):
    return [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()} for r in df.to_dict('records')]
a = pd.read_csv('acs_2019_2023_by_tract.csv'); h = pd.read_csv('hmda_2025_by_tract.csv'); g = pd.read_csv('tract_geography.csv')
m = a.merge(h, on='tract_geoid', how='left').merge(g, on='tract_geoid', how='left')
m['lmi_tract_ffiec'] = m.tract_income_pct_of_msa.lt(80).where(m.tract_income_pct_of_msa.notna())
m.to_csv('merged_tract_profile.csv', index=False)
m['tract_geoid'] = m.tract_geoid.astype(str)
keep = ['tract_geoid','households','households_moe','pct_hh_income_under_25k','pct_hh_income_under_25k_moe','pct_people_below_poverty','pct_people_below_poverty_moe','pct_children_one_parent','pct_children_one_parent_moe','pct_people_in_limited_english_hh','pct_people_in_limited_english_hh_moe','pct_hh_no_vehicle','pct_hh_no_vehicle_moe','pct_hh_no_internet','pct_hh_no_internet_moe','note','applications','denial_rate_pct','home_purchase_denial_rate_pct','tract_income_pct_of_msa','branches_in_tract','km_to_nearest_branch']
data = {
  'tracts': clean(m[keep]), 'paths': json.load(open('tract_paths.json'))['paths'],
  'branches': clean(pd.read_csv('fdic_branches_2026.csv')[['bank','x','y']]),
  'sod': clean(pd.read_csv('fdic_sod_county_trend.csv')), 'hmda': clean(pd.read_csv('hmda_2021_2025_county_trend.csv')),
  'cfpb_year': clean(pd.read_csv('cfpb_complaints_by_year.csv')), 'sod_bank': clean(pd.read_csv('fdic_sod_by_bank_2021_vs_2025.csv')),
  'cfpb_issues': clean(pd.read_csv('cfpb_complaints_top_issues.csv')), 'hmda_lenders': clean(pd.read_csv('hmda_2025_top_lenders.csv')),
  'cfpb_zip': clean(pd.read_csv('cfpb_complaints_by_zip.csv', dtype={'zip': str})),
  'defaultTract': m.sort_values('pct_hh_income_under_25k', ascending=False).iloc[0].tract_geoid,
}
html = open('build/map_template.html').read().replace('/*DATA*/', json.dumps(data, separators=(',', ':')))
open('build/prince_william_banking_access.html', 'w').write(html)
print('built', len(html), 'bytes; LMI tracts:', int(m.lmi_tract_ffiec.eq(True).sum()))
