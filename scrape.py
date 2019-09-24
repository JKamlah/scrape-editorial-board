#!/usr/bin/env python3
import sys
import argparse
import random
import time
from collections import defaultdict
from lxml import html as etree
import requests
import json

def wait(t):
    """Wait for a random time interval"""
    time.sleep(t)

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

def extract_info(items,journalidx):
    info = []
    title = items[0].xpath(f'preceding::a[@href="/journal/{journalidx}"]')
    if not title:
        title = ""
    else:
        title = title[0].text
    subtitle = items[0].xpath(f'preceding::p[@class="c-journal-header__subtitle"]')
    if not subtitle :
        subtitle = ""
    else:
        subtitle = subtitle[0].text
    for item in items:
        if item.text_content() is None:
            continue
        itemparts = item.text_content().split(",")
        position = item.xpath("preceding::b")
        if not position:
            position = ""
        else:
            position = position[-1].text
        if True:
            info.append({"journal": title,
                         "journalsubtitle": subtitle,
                         "positions": position,
                         "name": item.text_content()})
        elif len(itemparts) == 1:
            info.append({"journal":title,
                         "journalsubtitle":subtitle,
                        "positions":position,
                         "name": itemparts[0]})
        elif len(itemparts) == 3:
            info.append({"journal":title,
                         "journalsubtitle":subtitle,
                         "positions":position,
                         "name":itemparts[0],
                         "institution":itemparts[1],
                         "country":itemparts[2]})
        elif len(itemparts) == 5:
            info.append({"journal":title,
                         "journalsubtitle":subtitle,
                         "positions":position,
                         "name":itemparts[0],
                         "institution":itemparts[1],
                         "city":itemparts[2],
                         "federal state":itemparts[3],
                         "country":itemparts[4]})
    return info

def find_item(html,pattern):
    html = etree.fromstring(html.text)
    res = html.xpath(f'.//p[contains(.,"{pattern}")]')
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
        return 


def main(args):
     # init results
    results = defaultdict()
    starttime = time.time()
    jobs = 0

    # the main loop
    for idx in range(args.startindex,args.endindex):
        url = f"https://beta.springer.com/journal/12186/editors"
        #url = f"https://beta.springer.com/journal/{idx}/editors"
        html = request_html(url)
        if html is not None:
            items = find_item(html,args.pattern)
            if items is not None:
                result = extract_info(items,idx)
                if result is not None:
                    results[idx] = result
        jobs += 1
        # display some progress stats
        if True:
            if jobs > 0 and jobs % 10 == 0:
                duration = time.time() - starttime
                seconds_per_job = duration / jobs
                c = (args.endindex-args.startindex)-jobs
                print("Resolved %d jobs in %s. %d jobs, %s remaining" % (
                    jobs, duration_string(duration), c, duration_string(seconds_per_job * c)))
    with open('results.json', 'w',encoding="utf-8") as writeFile:
         json.dump(results,writeFile, indent=4)
    #with open('results.csv', 'w') as writeFile:
    #    import csv
    #    f = csv.writer(writeFile)
    #    # Write CSV Header, If you dont need that, remove this line
    #    f.writerow(["Journalidx", "Journaltitle", "Journalsubtitle", "Info"])


if __name__ == "__main__":
    # set up command line options
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-p", "--pattern", dest="pattern",
       type=str, default="Mannheim",
         help="")
    argparser.add_argument("-s", "--startindex", dest="startindex",
         type=int, default=12000,
         help="Scraping startindex")
    argparser.add_argument("-e", "--endindex", dest="endindex",
         type=int, default=13000,
         help="Scraping endindex")
    argparser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
        help="Give verbose output")
    args = argparser.parse_args()
    main(args)
