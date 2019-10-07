#!/usr/bin/env python3
import sys
import argparse
import time
from collections import defaultdict
from lxml import html as etree
import requests
import json
import re
import csv
import pandas as pd
import os


def duration_string(sec):
    """Formats a time interval to a readable string"""
    sec = float(int(sec))
    if sec > 60 * 60 * 24:
        return "%.1f days" % (sec / float(60 * 60 * 24))
    if sec > 60 * 60:
        return "%.1f hours" % (sec / float(60 * 60))
    if sec > 60:
        return "%.1f minutes" % (sec / float(60))
    return "%d seconds" % sec


def extract_info(items, journal, pattern):
    """Extracts journal titel, subtitle and reference text"""
    info = []
    # Get journal titel and subtitle
    title = items[0].xpath(f'preceding::a[@href="/journal/{journal["id"]}"]')
    if not title:
        title = journal["title"]
    else:
        title = title[0].text
    subtitle = items[0].xpath(f'preceding::p[@class="c-journal-header__subtitle"]')
    if not subtitle:
        subtitle = ""
    else:
        subtitle = subtitle[0].text
    for item in items:
        text = item.text_content()
        text = re.sub(r"\s+", " ", text)
        if text is None:
            continue
        findings = re.finditer(fr'{pattern}', text)
        for finding in findings:
            start = finding.start() - 50 if finding.start() > 50 else 0
            end = finding.end() + 30 if finding.end() < len(text) else len(text)
            info.append({
                "id": journal["id"],
                "title": title,
                "subtitle": subtitle,
                "reference": "[..]" + text[start:end] + "[..]"
            })
    return info


def find_refs(publisher, html, pattern):
    """Search for references with pattern"""
    html = etree.fromstring(html.text)
    if publisher != "elsevier":
        res = html.xpath(f'.//p[contains(.,"{pattern}")]')
    else:
        res = html.xpath(f'.//div[@class="publication"]')
        if pattern not in res[0].text_content():
            res = []
    if res:
        return res
    return None


def request_html(url):
    session = requests.Session()
    try:
        response = session.get(url)
        return response
    except requests.exceptions.RequestException as e:
        if args.verbose:
            sys.stderr.write("Error: %s.\n" % e)
        pass
    except Exception as e:
        print(f"Error occurred while html request: {e}")
        pass
    return


def output(publisher, journals):
    results = defaultdict()
    for journal in journals:
        if journal['results']:
            results[journal['id']] = journal["results"]
    resdir = f"./editorialboard/results/"
    if not os.path.exists(resdir):
        os.mkdir(resdir)
    with open(f'{resdir}{publisher}.json', 'w', encoding="utf-8") as writeFile:
        json.dump(results, writeFile, indent=4, ensure_ascii=False)
    with open(f'{resdir}{publisher}.csv', 'w', encoding="utf-8", newline='') as writeFile:
        f = csv.writer(writeFile)
        # Write CSV Header, If you dont need that, remove this line
        f.writerow(["ID", "Title", "Subtitle", "Reference"])
        for idx, result in results.items():
            for ref in result:
                f.writerow([ref["id"], ref["title"], ref["subtitle"], ref["reference"]])


def store_html(journal, publisher, html):
    htmldir = f"./editorialboard/html/{publisher}/"
    if not os.path.exists(htmldir):
        os.makedirs(htmldir)
    with open(htmldir + f"/{journal['id']}.html", "w") as f:
        f.write(html.text)
    return


def elsevier_journals(args):
    journals = []
    journaldf = pd.read_excel(args.publisherfile, sheet_name="Europe", header=0, dtype=str)
    journaldf = journaldf.dropna(subset=["Journal Title"])
    for row in journaldf.iterrows():
        id = row[1]["Journal No."]
        title = row[1].get("Journal Title", "")
        journals.append(
            {"id": id,
             "url": f"https://www.journals.elsevier.com/{title.replace(' - ', '-').replace(' ', '-')}/editorial-board",
             "title": title, "results": []})
    return journals


def springer_journals(args):
    journals = []
    journaldf = pd.read_excel(args.publisherfile, sheet_name="list", header=5, dtype=str)
    journaldf = journaldf.dropna(subset=["product_id"])
    for row in journaldf.iterrows():
        id = row[1]["product_id"]
        title = row[1].get("Title", "")
        journals.append(
            {"id": id, "url": f"https://beta.springer.com/journal/{id}/editors", "title": title, "results": []})
    return journals


def wiley_journals(args):
    journals = []
    journaldf = pd.read_excel(args.publisherfile, sheet_name="Included", header=3, dtype=str)
    journaldf = journaldf.dropna(subset=["Journal Homepage URL"])
    for row in journaldf.iterrows():
        id = row[1]["eISSN"]
        title = row[1].get("Title", "")
        journals.append(
            {"id": id, "url": f"{row[1].get('Journal Homepage URL', '')}/homepage/editorialboard.html".replace(".com",
                                                                                                               ".com/page"),
             "title": title, "results": []})
    return journals


def main(args):
    # init results
    starttime = time.time()
    jobs = 0

    publisher = args.publisherfile.split("_")[0]
    publisher_journals = {
        "elsevier": elsevier_journals,
        "springer": springer_journals,
        "wiley": wiley_journals,
    }
    journals = publisher_journals.get(publisher, [])(args)
    # the main loop
    for journal in journals:
        url = journal["url"]
        html = request_html(url)
        if html is not None and html.status_code == 200:
            store_html(journal, publisher, html)
            items = find_refs(publisher, html, args.pattern)
            if items is not None:
                result = extract_info(items, journal, args.pattern)
                if result is not None:
                    journal["results"] = result
        jobs += 1
        # display some progress stats
        if True:
            if jobs > 0 and jobs % 10 == 0:
                duration = time.time() - starttime
                seconds_per_job = duration / jobs
                c = len(journals) - jobs
                print("Resolved %d jobs in %s. %d jobs, %s remaining" % (
                    jobs, duration_string(duration), c, duration_string(seconds_per_job * c)))
            if jobs > 0 and jobs % 500 == 0:
                output(publisher, journals)
    output(publisher, journals)


if __name__ == "__main__":
    # set up command line options
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "-f", "--publisherfile", dest="publisherfile",
        type=str, default="elsevier_journals_2019.xlsx",
    )
    argparser.add_argument(
        "-p", "--pattern", dest="pattern",
        type=str, default="Mannheim",
    )
    argparser.add_argument(
        "-v", "--verbose", dest="verbose", action="store_true",
        help="Give verbose output"
    )
    args = argparser.parse_args()
    main(args)
