import flask
import json
from flask import Flask, request, render_template, jsonify, redirect, url_for
import os
import time
import pandas as pd
import numpy as np
import requests
from train_generic import train_predict
from azure.storage.blob import BlobServiceClient


print("app is started")
# Create flask app
app = Flask(__name__)

app._static_folder = 'static'

blob_service_client = BlobServiceClient.from_connection_string("DefaultEndpointsProtocol=https;AccountName=salesforecastingstorage;AccountKey=pgnbKGA3fcy+X+JcSMVX/vj6My6Kg46ycdsJQUBn9GdTJ6rSW8+CGZeYqRqhLVG/Bu4pbpKKSCVQ+ASt3/5XPg==;EndpointSuffix=core.windows.net")
container_client = blob_service_client.get_container_client("fit-blob")

@app.route("/")
def home():
    return render_template("index1.html")

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    st=time.time()
    if request.method == 'POST':
        # Get the uploaded CSV file
        uploaded_file = request.files['file']
        num_months = int(request.form.get('NOM'))

        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                #uploading train csv to blob storage
                csv_data = df.to_csv(index=False)
                blob_name = "Train_Dataframe_input.csv"  # Specify the desired blob name
                blob_client = container_client.get_blob_client(blob_name)
                blob_client.upload_blob(csv_data, blob_type="BlockBlob", overwrite=True)
                #predicting results
                combined_predictions=train_predict(df,num_months)
                combined_predictions = combined_predictions.fillna(0)
                for col in combined_predictions.select_dtypes(include='float64'):
                    combined_predictions[col] = combined_predictions[col].astype(int)
                columns_to_replace = ['Best Model', 'Actual', 'Forecast_Lower', 'Forecast', 'Forecast_Upper']
                combined_predictions[columns_to_replace] = combined_predictions[columns_to_replace].replace(0, '')
                print("===============================================")
                print(combined_predictions)
                print("===============================================")
                #uploading forecast results to blob
                blob_client = container_client.get_blob_client("forecast_results.csv")
                combined_predictions.to_csv('forecast_results.csv', index=False)  # Save to a local file for demonstration
                with open('forecast_results.csv', 'rb') as data:
                    blob_client.upload_blob(data, overwrite=True)
                return render_template('index1.html', tables=[combined_predictions.to_html(classes='data1', index=False)], titles='Predicted Sales')

            except Exception as e:
                return render_template("index1.html", prediction_text=f"Error: {str(e)}")

        else:
            return render_template("index1.html", prediction_text="Please upload a CSV file.")
    end=time.time()
    print("predictions time",end-time)
    return jsonify(combined_predictions)

@app.route('/refresh_and_view_report', methods=['POST','GET'])
def refresh_and_view_report():
        AUTHORITY_URL = 'https://login.windows.net/common'
        RESOURCE = 'https://analysis.windows.net/powerbi/api'
        # Replace these values with your actual values
        client_id = "1bc9dbcb-e809-4172-a42b-54cc5a100a3c"
        client_secret = "MY18Q~YBzXFDjdBz8uc6K~Xq0UH_UaIPZ05f_aNm"
        username = "fit_ds@ormae.com"
        password = "Wafers@2024"
        tenant_id = "19e3cf18-820e-4e14-8589-72f62ed533f2"
        api_url = "https://api.powerbi.com/v1.0/myorg/"
        dataset_id = "f8300088-9502-422a-af8b-cb46e619c640"
        report_id = "dc049b20-7adb-49d5-9172-d895a661648e"
        group_id = "af788735-0b24-4d8c-b0f7-a01715f9a55c"
        # Get an access token using Resource Owner Password Credentials (ROPC)
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        token_payload = {
                        'grant_type': 'password',
                        'client_id': client_id,
                        'client_secret': client_secret,
                        # 'resource': 'https://graph.microsoft.com',
                        'scope': "https://analysis.windows.net/powerbi/api/.default",
                        'username': username,
                        'password': password,
                        }
        token_response = requests.get(token_url, data=token_payload)
        token_data = token_response.json()
                
        if 'access_token' in token_data:
            access_token = token_data['access_token']
            # print(f"Access Token: {access_token}")
            refresh_url_data = f"{api_url}datasets/{dataset_id}/refreshes"
            refresh_url_report = f"{api_url}groups/{group_id}/reports/{report_id}/refreshes"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }   
            response_data = requests.post(refresh_url_data, headers=headers)
            response_report = requests.post(refresh_url_report, headers=headers)
            print(response_data)
            print("Dataset Refresh Response:", response_data.text)
            print(response_report)
            print("Report Refresh Response:", response_report.text)
            
            report_url = f"https://app.powerbi.com/groups/{group_id}/reports/{report_id}"
            return redirect(report_url)
        else:
            return jsonify({"success": False, "message": f"Failed to obtain access token. Response: {token_data}"})
        
# Add API endpoint
@app.route("/predict_api", methods=["POST"])
def predict_api():
    try:
        # Get the uploaded CSV file
        uploaded_file = request.files['file']
        num_months = int(request.form.get('NOM'))

        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            #predicting results
            combined_predictions=train_predict(df,num_months)
            print(combined_predictions)

            return jsonify({'predictions': combined_predictions.to_dict(orient='records')})

        else:
            return jsonify({'error': 'Please upload a CSV file.'})

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/refresh_and_view_report_api', methods=['POST'])
def refresh_and_view_report_api():
    try:
        # Get authentication details (replace with your actual values)
        AUTHORITY_URL = 'https://login.windows.net/common'
        RESOURCE = 'https://analysis.windows.net/powerbi/api'
        # Replace these values with your actual values
        client_id = "1bc9dbcb-e809-4172-a42b-54cc5a100a3c"
        client_secret = "MY18Q~YBzXFDjdBz8uc6K~Xq0UH_UaIPZ05f_aNm"
        username = "fit_ds@ormae.com"
        password = "Wafers@2024"
        tenant_id = "19e3cf18-820e-4e14-8589-72f62ed533f2"
        api_url = "https://api.powerbi.com/v1.0/myorg/"
        dataset_id = "f8300088-9502-422a-af8b-cb46e619c640"
        report_id = "dc049b20-7adb-49d5-9172-d895a661648e"
        group_id = "af788735-0b24-4d8c-b0f7-a01715f9a55c"
        # Get an access token using Resource Owner Password Credentials (ROPC)
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        token_payload = {
                        'grant_type': 'password',
                        'client_id': client_id,
                        'client_secret': client_secret,
                        # 'resource': 'https://graph.microsoft.com',
                        'scope': "https://analysis.windows.net/powerbi/api/.default",
                        'username': username,
                        'password': password,
                        }
        token_response = requests.get(token_url, data=token_payload)
        token_data = token_response.json()

        if 'access_token' in token_data:
            access_token = token_data['access_token']

            # Define URLs for dataset and report refresh
            refresh_url_data = f"{api_url}datasets/{dataset_id}/refreshes"
            refresh_url_report = f"{api_url}groups/{group_id}/reports/{report_id}/refreshes"

            # Set headers for API request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Trigger dataset refresh
            response_data = requests.post(refresh_url_data, headers=headers)

            # Trigger report refresh
            response_report = requests.post(refresh_url_report, headers=headers)

            print(response_data)
            print("Dataset Refresh Response:", response_data.text)
            print(response_report)
            print("Report Refresh Responsee:", response_report.text)

            return jsonify({"success": True, "message": "Refresh triggered successfully."})

        else:
            return jsonify({"success": False, "message": f"Failed to obtain access token. Response: {token_data}"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
    
