# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots

import pandas as pd
from pandas.tseries.offsets import *
pd.options.mode.chained_assignment = None

import numpy as np
import json

import os


default_colors = [ '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52',
'#9e7200', '#00588d', '#ff0000', '#352300', '#ff003e',
'#00463e', '#7b61ff', '#ffb9f6', '#00a700', '#724f6a', '#8d4fb0', '#72ff00', '#002ca7',
'#1aca61', '#84a709', '#007bf6', '#6a8d4f', '#ff8d6a', '#84d3f6', '#b91ae5', '#46ffff',
'#840061', '#95ffc1', '#e5ff00', '#950000', '#00f658', '#35009e', '#f66a95', '#ff009e',
'#008d7b', '#f6ed84', '#8d9eff', '#352300', '#95ff46', '#4600ff', '#000046', '#ff72ff',
'#007200', '#ff4f00', '#00b9ff', '#00ffb9', '#ffc100', '#0046ff', '#00ff00', '#ff00ff']
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
default_states = []

# Import data
# Load cases/deaths data
cases_data = pd.read_csv('data/cases_and_deaths.csv', parse_dates=['date'])
cases_data['day_of_week'] = cases_data['date'].dt.day_name()
cases_data['city'] = cases_data['city'].str.split(',').str[0]

# Get the dates which are weekends
all_dates = cases_data[['date', 'day_of_week']].drop_duplicates()
present_saturdays = set(all_dates[all_dates['day_of_week'] == 'Saturday']['date'])
implied_saturdays = set(all_dates[all_dates['day_of_week'] == 'Sunday']['date'] - pd.DateOffset(days=1))
saturdays = present_saturdays.union(implied_saturdays)

# Get all the states present in the data for the map
states = cases_data[cases_data['state_abbreviation'] != '']['state_abbreviation'].drop_duplicates().to_frame().reset_index(drop=True)
states_with_county = set(cases_data[cases_data.county.notnull()]['state_abbreviation'])
states['has_counties'] = states['state_abbreviation'].isin(states_with_county)

# For the Date slider
dates = cases_data['date'].drop_duplicates().sort_values().reset_index(drop=True)
min_date = min(dates)
max_date = max(dates)

empty_plot = {
        'data': [],
        'layout': go.Layout(
            xaxis={
                'showticklabels': False,
                'ticks': '',
                'showgrid': False,
                'zeroline': False
            },
            yaxis={
                'showticklabels': False,
                'ticks': '',
                'showgrid': False,
                'zeroline': False
            })
        }

# Build the app

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
server.secret_key = os.environ.get('SECRET_KEY', 'my-secret-key')


