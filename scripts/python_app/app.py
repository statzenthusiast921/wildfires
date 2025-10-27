import pandas as pd
import numpy as np
import os
import plotly.express as px
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import json
from urllib.request import urlopen
import plotly.graph_objects as go


#-----Read in and set up data
raw_wf1 = pd.read_csv('https://raw.githubusercontent.com/statzenthusiast921/wildfires/refs/heads/main/data/raw_wildfires_part1.csv', low_memory=False)
raw_wf2 = pd.read_csv('https://raw.githubusercontent.com/statzenthusiast921/wildfires/refs/heads/main/data/raw_wildfires_part2.csv')
fc_wf = pd.read_csv('https://raw.githubusercontent.com/statzenthusiast921/wildfires/refs/heads/main/data/wildfire_forecast_results.csv')
state_county_refs = pd.read_csv('https://raw.githubusercontent.com/statzenthusiast921/wildfires/refs/heads/main/data/state_county_references.csv')
state_county_refs = state_county_refs.rename(
    columns={
        'fips_code_lz': 'FIPS', 
    }
)
raw_wf = pd.concat([raw_wf1,raw_wf2],ignore_index=True)
raw_wf = pd.merge(raw_wf, state_county_refs, on='FIPS', how='left')
raw_wf['FIPS'] = raw_wf['FIPS'].astype(str)
raw_wf['FIPS'] = raw_wf.apply(
    lambda row: '0' + str(row['FIPS']) if row['state_name'] == 'California' else str(row['FIPS']),
    axis=1
)

fc_wf['stage'] = np.where(fc_wf['stage']=="actuals","Actuals","Forecast")
#----- Condense cause categories down a bit
cause_mapping = {
    # Map multiple specific causes to a single "Human - Equipment" category
    'Campfire': 'Recreation (Accident)',
    'Children': 'Recreation (Accident)',
    'Fireworks': 'Recreation (Accident)',
    'Smoking': 'Recreation (Accident)',
    'Equipment Use': 'Infrastructure (Accident)',
    'Powerline': 'Infrastructure (Accident)',
    'Railroad': 'Infrastructure (Accident)',

    'Debris Burning': 'Land Management (Accident)',
    'Structure': 'Land Management (Accident)',
    'Missing/Undefined':'Miscellaneous',
    'Miscellaneous':'Miscellaneous'

}

raw_wf['CONDENSED_CAUSE'] = raw_wf['STAT_CAUSE_DESCR'].replace(cause_mapping)


#Load in shape files for choropleth maps
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)


#-----Set up choices for dropdown menus
state_choices = sorted(raw_wf['state_name'].unique())
county_choices = sorted(raw_wf['county_name'].unique())
year_choices = sorted(raw_wf['FIRE_YEAR'].unique())

cause_choices = [{"label": "All Causes", "value": "All"}] + [
    {"label": c, "value": c} for c in raw_wf["STAT_CAUSE_DESCR"].unique()
]

cause_choices_condensed = [{"label": "All Causes", "value": "All"}] + [
    {"label": c, "value": c} for c in raw_wf["CONDENSED_CAUSE"].unique()
]

plot_choices = ['# Fires','Avg Fire Size']

#----- State --> County Dictionary
df_for_dict = raw_wf[['state_name','county_name']]
df_for_dict = df_for_dict.drop_duplicates(subset='county_name',keep='first')
state_county_dict = df_for_dict.groupby('state_name')['county_name'] \
                               .apply(lambda x: sorted(x)) \
                               .to_dict()

#----- Define style for different pages in app
tabs_styles = {
    'height': '44px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'fontWeight': 'bold',
    'color':'white',
    'backgroundColor': '#222222'

}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#626ffb',
    'color': 'white',
    'padding': '6px'
}



