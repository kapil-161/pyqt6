"""
Visualization functions for DSSAT output data
"""
# OPTIMIZED: Import only what's needed from plotly
from plotly.graph_objects import Figure, Scatter
import logging
# OPTIMIZED: Import only what's needed from pandas
from pandas import DataFrame
from typing import List

logger = logging.getLogger(__name__)

def create_plot(data: DataFrame, x_var: str, y_var: str, treatments: List[str]) -> Figure:
    """Create plot with simulated and observed data."""
    fig = Figure()
    
    if not (x_var and y_var) or data.empty:
        return fig
        
    try:
        y_vars = y_var if isinstance(y_var, list) else [y_var]
        
        for trt in treatments:
            treatment_data = data[data.get("TRT", data.get("TRNO")) == trt]
            if treatment_data.empty:
                logger.warning(f"No data for treatment: {trt}")
                continue
                
            for y_var_item in y_vars:
                # Plot simulated data if available
                if y_var_item in treatment_data.columns:
                    fig.add_trace(
                        Scatter(
                            x=treatment_data[x_var],
                            y=treatment_data[y_var_item],
                            mode="lines+markers",
                            name=f"{y_var_item} (Simulated, TRT {trt})",
                            line=dict(dash="solid"),
                        )
                    )
                    
                # Plot observed data if available
                obs_mask = treatment_data[y_var_item].notna()
                if obs_mask.any():
                    fig.add_trace(
                        Scatter(
                            x=treatment_data[obs_mask][x_var],
                            y=treatment_data[obs_mask][y_var_item],
                            mode="markers",
                            name=f"{y_var_item} (Observed, TRT {trt})",
                            marker=dict(symbol="circle", size=10, color="red"),
                        )
                    )
        
        # Update layout once
        fig.update_layout(
            title="",
            xaxis_title=x_var,
            yaxis_title=", ".join(y_vars),
            template="plotly_white",
            height=600,
            showlegend=True,
        )
        
    except Exception as e:
        logger.error(f"Error creating plot: {str(e)}")
        
    return fig