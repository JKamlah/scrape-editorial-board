#!/usr/bin/env python3
# import sys
# import argparse
from lxml import html as etree
from zipfile import ZipFile
import re
import csv


def text(xpathArray):
    if len(xpathArray) > 0:
        return xpathArray[0].text_content().strip()
    else:
        return ""

def isPerson(text):
    # this is very rough at the moment...
    text = text.strip()
    titles =  ["Prof", "Professor", "Dr", "DPhil", "PhD", "MD", "Mr", "Mrs"]
    firstWord = text.split(" ")[0].replace(".", "")
    lastWord = text.split(" ")[-1].replace(".", "")
    return ((firstWord in titles) or (lastWord in titles))


def isInstitution(text):
    text = text.strip().lower()
    return (("university" in text) or ("department" in text) or ("dept" in text)
            or ("institution" in text) or ("hospital" in text)
            or ("college" in text) or ("school" in text)
            or ("institute" in text) or ("center" in text))


def isRoleName(text):
    text = text.strip(" :").lower()
    text = re.sub("s?[:.]?$", "", text)
    roleNames = [
        "advisory board",
        "advisory editor",
        "articles editor",
        "associate editor",
        "associate managing editor",
        "board of field editor",
        "chair of the international editorial board",
        "consulting editor",
        "decision editor",
        "deputy editor",
        "deputy editor for science",
        "deputy editors in chief",
        "deputy editors-in-chief",
        "editor",
        "editorial board",
        "editor in chief",
        "editor-in-chief",
        "editors-in-chief",
        "editorial advisory board",
        "editorial assistant",
        "editorial coordinator",
        "editorial manager",
        "editorial office",
        "editorial secretary",
        "emeritus editor",
        "executive editor",
        "executive editors-in-chief",
        "field editor",
        "former editor",
        "founding editor",
        "honorary advisory board",
        "honorary editor-in-chief",
        "international executive advisory board",
        "journal editorial board",
        "journal manager",
        "managing editor",    
        "members of the editorial board",
        "past editors-in-chief",
        "peer-review coordinator",
        "president",
        "production editor",
        "publisher",
        "reviews editor",
        "reviewing editor",
        "scientific editor",
        "scientific advisory board",
        "section editor",
        "senior editor",
        "trainee advisory board",
        "vice president"
    ]
    return (text in roleNames)


with open('wiley.csv', 'w', encoding="utf-8", newline='') as writeFile:
    f = csv.writer(writeFile)
    f.writerow(["ID", "Title", "Name", "Affiliation", "Role"])
    with ZipFile("wiley_result.zip", 'r') as zip:
        # Use for testing
        for fileName in zip.namelist():#[:50]:
        # for fileName in zip.namelist():
            if ".html" not in fileName:
                continue
            with zip.open(fileName) as file:
                # replace br with newlines such that we can easier parse that
                content = file.read().decode('utf-8').replace("<br>", "\n")
                html = etree.fromstring(content)
                journal = text(html.xpath('//title'))
                role = ""

                main = html.xpath('//*[contains(@class, "main-content")]')
                if len(main) != 1 or text(main) == "":
                    # use .row instead if no .main-content is found
                    main = html.xpath('//*[contains(@class, "row")]')
                if len(main) != 1 or text(main) == "":
                    print("WARNING: main/row not found or empty " + fileName)
                    continue
                else:
                    main = main[0]
                
                # substitute table structure with paragraphs
                if len(main.xpath('.//table')) > 0:
                    cells = main.xpath('.//td')
                    for cell in cells:
                        if len(cell.xpath('.//p')) == 0:
                            parent = cell.getparent()
                            newNode = etree.Element("p")
                            newNode.append(cell)
                            parent.append(newNode)
                
                paragraphs = main.xpath('.//p')
                
                # we treat consecutive new lines (resulting from <br>s)
                # also as delimiter for new paragraphs
                paragraphsExtended = []
                for par in paragraphs:
                    if re.search("\n\s*\n", par.text_content().strip()):
                        paragraphsExtended.extend(
                            re.split(r"\s*\n\s*\n\s*", par.text_content().strip())
                        )
                    else:
                        paragraphsExtended.append(par.text_content().strip())
                
                for par in paragraphsExtended:
                    lines = par.split("\n")
                    # check whether we have to split into lines 
                    # which then must contain information of the
                    # form "name, affiliation" resp. "editorial role"
                    nonsplittable = 0
                    for line in lines:
                        if isRoleName(line):
                            continue
                        if "," not in line and "(" not in line:
                            nonsplittable += 1
                        elif isInstitution(line.replace("(", ",").split(",")[0]):
                            nonsplittable += 1
                        elif re.match(r"^\s*[0-9]+", line):
                            nonsplittable += 1
                    if nonsplittable >= len(lines) / 2 and len(lines) < 10:
                        # if most of the individual lines are nonsplittable
                        # then we assume that these lines belong together
                        # e.g. as adress lines for an editor
                        nlines = []
                        remaining = []
                        for line in lines:
                            # append any role immediately but collect all the
                            # other lines to be added as last element
                            if isRoleName(line):
                                nlines.append(line)
                                continue
                            if line.strip() != "":
                                remaining.append(line)
                        if len(remaining) > 0:
                            nlines.append(",".join(remaining))
                        lines = nlines
                            
                    for line in lines:
                        if line.strip() == "":
                            continue
                        if isRoleName(line):
                            role = line
                            continue
                        # substitute final parenthesis with comma if it
                        # contains the affiliation information
                        parentheses = re.match(r"^(.*)\((.*)\)$", line.strip())
                        if parentheses:
                            if isInstitution(parentheses.group(2)):
                                line = parentheses.group(1) + ", " + parentheses.group(2)
                        # split lines by comma and take the first part as
                        # name and everything else as the affiliation
                        parts = line.split(",")
                        if len(parts) == 1:
                            if isPerson(line):
                                f.writerow([fileName, journal, line, "", role])
                            elif "@" not in line:
                                print("WARNING: nothing to split found in " + line)
                        else:
                            name = parts[0].strip()
                            affiliation = ",".join(parts[1:]).strip()
                            f.writerow([fileName, journal, name, affiliation, role])