app = dash.Dash(__name__,assets_folder=os.path.join(os.curdir,"assets"))
server = app.server
app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(
            label='Welcome',value='tab-1',style=tab_style, selected_style=tab_selected_style,
            children=[
                html.Div([
                    html.H1(dcc.Markdown('''**Welcome to my Wildfire Dashboard!**''')),
                    html.Br()
                ]),
                   
                html.Div([
                    html.P(dcc.Markdown('''**What is the purpose of this dashboard?**'''),style={'color':'white'}),
                ],style={'text-decoration': 'underline'}),
                html.Div([
                    html.P("This dashboard was created as a tool to answer the following questions:",style={'color':'white'}),
                    html.P("1.) Where on the west coast do we see the highest concentration of fires?",style={'color':'white'}),
                    html.P("2.) What causes these fires?",style={'color':'white'}),
                    html.P("3.) When do these fires most often occur?",style={'color':'white'}),
                    html.P("4.) Have fires been lasting longer or buring more acres over time?",style={'color':'white'}),
                    html.P("5.) Can we build a model to predict fire frequency?",style={'color':'white'}),
                    html.Br()
                ]),
                html.Div([
                    html.P(dcc.Markdown('''**What data is being used for this analysis?**'''),style={'color':'white'}),
                ],style={'text-decoration': 'underline'}),
                   
                html.Div([
                    html.P(["The data utilized for this analysis was taken from this Kaggle link ",html.A('here',href='https://www.kaggle.com/datasets/rtatman/188-million-us-wildfires'), '.'],style={'color':'white'}),
                    html.Br()
                ]),
                html.Div([
                    html.P(dcc.Markdown('''**What are the limitations of this data?**'''),style={'color':'white'}),
                ],style={'text-decoration': 'underline'}),
                html.Div([
                    html.P("1.) To build a truly solid model, I would need daily precipitation and soil moisture data which was difficult to find.",style={'color':'white'})
                ])
            ]),
            dcc.Tab(label='Where do most fires occur?',value='tab-2',style=tab_style, selected_style=tab_selected_style,
                children = [
                    dbc.Row([
                        dbc.Col([
                        #----- State filter
                            html.Label("Select a state:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                                id='dropdown1',
                                style={'color':'black'},
                                options=[{'label': i, 'value': i} for i in state_choices],
                                value=state_choices[0]
                            )
                        ], width = 4),
                        dbc.Col([
                        #----- County filter
                            html.Label("Select a county:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                                id='dropdown2',
                                style={'color':'black'},
                                options=[{'label': i, 'value': i} for i in county_choices],
                                value=county_choices[0]
                            )
                        ], width = 4),
                         dbc.Col([
                        #----- Cause filter
                            html.Label("Select a cause:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                              id="dropdown3",
                                options=cause_choices,
                                value="All",   # start with all selected
                                multi=False,
                                placeholder="Select fire cause",
                                style={"color": "black"}
                            )
                        ], width = 4)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dcc.RangeSlider(
                               id='slider1',
                               min=np.min(year_choices),
                               max=np.max(year_choices),
                               step=1,
                               value=[1992, 2015],

                               marks={1992: '1992',
                                      1994: '1994',
                                      1996: '1996',
                                      1998: '1998',
                                      2000: '2000',
                                      2002: '2002',
                                      2004: '2004',
                                      2006: '2006',
                                      2008: '2008',
                                      2010: '2010',
                                      2012: '2012',
                                      2014: '2014'
                               }
                            )
                        ])
                    ]),
                    #----- Cards for Choropleth/Treemaps
                    dbc.Row([
                        dbc.Col([
                            dbc.Card(id='card1')
                        ], width = 4),
                        dbc.Col([
                            dbc.Card(id='card2')
                        ], width = 4),
                        dbc.Col([
                            dbc.Card(id='card3')
                        ], width = 4),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(id='historical_state_map')
                        ], width = 6),
                        dbc.Col([
                            dcc.Graph(id = 'county_chart')
                        ], width = 6)
                    ])

            ]),
            dcc.Tab(label='How have wildfires changed over time?',value='tab-3',style=tab_style, selected_style=tab_selected_style,
                children = [
                    dbc.Row([
                        dbc.Col([
                        #----- State filter
                            html.Label("Select a state:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                                id='dropdown4',
                                style={'color':'black'},
                                options=[{'label': i, 'value': i} for i in state_choices],
                                value=state_choices[0]
                            )
                        ], width = 3),
                        dbc.Col([
                        #----- County filter
                            html.Label("Select a county:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                                id='dropdown5',
                                style={'color':'black'},
                                options=[{'label': i, 'value': i} for i in county_choices],
                                value=county_choices[0]
                            )
                        ], width = 3),
                         dbc.Col([
                        #----- Cause filter
                            html.Label("Select a cause:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                              id="dropdown6",
                                options=cause_choices_condensed,
                                value="All",   # start with all selected
                                multi=False,
                                placeholder="Select fire cause",
                                style={"color": "black"}
                            )
                        ], width = 3),
                        dbc.Col([
                        #----- Plot filter
                            html.Label("Select a plot:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                                id='dropdown7',
                                style={'color':'black'},
                                options=[{'label': i, 'value': i} for i in plot_choices],
                                value=plot_choices[0]
                            )
                        ], width = 3),
                    ]),
                    #----- Cards for Timeline
                    dbc.Row([
                        dbc.Col([
                            dbc.Card(id='card4')
                        ], width = 4),
                        dbc.Col([
                            dbc.Card(id='card5')
                        ], width = 4),
                        dbc.Col([
                            dbc.Card(id='card6')
                        ], width = 4),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            #----- Timeline of Fires (Choose a chart)
                            dcc.Graph(id = 'fire_timeline', style={'height': '400px'}),
                        ], width = 12)
                    ])
                ]
            ),
            dcc.Tab(label='What do we expect for the future?',value='tab-4',style=tab_style, selected_style=tab_selected_style,
                children = [
                    dbc.Row([
                        dbc.Col([
                        #----- State filter
                            html.Label("Select a state:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                                id='dropdown8',
                                style={'color':'black'},
                                options=[{'label': i, 'value': i} for i in state_choices],
                                value=state_choices[0]
                            )
                        ], width = 6),
                        dbc.Col([
                        #----- County filter
                            html.Label("Select a county:", style={"color": "white", "font-weight": "bold"}),
                            dcc.Dropdown(
                                id='dropdown9',
                                style={'color':'black'},
                                options=[{'label': i, 'value': i} for i in county_choices],
                                value=county_choices[0]
                            )
                        ], width = 6)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card(id='card7')
                        ], width = 4),
                        dbc.Col([
                            dbc.Card(id='card8')
                        ], width = 4),
                        dbc.Col([
                            dbc.Card(id='card9')
                        ], width = 4),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(id = 'forecast_chart')
                        ])
                    ])
                ]
            )
        
            ]
        )
    ])