app.title = 'Covid-19 Dashboard'
app.layout = html.Div([
    # row - Header
    html.Div([
        html.H1(children='COVID 19 Cases And Deaths',
                className='twelve columns'),
        html.P(["Data Source: ", html.A('Johns Hopkins University Center for Systems Science and Engineering',
                                         href='https://github.com/CSSEGISandData/COVID-19'), html.Br(),
                "Author: ", html.A('Jack Barbey', href='https://www.linkedin.com/in/jack-barbey/')]
        ),
    ], className='row', style={'marginBottom': 20}),

    html.Button('Notes & Instructions', id='instructions-button', n_clicks=0),
    html.Div([  # instructions modal div
        html.Div([  # content div
            html.Div([
                html.H6('Steps For Use:'),
                html.P([
                    '1. Select which states to include by clicking them on the map.', html.Br(),
                    '2. Select the range of dates to display. It is automatically set to the maximum date range.', html.Br(),
                    '3. Select whether to view the data aggregated for the state overall or for the top 4 metropolitan areas in each state.', html.Br(),
                    '4. Select whether to display confirmed cases or deaths, both normalized by population', html.Br(),
                    '5. Select whether to break the plots out by indiviudal counties.', html.Br(),
                    '6. Select whether to plot daily new records or cumulative counts over time.', html.Br(),
                    '7. Select whether to smooth the data using a locally linear Savgol Filter, window size of 13 days.', html.Br(),
                ]),
                html.H6('Notes and Tips:'),
                html.P([
                    "- For metro areas which extend over multiple states, each state's portion of that metro area will be shown indiviudally when 'Metro' aggregation is selected. ", html.Br(),
                    "- The gray bars on the plots indicate weekends.", html.Br(),
                    "- You may need to scroll on the legend at the bottom to display the full list.", html.Br(),
                    "- Items in the plot's legends can be clicked to be removed or double clicked to isolate their lines.", html.Br(),
                    "- You can zoom in on the plot by drawing a rectangle over the portion of interest.", html.Br(),
                ]),

            ]),

            html.Hr(),
            html.Button('Close', id='modal-close-button')
        ],

            className='modal-content',
        ),
        ],
        id='modal',
        className='modal',
        style={"display": "none"},
    ),
    html.Br(),

    # row - all selectors
    html.Div([
        # column - Map
        html.Div([
                # Choose a state
                dcc.Graph(id='states-plot', figure=empty_plot),  # Initialize empty until 1st callback

                # Stores which states are clicked
                dcc.Store(id='states-memory', data=default_states),

        ], className='seven columns'),

        # column - All other selectors
        html.Div([
            # row - Date range and state/city
            html.Div([
                # column - date range
                html.Div([
                    html.H6('Date Range:'),
                    dcc.DatePickerRange(
                        id='date-range',
                        min_date_allowed=min_date,
                        start_date=min_date,
                        max_date_allowed=max_date,
                        end_date=max_date,
                        initial_visible_month=max_date
                        ),
                ], className='seven columns',  style={'marginLeft': 0, 'marginRight':15}),

                # column - state/city
                html.Div([
                    html.H6('State or City:'),
                    dcc.RadioItems(
                        id='state-or-city-selector',
                        options=[
                            {'label': 'State', 'value': 'state'},
                            {'label': 'Metro', 'value': 'state_metro'},
                        ],
                        value='state',
                        #labelStyle={'display': 'inline-block'}
                    ),
                ], className='five columns', style={'marginLeft': 0, 'marginRight':0}),
            ], className='row', style={'marginBottom': 25}),

            # row - deaths/cases and county
            html.Div([
                # column - deaths/cases
                html.Div([
                    html.H6('Confirmed Cases or Deaths'),
                    dcc.RadioItems(
                        id='cases-or-deaths',
                        options=[
                            {'label': 'Cases Per 100,000 People', 'value': 'cases'},
                            {'label': 'Deaths Per 100,000 People', 'value': 'deaths'},
                        ],
                        value='cases'
                    ),
                ], className='seven columns',  style={'marginLeft': 0, 'marginRight':15}),

                # column - county selector
                html.Div([
                    html.H6('By County'),
                    dcc.Checklist(
                        id='cases-by-county',
                        options=[
                            {'label': 'Show', 'value': 1},
                        ],
                        value=[]
                    ),
                ], className='five columns', style={'marginLeft': 0, 'marginRight':0}),
            ], className='row', style={'marginBottom': 25}),

            # row - new/cumulative and smooth
            html.Div([
                # column - new/cumulative
                html.Div([
                    html.H6('Daily New or Cumulative'),
                    dcc.RadioItems(
                        id='cumulative-or-new',
                        options=[
                            {'label': 'New', 'value': 'new'},
                            {'label': 'Cumulative', 'value': 'cumulative'},
                        ],
                        value='new'
                    ),
                ], className='seven columns',  style={'marginLeft': 0, 'marginRight':15}),

                # column - smooth or not
                html.Div([
                    html.H6('Smooth Data'),
                    dcc.Checklist(
                        id='smooth-cases',
                        options=[
                            {'label': 'Show', 'value': 1},
                        ],
                        value=[]
                    ),
                ], className='five columns', style={'marginLeft': 0, 'marginRight':0}),

            ], className='row', style={'marginBottom': 25})

        ], className='five columns', style={'marginLeft': 5, 'marginRight':0})

    ], className='row', style={'marginBottom': 25, 'marginTop': 30}),

    # row - Plot title
    html.Div([
        html.H3('Cases and Deaths Data, Normalized by Population')
    ], className='row'),


    # row - Cases/Deaths plot
    html.Div([
        html.Div([
            dcc.Graph(id='cases-plot', figure=empty_plot)  # Initialize empty until 1st callback
        ], className='twelve columns'),
    ], className='row'),
])


@app.callback(
    [dash.dependencies.Output('states-plot', 'figure'),
     dash.dependencies.Output('states-memory', 'data')],
    [dash.dependencies.Input('states-plot', 'clickData')],
    [dash.dependencies.State('states-memory', 'data')]
    )
