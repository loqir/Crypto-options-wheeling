import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path
import plotly.express as px
import pandas as pd
import numpy as np

pio.templates.default = "plotly_dark"

############## Plotting functions#################

def get_segment_color(value, vmin, vmax):
    if pd.isna(value):
        return "gray"

    if vmax == vmin:
        return "orange"

    scaled = (value - vmin) / (vmax - vmin)

    if scaled < 0.33:
        return "green"
    elif scaled < 0.66:
        return "orange"
    else:
        return "red"


def build_plot(
    grp,
    x_col,
    y_col="theta",
    width=520,
    height=340,
):
    temp = grp.sort_values(x_col).reset_index(drop=True).copy()

    # Convert datetime to string for display
    if pd.api.types.is_datetime64_any_dtype(temp[x_col]):
        x_display = temp[x_col].dt.strftime("%Y-%m-%d").tolist()
        point_labels = x_display
    else:
        x_display = temp[x_col].tolist()
        point_labels = [str(int(v)) if pd.notna(v) else "" for v in temp[x_col]]

    temp["_x_display"] = x_display

    fig = go.Figure()

    # Use absolute theta magnitude within this group to determine line color
    theta_mag = temp[y_col].abs()
    vmin = theta_mag.min()
    vmax = theta_mag.max()

    # Draw line as colored segments
    for i in range(len(temp) - 1):
        seg_value = (theta_mag.iloc[i] + theta_mag.iloc[i + 1]) / 2
        seg_color = get_segment_color(seg_value, vmin, vmax)

        fig.add_trace(
            go.Scatter(
                x=[temp["_x_display"].iloc[i], temp["_x_display"].iloc[i + 1]],
                y=[temp[y_col].iloc[i], temp[y_col].iloc[i + 1]],
                mode="lines",
                line=dict(width=2, color=seg_color),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # Points + labels + hover
    temp["theta_gamma_ratio"] = np.where(
        temp["gamma"] != 0, temp["theta"] / temp["gamma"], "Undefined"
    )
    fig.add_trace(
        go.Scatter(
            x=temp["_x_display"],
            y=temp[y_col],
            mode="markers+text",
            name="Observed",
            text=point_labels,
            textposition="top center",
            textfont=dict(size=9),
            marker=dict(size=6, color="white"),  # Changed color to white
            customdata=np.stack([
                temp["instrument_name"],
                temp["mark_iv"],
                temp["underlying_price"],
                temp["best_bid_price"],
                temp["best_ask_price"],
                temp["gamma"],
                temp["theta_gamma_ratio"],
            ], axis=1),
            hovertemplate=(
                f"{x_col}: %{{x}}<br>"
                f"{y_col}: %{{y}}<br>"
                "Mark IV: %{customdata[1]}<br>"
                "Underlying: %{customdata[2]}<br>"
                "Best Bid: %{customdata[3]}<br>"
                "Best Ask: %{customdata[4]}<br>"
                "Gamma: %{customdata[5]}<br>"
                "Theta/Gamma: %{customdata[6]:.3f}<br>"
                "Instrument: %{customdata[0]}<extra></extra>"
            )
        )
    )

    fig.update_layout(
        title=None,
        xaxis_title=x_col,
        yaxis_title=y_col,
        hovermode="closest",
        width=width,
        height=height,
        margin=dict(l=40, r=20, t=20, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=9)
        ),
        xaxis=dict(
            tickfont=dict(size=9),
            title_font=dict(size=11)
        ),
        yaxis=dict(
            tickfont=dict(size=9),
            title_font=dict(size=11)
        )
    )

    return fig

def export_html(
    df,
    group_by_col,
    x_col,
    output_file,
    y_col="theta",
    page_title="Charts",
    summary_text="",
):
    groups = {
        group_value: grp.sort_values(x_col).reset_index(drop=True)
        for group_value, grp in df.groupby(group_by_col)
    }

    html_parts = ["""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Charts</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 16px;
                background: #121212; /* Dark background */
                color: #e0e0e0; /* Light text */
            }
            h1 {
                margin-bottom: 6px;
                font-size: 24px;
                color: #ffffff; /* White text for headings */
            }
            .summary {
                margin-bottom: 16px;
                color: #b0b0b0; /* Light gray text for summary */
                font-size: 14px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr); /* 3 plots per row */
                gap: 16px;
                align-items: start;
            }
            .chart-block {
                background: #1e1e1e; /* Darker background for chart blocks */
                border: 1px solid #333; /* Subtle border */
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.2);
            }
            .chart-title {
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 6px;
                color: #ffffff; /* White text for chart titles */
            }
        </style>
    </head>
    <body>
    """]

    html_parts.append(f"<h1>{page_title}</h1>")
    html_parts.append(f"<div class='summary'>{summary_text}</div>")
    html_parts.append("<div class='grid'>")

    for group_value in sorted(groups.keys()):
        grp = groups[group_value]

        fig = build_plot(
            grp=grp,
            x_col=x_col,
            y_col=y_col,
        )

        html_parts.append(
            f"<div class='chart-block'><div class='chart-title'>{group_by_col}: {group_value}</div>"
        )
        html_parts.append(pio.to_html(fig, full_html=False, include_plotlyjs="cdn"))
        html_parts.append("</div>")

    html_parts.append("</div></body></html>")

    output_path = Path(output_file)
    output_path.write_text("".join(html_parts), encoding="utf-8")
    return str(output_path)

def build_time_series_plot(
    df,
    x_col="timestamp",
    y_col="theta",
    group_col="instrument_name",
    sort_col="expiration_sg_dt",  # Column to sort by (e.g., expiry date)
    width=520,
    height=340,
):
    fig = go.Figure()

    # Sort the DataFrame by the sort column (e.g., expiration date)
    df = df.sort_values(by=sort_col).reset_index(drop=True)

    # Use a predefined Plotly color palette
    color_palette = px.colors.qualitative.Set1
    color_count = len(color_palette)

    # Group by the specified column (e.g., instrument_name)
    for i, (group_value, grp) in enumerate(df.groupby(group_col, sort=False)):  # Ensure group order follows sorted DataFrame
        grp = grp.sort_values(x_col).reset_index(drop=True)

        # Assign a color from the palette, cycling through if there are more groups than colors
        line_color = color_palette[i % color_count]

        # Add a line for each group, ensuring lines are only connected within the same group
        if len(grp) > 1:
            fig.add_trace(
                go.Scatter(
                    x=grp[x_col],
                    y=grp[y_col],
                    mode="lines+markers",
                    name=str(group_value).split("-")[1],  # Legend name
                    line=dict(color=line_color),
                    marker=dict(color=line_color),
                    text=grp["instrument_name"],
                    customdata=np.stack(
                        [
                            grp["mark_iv"],
                            grp["underlying_price"],
                            grp["gamma"],
                            grp["theta"] / grp["gamma"],  
                        ],
                        axis=-1,
                    ),
                    hovertemplate=(
                        f"{x_col}: %{{x}}<br>"
                        f"{y_col}: %{{y}}<br>"
                        "Mark IV: %{customdata[0]:.2f}<br>"
                        "Underlying Price: %{customdata[1]:.2f}<br>"
                        "Gamma: %{customdata[2]:.5f}<br>"
                        "Theta/Gamma Ratio: %{customdata[3]:.7f}<br>"
                        "Instrument: %{text}<extra></extra>"
                    ),
                )
            )
        else:
            # Ensure legend is shown for single points
            fig.add_trace(
                go.Scatter(
                    x=grp[x_col],
                    y=grp[y_col],
                    mode="markers",
                    name=str(group_value).split("-")[1],  # Legend name
                    marker=dict(color=line_color, size=10),
                    text=grp["instrument_name"],
                    customdata=np.stack(
                        [
                            grp["mark_iv"],
                            grp["underlying_price"],
                            grp["gamma"],
                            grp["gamma"] / grp["theta"],  # gamma/theta ratio
                        ],
                        axis=-1,
                    ),
                    hovertemplate=(
                        f"{x_col}: %{{x}}<br>"
                        f"{y_col}: %{{y}}<br>"
                        "Mark IV: %{customdata[0]:.2f}<br>"
                        "Underlying Price: %{customdata[1]:.2f}<br>"
                        "Gamma: %{customdata[2]:.4f}<br>"
                        "Gamma/Theta Ratio: %{customdata[3]:.4f}<br>"
                        "Instrument: %{text}<extra></extra>"
                    ),
                    showlegend=True,
                )
            )

    fig.update_layout(
        title=None,
        xaxis_title=x_col,
        yaxis_title=y_col,
        hovermode="closest",
        width=width,
        height=height,
        margin=dict(l=40, r=20, t=20, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=9)
        ),
        xaxis=dict(
            tickfont=dict(size=9),
            title_font=dict(size=11)
        ),
        yaxis=dict(
            tickfont=dict(size=9),
            title_font=dict(size=11)
        )
    )

    return fig

