import time
import csv
from network.api import get_active_accounts
from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata


semester_key = {

    "2237": 'fa23',
    "2243": 'sp24',
    "2245": 'su24',
    "2247": 'fa24',
    "2253": "sp25",
    "2255": "su25",
    "2257": "fa25",
    "2263": "sp26",


}

def get_all_course_ids(offset=0):

    count = 1 + offset
    course_ids = get_active_accounts(count)

    with open(r"C:\Users\Fonta\OneDrive - San Francisco State University\Desktop\test.csv", "w", newline="")\
            as csvfile:
        writer = csv.writer(csvfile, delimiter=",")



        while len(course_ids) > 0:

            course_ids = get_active_accounts(count)
            print(course_ids)
            count += 1
            time.sleep(0.3)
            # print(course_ids)

            for course_id in course_ids:

                    course_codes = course_id["course_code"].split("-")
                    if semester_key.get(course_codes[0]):

                        semester = semester_key[course_codes[0]]
                        course = course_codes[1]
                        course_number = course_codes[2]
                        course_section = course_codes[3]

                    course_gen_id = f"{semester}{course}{course_number}{course_section}".replace(" ", "")
                    print(course_gen_id)

                    writer.writerow([course_gen_id, course_id["id"],f"{semester}", course_id["name"]])





if __name__=="__main__":
    set_canvas_api_key_to_environment_variable()
    load_config_data_from_appdata()
    get_all_course_ids(219)



""" Old system

                course_codes = course["course_code"].split("-")
                if len(course_codes) > 4:
                    course_name, code, section, semester, year = course_codes[0],\
                        course_codes[1], course_codes[2], course_codes[3], course_codes[4]



                    print(semester, year, course_name, code, section)
                    course_gen_id = f"{semester[0:2].lower()}{year[2:4]}{course_name}{code[1:4]}{section}".replace("_","")
                    print(course_gen_id)
                    writer.writerow([course_gen_id, course["id"],f"{semester[0:2].lower()}{year[2:4]}", course["name"]])



"""