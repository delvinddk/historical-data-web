import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import plotly.express as px
from datetime import datetime

# Set page configuration
st.set_page_config(page_title="My Streamlit App", page_icon="🌍")

# Attempt to allow embedding in iframe
st.markdown(
    """
    <meta http-equiv="Content-Security-Policy" content="frame-ancestors *;">
    <style>
        iframe {border: none !important;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("My Streamlit App")
st.write("This app is trying to be embedded in an iframe.")


# Increase server max message size
st._config.set_option("server.maxMessageSize", 500)

# Automatically detect a column related to traffic volume
def detect_traffic_volume_columns(data):
    keywords = ['traffic_volume', 'volume', 'traffic', 'count']
    return [col for col in data.columns if any(keyword in col.lower() for keyword in keywords)]

# Detect the datetime column in the dataset
def detect_datetime_column(data):
    keywords = ['datetime', 'date_time', 'timestamp', 'date']
    for col in data.columns:
        if any(keyword in col.lower() for keyword in keywords):
            return col
    return None

# Preprocess the data
def preprocess_data(uploaded_file):
    try:
        # Read the file as a DataFrame
        data = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Error reading the file: {e}")
        return None
    
    data.columns = map(str.lower, data.columns)
    datetime_col = detect_datetime_column(data)
    if datetime_col:
        data[datetime_col] = pd.to_datetime(data[datetime_col], errors='coerce')
        data = data.dropna(subset=[datetime_col])
        if not pd.api.types.is_datetime64_any_dtype(data[datetime_col]):
            st.warning(f"'{datetime_col}' could not be converted to datetime. Ensure the values are in a valid format.")
            return None
        data.rename(columns={datetime_col: 'datetime'}, inplace=True)
        return data
    else:
        st.warning("The data must contain a column with datetime information (e.g., 'datetime', 'Date_Time', 'timestamp').")
        return None


# Generate time options in HH:MM:SS format
def generate_time_options():
    return [f"{hour:02d}:{minute:02d}:00" for hour in range(24) for minute in range(0, 60, 5)]

# Folium Map Visualization
def plot_folium_map_with_geojson(filtered_data):
    if 'longitude' in filtered_data.columns and 'latitude' in filtered_data.columns:
        st.subheader("Filtered Geographical Data Map (Folium)")

        # Convert lat/long to numeric and clean data
        filtered_data['latitude'] = pd.to_numeric(filtered_data['latitude'], errors='coerce')
        filtered_data['longitude'] = pd.to_numeric(filtered_data['longitude'], errors='coerce')
        filtered_data = filtered_data.dropna(subset=['latitude', 'longitude'])
        filtered_data = filtered_data[
            (filtered_data['latitude'].between(-90, 90)) & 
            (filtered_data['longitude'].between(-180, 180))
        ]

        if filtered_data.empty:
            st.error("No valid geographical data to display. Ensure latitude and longitude values are correct.")
            return

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(
            filtered_data,
            geometry=gpd.points_from_xy(filtered_data['longitude'], filtered_data['latitude'])
        )

        # Map styles
        map_styles = {
            "Humanitarian OSM": "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
            "CartoDB Positron": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
            "CartoDB DarkMatter": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        }
        map_style = st.sidebar.selectbox("Select Map Style", options=list(map_styles.keys()), index=0)
        tiles_url = map_styles[map_style]

        # Create map
        m = folium.Map(
            location=[gdf['latitude'].mean(), gdf['longitude'].mean()],
            zoom_start=10,
            tiles=tiles_url,
            attr=f"{map_style} - Map Tiles"
        )

        # Add GeoJson for full styling control
        for _, row in gdf.iterrows():
            geojson_data = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row['longitude'], row['latitude']]
                },
                "properties": {
                    "tooltip": (
                        f"Region ID: {row.get('region_id', 'N/A')}<br>"
                        f"Region: {row.get('region_name', 'N/A')}<br>"
                        f"Road ID: {row.get('area_name', 'N/A')}<br>"
                        f"City: {row.get('city', 'N/A')}<br>"
                        f"Latitude: {row['latitude']}<br>"
                        f"Longitude: {row['longitude']}"
                    )
                }
            }

            # Tooltip content only
            tooltip_content = (
                f"Region ID: {row.get('region_id', 'N/A')}<br>"
                f"Region: {row.get('region_name', 'N/A')}<br>"
                f"Road ID: {row.get('area_name', 'N/A')}<br>"
                f"City: {row.get('city', 'N/A')}<br>"
                f"Latitude: {row['latitude']}<br>"
                f"Longitude: {row['longitude']}"
            )

            # Add the point using GeoJson with styling
            folium.GeoJson(
                geojson_data,
                style_function=lambda x: {
                    "fillColor": "#0000ff",
                    "color": "#0000ff",
                    "fillOpacity": 0.3,
                    "opacity": 0.5,
                    "radius": 8
                },
                tooltip=folium.Tooltip(tooltip_content, sticky=True)  # Tooltip only
            ).add_to(m)

        folium_static(m)
    else:
        st.warning("Longitude and Latitude columns are missing.")
        
# Dashboard function
def historical_data():
    st.title("Advanced Dashboard with Map and Visualizations")

    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is not None:
        if uploaded_file.size > 300 * 1024 * 1024:
            st.error("File size exceeds 300MB. Please upload a smaller file.")
            return

        processed_data = preprocess_data(uploaded_file)

        if processed_data is not None and not processed_data.empty:
            st.sidebar.title("Map Customization")

            st.subheader("Filter Data by Date and Time")
            datetime_min = processed_data['datetime'].min()
            datetime_max = processed_data['datetime'].max()

            years = sorted(processed_data['datetime'].dt.year.unique())
            months = list(range(1, 13))
            days = list(range(1, 32))
            times = generate_time_options()

            st.write("### Select Start Datetime")
            start_year = st.selectbox("Year", years, index=0, key="start_year")
            start_month = st.selectbox("Month", months, index=0, key="start_month")
            start_day = st.selectbox("Day", days, index=0, key="start_day")
            start_time = st.selectbox("Time (HH:MM:SS)", times, index=0, key="start_time")

            st.write("### Select End Datetime")
            end_year = st.selectbox("Year", years, index=len(years) - 1, key="end_year")
            end_month = st.selectbox("Month", months, index=len(months) - 1, key="end_month")
            end_day = st.selectbox("Day", days, index=len(days) - 1, key="end_day")
            end_time = st.selectbox("Time (HH:MM:SS)", times, index=len(times) - 1, key="end_time")

            try:
                start_datetime = datetime.strptime(f"{start_year}-{start_month:02d}-{start_day:02d} {start_time}", "%Y-%m-%d %H:%M:%S")
                end_datetime = datetime.strptime(f"{end_year}-{end_month:02d}-{end_day:02d} {end_time}", "%Y-%m-%d %H:%M:%S")
                filtered_data = processed_data[
                    (processed_data['datetime'] >= start_datetime) & 
                    (processed_data['datetime'] <= end_datetime)
                ]
            except ValueError:
                st.error("Invalid date combination. Please select valid year, month, day, and time.")
                return

            st.write(f"Displaying data for datetime between {start_datetime} and {end_datetime}:")
            st.write(filtered_data)

            # Map visualization
            plot_folium_map_with_geojson(filtered_data)

            # Chart Visualizations
            if processed_data is not None and not processed_data.empty:
             st.sidebar.title("Chart Customization")

            # Histogram Customization
            st.sidebar.subheader("Histogram Customization")
            hist_color = st.sidebar.color_picker("Select Histogram Color", "#636EFA")
            hist_barmode = st.sidebar.selectbox("Select Barmode", ['stack', 'overlay'], key="hist_barmode")

            # Scatter Plot Customization
            st.sidebar.subheader("Scatter Plot Customization")
            scatter_color = st.sidebar.color_picker("Select Scatter Plot Color", "#EF553B")
            scatter_size = st.sidebar.slider("Select Point Size", 5, 20, 10, key="scatter_size")

            # Line Plot Customization
            st.sidebar.subheader("Line Plot Customization")
            line_color = st.sidebar.color_picker("Select Line Color", "#00CC96")

            # Bar Chart Customization
            st.sidebar.subheader("Bar Chart Customization")
            bar_color = st.sidebar.color_picker("Select Bar Color", "#AB63FA")
            bar_orientation = st.sidebar.radio("Select Bar Orientation", ['vertical', 'horizontal'], key="bar_orientation")

            # 3D Scatter Plot Customization
            st.sidebar.subheader("3D Scatter Plot Customization")
            scatter_3d_color = st.sidebar.color_picker("Select 3D Scatter Plot Color", "#FFA15A")

            # Advanced Data Visualizations
            st.subheader("Advanced Data Visualizations")

            # Histogram
            st.write("### Histogram")
            if not filtered_data.empty:
                column_to_plot = st.selectbox("Select Column for Histogram", options=filtered_data.columns, key="histogram")
                fig_hist = px.histogram(filtered_data, x=column_to_plot, color_discrete_sequence=[hist_color], barmode=hist_barmode)
                st.plotly_chart(fig_hist)

            # Scatter Plot
            st.write("### Scatter Plot")
            if not filtered_data.empty:
                x_scatter = st.selectbox("Select X-axis", options=filtered_data.columns, key="scatter_x")
                y_scatter = st.selectbox("Select Y-axis", options=filtered_data.columns, key="scatter_y")
                fig_scatter = px.scatter(filtered_data, x=x_scatter, y=y_scatter, color_discrete_sequence=[scatter_color])
                fig_scatter.update_traces(marker=dict(size=scatter_size))
                st.plotly_chart(fig_scatter)

            # Line Plot
            st.write("### Line Plot")
            if not filtered_data.empty:
                x_lineplot = st.selectbox("Select X-axis", options=filtered_data.columns, key="lineplot_x")
                y_lineplot = st.selectbox("Select Y-axis", options=filtered_data.columns, key="lineplot_y")
                fig_line = px.line(filtered_data, x=x_lineplot, y=y_lineplot, color_discrete_sequence=[line_color])
                st.plotly_chart(fig_line)

            # Bar Chart
            st.write("### Bar Chart")
            if not filtered_data.empty:
                column_bar = st.selectbox("Select Column for Bar Chart", options=filtered_data.columns, key="bar")
                fig_bar = px.bar(
                    filtered_data,
                    x=column_bar if bar_orientation == 'vertical' else filtered_data.columns[1],
                    y=filtered_data.columns[1] if bar_orientation == 'vertical' else column_bar,
                    color_discrete_sequence=[bar_color]
                )
                st.plotly_chart(fig_bar)

                # 3D Scatter Plot
                if 'region_id' in processed_data.columns and 'datetime' in processed_data.columns:
                    st.write("### 3D Scatter Plot")

                    # Detect traffic-related columns
                    traffic_volume_columns = detect_traffic_volume_columns(processed_data)

                    if not traffic_volume_columns:
                        st.error("No suitable columns found for traffic volume. Please ensure the dataset includes relevant columns.")
                    else:
                        st.write(f"Detected traffic volume columns: {', '.join(traffic_volume_columns)}")

                    # Ensure the datetime column is in datetime format
                    processed_data['datetime'] = pd.to_datetime(processed_data['datetime'])

                    for col in traffic_volume_columns:
                        # Generate 3D scatter plot
                        fig_3d = px.scatter_3d(
                            processed_data,
                            x=col,  # Use the detected traffic column for X-axis
                            y='datetime',  # Use datetime column for Y-axis
                            z='region_id',  # Region or other categorical data for Z-axis
                            color_discrete_sequence=[scatter_3d_color]
                        )

                        # Update layout to ensure better datetime formatting
                        fig_3d.update_layout(
                            scene=dict(
                                yaxis=dict(
                                    title="Datetime",
                                    tickformat="%b %Y",  # Display in "Month Year" format
                                )
                            )
                        )

                        # Display the plot
                        st.plotly_chart(fig_3d)

# Run the dashboard
historical_data()