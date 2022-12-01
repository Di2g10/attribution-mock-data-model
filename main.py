from datetime import date
import pandas as pd
from tkinter import *
from tkinter import messagebox

pd.options.mode.chained_assignment = None  # default='warn'

# # Functions for this migration
from src.data.field_mapping import *
# from src.data.locations import *
# from src.data.extract_and_cache_data import *



top = Tk()
top.geometry("100x100")

run_mapping = messagebox.askyesno("Confirm", "Run field mapping?")
run_value_mapping = messagebox.askyesno("Confirm", "Run field value mapping?")



if run_mapping:
    print("Running field mapping.")
    src.data.field_mapping.blackline_data()

else:
    print("Do not run field mapping.")


if run_value_mapping:
    print("Run value mapping.")
else:
    print("Do not run mapping.")






