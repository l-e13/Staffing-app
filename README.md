# Roster Ingestion App

This is a Streamlit web app that allows users to upload one or more Excel roster reports, cleans and processes them, pushes the data to Supabase, and logs ingestion attempts.

## Features
- Upload multiple Excel files at once
- Cleans raw data according to generic logic
- Renames columns to meaningful schema names
- Pushes rows to Supabase `roster_data` table
- Logs each upload (filename, timestamp, row count, status) to `processed_uploads`
- Skips already processed filenames, with “Force reprocess” option
- Shows final preview and summary
