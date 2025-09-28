import pandas as pd
import numpy as np
import os
import plotly.express as px
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash import dash_table
import json
from urllib.request import urlopen
import plotly.io as pio
pio.renderers.default = "vscode"
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

#Load in shape files for choropleth maps
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

# amtrak_df['month_date'] = pd.to_datetime(amtrak_df['month_date'])
# amtrak_df['year'] = amtrak_df['month_date'].dt.year
# amtrak_df['month'] = amtrak_df['month_date'].dt.month

#-----Set up choices for dropdown menus
state_choices = sorted(raw_wf['state_name'].unique())
county_choices = sorted(raw_wf['county_name'].unique())
year_choices = sorted(raw_wf['FIRE_YEAR'].unique())
#cause_choices = sorted(raw_wf['STAT_CAUSE_DESCR'].unique())

cause_choices = [{"label": "All Causes", "value": "All"}] + [
    {"label": c, "value": c} for c in raw_wf["STAT_CAUSE_DESCR"].unique()
]


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
        dcc.Tab(label='Welcome',value='tab-1',style=tab_style, selected_style=tab_selected_style,
               children=[
                   html.Div([
                       html.H1(dcc.Markdown('''**Welcome to my Wildfire Dashboard!**''')),
                       html.Br()
                   ]),
                   
                   html.Div([
                        html.P(dcc.Markdown('''**What is the purpose of this dashboard?**'''),style={'color':'white'}),
                   ],style={'text-decoration': 'underline'}),
                   html.Div([
                       html.P("This dashboard was created as a tool to blah blah blah",style={'color':'white'}),
                       html.Br()
                   ]),
                   html.Div([
                       html.P(dcc.Markdown('''**What data is being used for this analysis?**'''),style={'color':'white'}),
                   ],style={'text-decoration': 'underline'}),
                   
                   html.Div([
                       html.P(["The data utilized for this dashboard was scraped from the ",html.A('Blah.',href='')],style={'color':'white'}),
                       html.Br()
                   ]),
                   html.Div([
                       html.P(dcc.Markdown('''**What are the limitations of this data?**'''),style={'color':'white'}),
                   ],style={'text-decoration': 'underline'}),
                   html.Div([
                       html.P("1.) Limitation 1 .",style={'color':'white'}),
                       html.P("2.) Limitation 2 .",style={'color':'white'}),

                   ])


               ]),
               dcc.Tab(label='Historical Fires',value='tab-2',style=tab_style, selected_style=tab_selected_style,
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
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(id='historical_state_map')
                        ], width = 6),
                        dbc.Col([
                            dcc.Graph(id = 'county_chart')
                        ], width = 6)
                    ])


               ])
        
            ]
        )
    ])


#Filter county choices by state dropdown
@app.callback(
    Output('dropdown2', 'options'), #--> filter counties
    Output('dropdown2', 'value'),
    Input('dropdown1', 'value') #--> choose state
)
def set_city_options(selected_state):
    return [{'label': i, 'value': i} for i in state_county_dict[selected_state]], state_county_dict[selected_state][0]


@app.callback(
    Output('dropdown3', 'options'),
    Output('dropdown3', 'value'),
    Input('dropdown1', 'value'),
    Input('dropdown2', 'value')
)
def set_cause_options(dd1, dd2):
    filtered_df = raw_wf[(raw_wf['state_name'] == dd1) & (raw_wf['county_name'] == dd2)]
    causes = sorted(filtered_df['STAT_CAUSE_DESCR'].unique().tolist())
    options = [{"label": "All", "value": "All"}] + [{"label": c, "value": c} for c in causes]
    return options, "All"



@app.callback(
    Output('historical_state_map','figure'),
    Input('dropdown1','value'),
    Input('dropdown2','value'),
    Input('dropdown3','value'),
    Input('slider1','value')
)
def plot_historical_fire_map(dd1, dd2, dd3, slider_range):
    # --- correct filtering (use filtered_df for subsequent filters) ---
    filtered_df = raw_wf[
        (raw_wf['state_name'] == dd1) &
        (raw_wf['FIRE_YEAR'] >= slider_range[0]) &
        (raw_wf['FIRE_YEAR'] <= slider_range[1])
    ]
    # --- Handle "All" ---
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
        hover_name="county_name",
        color_continuous_scale="Oranges",
        opacity=0.6,
        mapbox_style="carto-positron",
        center=view["center"],
        zoom=view["zoom"],
        labels={"count": "# Fires"},
        featureidkey="id"  ,
        title=f"Wildfires in {dd1} ({slider_range[0]}-{slider_range[1]})"

    )
    fig.update_layout(
        margin=dict(t=30, l=0, r=0, b=0),
        coloraxis_showscale=True,
        title_x=0.5,
        )
    fig.update_traces(
        hovertemplate="County: %{hovertext}<br># Fires: %{z}<extra></extra>"
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
        uniformtext=dict(minsize=10, mode="hide")
    )

    return fig


if __name__=='__main__':
    app.run(debug=True)
