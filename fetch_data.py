import pandas as pd
import numpy as np

if __name__ == '__main__':

    fips_to_city = pd.read_csv('data/fips_to_city.csv')\
                     .rename(columns={'cbsacode':'dma', 'cbsatitle':'dma_name', 'countycountyequivalent':'county'})
    fips_to_city['fips'] = fips_to_city['fipsstatecode']*1000 + fips_to_city['fipscountycode']
    our_counties = fips_to_city[['dma', 'dma_name', 'fips', 'county']]

    # Get the cases and deaths for all states
    us_state_abbrev = {'Alabama': 'AL', 'Alaska': 'AK', 'American Samoa': 'AS', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Guam': 'GU', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Northern Mariana Islands':'MP', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Puerto Rico': 'PR', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virgin Islands': 'VI', 'Virginia': 'VA', 'Wx ashington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
    }

    cases = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv')
    dates = list(cases.columns.difference(['UID', 'iso2', 'iso3', 'code3', 'FIPS', 'Admin2', 'Province_State', 'Country_Region', 'Lat', 'Long_', 'Combined_Key']))
    cases['state_abbreviation'] = [us_state_abbrev[i] if i in us_state_abbrev else '' for i in cases['Province_State']]
    cases_melt = pd.melt(cases, id_vars=['FIPS', 'state_abbreviation', 'Admin2', 'Province_State'], value_vars=dates).rename(columns={'value':'cases', 'FIPS':'fips', 'Province_State':'state', 'Admin2':'county'})
    cases_melt['date'] = pd.to_datetime(cases_melt['variable'])
    cases_melt = cases_melt.drop('variable', axis=1)

    deaths = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv')
    dates = list(deaths.columns.difference(['UID', 'iso2', 'iso3', 'code3', 'FIPS', 'Admin2', 'Province_State', 'Country_Region', 'Lat', 'Long_', 'Combined_Key', 'Population']))
    deaths['state_abbreviation'] = [us_state_abbrev[i] if i in us_state_abbrev else '' for i in deaths['Province_State']]
    deaths_melt = pd.melt(deaths, id_vars=['FIPS', 'state_abbreviation', 'Admin2', 'Province_State', 'Population'], value_vars=dates).rename(columns={'value':'deaths', 'FIPS':'fips', 'Province_State':'state', 'Admin2':'county', 'Population':'population'})
    deaths_melt['date'] = pd.to_datetime(deaths_melt['variable'])
    deaths_melt = deaths_melt.drop('variable', axis=1)

    cases_and_deaths = cases_melt.merge(deaths_melt, on=['date', 'fips', 'state', 'state_abbreviation', 'county', 'state']).sort_values(by=['date', 'state_abbreviation', 'county'])
    cases_and_deaths = cases_and_deaths[cases_and_deaths.population != 0] # Filter out some weird data

    cases_and_deaths['new_cases'] = cases_and_deaths.groupby(['fips', 'state_abbreviation', 'county', 'state'])['cases'].diff().fillna(0)
    cases_and_deaths['new_deaths'] = cases_and_deaths.groupby(['fips', 'state_abbreviation', 'county', 'state'])['deaths'].diff().fillna(0)

    # Get the cases and deaths for just the states/counties in the motion data
    # Cases/deaths by state
    cases_and_deaths_state = cases_and_deaths.groupby(['date', 'state', 'state_abbreviation'])[['population', 'cases', 'deaths', 'new_cases', 'new_deaths']].sum().reset_index()
    cases_and_deaths_state = cases_and_deaths_state.assign(**{'fips': np.nan, 'county': np.nan, 'dma': np.nan, 'dma_name': np.nan})
    for col in ['new_cases', 'new_deaths', 'cases', 'deaths']:
      cases_and_deaths_state[col+'_norm'] = cases_and_deaths_state[col]/cases_and_deaths_state['population'] * 100000





    # Cases/deaths by county for metro area counties
    cases_and_deaths_county = cases_and_deaths.drop('county', axis=1).merge(our_counties, on='fips')
    for col in ['new_cases', 'new_deaths', 'cases', 'deaths']:
      cases_and_deaths_county[col+'_norm'] = cases_and_deaths_county[col]/cases_and_deaths_county['population'] * 100000

    # Cases/deaths by state/metro for our metros
    cases_and_deaths_dma = cases_and_deaths_county.groupby(['date', 'state', 'state_abbreviation', 'dma', 'dma_name'])[['population', 'cases', 'deaths', 'new_cases', 'new_deaths']].sum().reset_index()
    cases_and_deaths_dma = cases_and_deaths_dma.assign(**{'fips': np.nan, 'county': np.nan})
    for col in ['new_cases', 'new_deaths', 'cases', 'deaths']:
      cases_and_deaths_dma[col+'_norm'] = cases_and_deaths_dma[col]/cases_and_deaths_dma['population'] * 100000

    all_cases_and_deaths = pd.concat([
      cases_and_deaths_state[['date', 'state', 'state_abbreviation', 'dma', 'dma_name', 'county', 'fips', 'population', 'new_cases', 'cases', 'new_deaths', 'deaths', 'new_cases_norm', 'cases_norm', 'new_deaths_norm', 'deaths_norm']],
      cases_and_deaths_county[['date', 'state', 'state_abbreviation', 'dma', 'dma_name', 'county', 'fips', 'population', 'new_cases', 'cases', 'new_deaths', 'deaths', 'new_cases_norm', 'cases_norm', 'new_deaths_norm', 'deaths_norm']],
      cases_and_deaths_dma[['date', 'state', 'state_abbreviation', 'dma', 'dma_name', 'county', 'fips', 'population', 'new_cases', 'cases', 'new_deaths', 'deaths', 'new_cases_norm', 'cases_norm', 'new_deaths_norm', 'deaths_norm']]
    ])


    # Smooth the cases and deaths data
    sorted_cases_and_deaths = all_cases_and_deaths.sort_values(by=['dma', 'dma_name', 'state_abbreviation', 'county', 'fips', 'date']).fillna({'dma': -1, 'dma_name': -1, 'county':-1, 'fips':-1}) # Fill nan so we can group on them

    cols_to_smooth = ['cases', 'cases_norm',  'new_cases', 'new_cases_norm', 'deaths', 'deaths_norm', 'new_deaths',  'new_deaths_norm']

    dates = sorted_cases_and_deaths[['dma', 'dma_name', 'state_abbreviation', 'county', 'fips', 'date']].sort_values(by=['dma', 'dma_name', 'state_abbreviation', 'county', 'fips', 'date'])['date'].reset_index(drop=True)
    smoothed = sorted_cases_and_deaths.groupby(['dma', 'dma_name', 'state_abbreviation', 'county', 'fips'], sort=False)[cols_to_smooth].rolling(7, win_type='hamming', center=True, min_periods=1).mean().fillna(0).reset_index().drop('level_5', axis=1)

    smoothed.columns = [i+'_smooth' if i in cols_to_smooth else i for i in smoothed.columns]
    smoothed['date'] = dates

    cases_and_deaths_smooth = sorted_cases_and_deaths.merge(smoothed, on=['dma', 'dma_name', 'state_abbreviation', 'county', 'fips', 'date'])
    cases_and_deaths_smooth = cases_and_deaths_smooth.replace({'dma': -1, 'dma_name': -1, 'county':-1, 'fips':-1}, np.nan) # Undo the fillnan

    cases_and_deaths_smooth.to_csv('data/cases_and_deaths.csv')
