
import pandas as pd
from datetime import datetime, timedelta, time

# Define Global Variables
time_interval=30
today_date = datetime.today().date()

def transform_time_inout(df):
    '''
    This function adds date to time columns and adjust the 15mins interval end/start shifts to 30-mins interval'''
    # Convert 'Time in' and 'Time out' to datetime with today's date
    # print("\n\n df.head()")
    # print(df.head())
    # print(df.columns)
    # print("First Row:")
    # print(df.iloc[0,])
    # print("Second Row:")
    # print(df.iloc[1,])
    df['Time in'] = pd.to_datetime(df['Time in'], format='%Y-%m-%d %H:%M:%S').apply(lambda x: datetime.combine(today_date, x.time()))
    df['Time out'] = pd.to_datetime(df['Time out'], format='%Y-%m-%d %H:%M:%S').apply(lambda x: datetime.combine(today_date, x.time()))

    # Note: If the initial shift allocation starts (Time In) at any 15mins interval (like 8:45), we are shifting to later 30mins (9:00) AND if the initial shift allocation ends (Time Out) at any 15mins interval (like 6:15), we are shifting to previous 30mins (6:00). 
    # Function to adjust times based on 15-minute intervals
    def adjust_time_in(time_in):
        if time_in.minute == 45:
            # Shift forward to the next 30-minute mark
            return time_in.replace(minute=0) + timedelta(hours=1)
        elif time_in.minute == 30:
            # Already at a 30-minute mark, do nothing
            return time_in
        elif time_in.minute == 15:
            # Shift forward to the next 30-minute mark
            return time_in.replace(minute=30)
        return time_in

    def adjust_time_out(time_out):
        if time_out.minute == 15:
            # Shift backward to the previous 30-minute mark
            return time_out.replace(minute=0)
        elif time_out.minute == 30:
            # Already at a 30-minute mark, do nothing
            return time_out
        elif time_out.minute == 45:
            # Shift backward to the previous 30-minute mark
            return time_out.replace(minute=30)
        return time_out

    # Apply adjustments to the 'Time in' and 'Time out' columns
    df['Time in'] = df['Time in'].apply(adjust_time_in)
    df['Time out'] = df['Time out'].apply(adjust_time_out)

    return df

def create_working_flag(filtered_df):
    '''
    This function will add every 30mins interval for every customer and created a Working Flag column
    '''
    new_rows = []
    first_start_time = filtered_df['Time in'].min()
    max_end_time = filtered_df['Time out'].max()

    # Get unique names from filtered_df
    unique_names = filtered_df['Name'].unique()

    # Iterate through each individual
    for name in unique_names:
        start_time = first_start_time
        end_time = max_end_time
        
        # Generate 30 minute intervals
        while start_time < end_time:
            new_row = {
                'Name': name,
                'Start_time': start_time.time(),
                'End_time': (start_time + timedelta(minutes=time_interval)).time()
            }
            new_rows.append(new_row)
            start_time += timedelta(minutes=30)

    # Create the new DataFrame
    work_status_df = pd.DataFrame(new_rows)


    def get_working_flag(name, start_time, end_time):
        # Get all working hours for the specific name
        employee_records = filtered_df[filtered_df['Name'] == name]
        
        # Iterate through all records for the employee
        for index, record in employee_records.iterrows():
            # Convert Time in and Time out to time objects
            time_in = record['Time in'].time()  # Use .time() to get the time object
            time_out = record['Time out'].time()  # Use .time() to get the time object

            # Check if the Start_time and End_time fall within the working hours
            if (time_in <= start_time < time_out) or (time_in < end_time <= time_out) or (start_time <= time_in and end_time >= time_out):
                return 1  # Working
        
        return 0  # Not working if none of the records match

    # Add the 'Working Flag' column to work_status_df
    work_status_df['Working Flag'] = work_status_df.apply(
        lambda row: get_working_flag(row['Name'], row['Start_time'], row['End_time']), axis=1
    )

    return work_status_df