#Filter county choices by state dropdown
@app.callback(
    Output('dropdown2', 'options'), #--> filter counties
    Output('dropdown2', 'value'),
    Input('dropdown1', 'value') #--> choose state
)
def set_county_options(selected_state):
    return [{'label': i, 'value': i} for i in state_county_dict[selected_state]], state_county_dict[selected_state][0]


#----- Dynamically set cause options based on available state-county values
@app.callback(
    Output('dropdown3', 'options'),
    Output('dropdown3', 'value'),
    Input('dropdown1', 'value'),
    Input('dropdown2', 'value')
)
def set_cause_options(dd1, dd2):

    filtered_df = raw_wf[(raw_wf['state_name'] == dd1) & (raw_wf['county_name'] == dd2)]
    filtered_df = filtered_df[~filtered_df['STAT_CAUSE_DESCR'].isin(['Missing/Undefined','Miscellaneous'])]

    causes = sorted(filtered_df['STAT_CAUSE_DESCR'].unique().tolist())
    options = [{"label": "All", "value": "All"}] + [{"label": c, "value": c} for c in causes]
    return options, "All"


#Filter county choices by state dropdown 
@app.callback(
    Output('dropdown5', 'options'), #--> filter counties
    Output('dropdown5', 'value'),
    Input('dropdown4', 'value') #--> choose state
)
def set_county_options2(selected_state):
    return [{'label': i, 'value': i} for i in state_county_dict[selected_state]], state_county_dict[selected_state][0]


#----- Dynamically set cause options based on available state-county values
@app.callback(
    Output('dropdown6', 'options'),
    Output('dropdown6', 'value'),
    Input('dropdown4', 'value'),
    Input('dropdown5', 'value')
)
def set_cause_options2(dd4, dd5):

    filtered_df = raw_wf[(raw_wf['state_name'] == dd4) & (raw_wf['county_name'] == dd5)]
    filtered_df = filtered_df[~filtered_df['CONDENSED_CAUSE'].isin(['Miscellaneous'])]

    causes = sorted(filtered_df['CONDENSED_CAUSE'].unique().tolist())
    options = [{"label": "All", "value": "All"}] + [{"label": c, "value": c} for c in causes]
    return options, "All"


#Filter county choices by state dropdown 
@app.callback(
    Output('dropdown9', 'options'), #--> filter counties
    Output('dropdown9', 'value'),
    Input('dropdown8', 'value') #--> choose state
)
def set_county_options3(selected_state):
    return [{'label': i, 'value': i} for i in state_county_dict[selected_state]], state_county_dict[selected_state][0]


