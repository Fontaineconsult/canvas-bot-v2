import requests
import json

# test = requests.get("https://sfsu.instructure.com/api/v1/courses/18411/modules/178737/items/1421214?access_token=21165~52wEZ0DokOqALLje597gj9vC7KVsP7g9LThae0OHk5a62QnbCFK94w0WCxSZ1ISB")
# print(test.content)


# test = requests.get("https://sfsu.instructure.com/api/v1/courses/18411/modules?access_token=21165~52wEZ0DokOqALLje597gj9vC7KVsP7g9LThae0OHk5a62QnbCFK94w0WCxSZ1ISB")
# print(test.content)
#
# stuff = json.loads(test.content)
#
# for each in stuff:
#     print(each)


assignments = requests.get("https://sfsu.instructure.com/api/v1/courses/18411/modules?21165~52wEZ0DokOqALLje597gj9vC7KVsP7g9LThae0OHk5a62QnbCFK94w0WCxSZ1ISB")
stuff1 = json.loads(assignments.content)

for each in stuff1:
    print(each)