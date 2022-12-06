from datetime import date
import pandas as pd
from tkinter import *
from tkinter import messagebox

pd.options.mode.chained_assignment = None  # default='warn'

# # Functions for this migration
from src.data.create_cache import *
from src.data.field_mapping import *
# from src.data.locations import *
# from src.data.extract_and_cache_data import *



top = Tk()
top.geometry("100x100")

#run_mapping = messagebox.askyesno("Confirm", "Run field mapping?")
#run_value_mapping = messagebox.askyesno("Confirm", "Run field value mapping?")

# Select macro's you would like to run
# 1 = TRUE
extract_data = 1
map_fields = 0
map_field_values = 0

if extract_data == 1:
    print("Extracting data from snowflake into cache.")
    src.data.create_cache.blackline_data()
    src.data.create_cache.formulate_data()
else:
    print("No data extracted.")

if map_fields == 1:
    print("Running field mapping.")

else:
    print("Do not run field mapping.")


if map_field_values == 1:
    print("Run value mapping.")

else:
    print("Do not run mapping.")






