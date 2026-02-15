"""
Weight prediction module for Smart Scale application.
Implements multiple forecasting methods with confidence intervals.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import warnings
import logging

# Suppress non-critical warnings
warnings.filterwarnings("ignore")

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet package not installed. Prophet forecasting will not be available.")

class WeightPredictor:
    """
    Provides multiple methods for predicting future weight values
    based on historical measurement data.
    """
    
    def __init__(self, csv_file):
        """
        Initialize the weight predictor with the path to the CSV file.
        
        Args:
            csv_file (str): Path to the CSV file containing historical measurements
        """
        self.csv_file = csv_file
        self.data = None
        self.user_data = {}
        self.load_data()
    
    def load_data(self):
        """
        Load and preprocess data from the CSV file.
        """
        try:
            df = pd.read_csv(self.csv_file)
            # Check if required columns exist
            if 'weight' not in df.columns or 'timestamp' not in df.columns or 'USER_NAME' not in df.columns:
                logging.error("CSV file missing required columns (weight, timestamp, USER_NAME)")
                return
                
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Set timestamp as index
            df = df.set_index('timestamp')
            
            # Sort by timestamp
            df = df.sort_index()
            
            self.data = df
            
            # Split data by user
            for user in df['USER_NAME'].unique():
                self.user_data[user] = df[df['USER_NAME'] == user].copy()
                
            logging.info(f"Data loaded successfully. Found {len(df)} measurements for {len(self.user_data)} users.")
        except Exception as e:
            logging.error(f"Error loading data: {e}")
    
    def get_users(self):
        """
        Get list of users with available data.
        
        Returns:
            list: List of usernames
        """
        return list(self.user_data.keys())
    
    def get_user_data(self, username):
        """
        Get data for a specific user.
        
        Args:
            username (str): Username to get data for
            
        Returns:
            DataFrame: User's measurement data
        """
        return self.user_data.get(username, pd.DataFrame())
    
    def predict_linear_regression(self, username, days_ahead):
        """
        Predict future weight using simple linear regression with time-weighted observations.
        
        Args:
            username (str): Username to predict for
            days_ahead (int): Number of days to predict ahead
            
        Returns:
            dict: Prediction results with confidence intervals
        """
        user_df = self.get_user_data(username)
        
        if user_df.empty or len(user_df) < 5:  # Need at least 5 data points
            logging.warning(f"Not enough data for user {username} to make predictions")
            return None
            
        try:
            # Prepare data for linear regression
            X = np.array(range(len(user_df))).reshape(-1, 1)
            y = user_df['weight'].values
            
            # Calculate time weights based on intervals between observations
            time_diffs = user_df.index.to_series().diff().dt.total_seconds() / 86400  # Convert to days
            time_diffs.iloc[0] = time_diffs.iloc[1] if len(time_diffs) > 1 else 1  # Handle first value
            
            # Normalize weights (0 to 1 range)
            weights = time_diffs / time_diffs.max()
            weights = np.maximum(weights, 0.1)  # Ensure minimum weight of 0.1
            
            # Fit weighted linear regression model
            model = LinearRegression()
            model.fit(X, y, sample_weight=weights)
            
            # Create prediction dates
            last_date = user_df.index.max()
            future_dates = pd.date_range(start=last_date, periods=days_ahead + 1, freq='D')[1:]
            
            # Create X values for prediction
            X_pred = np.array(range(len(user_df), len(user_df) + days_ahead)).reshape(-1, 1)
            
            # Make predictions
            y_pred = model.predict(X_pred)
            
            # Calculate weighted prediction intervals (95% confidence)
            weighted_residuals = (y - model.predict(X)) * np.sqrt(weights)
            sse = np.sum(weighted_residuals ** 2)
            
            # Standard error of the regression
            se = np.sqrt(sse / (len(y) - 2))
            
            # Calculate confidence intervals
            t_value = 1.96  # Approximate t-value for 95% confidence
            
            # Calculate prediction intervals
            y_lower = y_pred - t_value * se
            y_upper = y_pred + t_value * se
            
            # Create prediction DataFrame
            pred_df = pd.DataFrame({
                'ds': future_dates,
                'yhat': y_pred,
                'yhat_lower': y_lower,
                'yhat_upper': y_upper
            })
            
            return {
                'method': 'linear_regression',
                'predictions': pred_df,
                'last_value': user_df['weight'].iloc[-1],
                'last_date': last_date
            }
            
        except Exception as e:
            logging.error(f"Error in linear regression prediction: {e}")
            return None
    
    def predict_arima(self, username, days_ahead):
        """
        Predict future weight using ARIMA model with time-weighted observations.
        Observations with longer time intervals since the previous measurement
        receive higher weight (importance).
        
        Args:
            username (str): Username to predict for
            days_ahead (int): Number of days to predict ahead
            
        Returns:
            dict: Prediction results with confidence intervals
        """
        user_df = self.get_user_data(username)
        
        if user_df.empty or len(user_df) < 10:  # Need more data for ARIMA
            logging.warning(f"Not enough data for user {username} to make ARIMA predictions")
            return None
            
        try:
            # Get weight series (original, unmodified values)
            series = user_df['weight'].copy()
            
            # Calculate time intervals between observations (in days)
            time_diffs = user_df.index.to_series().diff().dt.total_seconds() / 86400
            time_diffs.iloc[0] = time_diffs.iloc[1] if len(time_diffs) > 1 else 1
            
            # Normalize time weights (0 to 1 range)
            # Longer intervals -> higher weight (more important observation)
            time_weights = time_diffs / time_diffs.max()
            time_weights = np.maximum(time_weights, 0.1)  # Ensure minimum weight of 0.1
            
            # Resample to regular daily frequency using interpolation
            # This helps ARIMA work better with irregular time series
            daily_series = series.resample('D').mean().interpolate(method='linear')
            
            # Check if differencing is needed (stationarity test)
            adf_result = adfuller(daily_series.dropna())
            p_value = adf_result[1]
            
            # Set ARIMA parameters based on stationarity
            if p_value < 0.05:  # Stationary series
                order = (2, 0, 2)
            else:  # Non-stationary series
                order = (2, 1, 2)
            
            # Build observation weights on the daily grid:
            # For days that had actual measurements, use the computed time weight.
            # For interpolated days, use a lower default weight.
            daily_weights = pd.Series(0.1, index=daily_series.index)
            for idx, w in zip(series.index, time_weights):
                # Find the closest daily index
                closest_day = daily_weights.index[daily_weights.index.get_indexer([idx], method='nearest')[0]]
                daily_weights[closest_day] = max(daily_weights[closest_day], w)
            
            # Invert weights to get sigma^2 for GLS-like weighting in ARIMA
            # Higher weight -> lower variance (more trusted observation)
            # sigma^2 proportional to 1/weight
            sigma2 = 1.0 / daily_weights.values
            sigma2 = sigma2 / sigma2.min()  # Normalize so minimum is 1
            
            # Fit ARIMA model on original weight values (not multiplied)
            model = ARIMA(daily_series, order=order)
            model_fit = model.fit()
            
            # Refit with GLS weights if possible (use sigma2 as observation noise)
            # statsmodels ARIMA doesn't natively support observation weights,
            # so we use a WLS approach: transform the series by dividing by sqrt(sigma2)
            # and then predict on the original scale
            sqrt_sigma = np.sqrt(sigma2)
            weighted_series_transformed = daily_series / sqrt_sigma
            
            try:
                model_weighted = ARIMA(weighted_series_transformed, order=order)
                model_weighted_fit = model_weighted.fit()
                
                # Make predictions on the transformed scale
                forecast = model_weighted_fit.get_forecast(steps=days_ahead)
                mean_forecast = forecast.predicted_mean
                conf_int = forecast.conf_int(alpha=0.05)
                
                # Scale predictions back to original scale
                # For future predictions, assume weight = 1 (no scaling needed)
                # The last observation's sigma is a reasonable baseline
                mean_values = mean_forecast.values
                lower_values = conf_int.iloc[:, 0].values
                upper_values = conf_int.iloc[:, 1].values
            except Exception:
                # Fallback: use unweighted ARIMA
                forecast = model_fit.get_forecast(steps=days_ahead)
                mean_values = forecast.predicted_mean.values
                conf_int = forecast.conf_int(alpha=0.05)
                lower_values = conf_int.iloc[:, 0].values
                upper_values = conf_int.iloc[:, 1].values
            
            # Create prediction dates
            last_date = user_df.index.max()
            future_dates = pd.date_range(start=last_date, periods=days_ahead + 1, freq='D')[1:]
            
            # Create prediction DataFrame
            pred_df = pd.DataFrame({
                'ds': future_dates,
                'yhat': mean_values,
                'yhat_lower': lower_values,
                'yhat_upper': upper_values
            })
            
            return {
                'method': 'arima',
                'predictions': pred_df,
                'last_value': series.iloc[-1],
                'last_date': last_date
            }
            
        except Exception as e:
            logging.error(f"Error in ARIMA prediction: {e}")
            return None
    
    def predict_prophet(self, username, days_ahead):
        """
        Predict future weight using Facebook Prophet.
        
        Args:
            username (str): Username to predict for
            days_ahead (int): Number of days to predict ahead
            
        Returns:
            dict: Prediction results with confidence intervals
        """
        if not PROPHET_AVAILABLE:
            logging.warning("Prophet package not installed.")
            return None
            
        user_df = self.get_user_data(username)
        
        if user_df.empty or len(user_df) < 5:  # Need at least 5 data points
            logging.warning(f"Not enough data for user {username} to make Prophet predictions")
            return None
            
        try:
            # Calculate time intervals between observations (in days)
            time_diffs = user_df.index.to_series().diff().dt.total_seconds() / 86400
            time_diffs.iloc[0] = time_diffs.iloc[1] if len(time_diffs) > 1 else 1
            
            # Normalize time weights (0 to 1 range) - longer intervals get higher weights
            time_weights = time_diffs / time_diffs.max()
            time_weights = np.maximum(time_weights, 0.1)  # Ensure minimum weight of 0.1
            
            # Apply time weights to weight values
            weighted_values = user_df['weight'].values * time_weights.values
            
            # Prepare data for Prophet
            prophet_df = pd.DataFrame({
                'ds': user_df.index,
                'y': weighted_values
            })
            
            # Fit Prophet model with weekly seasonality if enough data
            model = Prophet(interval_width=0.95)  # 95% confidence interval
            if len(user_df) >= 14:  # At least 2 weeks of data
                model.add_seasonality(name='weekly', period=7, fourier_order=3)
            model.fit(prophet_df)
            
            # Create future dataframe
            future = model.make_future_dataframe(periods=days_ahead)
            
            # Make predictions
            forecast = model.predict(future)
            
            # Get only future predictions
            last_date = user_df.index.max()
            future_forecast = forecast[forecast['ds'] > last_date].reset_index(drop=True)
            
            return {
                'method': 'prophet',
                'predictions': future_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']],
                'last_value': user_df['weight'].iloc[-1],
                'last_date': last_date
            }
            
        except Exception as e:
            logging.error(f"Error in Prophet prediction: {e}")
            return None
    
    def predict(self, username, method, days_ahead):
        """
        Make predictions using the specified method.
        
        Args:
            username (str): Username to predict for
            method (str): Prediction method ('linear', 'arima', 'prophet')
            days_ahead (int): Number of days to predict ahead
            
        Returns:
            dict: Prediction results
        """
        if method == 'linear':
            return self.predict_linear_regression(username, days_ahead)
        elif method == 'arima':
            return self.predict_arima(username, days_ahead)
        elif method == 'prophet':
            return self.predict_prophet(username, days_ahead)
        else:
            logging.error(f"Unknown prediction method: {method}")
            return None
            
    def get_all_predictions(self, username, days_ahead):
        """
        Get predictions from all available methods.
        
        Args:
            username (str): Username to predict for
            days_ahead (int): Number of days to predict ahead
            
        Returns:
            dict: Dictionary with predictions from all methods
        """
        results = {}
        
        # Linear regression (always available)
        linear_pred = self.predict_linear_regression(username, days_ahead)
        if linear_pred:
            results['linear'] = linear_pred
            
        # ARIMA (if enough data)
        arima_pred = self.predict_arima(username, days_ahead)
        if arima_pred:
            results['arima'] = arima_pred
            
        # Prophet (if available and enough data)
        if PROPHET_AVAILABLE:
            prophet_pred = self.predict_prophet(username, days_ahead)
            if prophet_pred:
                results['prophet'] = prophet_pred
                
        return results