def display_map(clickData, states_store):
    """
    Make the clickable map
    """
    states['selection'] = 0

    current_selected_states = set(states_store)

    if clickData is not None:
        selected_state = clickData['points'][0]['location']
        if selected_state not in current_selected_states:
            current_selected_states.add(selected_state)
        else:
            current_selected_states.remove(selected_state)

    states_to_show = states
    states_to_show.loc[states_to_show.state_abbreviation.isin(current_selected_states), 'selection'] = 1

    data = go.Choropleth({
         'colorscale': [[0, '#009dd9'], [0.5, '#a5a5a4'], [1, '#ffcd00']],
         'geo': 'geo',
         'hovertemplate': '%{location}',
         'locationmode': 'USA-states',
         'locations': states_to_show['state_abbreviation'],
         'name': '',
         'showlegend': False,
         'showscale': False,
         'z': states_to_show['selection']
    })

    plot = {
         'data': data,
         'layout': dict(
              height=450,
              geo_scope='usa', # limit map scope to USA
              margin=dict(
                l=0,
                r=0,
                b=0,
                t=0,
                pad=0
            ),
            dragmode = False
    )}


    return go.Figure(plot), list(current_selected_states)


@app.callback(
     dash.dependencies.Output('cases-plot', 'figure'),
    [dash.dependencies.Input('states-memory', 'data'),
     dash.dependencies.Input('state-or-city-selector', 'value'),
     dash.dependencies.Input('date-range', 'start_date'),
     dash.dependencies.Input('date-range', 'end_date'),
     dash.dependencies.Input('cases-by-county', 'value'),
     dash.dependencies.Input('smooth-cases', 'value'),
     dash.dependencies.Input('cases-or-deaths', 'value'),
     dash.dependencies.Input('cumulative-or-new', 'value')]
    )
def produce_cases_plot(states_list, state_or_metro, first_date, last_date, cases_by_county, smooth_data, cases_or_deaths, cumulative_or_new):
    """
    Determines the proper format and data to feed into the produce_case_normal_plot
    or produce_case_facet_plot based on the user settings
    """
    counties_bool = len(cases_by_county) != 0
    smooth_bool = len(smooth_data) != 0

    first_date = pd.to_datetime(first_date)
    last_date = pd.to_datetime(last_date)

    if state_or_metro == 'state':
    # Show cases for the state overall
        if counties_bool:
            # If showing counties, then show a graph for each state OR each state/metro with a line for each county
            filtered = cases_data[cases_data.county.notnull()]
            filtered['plot_bool'] = filtered['state_abbreviation'].isin(states_list)
            groups = list(filtered[['state_abbreviation', 'plot_bool']].sort_values(['state_abbreviation'])\
                                                                       .drop_duplicates().itertuples(index=False, name='Group'))
            return produce_case_facet_plot([first_date, last_date], filtered, groups, cases_or_deaths, cumulative_or_new, smooth_data)

        else:
            # If not showing counties, then show 1 graph with a line for each state OR each state/metro
            filtered = cases_data[(cases_data.city.isnull()) &
                                  (cases_data.county.isnull())]
            filtered['plot_bool'] = filtered['state_abbreviation'].isin(states_list)
            groups = list(filtered[['state_abbreviation', 'plot_bool']].sort_values(['state_abbreviation'])\
                                                                       .drop_duplicates().itertuples(index=False, name='Group'))

            return produce_case_normal_plot([first_date, last_date], filtered, groups, cases_or_deaths, cumulative_or_new, smooth_data)
    else:
    # Show cases for the counties in our metros
        if counties_bool:
            filtered = cases_data[cases_data.county.notnull()]
            filtered['plot_bool'] = filtered['state_abbreviation'].isin(states_list)
            groups = list(filtered[['city', 'state_abbreviation', 'plot_bool']].sort_values(['state_abbreviation', 'city'])\
                                                                       .drop_duplicates().itertuples(index=False, name='Group'))
            return produce_case_facet_plot([first_date, last_date], filtered, groups, cases_or_deaths, cumulative_or_new, smooth_data)

        else:
            # If not showing counties, then show 1 graph with a line for each state OR each state/metro
            filtered = cases_data[(cases_data.city.notnull()) &
                                  (cases_data.county.isnull())]
            filtered['plot_bool'] = filtered['state_abbreviation'].isin(states_list)
            groups = list(filtered[['city', 'state_abbreviation', 'plot_bool']].sort_values(['state_abbreviation', 'city'])\
                                                                                   .drop_duplicates().itertuples(index=False, name='Group'))

            return produce_case_normal_plot([first_date, last_date], filtered, groups, cases_or_deaths, cumulative_or_new, smooth_data)


