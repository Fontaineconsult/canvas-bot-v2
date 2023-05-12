import os


script_dir = os.path.dirname(os.path.abspath(__file__))

def check_if_file_exists():

    with open(os.path.join(script_dir, "CheckIfFileExists.bas"), 'r', encoding='iso-8859-1') as file:
        return file.read()


def add_document_triggers():

    with open(os.path.join(script_dir, "DocumentTriggers.cls"), 'r', encoding='iso-8859-1') as file:
        return file.read()


triggers = {

    "Sheet1": add_document_triggers(),

}

def get_vba_modules():
    return [check_if_file_exists]


def get_vba_triggers():
    return triggers

