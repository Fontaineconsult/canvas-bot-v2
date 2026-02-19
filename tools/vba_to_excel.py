import os
import warnings
import win32com.client as win32
import comtypes, comtypes.client
import pywintypes

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
            last_row = sh.Cells(sh.Rows.Count, column).End(-4162).Row  # -4162 = xlUp

            for row in range(2, last_row + 1):  # Start from row 2 to skip the header
                cell = sh.Cells(row, column)  # Column based on column value in dictionary
                address = cell.Value  # You may need to adjust this depending on the cell content
                if address and isinstance(address, str):
                    try:
                        sh.Hyperlinks.Add(Anchor=cell, Address=address)
                    except Exception:
                        pass  # Skip cells with values that aren't valid hyperlink addresses




def _get_excel():
    """Get an Excel COM object, clearing corrupted cache if needed."""
    import shutil
    try:
        return win32.gencache.EnsureDispatch('Excel.Application')
    except Exception:
        cache_dir = win32.gencache.GetGeneratePath()
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
        return win32.gencache.EnsureDispatch('Excel.Application')


def insert_vba(wb_path):
    import pythoncom
    pythoncom.CoInitialize()
    wb_path = os.path.abspath(wb_path)  # Normalize to absolute path with backslashes for COM
    xl = _get_excel()
    xl.DisplayAlerts = False
    xl.Visible = False

    try:
        ss = xl.Workbooks.Open(wb_path, CorruptLoad=1)
        insert_vba_modules(ss)
        insert_sheet_triggers(ss)
        insert_hyperlinks(ss, hyper_link_dict)
        ss.SaveAs(wb_path, FileFormat=52)
        ss.Close(True)
    except pywintypes.com_error as e:
        # HRESULT -2147352567 (0x80020009) with scode -2146827284 (0x800A03EC)
        # typically means VBA project access is blocked by Trust Center settings.
        if e.hresult == -2147352567 or (hasattr(e, 'excepinfo') and e.excepinfo and e.excepinfo[5] == -2146827284):
            warnings.warn(
                "Excel macro insertion failed — programmatic access to VBA is disabled.\n"
                "  To enable it:\n"
                "    1. Open Excel\n"
                "    2. Go to File > Options > Trust Center > Trust Center Settings\n"
                "    3. Click 'Macro Settings'\n"
                "    4. Check 'Trust access to the VBA project object model'\n"
                "    5. Click OK and re-run the export\n"
                "  The Excel file was saved without macros."
            )
        else:
            warnings.warn(f"Excel macro insertion failed: {e}\n  The Excel file was saved without macros.")
    except Exception as e:
        warnings.warn(f"Excel macro insertion failed: {e}\n  The Excel file was saved without macros.")
    finally:
        xl.Quit()
        pythoncom.CoUninitialize()