def produce_case_normal_plot(dates_range, data_to_plot, groups, cases_or_deaths, cumulative_or_new, smooth_data):
    """
    Given the selections generated in the callback function, produce the main plot of OOH
    """
    if cases_or_deaths == 'cases':
        if cumulative_or_new == 'cumulative':
            col = 'cases_norm'
            y_title = 'Cumulative Cases'
        else:
            col = 'new_cases_norm'
            y_title = 'Daily New Cases'
    else:
        if cumulative_or_new == 'cumulative':
            col = 'deaths_norm'
            y_title = 'Cumulative Deaths'
        else:
            col = 'new_deaths_norm'
            y_title = 'Daily New Deaths'

    if smooth_data: col = col + '_smooth'

    # Filter the data to the desired breakout
    data_to_plot = data_to_plot[data_to_plot['date'].between(*dates_range)]

    main_plot_traces = []
    for i, group in enumerate(groups):

        # Retrieve whether or not this line should be plotted.
        # All possible groups still should be named and added to list to keep lines intact when the plot changes
        plot_bool = group.plot_bool

        if plot_bool:
            filter_columns = [i for i in group._fields if i != 'plot_bool']

            filters = ["{} == '{}'".format(i, getattr(group, i)) for i in filter_columns]
            one_filter = " & ".join(filters)
            group_name = " - ".join([getattr(group, i) for i in filter_columns])

            this_groups_data = data_to_plot.query(one_filter)

            x = this_groups_data['date']
            y = this_groups_data[col]
            vis = True
            leg = True
            name = group_name
            color = default_colors[i%len(default_colors)]
            population = this_groups_data['population']

        else:
            x = None
            y = None
            vis = 'legendonly' # This results in constant color, but can conflict
            #vis = False # This results in changing colors, but wider range
            leg = False
            name = None
            color = None
            population = None

        # Make scatter for hours plot
        main_plot_traces.append(go.Scatter(
            x=x,
            y=y,
            name=name,
            meta=name,
            mode='lines+markers',
            line_shape='spline',
            hoverlabel = dict(namelength = 0), # prevents truncating of line name
            hovertemplate="<b>%{meta}</b><br>" +
                          "Date: %{x}<br>" +
                          y_title + ": %{y:.2f}<br>" +
                          "Population: %{customdata:,}",
            opacity=0.8,
            visible=vis,
            showlegend=True,
            legendgroup=name,
            marker_color=color,
            customdata=population
        ))

    # Shading for the weekends
    weekends = []
    for saturday in saturdays:
        weekends.append(dict(
            type="rect",
            # x-reference is assigned to the x-values
            xref="x",
            # y-reference is assigned to the plot paper [0,1]
            yref="paper",
            x0=saturday - pd.DateOffset(days=0.4),
            y0=0,
            x1=saturday + pd.DateOffset(days=1.4),
            y1=1,
            fillcolor="black",
            opacity=0.04,
            layer="below",
            line_width=0.0
        ))

    plot = {
        'data': main_plot_traces,
        'layout': dict(
            xaxis={
                'title': None,
                'range': dates_range,
                'showgrid': False,
            },
            yaxis={
                'title': None,
                'zeroline': True
            },
            height=500,
            margin={'l': 40, 'b': 100, 't': 10, 'r': 10},
            showlegend=True,
            legend={'orientation':'h'},
            hovermode='closest',
            transition={
                'duration': 800,
                'easing': 'cubic-in-out'
            },
            shapes=weekends
        )
    }

    return plot


