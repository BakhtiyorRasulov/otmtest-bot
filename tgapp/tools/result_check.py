import os
import json
from django.conf import settings
import telegram
from .codes import root_path

def get_file(query_data, random_num):
    answer_file = open(root_path + '/answers/{}/{}.json'.format(
        query_data ,random_num))
    answers_data = json.load(answer_file)
    answers = answers_data['answers']
    answer_file.close()

    return answers


def makeStringToList(anystring):
    anystring = list(anystring)
    returnString = []
    for i in anystring:
        returnString.append([i, True])
    return returnString


def normalize(anylist):
    for i in range(len(anylist)):
        anylist[i] = anylist[i].replace('.', '')

    return anylist


def calculate_point(answers, user_answers):
    point = 0
    for i in range(len(answers)):
        try:
            if answers[i][-1] == user_answers[i][0].upper():
                if i < 45:
                    point += 2.1
                else:
                    point += 3.1
            else:
                    user_answers[i][1] = False
        except IndexError:
            pass

    return point, user_answers


def getPoint(person_lang, query_data, random_num, user_answers):
    answers = get_file(query_data, random_num)
    answers = normalize(answers)
    user_answers = makeStringToList(user_answers)
    point, user_answers = calculate_point(answers, user_answers)

    return point, user_answers
