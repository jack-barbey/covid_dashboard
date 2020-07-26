import pandas as pd
import numpy as np
from scipy import signal


def custom_rolling_mean(group, cols_to_smooth):
    """
    A custom rolling smoother because the builtin method only seems to support boxcar windows
    Using a local linear savgol filter
    """
    # We are using a local linear smoother, 13 day window.
    results = {'date':group['date'].values}

    for col in cols_to_smooth:
        new_name = col+'_smooth'
        smoothed = signal.savgol_filter(group[col], 13, 1)
        results[new_name] = smoothed

    return pd.DataFrame(results)


if __name__ == '__main__':

    fips_to_city = pd.read_csv('data/fips_to_city.csv')\
                     .rename(columns={'cbsacode':'dma', 'cbsatitle':'dma_name', 'countycountyequivalent':'county'})
    fips_to_city['fips'] = fips_to_city['fipsstatecode']*1000 + fips_to_city['fipscountycode']
    our_counties = fips_to_city[['dma', 'dma_name', 'fips', 'county']]

    # Get the cases and deaths for all states
    us_state_abbrev = {'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
                   'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
                   'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI',
                   'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky':
                   'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan':
                   'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska':
                   'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
                   'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND',
                   'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
                   'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN',
                   'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA',
                   'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
                   }

    # Retrieve all cases data
    cases = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv')
    dates = list(cases.columns.difference(['UID', 'iso2', 'iso3', 'code3', 'FIPS', 'Admin2', 'Province_State', 'Country_Region', 'Lat', 'Long_', 'Combined_Key']))
    cases['state_abbreviation'] = [us_state_abbrev[i] if i in us_state_abbrev else '' for i in cases['Province_State']]

    # Melt into long format
    cases_melt = pd.melt(cases, id_vars=['FIPS', 'state_abbreviation', 'Admin2', 'Province_State'], value_vars=dates).rename(columns={'value':'cases', 'FIPS':'fips', 'Province_State':'state', 'Admin2':'county'})
    cases_melt['date'] = pd.to_datetime(cases_melt['variable'])
    cases_melt = cases_melt.drop('variable', axis=1)

    # Retrieve all deaths data
    deaths = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv')
    dates = list(deaths.columns.difference(['UID', 'iso2', 'iso3', 'code3', 'FIPS', 'Admin2', 'Province_State', 'Country_Region', 'Lat', 'Long_', 'Combined_Key', 'Population']))
    deaths['state_abbreviation'] = [us_state_abbrev[i] if i in us_state_abbrev else '' for i in deaths['Province_State']]

    # Melt into long format
    deaths_melt = pd.melt(deaths, id_vars=['FIPS', 'state_abbreviation', 'Admin2', 'Province_State', 'Population'], value_vars=dates).rename(columns={'value':'deaths', 'FIPS':'fips', 'Province_State':'state', 'Admin2':'county', 'Population':'population'})
    deaths_melt['date'] = pd.to_datetime(deaths_melt['variable'])
    deaths_melt = deaths_melt.drop('variable', axis=1)

    # Filter the data
    cases_melt = cases_melt[(cases_melt.state.isin(us_state_abbrev)) &
                            (cases_melt.date >= '2020-03-01')]

    deaths_melt = deaths_melt[(deaths_melt.state.isin(us_state_abbrev)) &
                              (deaths_melt.population > 0) &
                              (deaths_melt.date >= '2020-03-01')]

    # Merge into one dataframe
    cases_and_deaths = cases_melt.merge(deaths_melt, on=['date', 'fips', 'state', 'state_abbreviation', 'county', 'state']).sort_values(by=['date', 'state_abbreviation', 'county'])

    # Transform cumulative counts to daily new counts
    cases_and_deaths['new_cases'] = cases_and_deaths.groupby(['fips', 'state_abbreviation', 'county', 'state'])['cases'].diff().fillna(0)
    cases_and_deaths['new_deaths'] = cases_and_deaths.groupby(['fips', 'state_abbreviation', 'county', 'state'])['deaths'].diff().fillna(0)

    # Group the data by state
    cases_and_deaths_state = cases_and_deaths.groupby(['date', 'state', 'state_abbreviation'])[['population', 'cases', 'deaths', 'new_cases', 'new_deaths']].sum().reset_index()
    cases_and_deaths_state = cases_and_deaths_state.assign(**{'fips': np.nan, 'county': np.nan, 'city': np.nan})
    for col in ['new_cases', 'new_deaths', 'cases', 'deaths']:
        cases_and_deaths_state[col+'_norm'] = cases_and_deaths_state[col]/cases_and_deaths_state['population'] * 100000

    # Link counties to metro areas
    fips_to_city = pd.read_csv('data/fips_to_city.csv')\
                         .rename(columns={'cbsatitle':'city', 'countycountyequivalent':'county'})
    fips_to_city['fips'] = fips_to_city['fipsstatecode']*1000 + fips_to_city['fipscountycode']
    our_counties = fips_to_city[['city', 'fips', 'county']]

    # Get the k largest metros by state
    k = 4
    populations = deaths_melt[['fips','state_abbreviation','population']].drop_duplicates()
    county_pops = populations.merge(our_counties, on='fips')
    metro_pops = county_pops.groupby(['city', 'state_abbreviation'])['population'].sum().to_frame().reset_index()
    top_pops = metro_pops.groupby('state_abbreviation')['population'].nlargest(k).reset_index().drop('level_1', axis=1)
    top_metros = metro_pops.merge(top_pops)[['city', 'state_abbreviation']]

    # filter our_counties to just these metros
    our_counties = our_counties.merge(top_metros)

    # Group the data by metro area counties
    cases_and_deaths_county = cases_and_deaths.drop('county', axis=1).merge(our_counties, on=['fips', 'state_abbreviation'])
    for col in ['new_cases', 'new_deaths', 'cases', 'deaths']:
        cases_and_deaths_county[col+'_norm'] = cases_and_deaths_county[col]/cases_and_deaths_county['population'] * 100000

    # Cases/deaths by state/metro for our metros
    cases_and_deaths_city = cases_and_deaths_county.groupby(['date', 'state', 'state_abbreviation', 'city'])[['population', 'cases', 'deaths', 'new_cases', 'new_deaths']].sum().reset_index()
    cases_and_deaths_city = cases_and_deaths_city.assign(**{'fips': np.nan, 'county': np.nan})
    for col in ['new_cases', 'new_deaths', 'cases', 'deaths']:
        cases_and_deaths_city[col+'_norm'] = cases_and_deaths_city[col]/cases_and_deaths_city['population'] * 100000

    # Concatenate all the data into one df
    all_cases_and_deaths = pd.concat([
        cases_and_deaths_state[['date', 'state', 'state_abbreviation', 'city', 'county', 'fips', 'population', 'new_cases', 'cases', 'new_deaths', 'deaths', 'new_cases_norm', 'cases_norm', 'new_deaths_norm', 'deaths_norm']],
        cases_and_deaths_county[['date', 'state', 'state_abbreviation', 'city', 'county', 'fips', 'population', 'new_cases', 'cases', 'new_deaths', 'deaths', 'new_cases_norm', 'cases_norm', 'new_deaths_norm', 'deaths_norm']],
        cases_and_deaths_city[['date', 'state', 'state_abbreviation', 'city', 'county', 'fips', 'population', 'new_cases', 'cases', 'new_deaths', 'deaths', 'new_cases_norm', 'cases_norm', 'new_deaths_norm', 'deaths_norm']]
    ])

    # Smooth the cases and deaths data
    sorted_cases_and_deaths = all_cases_and_deaths\
                                    .sort_values(by=['city', 'state_abbreviation', 'county', 'fips', 'date'])\
                                    .fillna({'city': -1, 'county':-1, 'fips':-1}) # Fill nan so we can group on them

    cols_to_smooth = ['cases', 'cases_norm',  'new_cases', 'new_cases_norm', 'deaths',
                      'deaths_norm', 'new_deaths',  'new_deaths_norm']

    smoothed = sorted_cases_and_deaths\
        .groupby(['city', 'state_abbreviation', 'county', 'fips'], sort=False)\
        .apply(lambda x: custom_rolling_mean(x, cols_to_smooth))\
        .reset_index().drop('level_4', axis=1)

    cases_and_deaths_smooth = sorted_cases_and_deaths.merge(smoothed, on=['city', 'state_abbreviation', 'county', 'fips', 'date'])
    cases_and_deaths_smooth = cases_and_deaths_smooth.replace({'city': -1, 'county':-1, 'fips':-1}, np.nan) # Undo the fillnan

    # Output data
    cases_and_deaths_smooth.to_csv('data/cases_and_deaths.csv', index=False)
