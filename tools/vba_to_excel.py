import win32com.client as win32
import comtypes, comtypes.client

from tools.vba.vba_strings import get_vba_modules, get_vba_triggers



hyper_link_dict = {

    1: [4, 7, 9, 12],
    2: [6, 8],
    3: [5, 8, 10],
    5: [6, 8],
    8: [5,7],

}


def insert_vba_modules(ss):

    excelmodule = ss.VBProject.VBComponents.Add(1)  # vbext_ct_StdModule


    for module in get_vba_modules():
        excelmodule.CodeModule.AddFromString(module())


def insert_sheet_triggers(ss):

    triggers_dict = get_vba_triggers()

    for sheet_name in triggers_dict:
        # Retrieve the sheet's VBComponent
        xlmodule = ss.VBProject.VBComponents(sheet_name)

        # Add the VBA code to the sheet's code module
        xlmodule.CodeModule.AddFromString(triggers_dict[sheet_name])



def insert_hyperlinks(ss, hyper_link_dict):

    # This is a work around as the Hyperlink object in openpyXL doesn't seem to work.

    for sheet_number, columns in hyper_link_dict.items():
        sh = ss.Worksheets(sheet_number)  # Get the appropriate worksheet based on dictionary key

        for column in columns:  # Iterate over columns to add hyperlinks
            last_row = sh.Cells(sh.Rows.Count, column).End(win32.constants.xlUp).Row

            for row in range(2, last_row + 1):  # Start from row 2 to skip the header
                cell = sh.Cells(row, column)  # Column based on column value in dictionary
                address = cell.Value  # You may need to adjust this depending on the cell content
                if address:  # Skip cells without a value
                    sh.Hyperlinks.Add(Anchor=cell, Address=address)




def insert_vba(wb_path):

    xl = win32.gencache.EnsureDispatch('Excel.Application')
    xl.DisplayAlerts = False
    xl.Visible = False

    ss = xl.Workbooks.Open(wb_path, CorruptLoad=1)

    insert_vba_modules(ss)
    insert_sheet_triggers(ss)
    insert_hyperlinks(ss, hyper_link_dict)
    ss.SaveAs(wb_path, FileFormat=52)
    ss.Close(True)
    xl.Quit()
    xl.DisplayAlerts = True
