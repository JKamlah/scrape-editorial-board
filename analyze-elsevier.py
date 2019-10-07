#!/usr/bin/env python3
import sys
import argparse
#import time
#from collections import defaultdict
from lxml import html as etree
from zipfile import ZipFile
#import requests
#import json
#import re
import csv


def text(xpathArray):
    if len(xpathArray) > 0:
        return xpathArray[0].text_content().strip()
    else:
        return ""

with open('elsevier.csv', 'w', encoding="utf-8", newline='') as writeFile:
    f = csv.writer(writeFile)
    f.writerow(["ID", "Title", "Name", "Affiliation", "Role"])
    with ZipFile("elsevier_result.zip", 'r') as zip:
        # Use for testing
        # for fileName in zip.namelist()[:10]:
        for fileName in zip.namelist():
            if ".html" not in fileName:
                continue
            with zip.open(fileName) as file:
                content = file.read()
                html = etree.fromstring(content)
                journal = ''
                if len(html.xpath('//h1')) > 0:
                    journal = html.xpath('//h1')[0].text.replace("- Editorial Board", "").strip()
                editors = html.xpath('//*[@class="publication-editor"]')
                if len(editors) == 0:
                    print("WARNING: No editors found in " + fileName)
                for editor in editors:
                    name = text(editor.xpath('./*[contains(@class, "publication-editor-name")]'))
                    affiliation = text(editor.xpath('./*[contains(@class, "publication-editor-affiliation")]'))
                    role = text(editor.xpath('./preceding::*[contains(@class, "publication-editor-type")][1]'))
                    f.writerow([fileName, journal, name, affiliation, role])
