import streamlit as st
import pandas as pd
from datetime import timedelta

# Function Definitions
def clean_id_string(id_string):
    if pd.isna(id_string):
        return []
    
    items = str(id_string).split(',')
    clean_ids = []
    
    for item in items:
        item = re.sub(r'\+.*', '', item.strip())
        item = re.sub(r'\D+$', '', item)
        digits = re.findall(r'\d+', item)
        
        if digits:
            clean_ids.append(int(digits[0]))
    
    return clean_ids

def safe_numeric(value, default=0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def add_working_days(start_date, days):
    current_date = start_date
    working_days_added = 0
    while working_days_added < days:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            working_days_added += 1
    return current_date

def calculate_projected_start(df, unique_id_col, status_date_col, start_col, percent_complete_col, remaining_duration_col, predecessors_col):
    if unique_id_col not in df.columns:
        st.error(f"Error: '{unique_id_col}' column not found in DataFrame")
        return None, None, None, pd.DataFrame()

    task = df.loc[df[unique_id_col] == unique_id]
    if task.empty:
        st.warning(f"Task with ID {unique_id} not found in the DataFrame")
        return None, None, None, pd.DataFrame()
    task = task.iloc[0]
    
    status_date = pd.to_datetime(task[status_date_col], errors='coerce')
    planned_start = pd.to_datetime(task[start_col], errors='coerce')
    if pd.isna(status_date):
        st.warning(f"Invalid Status Date for task {unique_id}")
        return None, None, None, pd.DataFrame()
    if pd.isna(planned_start):
        st.warning(f"Invalid Planned Start Date for task {unique_id}")
        return None, None, None, pd.DataFrame()
    
    if pd.isna(task[predecessors_col]):
        return status_date, planned_start, 0, pd.DataFrame()
    
    predecessors = clean_id_string(task[predecessors_col])
    
    predecessor_data = []
    
    for pred_id in predecessors:
        predecessor = df.loc[df[unique_id_col] == pred_id]
        if predecessor.empty:
            st.warning(f"Predecessor with ID {pred_id} not found in the DataFrame")
            continue
        predecessor = predecessor.iloc[0]
        
        pred_status_date = pd.to_datetime(predecessor[status_date_col], errors='coerce')
        if pd.isna(pred_status_date):
            st.warning(f"Invalid Status Date for predecessor {pred_id}")
            continue
        
        percent_complete = safe_numeric(predecessor[percent_complete_col])  # already a fraction, no need to multiply by 100
        remaining_duration = safe_numeric(predecessor[remaining_duration_col])
        
        if percent_complete == 1:
            continue
        
        predecessor_data.append({
            'Predecessor ID': pred_id,
            '% Complete': percent_complete,
            'Remaining Duration': remaining_duration,
            'Status Date': pred_status_date
        })
    
    predecessor_df = pd.DataFrame(predecessor_data)
    
    if predecessor_df.empty:
        return status_date, planned_start, 0, pd.DataFrame()
    
    max_remaining_duration = predecessor_df['Remaining Duration'].max()
    st.write(f"Maximum Remaining Duration for task {unique_id}: {max_remaining_duration}")
    
    projected_start = add_working_days(status_date, max_remaining_duration)
    
    st.write(f"Projected start date calculated as status date ({status_date}) + max remaining duration ({max_remaining_duration} working days) = {projected_start}")
    
    # Calculate the delta between projected start and planned start
    delta = (projected_start - planned_start).days
    
    return projected_start, planned_start, delta, predecessor_df

# Streamlit App
def main():
    st.title('Projected Start Date Calculator')
    
    # File Upload
    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')
            sheet_names = list(df.keys())
            selected_sheet = st.selectbox("Select Sheet", sheet_names)
            df = df[selected_sheet]
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
            return
    else:
        st.warning("Please upload an Excel file")
        return
    
    if st.checkbox("Show DataFrame"):
        st.write(df)
    
    # Select columns
    with st.form(key='column_selection_form'):
        unique_id_col = st.selectbox('Select Unique ID Column', options=df.columns)
        status_date_col = st.selectbox('Select Status Date Column', options=df.columns)
        start_col = st.selectbox('Select Start Date Column', options=df.columns)
        percent_complete_col = st.selectbox('Select % Complete Column', options=df.columns)
        remaining_duration_col = st.selectbox('Select Remaining Duration Column', options=df.columns)
        predecessors_col = st.selectbox('Select Predecessors Column', options=df.columns)
        
        submit_button = st.form_submit_button(label='Calculate Projected Start Date')
    
    if submit_button:
        projected_start, planned_start, delta, pred_df = calculate_projected_start(df, unique_id_col, status_date_col, start_col, percent_complete_col, remaining_duration_col, predecessors_col)
        
        if projected_start is not None and planned_start is not None:
            st.write(f"Projected start date: {projected_start}")
            st.write(f"Planned start date: {planned_start}")
            st.write(f"Delta (days): {delta}")
            st.write("\nPredecessor information:")
            st.write(pred_df)
        else:
            st.warning(f"Unable to calculate projected start date")
    
if __name__ == "__main__":
    main()
