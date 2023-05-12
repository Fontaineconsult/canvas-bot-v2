import win32com.client as win32
import comtypes, comtypes.client

from tools.vba.vba_strings import get_vba_modules, get_vba_triggers


def insert_vba_modules(wb_path):

    xl = win32.gencache.EnsureDispatch('Excel.Application')
    xl.Visible = True


    ss = xl.Workbooks.Open(wb_path)

    sh = ss.ActiveSheet

    xlmodule = ss.VBProject.VBComponents.Add(1)  # vbext_ct_StdModule


    for module in get_vba_modules():
        xlmodule.CodeModule.AddFromString(module())
        ss.Save()

    ss.Close(True)



def insert_sheet_triggers(wb_path):

    xl = win32.gencache.EnsureDispatch('Excel.Application')
    xl.Visible = True

    ss = xl.Workbooks.Open(wb_path)


    triggers_dict = get_vba_triggers()

    for sheet_name in triggers_dict:
        # Retrieve the sheet's VBComponent
        xlmodule = ss.VBProject.VBComponents(sheet_name)

        # Add the VBA code to the sheet's code module
        xlmodule.CodeModule.AddFromString(triggers_dict[sheet_name])
        ss.Save()

    ss.Close(True)



def insert_vba(wb_path):

    insert_vba_modules(wb_path)
    insert_sheet_triggers(wb_path)