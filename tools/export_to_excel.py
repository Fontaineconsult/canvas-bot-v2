import os
import zipfile
from openpyxl.worksheet.table import Table, TableStyleInfo
import openpyxl
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.utils.cell import get_column_letter

def create_excel_file(json_data, excel_file_path=None):

    """
    Creates an excel file with the appropriate sheets.
    :param json_data:
    :param excel_file_path:
    :return:
    """
    wb = openpyxl.Workbook()
    ws = wb["Sheet"]
    wb.remove(ws)
    wb.create_sheet('Documents')
    wb.create_sheet('Document Sites')
    wb.create_sheet('Image Files')
    wb.create_sheet('Video Files')
    wb.create_sheet('Video Sites')
    wb.create_sheet('Audio Files')
    wb.create_sheet('Audio Sites')
    wb.create_sheet('Unsorted')

    wb.save(excel_file_path)
    wb.close()

    # build_xcel_file(json_data, excel_file_path)


def remove_key_recursively(obj, key_to_remove):
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key != key_to_remove:
                result[key] = remove_key_recursively(value, key_to_remove)
        return result
    elif isinstance(obj, list):
        result = []
        for item in obj:
            result.append(remove_key_recursively(item, key_to_remove))
        return result
    else:
        return obj




def apply_sheet_styles(excel_file_path):
    wb = openpyxl.load_workbook(excel_file_path)



    for sheet_name in wb.sheetnames:

        sheet = wb[sheet_name]

        if sheet.dimensions == "A1:A1":
            continue

        # first_row_values = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))][0]
        sheet.column_dimensions['A'].width = 15
        sheet.column_dimensions['B'].width = 15
        sheet.column_dimensions['C'].width = 15
        sheet.column_dimensions['D'].width = 20
        sheet.column_dimensions['E'].width = 20
        sheet.column_dimensions['F'].width = 50
        sheet.column_dimensions['G'].width = 50
        sheet.column_dimensions['H'].width = 150
        sheet_name = sheet_name.replace(" ", "-")


        table = Table(displayName=sheet_name, ref=sheet.dimensions)

        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                       showLastColumn=False, showRowStripes=True, showColumnStripes=True)

        table.tableStyleInfo = style
        sheet.add_table(table)
        wb.save(excel_file_path)

    wb.close()

def find_key_names(d, path=None):
    if path is None:
        path = []
    result = []
    for k, v in d.items():
        new_path = path + [k]
        if isinstance(v, list):
            result.append(new_path)
        elif isinstance(v, dict):
            sub_result = find_key_names(v, new_path)
            result += sub_result
    return result


def add_header_to_sheet(file_path, sheet_name, header_row):
    """
    Adds a header row to a sheet based on the keys in a Python dictionary.

    Args:
        file_path (str): The path to the Excel file.
        sheet_name (str): The name of the sheet to add the header row to.
        header_row (dict): A dictionary whose keys will be used as the header row.
    """
    # Load the workbook and select the sheet
    wb = openpyxl.load_workbook(file_path)
    sheet = wb[sheet_name]

    # Add the header row to the sheet



    for col_idx, header_name in enumerate(header_row):

        cell = sheet.cell(row=1, column=col_idx+1)
        cell.value = " ".join(word.capitalize() for word in header_name.replace('_', ' ').split(' '))



    # Save the workbook
    wb.save(file_path)
    wb.close()


def dicts_to_excel(filename, sheetname, data, download_hidden_files):
    # Load an existing Excel workbook or create a new one if it doesn't exist
    try:
        wb = openpyxl.load_workbook(filename)
    except FileNotFoundError:
        wb = openpyxl.Workbook()


    # Create a new sheet with the specified sheet name or get the existing one
    if sheetname in wb:
        ws = wb[sheetname]
    else:
        ws = wb.create_sheet(sheetname)

    # Write data rows (values from each dictionary)

    for row_num, item in enumerate(data, 2):  # Start from row 2

        for col_num, key in enumerate(item.keys(), 1):

            if key == "save_path":
                if item['is_hidden'] and not download_hidden_files:
                    continue

                target = item.get(key)
                if item['source_page_type'] == 'BoxPage':
                    print("BOX")
                    target = item.get("url")

                print(target)
                hyperlink = Hyperlink(ref=f"{get_column_letter(col_num)}{row_num}",
                                      target=target, display="Open File")
                ws.cell(row=row_num, column=col_num).hyperlink = hyperlink
                continue

            ws.cell(row=row_num, column=col_num).value = item.get(key)


    # Save the workbook to a file
    wb.save(filename)
    wb.close()


def build_xcel_file(json_data, excel_file_path, download_hidden_files):

    key_paths = find_key_names(json_data)
    for path in key_paths:
        # navigate to the list using each path
        sub_dict = json_data
        for key in path[:-1]:
            sub_dict = sub_dict[key]
        my_list = sub_dict[path[-1]]
        sheet_name = " ".join(word.capitalize() for word in path[-1].replace('_', ' ').split(' '))

        try:
            add_header_to_sheet(excel_file_path, sheet_name, my_list[0])
            dicts_to_excel(excel_file_path, sheet_name, my_list, download_hidden_files)
        except IndexError:
            pass


def save_as_excel(json_data, file_save_path, download_hidden_files):


    xcel_path = os.path.join(file_save_path, json_data['course_id'] + '.xlsx')
    json_data = remove_key_recursively(json_data, 'path')

    create_excel_file(json_data, xcel_path)
    build_xcel_file(json_data, xcel_path, download_hidden_files)
    apply_sheet_styles(xcel_path)