def produce_case_facet_plot(dates_range, data_to_plot, groups, cases_or_deaths, cumulative_or_new, smooth_data):
    """
    Makes a facet plot where each plot corresponds to one line in the major plot above
    """
    default_max_in_row = 1
    colors_assigned = {} # To unify colors across lines

    if cases_or_deaths == 'cases':
        if cumulative_or_new == 'cumulative':
            col = 'cases_norm'
            y_title = 'Cumulative Cases'
        else:
            col = 'new_cases_norm'
            y_title = 'Daily New Cases'
    else:
        if cumulative_or_new == 'cumulative':
            col = 'deaths_norm'
            y_title = 'Cumulative Deaths'
        else:
            col = 'new_deaths_norm'
            y_title = 'Daily New Deaths'

    if smooth_data: col = col + '_smooth'

    # Get the groups. Each group is a facet
    groups_to_plot = [i for i in groups if i.plot_bool]

    if len(groups_to_plot) == 0: return empty_plot

    filter_columns = [i for i in groups_to_plot[0]._fields if i != 'plot_bool']
    names = [" - ".join([getattr(group, column) for column in filter_columns]) for group in groups_to_plot]

    max_in_row = min(default_max_in_row, len(groups_to_plot))

    num_rows = int(np.ceil(len(groups_to_plot)/max_in_row))

    # Filter the data to the desired breakout
    data_to_plot = data_to_plot[data_to_plot['date'].between(*dates_range)]

    fig = make_subplots(
            rows=num_rows,
            cols=max_in_row,
            shared_xaxes=False,
            shared_yaxes=False,
            x_title='Date',
            y_title=None,
            subplot_titles=names,
            vertical_spacing = 0.05,
            horizontal_spacing = 0.01
        )

    range_min = 0
    range_max = 0
    for i, group in enumerate(groups_to_plot):
        fig_row = int(np.ceil((i+1)/max_in_row))
        fig_col = i%max_in_row + 1

        filter_columns = [i for i in group._fields if i != 'plot_bool']
        filters = ["{} == '{}'".format(i, getattr(group, i)) for i in filter_columns]
        one_filter = " & ".join(filters)
        name = " - ".join([getattr(group, i) for i in filter_columns])

        this_groups_data = data_to_plot.query(one_filter)

        # Keeping track of the ranges for shading weekends
        range_min = min(range_min, min(this_groups_data[col]))
        range_max = max(range_max, max(this_groups_data[col]))

        counties = sorted(this_groups_data.county.unique())

        # Make a seperate line for each subcategory
        for county in counties:
            this_lines_data = this_groups_data[this_groups_data['county'] == county]

            # Get the color of the line based on the county. If it has already been shown before
            # then make it invisible in the legend as well
            show_in_legend = False
            if county not in colors_assigned:
                colors_assigned[county] = default_colors[len(colors_assigned)%len(default_colors)]
                show_in_legend = True

            fig.add_trace(
                go.Scatter(
                    x=this_lines_data['date'],
                    y=this_lines_data[col],
                    name=county,
                    meta=county,
                    mode='lines+markers',
                    line_shape='spline',
                    hovertemplate="<b>%{meta}</b><br>" +
                                  "Date: %{x}<br>" +
                                  y_title + ": %{y:.2f}<br>"+
                                  "Population: %{customdata:,}",
                    hoverlabel = dict(namelength = 0),
                    opacity=0.8,
                    showlegend=show_in_legend,
                    legendgroup=county,
                    marker_color=colors_assigned[county],
                    customdata=this_lines_data['population']
                ),
            row=fig_row, col=fig_col
            )

    weekends = []
    # Create the shapes for shading weekends
    for i in range(len(groups_to_plot)):
        for saturday in saturdays:
            sunday = saturday + pd.DateOffset(days=1)
            if (((saturday >= dates_range[0]) & (saturday <= dates_range[1])) |
                ((sunday >= dates_range[0]) & (sunday <= dates_range[1]))) :
                weekends.append(dict(
                    type="rect",
                    # x and y reference is assigned to the x-values of each subplot
                    xref="x"+str(i+1),
                    yref="y"+str(i+1),
                    x0=saturday - pd.DateOffset(days=0.4),
                    y0=range_min,
                    x1=saturday + pd.DateOffset(days=1.4),
                    y1=range_max,
                    fillcolor="black",
                    opacity=0.04,
                    layer="below",
                    line_width=0.0
                ))

    fig.update_layout(height=500*num_rows, hovermode='closest', plot_bgcolor='rgba(0,0,0,0)', shapes=weekends)
    fig.for_each_yaxis(lambda a: a.update(hoverformat='.2f', zeroline=True, zerolinewidth=0.5,
                                          gridcolor='rgba(135, 143, 135, 0.2)',
                                          zerolinecolor='black', rangemode='tozero', showgrid=True))
    fig.for_each_xaxis(lambda a: a.update(showgrid=False))

    return fig


# hide/show modal
@app.callback(dash.dependencies.Output('modal', 'style'),
             [dash.dependencies.Input('instructions-button', 'n_clicks')])
def show_modal(n):
    if n > 0:
        return {"display": "block"}
    return {"display": "none"}

# Close modal by resetting info_button click to 0
@app.callback(dash.dependencies.Output('instructions-button', 'n_clicks'),
              [dash.dependencies.Input('modal-close-button', 'n_clicks')])
def close_modal(n):
    return 0


if __name__ == '__main__':
    app.run_server()