def create_remaining_hours(work_status_df, filtered_df):
    # Caluculate remaining hours left 
    greeter_priority_df= work_status_df.copy()
    work_status_copy_df= work_status_df.copy()

    # Calculate remaining hours left
    # Ensure all time columns are converted to strings in case they are of type datetime.time
    greeter_priority_df['Start_time'] = greeter_priority_df['Start_time'].astype(str)
    greeter_priority_df['End_time'] = greeter_priority_df['End_time'].astype(str)
    work_status_copy_df['Start_time'] = work_status_copy_df['Start_time'].astype(str)
    work_status_copy_df['End_time'] = work_status_copy_df['End_time'].astype(str)

    def calculate_remaining_hours(employee, current_time, work_status_df, filtered_df):
        # Convert current_time to datetime object
        current_time = pd.to_datetime(f"{today_date} {current_time}", format="%Y-%m-%d %H:%M:%S")

        # Initialize remaining time
        remaining_time = 0.0

        # Filter for the specific employee's schedule
        employee_schedule = filtered_df[filtered_df['Name'] == employee]
        working_shifts = work_status_df[(work_status_df['Name'] == employee) & (work_status_df['Working Flag'] == 1)]

        #print("employee_schedule\n", employee_schedule)

        # Identify the active shift
        for _, shift in employee_schedule.iterrows():
            shift_start = pd.to_datetime(shift['Time in'])
            shift_end = pd.to_datetime(shift['Time out'])

            #print("\ncurrent_time", current_time)
            #print("shift_end", shift_end, '\n')

            # Skip if the shift has ended
            if current_time >= shift_end:
                #print("current_time >= shift_end")
                continue

            # If within this shift, calculate remaining hours
            if shift_start <= current_time < shift_end:
                #print("shift_start <= current_time < shift_end")
                remaining_time = (shift_end - current_time).total_seconds() / 3600  # Hours
                break
            elif current_time < shift_start:
                #print("current_time < shift_start")
                # If the current time is before the shift, skip to the next one
                continue

        return remaining_time


    # Apply the calculation to the DataFrame
    greeter_priority_df['Remaining_hours_left'] = greeter_priority_df.apply(
        lambda row: calculate_remaining_hours(row['Name'], row['Start_time'], work_status_copy_df, filtered_df), axis=1
    )
    return greeter_priority_df

def alert_employee_shortage(work_status_df, emp_count_req):

    emp_aval= work_status_df.copy()
    emp_aval.rename(columns={'Start_time': 'Work_From', 'End_time': 'Work_To', 'Working Flag': 'Working_Flag'}, inplace=True)

    # Create "total available employee" column

    # Group By the From and To time of "Work Status Per Time" table and count the number of available employees
    grouped_avl_by_time= emp_aval.groupby(['Work_From', 'Work_To']).agg({'Working_Flag': 'sum'}).reset_index()
    grouped_avl_by_time.columns= ['Work_From', 'Work_To', 'Total_Avl_Emp']

    # Join it with the emp_count_req table
    emp_demand_check= pd.merge(emp_count_req, grouped_avl_by_time, how='left', left_on=['From_Time','To_Time'], right_on=['Work_From','Work_To'])
    columns_needed= ['From_Time', 'To_Time', 'Reg_Up_Needed', 'Reg_Down_Needed', 'Greeter_Up_Needed', 'Greeter_Down_Needed', 'Min_Total_Emp_Needed', 'Total_Avl_Emp']
    emp_demand_check= emp_demand_check[columns_needed]
    emp_demand_check['Total_Avl_Emp'].fillna(0, inplace=True) # If no emp are available on a selected shift, make the availability zero. 

    # Create an availability check flag and alert 
    def alert_insufficient_emp(emp_demand_check: pd.DataFrame):
        shortage= emp_demand_check[emp_demand_check['Availability_Check_Flag'] == False]
        if(len(shortage)==0):
            print("No shortage of employees for the whole day")
        else:
            error_message = (
            "ALERT: Employees are on shortage for the following time slots:\n" +
            shortage[['From_Time', 'To_Time', 'Min_Total_Emp_Needed', 'Total_Avl_Emp']].to_string(index=False)
            )
            raise RuntimeError(error_message)
        return

    emp_demand_check['Availability_Check_Flag']= emp_demand_check['Min_Total_Emp_Needed']<= emp_demand_check['Total_Avl_Emp']
    alert_insufficient_emp(emp_demand_check)
    return emp_demand_check