#----- Callback for choropleth map
@app.callback(
    Output('historical_state_map','figure'),
    Input('dropdown1','value'),
    Input('dropdown2','value'),
    Input('dropdown3','value'),
    Input('slider1','value')
)
def plot_historical_fire_map(dd1, dd2, dd3, slider_range):
    filtered_df = raw_wf[
        (raw_wf['state_name'] == dd1) &
        (raw_wf['FIRE_YEAR'] >= slider_range[0]) &
        (raw_wf['FIRE_YEAR'] <= slider_range[1])
    ]
    if dd3 != "All":
        filtered_df = filtered_df[filtered_df["STAT_CAUSE_DESCR"] == dd3]


    fire_counts = (
        filtered_df.groupby(['county_name','FIPS'])
        .size()
        .reset_index(name='count')
    )

    # ensure FIPS are 5-digit strings so they match the geojson "id"
    fire_counts['FIPS'] = fire_counts['FIPS'].astype(str).str.zfill(5)

    # state view centers
    state_views = {
        "California": {"center": {"lat": 37.5, "lon": -119.5}, "zoom": 4},
        "Oregon":     {"center": {"lat": 44.0, "lon": -120.5}, "zoom": 5},
        "Washington": {"center": {"lat": 47.5, "lon": -120.5}, "zoom": 5}
    }
    view = state_views.get(dd1, {"center": {"lat": 37.5, "lon": -119.5}, "zoom": 4})

    # --- Use the Mapbox choropleth so Scattermapbox overlays line up ---
    fig = px.choropleth_mapbox(
        fire_counts,
        geojson=counties,
        locations="FIPS",
        color="count",
        #hover_name="county_name",
        hover_data = {"county_name": True, "count": True, 'FIPS': False},
        color_continuous_scale="Oranges",
        opacity=0.6,
        center=view["center"],
        zoom=view["zoom"],
        labels={
            "count": "# Fires",
            "county_name": "County Name"  
        },
        featureidkey="id",
        title=f"Wildfires in {dd1} ({slider_range[0]}-{slider_range[1]})"

    )

    fig.update_layout(
        margin=dict(t=30, l=0, r=0, b=0),
        coloraxis_showscale=True,
        title_x=0.5,
        mapbox_style="carto-positron",
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white')
    )


    # --- overlay blue outline for selected county ---
    if dd2 and dd2 in fire_counts['county_name'].values:
        highlight_fips = fire_counts.loc[fire_counts['county_name'] == dd2, 'FIPS'].iloc[0]
        fips5 = str(highlight_fips).zfill(5)

        # Debug helper (uncomment while testing)
        # print("looking for FIPS:", fips5)
        # print("sample geojson ids:", [feat.get('id') for feat in counties.get('features', [])[:6]])

        # find matching geojson feature by id (or by name fallback)
        feature = None
        for feat in counties.get('features', []):
            feat_id = feat.get('id')
            props = feat.get('properties', {}) or {}
            if feat_id is not None and str(feat_id) == fips5:
                feature = feat
                break
            # fallback: match by county name property (some GeoJSON use NAME)
            if props.get('NAME') and props.get('NAME').lower() == dd2.lower():
                feature = feat
                break

        if feature:
            geom = feature.get('geometry', {})
            gtype = geom.get('type')
            coords = geom.get('coordinates', [])

            # normalize: list of polygons (each polygon is list of rings)
            polygons = []
            if gtype == 'Polygon':
                polygons = [coords]
            elif gtype == 'MultiPolygon':
                polygons = coords

            for poly in polygons:
                if not poly:
                    continue
                outer_ring = poly[0]  # outer ring
                lons = [p[0] for p in outer_ring]
                lats = [p[1] for p in outer_ring]

                # draw outline with Scattermapbox (lines only)
                fig.add_trace(go.Scattermapbox(
                    lon = lons,
                    lat = lats,
                    mode = 'lines',
                    line = dict(color='blue', width=3),
                    fill = 'none',
                    hoverinfo = 'skip',
                    showlegend = False
                ))
        else:
            print(f"[plot_historical_fire_map] couldn't find GeoJSON feature for FIPS {fips5} / county {dd2}")


    return fig


