#!/usr/bin/env python
# coding: utf-8

# In[1]:


from greeter_allocation import *
from register_salesfloor_acclocation import *
from utils import transform_time_inout, create_working_flag, create_remaining_hours, alert_employee_shortage, convert_df_to_emp_view
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")


# In[ ]:


# 1. Read Emp Availability table, filter and format Time columns
path= r".\00_Input\01_Emp_Availability_Initial.xlsx" #"/Users/saaijeeshsn/Documents/bookstore_local/CU-BookStore-Work-Scheduling/00_Input/01_Emp_Availability_Initial.xlsx" # TODO: Read from Frontend

df = pd.read_excel(path, names=['Name', 'Responsibility', 'Time in', 'Time out'])
filtered_df = df[~df['Responsibility'].isin(['Technology', 'Office Work']) & ~df['Name'].str.contains('Available')] # Filter out not-required roles and names
filtered_df= transform_time_inout(filtered_df)

# 2. Create Working Flag and Remaining Hours Left
work_status_df = create_working_flag(filtered_df)
work_status_df= work_status_df[work_status_df['Working Flag']==1] # Filter only working hours for every employee
work_status_df= create_remaining_hours(work_status_df, filtered_df)
work_status_df['Start_time'] = pd.to_datetime(work_status_df['Start_time'], format='%H:%M:%S').dt.time
work_status_df['End_time'] = pd.to_datetime(work_status_df['End_time'], format='%H:%M:%S').dt.time


# In[ ]:


#1. Read Shift Req table, format Time columns
path= r".\00_Input\02_Emp_Count_Requirement.xlsx"
emp_count_req= pd.read_excel(path) # TODO: Read from Frontend
emp_count_req['From_Time'] = pd.to_datetime(emp_count_req['From_Time'], format='%H:%M:%S').dt.time
emp_count_req['To_Time'] = pd.to_datetime(emp_count_req['To_Time'], format='%H:%M:%S').dt.time

# 2. Alert if available employees are insufficient to satisfy the required count
emp_requirements= alert_employee_shortage(work_status_df, emp_count_req)


# In[4]:


greeter_assignment, greeter_shift_done_dict = allocate_greeter(work_status_df, emp_requirements)

# Remove stockroom employees from register allocation
stockroom_emps= filtered_df[filtered_df['Responsibility']=='Stockroom']['Name'].tolist()
work_status_df = work_status_df[~work_status_df['Name'].isin(stockroom_emps)]

# In[7]:

# Allocate Registers
register_allocation= allocate_register_salesfloor(emp_requirements, work_status_df, greeter_assignment)
final_allocation= pd.merge(greeter_assignment, register_allocation, how='outer', left_on=['From_Time', 'To_Time'], right_on=['From_Time', 'To_Time'])


# In[8]:
# 1. Take Other than 'Technology' and 'Office Work' RESPONSIBILITY and 'Avaiable' NAME
filtered_others_df = df[~df['Responsibility'].isin(['Greeter', 'Lead Student', 'Sales Floor/Cashier']) & ~df['Name'].str.contains('Available')] # Filter out not-required roles and names
filtered_others_df= transform_time_inout(filtered_others_df)

# Adding empty columns for each responsibility
final_allocation["Technology"] = None
final_allocation["Office Work"] = None
final_allocation["Stockroom"] = None

# Iterate over each row in filtered_others_df
for index, row in filtered_others_df.iterrows():

    emp_name = row['Name']
    time_in = row['Time in'].time()  # Extract only the time part
    time_out = row['Time out'].time()  # Extract only the time part
    responsibility = row['Responsibility']

    # Filter final_allocation for the corresponding time range
    # Directly compare the time part (no need for .apply(lambda x: x.time()))
    mask = (final_allocation['From_Time'] >= time_in) & \
           (final_allocation['To_Time'] <= time_out)

    # For each matching row, add the emp_name to the respective responsibility column
    for idx in final_allocation[mask].index:
        # Append the emp_name to the respective column
        if responsibility == "Office Work":
            if final_allocation.at[idx, "Office Work"] is None:
                final_allocation.at[idx, "Office Work"] = [emp_name]
            else:
                final_allocation.at[idx, "Office Work"].append(emp_name)
        elif responsibility == "Stockroom":
            if final_allocation.at[idx, "Stockroom"] is None:
                final_allocation.at[idx, "Stockroom"] = [emp_name]
            else:
                final_allocation.at[idx, "Stockroom"].append(emp_name)
        elif responsibility == "Technology":
            if final_allocation.at[idx, "Technology"] is None:
                final_allocation.at[idx, "Technology"] = [emp_name]
            else:
                final_allocation.at[idx, "Technology"].append(emp_name)

# Remove Emp from Stockroom if allocated to greeter in the same time
for index,row in final_allocation.iterrows():
    if(row['Stockroom']==None): continue
    if(row['Upstairs Greeter'] in row['Stockroom']):
        row['Stockroom'].remove(row['Upstairs Greeter'])
    if(row['Downstairs Greeter'] in row['Stockroom']):
        row['Stockroom'].remove(row['Downstairs Greeter'])

# Get the final employee view
emp_view= convert_df_to_emp_view(final_allocation)

# Format time
final_allocation["From_Time"] = final_allocation["From_Time"].dt.strftime("%I:%M %p")
final_allocation["To_Time"] = final_allocation["To_Time"].dt.strftime("%I:%M %p")
final_allocation.drop(columns=['Greeter_Down_Needed', 'Greeter_Up_Needed', 'Reg_Up_Needed', 'Reg_Down_Needed'], inplace=True)


# In[9]:


# Get the current date and time
current_datetime = datetime.now()
current_datetime = current_datetime.strftime("%Y-%m-%d-%H-%M-%S")

# Save for flask output
final_allocation.to_excel("./01_Output/Final_Allocation.xlsx", index=False)
emp_view.to_excel("./01_Output/Final_Allocation_Emp_View.xlsx", index=False)

final_allocation.to_excel(fr"./01_Output/Historical_Files/Final_Allocation_{current_datetime}.xlsx", index=False)
emp_view.to_excel(fr"./01_Output/Historical_Files/Final_Allocation_Emp_View_{current_datetime}.xlsx", index=False)


# In[ ]:




