import time
import csv
from network.api import get_active_accounts
from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata

if __name__=="__main__":
    set_canvas_api_key_to_environment_variable()
    load_config_data_from_appdata()


def get_all_course_ids():

    count = 1
    course_ids = get_active_accounts(count)

    with open("../../accessiblebookchecker/root/application/migrations/data_import/raw_data/file.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=",")



        while len(course_ids) > 0:

            course_ids = get_active_accounts(count)
            count += 1
            time.sleep(1)
            # print(course_ids)

            for course in course_ids:
                course_codes = course["course_code"].split("-")
                if len(course_codes) > 4:
                    course_name, code, section, semester, year = course_codes[0],\
                        course_codes[1], course_codes[2], course_codes[3], course_codes[4]

                    course_gen_id = f"{semester[0:2].lower()}{year[2:4]}{course_name}{code[1:4]}{section}".replace("_","")
                    writer.writerow([course_gen_id, course["id"],f"{semester[0:2].lower()}{year[2:4]}", course["name"]])