def export_time_series_html(
    df,
    group_by_col,
    x_col,
    output_file,
    y_col="theta",
    page_title="Time Series Charts",
    summary_text="",
):
    groups = {
        group_value: grp.sort_values(x_col).reset_index(drop=True)
        for group_value, grp in df.groupby(group_by_col)
    }

    html_parts = ["""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Time Series Charts</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 16px;
                background: #121212; /* Dark background */
                color: #e0e0e0; /* Light text */
            }
            h1 {
                margin-bottom: 6px;
                font-size: 24px;
                color: #ffffff; /* White text for headings */
            }
            .summary {
                margin-bottom: 16px;
                color: #b0b0b0; /* Light gray text for summary */
                font-size: 14px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr); /* 3 plots per row */
                gap: 16px;
                align-items: start;
            }
            .chart-block {
                background: #1e1e1e; /* Darker background for chart blocks */
                border: 1px solid #333; /* Subtle border */
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.2);
            }
            .chart-title {
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 6px;
                color: #ffffff; /* White text for chart titles */
            }
        </style>
    </head>
    <body>
    """]

    html_parts.append(f"<h1>{page_title}</h1>")
    html_parts.append(f"<div class='summary'>{summary_text}</div>")
    html_parts.append("<div class='grid'>")

    for group_value in sorted(groups.keys()):
        grp = groups[group_value]

        fig = build_time_series_plot(
            df=grp,
            x_col=x_col,
            y_col=y_col,
        )

        html_parts.append(
            f"<div class='chart-block'><div class='chart-title'>{group_by_col}: {group_value}</div>"
        )
        html_parts.append(pio.to_html(fig, full_html=False, include_plotlyjs="cdn"))
        html_parts.append("</div>")

    html_parts.append("</div></body></html>")

    output_path = Path(output_file)
    output_path.write_text("".join(html_parts), encoding="utf-8")
    return str(output_path)
