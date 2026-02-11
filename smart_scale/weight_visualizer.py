"""
Visualization module for weight predictions.
Generates Plotly charts for predicted weight values with confidence intervals.
"""

import pandas as pd
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging

class WeightVisualizer:
    """
    Creates visualizations for weight data and predictions.
    """
    
    def __init__(self, theme='light'):
        """
        Initialize the visualizer with a theme.
        
        Args:
            theme (str): Chart theme ('light' or 'dark')
        """
        self.theme = theme
        self.colors = self._get_theme_colors(theme)
    
    def _get_theme_colors(self, theme):
        """
        Get color scheme based on theme.
        
        Args:
            theme (str): Theme name
            
        Returns:
            dict: Color definitions
        """
        if theme == 'dark':
            return {
                'background': '#282c34',
                'text': '#eaeaea',
                'grid': '#3e4451',
                'line': '#61dafb',
                'area': 'rgba(97, 218, 251, 0.2)',
                'highlight': '#c678dd',
                'series': ['#61dafb', '#98c379', '#e06c75', '#d19a66', '#c678dd']
            }
        else:  # light theme
            return {
                'background': '#ffffff',
                'text': '#333333',
                'grid': '#eeeeee',
                'line': '#1f77b4',
                'area': 'rgba(31, 119, 180, 0.2)',
                'highlight': '#ff7f0e',
                'series': ['#1f77b4', '#2ca02c', '#d62728', '#ff7f0e', '#9467bd']
            }
    
    def create_prediction_chart(self, historical_data, prediction_results, method, timeframe):
        """
        Create an interactive chart showing historical data and predictions.
        
        Args:
            historical_data (DataFrame): Historical weight measurements
            prediction_results (dict): Prediction results from WeightPredictor
            method (str): Prediction method used
            timeframe (str): Selected prediction timeframe
            
        Returns:
            dict: Plotly figure object
        """
        if prediction_results is None or method not in prediction_results:
            return self._create_error_chart("No prediction data available")
            
        pred_data = prediction_results[method]
        predictions = pred_data['predictions']
        
        if historical_data.empty or predictions.empty:
            return self._create_error_chart("Insufficient data for visualization")
        
        try:
            # Create figure
            fig = go.Figure()
            
            # Add historical data
            fig.add_trace(go.Scatter(
                x=historical_data.index,
                y=historical_data['weight'],
                mode='lines+markers',
                name='Historical Weight',
                line=dict(color=self.colors['line'], width=2),
                marker=dict(size=6),
                hovertemplate='%{x|%Y-%m-%d}: %{y:.1f} kg<extra></extra>'
            ))
            
            # Add prediction line
            fig.add_trace(go.Scatter(
                x=predictions['ds'],
                y=predictions['yhat'],
                mode='lines',
                name='Predicted Weight',
                line=dict(color=self.colors['highlight'], width=2, dash='dot'),
                hovertemplate='%{x|%Y-%m-%d}: %{y:.1f} kg<extra></extra>'
            ))
            
            # Add confidence interval
            fig.add_trace(go.Scatter(
                x=pd.concat([predictions['ds'], predictions['ds'].iloc[::-1]]),
                y=pd.concat([predictions['yhat_upper'], predictions['yhat_lower'].iloc[::-1]]),
                fill='toself',
                fillcolor=self.colors['area'],
                line=dict(color='rgba(255,255,255,0)'),
                hoverinfo='skip',
                showlegend=False,
                name='95% Confidence'
            ))
            
            # Add confidence interval bounds as separate traces (for hover info)
            fig.add_trace(go.Scatter(
                x=predictions['ds'],
                y=predictions['yhat_upper'],
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hovertemplate='Upper: %{y:.1f} kg<extra></extra>',
                name='Upper Bound'
            ))
            
            fig.add_trace(go.Scatter(
                x=predictions['ds'],
                y=predictions['yhat_lower'],
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hovertemplate='Lower: %{y:.1f} kg<extra></extra>',
                name='Lower Bound'
            ))
            
            # Calculate y-axis range with padding
            all_weights = pd.concat([
                historical_data['weight'],
                predictions['yhat'],
                predictions['yhat_lower'],
                predictions['yhat_upper']
            ])
            y_min = all_weights.min() - 1
            y_max = all_weights.max() + 1
            
            # Update layout
            method_names = {
                'linear': 'Linear Regression',
                'arima': 'ARIMA Model',
                'prophet': 'Prophet Model'
            }
            
            fig.update_layout(
                title=f"Weight Prediction ({method_names.get(method, method)})",
                xaxis_title="Date",
                yaxis_title="Weight (kg)",
                yaxis=dict(range=[y_min, y_max]),
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=40, r=40, t=60, b=40),
                plot_bgcolor=self.colors['background'],
                paper_bgcolor=self.colors['background'],
                font=dict(color=self.colors['text'])
            )
            
            # Add annotation showing the timeframe
            fig.add_annotation(
                xref="paper", yref="paper",
                x=0.01, y=0.99,
                text=f"Prediction: {timeframe}",
                showarrow=False,
                font=dict(size=12),
                bgcolor="rgba(255,255,255,0.7)",
                bordercolor="gray",
                borderwidth=1,
                borderpad=4,
                align="left"
            )
            
            return fig
            
        except Exception as e:
            logging.error(f"Error creating prediction chart: {e}")
            return self._create_error_chart(f"Error: {str(e)}")
    
    def create_comparison_chart(self, historical_data, prediction_results, timeframe):
        """
        Create a chart comparing different prediction methods.
        
        Args:
            historical_data (DataFrame): Historical weight measurements
            prediction_results (dict): All prediction results from WeightPredictor
            timeframe (str): Selected prediction timeframe
            
        Returns:
            dict: Plotly figure object
        """
        if not prediction_results or len(prediction_results) == 0:
            return self._create_error_chart("No prediction data available")
        
        if historical_data.empty:
            return self._create_error_chart("Insufficient historical data")
            
        try:
            # Create figure
            fig = go.Figure()
            
            # Add historical data
            fig.add_trace(go.Scatter(
                x=historical_data.index,
                y=historical_data['weight'],
                mode='lines+markers',
                name='Historical Weight',
                line=dict(color=self.colors['line'], width=2),
                marker=dict(size=6),
                hovertemplate='%{x|%Y-%m-%d}: %{y:.1f} kg<extra></extra>'
            ))
            
            # Add prediction lines for each method
            method_names = {
                'linear': 'Linear Regression',
                'arima': 'ARIMA Model',
                'prophet': 'Prophet Model'
            }
            
            for i, (method, pred_data) in enumerate(prediction_results.items()):
                predictions = pred_data['predictions']
                color = self.colors['series'][i % len(self.colors['series'])]
                
                fig.add_trace(go.Scatter(
                    x=predictions['ds'],
                    y=predictions['yhat'],
                    mode='lines',
                    name=method_names.get(method, method),
                    line=dict(color=color, width=2, dash='dot'),
                    hovertemplate='%{x|%Y-%m-%d}: %{y:.1f} kg<extra></extra>'
                ))
            
            # Calculate y-axis range with padding
            all_y_values = historical_data['weight'].values
            
            for pred_data in prediction_results.values():
                predictions = pred_data['predictions']
                all_y_values = np.concatenate([all_y_values, predictions['yhat'].values])
            
            y_min = np.min(all_y_values) - 1
            y_max = np.max(all_y_values) + 1
            
            # Update layout
            fig.update_layout(
                title="Weight Prediction Comparison",
                xaxis_title="Date",
                yaxis_title="Weight (kg)",
                yaxis=dict(range=[y_min, y_max]),
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=40, r=40, t=60, b=40),
                plot_bgcolor=self.colors['background'],
                paper_bgcolor=self.colors['background'],
                font=dict(color=self.colors['text'])
            )
            
            # Add annotation showing the timeframe
            fig.add_annotation(
                xref="paper", yref="paper",
                x=0.01, y=0.99,
                text=f"Prediction: {timeframe}",
                showarrow=False,
                font=dict(size=12),
                bgcolor="rgba(255,255,255,0.7)",
                bordercolor="gray",
                borderwidth=1,
                borderpad=4,
                align="left"
            )
            
            return fig
            
        except Exception as e:
            logging.error(f"Error creating comparison chart: {e}")
            return self._create_error_chart(f"Error: {str(e)}")
    
    def _create_error_chart(self, message):
        """
        Create an error chart with a message.
        
        Args:
            message (str): Error message to display
            
        Returns:
            dict: Plotly figure object
        """
        fig = go.Figure()
        
        fig.update_layout(
            title="Chart Error",
            annotations=[
                dict(
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    text=message,
                    showarrow=False,
                    font=dict(size=16)
                )
            ],
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False
            ),
            plot_bgcolor=self.colors['background'],
            paper_bgcolor=self.colors['background'],
            font=dict(color=self.colors['text'])
        )
        
        return fig