def convert_df_to_emp_view(df):
    # 1. Format by time and sort ascending

    # Step 1: Convert to datetime objects
    df["From_Time"] = pd.to_datetime(df["From_Time"], format="%H:%M:%S")
    df["To_Time"] = pd.to_datetime(df["To_Time"], format="%H:%M:%S")

    # Step 2: Sort by `From_Time` in ascending order
    df = df.sort_values(by="From_Time")

    # 4. Convert to dictionary
    dynamo_db_input=dict()

    def check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name):
        if (emp_name not in dynamo_db_input): # Add name to dictionary if not exist and create template
            dynamo_db_input[emp_name]= {
                "Name": emp_name,
                "Data": [],
            }
            return dynamo_db_input
        else:
            return dynamo_db_input

    for index,row in df.iterrows():
        # Convert Greeter Up
        if row['Upstairs Greeter'] !='' and row['Upstairs Greeter'] !=None: 
            emp_name= row['Upstairs Greeter']
            dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
            # Data row to append
            data_row={
                'Location': 'Greeter Upstair',
                'TimeIn': row['From_Time'],
                'TimeOut': row['To_Time']
                }
            dynamo_db_input[emp_name]['Data'].append(data_row)

        # Convert Greeter Down
        if row['Downstairs Greeter'] !='' and row['Downstairs Greeter'] !=None: 
            emp_name= row['Downstairs Greeter']
            dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
            # Data row to append
            data_row={
                'Location': 'Greeter Downstair',
                'TimeIn': row['From_Time'],
                'TimeOut': row['To_Time']
                }
            dynamo_db_input[emp_name]['Data'].append(data_row)

        # Convert Register Up
        if row['Register Up'] !='' and row['Register Up'] !=None: 
            emp_names= row['Register Up']
            for emp_name in emp_names:
                dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
                # Data row to append
                data_row={
                    'Location': 'Register Upstair',
                    'TimeIn': row['From_Time'],
                    'TimeOut': row['To_Time']
                    }
                dynamo_db_input[emp_name]['Data'].append(data_row)
        
        # Convert Register Down
        if row['Register Down'] !='' and row['Register Down'] !=None: 
            emp_names= row['Register Down']
            for emp_name in emp_names:
                dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
                # Data row to append
                data_row={
                    'Location': 'Register Downstair',
                    'TimeIn': row['From_Time'],
                    'TimeOut': row['To_Time']
                    }
                dynamo_db_input[emp_name]['Data'].append(data_row)
        
        # Convert Salesfloor Up
        if row['SF Up'] !='' and row['SF Up'] !=None: 
            emp_names= row['SF Up']
            for emp_name in emp_names:
                dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
                # Data row to append
                data_row={
                    'Location': 'Salesfloor Upstair',
                    'TimeIn': row['From_Time'],
                    'TimeOut': row['To_Time']
                    }
                dynamo_db_input[emp_name]['Data'].append(data_row)
        
        # Convert Salesfloor Down
        if row['SF Down'] !='' and row['SF Down'] !=None: 
            emp_names= row['SF Down']
            for emp_name in emp_names:
                dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
                # Data row to append
                data_row={
                    'Location': 'Salesfloor Downstair',
                    'TimeIn': row['From_Time'],
                    'TimeOut': row['To_Time']
                    }
                dynamo_db_input[emp_name]['Data'].append(data_row)

        # Convert Technology
        if row['Technology'] !='' and row['Technology'] !=None: 
            emp_names= row['Technology']
            for emp_name in emp_names:
                dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
                # Data row to append
                data_row={
                    'Location': 'Technology',
                    'TimeIn': row['From_Time'],
                    'TimeOut': row['To_Time']
                    }
                dynamo_db_input[emp_name]['Data'].append(data_row)

        # Convert Office Work
        if row['Office Work'] !='' and row['Office Work'] !=None: 
            emp_names= row['Office Work']
            for emp_name in emp_names:
                dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
                # Data row to append
                data_row={
                    'Location': 'Office Work',
                    'TimeIn': row['From_Time'],
                    'TimeOut': row['To_Time']
                    }
                dynamo_db_input[emp_name]['Data'].append(data_row)

        # Convert Stockroom
        if row['Stockroom'] !='' and row['Stockroom'] !=None: 
            emp_names= row['Stockroom']
            for emp_name in emp_names:
                dynamo_db_input= check_and_assign_new_name_dynamo_dict(dynamo_db_input,emp_name)
                # Data row to append
                data_row={
                    'Location': 'Stockroom',
                    'TimeIn': row['From_Time'],
                    'TimeOut': row['To_Time']
                    }
                dynamo_db_input[emp_name]['Data'].append(data_row)
        
    # Remove names as keys and convert to a list of dictionaries
    dynamo_db_input_records= []

    for key,value in dynamo_db_input.items():
        dynamo_db_input_records.append(value)

    # Convert to a DataFrame
    rows = []
    for entry in dynamo_db_input_records:
        name = entry['Name']
        for record in entry['Data']:
            rows.append({'Name': name, **record})

    df = pd.DataFrame(rows)
    df = df.sort_values(by=['Name','TimeIn'], ascending=[True,True])

    # Merge consecutive time intervals for the same employee and location
    merged_rows = []
    for name, group in df.groupby("Name"):
        group = group.sort_values("TimeIn")  # Ensure sorted by TimeIn
        temp_row = group.iloc[0].to_dict()  # Start with the first row
        for _, row in group.iloc[1:].iterrows():
            if row["Location"] == temp_row["Location"] and row["TimeIn"] == temp_row["TimeOut"]:
                temp_row["TimeOut"] = row["TimeOut"]  # Extend the time interval
            else:
                merged_rows.append(temp_row)  # Save the previous row
                temp_row = row.to_dict()  # Start a new row
        merged_rows.append(temp_row)  # Append the last row

    # Create the merged DataFrame
    merged_df = pd.DataFrame(merged_rows)
    
    def convert_time_format(time_obj):
        return time_obj.strftime("%I:%M%p").lstrip("0")  # Remove leading 0 for hours
    merged_df["TimeIn"] = merged_df["TimeIn"].apply(convert_time_format)
    merged_df["TimeOut"] = merged_df["TimeOut"].apply(convert_time_format)
    print("Data sorting and formating Successfull")
    print("Employee view created")
    return merged_df