@app.callback(
    Output('card1','children'),
    Output('card2','children'),
    Output('card3','children'),
    Input('dropdown1','value'),
    Input('dropdown2','value'),
    Input('dropdown3','value'),
    Input('slider1','value')

)
def tab1_cards(dd1, dd2, dd3, slider_range):

    filtered_df = raw_wf[
        (raw_wf['state_name'] == dd1) &
        (raw_wf['county_name'] == dd2) &
        (raw_wf['FIRE_YEAR'] >= slider_range[0]) &
        (raw_wf['FIRE_YEAR'] <= slider_range[1])
    ]

    filtered_df2 = raw_wf[
        (raw_wf['state_name'] == dd1) &
        (raw_wf['county_name'] == dd2) &
        (raw_wf['FIRE_YEAR'] >= slider_range[0]) &
        (raw_wf['FIRE_YEAR'] <= slider_range[1])
    ]
    if dd3 != "All":
        filtered_df = filtered_df[filtered_df["STAT_CAUSE_DESCR"] == dd3]



    median_fires = filtered_df2.groupby(['FIRE_YEAR']).size().reset_index(name = 'count')
    metric1 = float(np.median(median_fires['count']))


    card1 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Median # Fires in {dd2}'),
                    html.H5(f"{metric1}")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)


    state_df = raw_wf[
        (raw_wf['state_name'] == dd1) &
        (raw_wf['FIRE_YEAR'] >= slider_range[0]) &
        (raw_wf['FIRE_YEAR'] <= slider_range[1])
    ]
    county_median_fires = state_df.groupby(['county_name','FIRE_YEAR']).size().reset_index(name = 'count')
    median_per_county_df = county_median_fires.groupby('county_name')['count'].median().reset_index(name='MedianAnnualFires')
    filter_metric = median_per_county_df[median_per_county_df['MedianAnnualFires']>metric1]
    metric2 = filter_metric.shape[0]

    card2 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Median # Fires > {metric1} in {dd1}'),
                    html.H5(f"{metric2} counties")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

    county_median_fires = state_df.groupby(['county_name','FIRE_YEAR']).size().reset_index(name = 'count')
    median_per_county_df = county_median_fires.groupby('county_name')['count'].median().reset_index(name='MedianAnnualFires')
    
    percentile_90 = median_per_county_df['MedianAnnualFires'].quantile(0.90)
    filter_metric = median_per_county_df[median_per_county_df['MedianAnnualFires']>percentile_90]
    metric3 = filter_metric.shape[0]

    card3 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Median # Fires > 90th Percentile in {dd1}'),
                    html.H5(f"{metric3} counties")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)





    return card1, card2, card3
    

#----- Callback for County Treemap of Causes
@app.callback(
    Output('county_chart','figure'),
    Input('dropdown1','value'),
    Input('dropdown2','value'),
    Input('slider1','value')
)
def county_chart(dd1, dd2, slider_range):

    filtered_df = raw_wf[
        (raw_wf['state_name']==dd1) &
        (raw_wf['county_name']==dd2) &
        (raw_wf['FIRE_YEAR']>=slider_range[0]) &
        (raw_wf['FIRE_YEAR']<=slider_range[1])
    ]


    fire_cause_counts = filtered_df.groupby(['STAT_CAUSE_DESCR']).size().reset_index(name='count')

    fig = px.treemap(
        fire_cause_counts,
        path=["STAT_CAUSE_DESCR"],
        values="count",
        hover_data={"STAT_CAUSE_DESCR": True, "count": True},
        labels={"STAT_CAUSE_DESCR": "Cause", "count": "# Fires"}
    )
    fig.update_traces(
        hovertemplate="Cause: %{label}<br># Fires: %{value}<extra></extra>"
    )
    fig.update_layout(
        title=f"Wildfire Causes in {dd2}, {dd1} ({slider_range[0]}–{slider_range[1]})",
        title_x=0.5,
        margin=dict(t=30, l=0, r=0, b=0),
        uniformtext=dict(minsize=10, mode="hide"),
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white')
    )

    return fig

#---------------------------------------#
#---------- TAB 3: Timelines -----------#
#---------------------------------------#


