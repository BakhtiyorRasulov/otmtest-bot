import pandas as pd
import json
from tgproj.settings import BASE_DIR


def read_csv(csv_file):
    cfile = pd.read_csv(csv_file)
    return cfile


def translate(specs):
    with open(BASE_DIR + "/tgapp/tools/sLang.json", encoding="utf-8") as jfile:
        data = json.load(jfile)
        specs = data[specs]   
    return specs

def sort(cfile, lang, typ, fsub, ssub):
    new_cfile = cfile.loc[cfile["Lang"] == lang]
    new_cfile = new_cfile.loc[new_cfile["Type"] == typ]
    new_cfile = new_cfile.loc[new_cfile["FirstSub"] == fsub]
    new_cfile = new_cfile.loc[new_cfile["SecondSub"] == ssub]
    return new_cfile


def find_result(cfile, isScholar, point):
    new_cfile = cfile.loc[cfile[isScholar] <= round(point * 100 / 280.5)]
    if point > 270:
        cfile = cfile.sort_values(by=[isScholar], ascending=False).iloc[:20]
        return cfile
    elif len(new_cfile) >= 1:
        new_cfile.sort_values(by=[isScholar], ascending=False)
        if len(new_cfile) > 5:
            new_cfile = new_cfile.iloc[:20]
        return new_cfile
    else:
        return []


def normalize(results, isScholar, lang):
    sResult = ""   
    for i in range(len(results)):
        sResult += "{}. {}: {}\n".format(i+1, results["UniverName"].iloc[i].replace('Va', 'va'),
        results["Name"].iloc[i])
    
    return sResult


def getResult(point, lang, typ, specs):
    cfile = read_csv(BASE_DIR + "/tgapp/tools/data.csv")
    grant_result = ''
    contr_result = ''
    if lang == 'ru':
        specs = translate(specs)
    for isScholar in ["PSchol", "PCont"]:
        results = sort(cfile, lang, typ, specs.split('-')[0], specs.split('-')[1])
        results = find_result(results, isScholar, float(point))
        if len(results) !=0 :
            if isScholar == "PSchol":
                grant_result = normalize(results, isScholar, lang)
            else:
                contr_result = normalize(results, isScholar, lang)

    return grant_result, contr_result
