import pandas as pd
import json
import plotly
from flask import Flask, render_template, send_file, abort, request, jsonify
import os
import datetime
import sys
import logging

# Add the project root to the Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(app_dir)
sys.path.insert(0, project_root)

# Import our modules
from smart_scale.weight_predictor import WeightPredictor
from smart_scale.weight_visualizer import WeightVisualizer
from smart_scale.user_manager import UserManager

# Path to the CSV file and users file
CSV_FILE_PATH = os.path.join(project_root, 'scale_data.csv')
USERS_FILE_PATH = os.path.join(project_root, 'smart_scale', 'users.json')

# Initialize components
weight_predictor = WeightPredictor(CSV_FILE_PATH)
weight_visualizer = WeightVisualizer()
user_manager = UserManager(USERS_FILE_PATH)

app = Flask(__name__)

@app.route('/')
def dashboard():
    try:
        if not os.path.exists(CSV_FILE_PATH):
            return render_template('index.html', error="Nie znaleziono pliku scale_data.csv. Wykonaj najpierw pomiar.")

        df = pd.read_csv(CSV_FILE_PATH)
        if df.empty:
            return render_template('index.html', error="Plik CSV jest pusty. Brak danych do wyświetlenia.")

        # Enforce expected columns and order (same as DataStorage)
        COLUMNS_ORDER = [
            'USER_NAME', 'weight', 'impedance', 'lbm', 'fat_percentage', 'water_percentage',
            'muscle_mass', 'bone_mass', 'bmi', 'bmr', 'visceral_fat',
            'ideal_weight', 'metabolic_age', 'timestamp'
        ]

        # Add any missing columns with None so DataFrame is consistent
        for col in COLUMNS_ORDER:
            if col not in df.columns:
                df[col] = None

        # Keep only expected columns and in fixed order
        df = df.reindex(columns=COLUMNS_ORDER)

        # --- Prepare timestamps and date column ---
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
        df.dropna(subset=['timestamp'], inplace=True)
        df['date'] = df['timestamp'].dt.date

        # Get all available users for dropdown
        all_users = []
        if 'USER_NAME' in df.columns:
            # Extract unique users
            unique_users = df['USER_NAME'].dropna().unique().tolist()
            # Sort users but make sure 'lukasz' is first if present
            if 'lukasz' in unique_users:
                unique_users.remove('lukasz')
                all_users = ['lukasz'] + sorted(unique_users)
            else:
                all_users = sorted(unique_users)
        
        # Read optional date range and user filter from query params
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        selected_user = request.args.get('user')
        
        # If no user is selected and there are users available, select the first one
        if (not selected_user or selected_user == '') and all_users:
            selected_user = all_users[0]
            
        start_date = None
        end_date = None
        try:
            if start_date_str:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str:
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except Exception:
            # parse error — ignore filters
            start_date = None
            end_date = None

        # If no dates provided, default to last 30 days
        if not start_date_str and not end_date_str:
            today = datetime.date.today()
            default_end = today
            default_start = today - datetime.timedelta(days=30)
            start_date = default_start
            end_date = default_end
            # reflect into strings passed back to template
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()

        # Apply date-only filtering (ignore time)
        if start_date and end_date:
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        elif start_date:
            df = df[df['date'] >= start_date]
        elif end_date:
            df = df[df['date'] <= end_date]
            
        # Apply user filtering if selected
        if selected_user and 'USER_NAME' in df.columns:
            df = df[df['USER_NAME'] == selected_user]

        if df.empty:
            return render_template('index.html', error="Brak danych w wybranym zakresie dat lub dla wybranego użytkownika.", 
                                start_date=start_date_str or '', end_date=end_date_str or '',
                                all_users=all_users, selected_user=selected_user)

        # --- Simple statistical analysis on filtered data ---
        last_measurement = df.iloc[-1].to_dict()
        total_measurements = len(df)
        avg_weight = df['weight'].mean()
        min_weight = df['weight'].min()
        max_weight = df['weight'].max()

        stats = {
            'total': total_measurements,
            'avg_weight': round(avg_weight, 2),
            'min_weight': min_weight,
            'max_weight': max_weight
        }

        # Human-readable date labels (preserve time in labels)
        df['date_str'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')

        # Build chart data defensively (columns may still contain None)
        # Create time-aware series with x-y points for proper time scale rendering
        def series_xy(col):
            if col not in df.columns:
                return []
            s = df[['timestamp', col]].dropna(subset=[col])
            # Return epoch milliseconds timestamp as x value for time scale
            return [{'x': int(t.timestamp() * 1000), 'y': float(v)} for t, v in zip(s['timestamp'], s[col])]

        chart_data = {
            'weight': series_xy('weight'),
            'fat_percentage': series_xy('fat_percentage'),
            'muscle_mass': series_xy('muscle_mass'),
            'water_percentage': series_xy('water_percentage')
        }

        # Last measurement - present fields only
        last_measurement = {k: (None if pd.isna(v) else v) for k, v in df.iloc[-1].to_dict().items()}

        return render_template('index.html', last=last_measurement, stats=stats, chart_data=chart_data, 
                          start_date=start_date_str or '', end_date=end_date_str or '',
                          all_users=all_users, selected_user=selected_user)

    except Exception as e:
        return render_template('index.html', error=f"Wystąpił błąd: {e}")

@app.route('/download')
def download_csv():
    try:
        return send_file(CSV_FILE_PATH, as_attachment=True, download_name='scale_data.csv')
    except FileNotFoundError:
        abort(404, description="CSV file has not been created yet.")

@app.route('/prediction')
def weight_prediction():
    try:
        # Get parameters from request
        username = request.args.get('user', '')
        method = request.args.get('method', 'linear')
        days_str = request.args.get('days', '30')
        
        # Convert days to integer
        try:
            days = int(days_str)
        except ValueError:
            days = 30  # Default to 30 days
            
        # Map timeframe to display name
        timeframe_map = {
            '7': '1 Week',
            '30': '1 Month',
            '90': '3 Months',
            '180': '6 Months',
            '365': '1 Year'
        }
        timeframe = timeframe_map.get(days_str, f"{days} Days")
        
        # Check if user exists
        if not username:
            error_fig = weight_visualizer._create_error_chart("Please select a user")
            return jsonify({
                'error': 'No user selected',
                'graphJSON': json.dumps(error_fig, cls=plotly.utils.PlotlyJSONEncoder)
            })
            
        # Read and process the CSV file
        if not os.path.exists(CSV_FILE_PATH):
            error_fig = weight_visualizer._create_error_chart("CSV file not found")
            return jsonify({
                'error': 'CSV file not found',
                'graphJSON': json.dumps(error_fig, cls=plotly.utils.PlotlyJSONEncoder)
            })
            
        # Read CSV and clean data
        df = pd.read_csv(CSV_FILE_PATH)
        
        # Check for proper columns
        required_columns = ['USER_NAME', 'timestamp', 'weight']
        if not all(col in df.columns for col in required_columns):
            error_fig = weight_visualizer._create_error_chart("CSV file missing required columns")
            return jsonify({
                'error': 'CSV file missing required columns',
                'graphJSON': json.dumps(error_fig, cls=plotly.utils.PlotlyJSONEncoder)
            })
            
        # Fix malformed rows where username is in first column
        # Remove any rows that have non-numeric values in weight column
        try:
            df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
            df = df.dropna(subset=['weight'])
        except Exception as data_error:
            logging.warning(f"Error converting weight to numeric: {data_error}")
            # This is a more aggressive fix for malformed data
            good_rows = []
            for _, row in df.iterrows():
                try:
                    float(row['weight'])
                    good_rows.append(row)
                except (ValueError, TypeError):
                    continue
            if good_rows:
                df = pd.DataFrame(good_rows)
            else:
                error_fig = weight_visualizer._create_error_chart("No valid weight measurements found")
                return jsonify({
                    'error': 'No valid weight measurements found',
                    'graphJSON': json.dumps(error_fig, cls=plotly.utils.PlotlyJSONEncoder)
                })
                
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        
        # Filter for the specified user
        user_df = df[df['USER_NAME'] == username].sort_values('timestamp')
        
        if user_df.empty:
            error_fig = weight_visualizer._create_error_chart(f"No data for user: {username}")
            return jsonify({
                'error': 'No data for selected user',
                'graphJSON': json.dumps(error_fig, cls=plotly.utils.PlotlyJSONEncoder)
            })
            
        # Set timestamp as index
        user_df = user_df.set_index('timestamp')
        
        # Generate predictions based on method
        if method == 'comparison':
            # Get all available predictions
            predictions = weight_predictor.get_all_predictions(username, days)
            if not predictions:
                error_fig = weight_visualizer._create_error_chart("No prediction models available")
                return jsonify({
                    'error': 'No prediction models available',
                    'graphJSON': json.dumps(error_fig, cls=plotly.utils.PlotlyJSONEncoder)
                })
                
            # Create comparison chart
            fig = weight_visualizer.create_comparison_chart(user_df, predictions, timeframe)
        else:
            # Get single method prediction
            predictions = weight_predictor.get_all_predictions(username, days)
            if not predictions or method not in predictions:
                error_fig = weight_visualizer._create_error_chart(f"Prediction method {method} not available")
                return jsonify({
                    'error': f'Prediction method {method} not available',
                    'graphJSON': json.dumps(error_fig, cls=plotly.utils.PlotlyJSONEncoder)
                })
                
            # Create single method chart
            fig = weight_visualizer.create_prediction_chart(user_df, predictions, method, timeframe)
        
        # Convert to JSON
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify({
            'success': True,
            'graphJSON': graphJSON
        })
        
    except Exception as e:
        logging.exception("Error in prediction route")
        error_fig = weight_visualizer._create_error_chart(f"Error: {str(e)}")
        return jsonify({
            'error': str(e),
            'graphJSON': json.dumps(error_fig, cls=plotly.utils.PlotlyJSONEncoder)
        })

@app.route('/page2')
def page2():
    return render_template('page2.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