#----- Callback for the three cards
@app.callback(
    Output('card4','children'),
    Output('card5','children'),
    Output('card6','children'),

    Input('dropdown4','value'),
    Input('dropdown5','value'),
    Input('dropdown6','value'),
    Input('dropdown7','value')
)
def card_row2(dd4, dd5, dd6, dd7):

    filtered_df = raw_wf[
        (raw_wf['state_name']==dd4) &
        (raw_wf['county_name']==dd5)
    ]

    # filtered_df = raw_wf[
    #     (raw_wf['state_name']=="Oregon") &
    #     (raw_wf['county_name']=="Multnomah County")
    # ]

    if dd6 != "All":
        filtered_df = filtered_df[filtered_df["CONDENSED_CAUSE"] == dd6]

    if dd7 == "# Fires":
        filtered_df["StartDate"] = pd.to_datetime(filtered_df["StartDate"])
        filtered_df['month_name'] = filtered_df['StartDate'].dt.month_name()
        most_frequent_month = filtered_df["month_name"].value_counts().index[0]

        card4 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Month with Most Fires'),
                    html.H5(f"{most_frequent_month}")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

        last_year = filtered_df[filtered_df['StartDate']>='2015-01-01']
        fires_in_last_year = last_year.shape[0]

        card5 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Total Fires in Last Year (2015)'),
                    html.H5(f"{fires_in_last_year}")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)


        annual_counts = filtered_df.groupby(filtered_df['StartDate'].dt.year).size().rename('Annual_Fire_Count')
        annual_df = annual_counts.reset_index().rename(columns={'StartDate': 'Year'})
    
        # 1. Get the sorted DataFrame containing the max year/count row
        max_year_df = annual_df.sort_values(by='Annual_Fire_Count', ascending=False).head(1)
        
        # 2. Extract the integer values from the DataFrame
        max_year = int(max_year_df['Year'].iloc[0])
        max_year_num = int(max_year_df['Annual_Fire_Count'].iloc[0]) 


        card6 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Year with Most Fires'),
                    html.H5(f"{max_year} ({max_year_num})")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

    else:
        median_acres = float(filtered_df['FIRE_SIZE'].median())

        card4 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Median Acres Burned (1992-2015)'),
                    html.H5(f"{median_acres} acres")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

        days_above_median = filtered_df[filtered_df["FIRE_SIZE"]>median_acres]
        days_above_median = days_above_median[days_above_median['StartDate']>'2010-01-01']
        days_above_median = days_above_median['StartDate'].nunique()


        card5 = dbc.Card([
                dbc.CardBody([
                    html.P(f'> Median Acres Burned (2010-2015)'),
                    html.H5(f"{days_above_median} days")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

        percentile90 = filtered_df['FIRE_SIZE'].quantile(0.90)
        recent_fires = filtered_df[filtered_df['StartDate']>'2010-01-01']
        top10percentile_fires = recent_fires[recent_fires['FIRE_SIZE']>=percentile90]


        top10percentile_fires = top10percentile_fires['StartDate'].nunique()

        card6 = dbc.Card([
                dbc.CardBody([
                    html.P(f'> 90th Percentile Acres Burned (2010-2015)'),
                    html.H5(f"{top10percentile_fires} days")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

    return card4, card5, card6



#----- Callback for time series of fires 
@app.callback(
    Output('fire_timeline','figure'),
    Input('dropdown4','value'),
    Input('dropdown5','value'),
    Input('dropdown6','value'),
    Input('dropdown7','value')
)
def timeline_of_fires(dd4, dd5, dd6, dd7):

    filtered_df = raw_wf[
        (raw_wf['state_name']==dd4) &
        (raw_wf['county_name']==dd5)
    ]

    if dd6 != "All":
        filtered_df = filtered_df[filtered_df["CONDENSED_CAUSE"] == dd6]

    if dd7 == "# Fires":
        #----- Make sure StartDate is datetime
        filtered_df["StartDate"] = pd.to_datetime(filtered_df["StartDate"])

        #----- Collapse to first of month
        filtered_df["Month"] = filtered_df["StartDate"].dt.to_period("M").dt.to_timestamp()

        #----- Group by cause + month
        monthly_counts = (
            filtered_df.groupby(["CONDENSED_CAUSE", "Month"])
            .size()
            .reset_index(name="count")
        )

        min_date = monthly_counts['Month'].min()
        max_date = monthly_counts['Month'].max()

        # Generate a continuous range of months (timestamps)
        full_month_range = pd.date_range(start=min_date, end=max_date, freq='MS') 

        # 3. Create a DataFrame with all combinations of Cause and Month
        # Get all unique causes
        all_causes = monthly_counts['CONDENSED_CAUSE'].unique()

        # Create a MultiIndex of all combinations
        multi_index = pd.MultiIndex.from_product(
            [all_causes, full_month_range], 
            names=['CONDENSED_CAUSE', 'Month']
        )

        # Create an empty DataFrame with all combinations
        complete_index_df = pd.DataFrame(index=multi_index).reset_index()

        # 4. Merge the original data with the complete index
        # A left merge will keep all rows from complete_index_df (all months/causes)
        # and fill missing 'avg_fire_size' values with NaN.
        imputed_df = pd.merge(
            complete_index_df,
            monthly_counts,
            on=['CONDENSED_CAUSE', 'Month'],
            how='left'
        )

        # 5. Fill the NaN values with 0
        # Fill NaN for avg_fire_size where there was no data in that month
        imputed_df['count'] = imputed_df['count'].fillna(0)

        # Sort the final result
        monthly_counts = imputed_df.sort_values("Month")

        fig = px.line(
            monthly_counts, 
            x='Month', y='count',
            color='CONDENSED_CAUSE',
            labels={
                "StartDate": "Date", 
                "count": "# Fires", 
                "CONDENSED_CAUSE": "Cause"},
            title="Timeline of Fires by Cause"
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="# Fires",
            xaxis=dict(
                dtick="M12", 
                tickformat="%Y-%m",
                tickangle=270
            ),
            legend_title="Cause",
            plot_bgcolor="#222222",  
            paper_bgcolor="#222222" ,
            font=dict(color="white"),  # all text in white
            title_font=dict(color="white"),  # title specifically
            legend=dict(
                font=dict(color="white"),  # legend text white
                bgcolor="#222222",  # dark legend background
            )
        )

        fig.update_xaxes(color="white", showgrid=False, zeroline=False)
        fig.update_yaxes(color="white", showgrid=False, zeroline=False)
        # Find the max value per cause
        color_map = {trace.name: trace.line.color for trace in fig.data}

        max_points = monthly_counts.groupby('CONDENSED_CAUSE')['count'].idxmax()
        for idx in max_points:
            row = monthly_counts.loc[idx]
            fig.add_annotation(
                x=row['Month'],
                y=row['count'],
                text=f"Max: {int(row['count'])}",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-30,  # move text above the point
                bgcolor=color_map[row['CONDENSED_CAUSE']],
                bordercolor="black"
            )

        return fig
    else:

        #----- Make sure StartDate is datetime
        filtered_df["StartDate"] = pd.to_datetime(filtered_df["StartDate"])

        #----- Collapse to first of month
        filtered_df["Month"] = filtered_df["StartDate"].dt.to_period("M").dt.to_timestamp()

        #----- Group by cause + month
        monthly_counts = (
            filtered_df.groupby(["CONDENSED_CAUSE", "Month"])['FIRE_SIZE']
            .mean()
            .reset_index(name="avg_fire_size")
        )

        min_date = monthly_counts['Month'].min()
        max_date = monthly_counts['Month'].max()

        # Generate a continuous range of months (timestamps)
        full_month_range = pd.date_range(start=min_date, end=max_date, freq='MS') # 'MS' is Month Start

        # 3. Create a DataFrame with all combinations of Cause and Month
        # Get all unique causes
        all_causes = monthly_counts['CONDENSED_CAUSE'].unique()

        # Create a MultiIndex of all combinations
        multi_index = pd.MultiIndex.from_product(
            [all_causes, full_month_range], 
            names=['CONDENSED_CAUSE', 'Month']
        )

        # Create an empty DataFrame with all combinations
        complete_index_df = pd.DataFrame(index=multi_index).reset_index()

        # 4. Merge the original data with the complete index
        # A left merge will keep all rows from complete_index_df (all months/causes)
        # and fill missing 'avg_fire_size' values with NaN.
        imputed_df = pd.merge(
            complete_index_df,
            monthly_counts,
            on=['CONDENSED_CAUSE', 'Month'],
            how='left'
        )

        # 5. Fill the NaN values with 0
        # Fill NaN for avg_fire_size where there was no data in that month
        imputed_df['avg_fire_size'] = imputed_df['avg_fire_size'].fillna(0)

        monthly_counts = imputed_df.sort_values("Month")

        fig = px.line(
            monthly_counts, 
            x='Month', y='avg_fire_size',
            color='CONDENSED_CAUSE',
            labels={
                "Month": "Month", 
                "avg_fire_size": "Avg Fire Size", 
                "CONDENSED_CAUSE": "Cause"
            },
            title="Timeline of Fire Sizes by Cause"
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Avg Fire Size",
            xaxis=dict(
                dtick="M12", 
                tickformat="%Y-%m",
                tickangle=270
            ),
            legend_title="Cause",
            plot_bgcolor="#222222",  
            paper_bgcolor="#222222" ,
            font=dict(color="white"),  # all text in white
            title_font=dict(color="white"),  # title specifically
            legend=dict(
                font=dict(color="white"),  # legend text white
                bgcolor="#222222",  # dark legend background
            )
        )

        fig.update_xaxes(color="white", showgrid=False, zeroline=False)
        fig.update_yaxes(color="white", showgrid=False, zeroline=False)

            # Find the max value per cause
        color_map = {trace.name: trace.line.color for trace in fig.data}

        max_points = monthly_counts.groupby('CONDENSED_CAUSE')['avg_fire_size'].idxmax()
        for idx in max_points:
            row = monthly_counts.loc[idx]
            fig.add_annotation(
                x=row['Month'],
                y=row['avg_fire_size'],
                text=f"Max: {row['avg_fire_size']:.1f}",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-30,
                bgcolor=color_map[row['CONDENSED_CAUSE']],
                bordercolor="black"
            )

        return fig



@app.callback(
    Output('card7','children'),
    Output('card8','children'),
    Output('card9','children'),
    Input('dropdown8','value'),
    Input('dropdown9','value')
)
def tab3_cards(dd8, dd9):

    state_fires = fc_wf[
        (fc_wf['state_name'] == dd8) 
    ]

    county_sum_of_fires = state_fires.groupby('county_name')['value'].sum().reset_index()   
    county_sum_of_fires = county_sum_of_fires.sort_values(by='value', ascending=False).reset_index(drop=True)
    county_sum_of_fires['rank'] = county_sum_of_fires.index + 1

    #----- Pull out rank as numerator
    rank1 = int(county_sum_of_fires[county_sum_of_fires['county_name']==dd9]['rank'].values[0])
    total_counties1 = county_sum_of_fires.shape[0]

    card7 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Rank Total # Fires (1992-2015)'),
                    html.H5(f"{rank1} out of {total_counties1}")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

    state_fires2 = state_fires[state_fires['MonthStart']>='1/1/10']
    county_sum_of_fires2 = state_fires2.groupby('county_name')['value'].sum().reset_index()   
    county_sum_of_fires2 = county_sum_of_fires2.sort_values(by='value', ascending=False).reset_index(drop=True)
    county_sum_of_fires2['rank'] = county_sum_of_fires2.index + 1

    #----- Pull out rank as numerator
    rank2 = int(county_sum_of_fires2[county_sum_of_fires2['county_name']==dd9]['rank'].values[0])
    total_counties2 = county_sum_of_fires2.shape[0]

    card8 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Rank Total # Fires (2010-2015)'),
                    html.H5(f"{rank2} out of {total_counties2}")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

    fcs = state_fires[state_fires['stage']=="Forecast"]
    fcs = fcs[fcs['county_name']==dd9]
    fcs['MonthStart'] = pd.to_datetime(fcs['MonthStart'], format='%m/%d/%y')
    fcs['year'] = fcs['MonthStart'].dt.year

    fc_years = fcs.groupby('year')['value'].sum().reset_index()   

    #---- Quick little mini regression to grab slope (direction)
    X_years = fc_years['year'].tolist()
    Y_forecast = fc_years['value'].tolist()


    N = len(X_years)

    # 1. Calculate the necessary sums
    sum_X = sum(X_years)
    sum_Y = sum(Y_forecast)
    sum_XY = sum(x * y for x, y in zip(X_years, Y_forecast))
    sum_X2 = sum(x * x for x in X_years)

    # 2. Apply the Least-Squares Slope Formula (m)
    # Formula: m = [N * (Sum XY) - (Sum X) * (Sum Y)] / [N * (Sum X^2) - (Sum X)^2]
    numerator = N * sum_XY - sum_X * sum_Y
    denominator = N * sum_X2 - sum_X ** 2

    if denominator == 0:
        slope = 0
    else:
        slope = numerator / denominator

    direction = str(np.where(float(slope)>0, "Increasing", "Decreasing"))


    card9 = dbc.Card([
                dbc.CardBody([
                    html.P(f'Fire Forecast Trajectory'),
                    html.H5(f"{direction}")
                ])
            ],
            style={'display': 'inline-block',
                'width': '100%',
                'text-align': 'center',
                'background-color': '#70747c',
                'color':'white',
                'fontWeight': 'bold',
                'fontSize':16},
            outline=True)

    return card7, card8, card9

@app.callback(
    Output('forecast_chart', 'figure'),
    Input('dropdown8', 'value'),
    Input('dropdown9', 'value')
)
def forecast_chart(dd8, dd9):

    filtered_df = fc_wf[(fc_wf['state_name'] == dd8) & (fc_wf['county_name'] == dd9)]
    filtered_df['MonthStart'] = pd.to_datetime(filtered_df['MonthStart'])

    fig = px.line(
            filtered_df, 
            x='MonthStart', y='value',
            color='stage',
            labels={
                "MonthStart": "Date", 
                "value": "# Fires", 
                'stage': 'Key'
            },
            title=f"4-Year Fire Forecast for {dd9}",
            template="plotly_dark" 
    )

    fig.update_layout(
            xaxis_title="Month",
            xaxis=dict(
                dtick="M12", 
                tickformat="%Y-%m-%d",
                tickangle=270
            ),
            legend=dict(
                y=1,
                x=1,
                xanchor="right", 
                yanchor="top" 
            )
    )

    return fig

if __name__=='__main__':
    app.run(debug=True)
